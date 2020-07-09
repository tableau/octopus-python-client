import json
import logging
from pprint import pformat

from octopus_python_client.common import item_type_deployment_processes, item_type_projects, id_key, \
    deployment_process_id_key, item_type_channels, packages_key, action_name_key, package_reference_name_key, Common, \
    feed_id_key, package_id_key, item_type_feeds, item_type_packages, version_key, items_key, name_key, timestamp_key, \
    value_key, project_id_key, next_version_increment_key, release_notes_key, channel_id_key, selected_packages_key, \
    item_type_releases, item_type_deployments, item_type_tenants, item_type_environments, tenant_id_key, newline_sign, \
    environment_id_key, release_id_key, comments_key, release_versions_key, url_prefix_key, dot_sign, sha_key, \
    author_key, latest_commit_sha_key, title_key
from octopus_python_client.config import Config
from octopus_python_client.utilities.helper import replace_list_new_value, parse_string, find_item
from octopus_python_client.utilities.send_requests_to_octopus import operation_post

logger = logging.getLogger(__name__)


class ReleaseDeployment:
    def __init__(self, config: Config, project_name, channel_name=None, notes=None):
        self._config = config
        self._common = Common(config=self._config)

        assert project_name, "project name must not be empty!"
        project = self._common.get_single_item_by_name(item_type=item_type_projects, item_name=project_name)
        assert project, f"Project {project_name} cannot be found or you do not have permission to access!"
        self._project_id = project.get(id_key)
        self._deployment_process_id = project.get(deployment_process_id_key)
        self._notes = notes
        self._release_request_payload = {project_id_key: self._project_id, release_notes_key: notes}

        self._channel_id = ""
        if channel_name:
            channel = self._common.find_sub_by_item(item_type=item_type_projects, item_id=self._project_id,
                                                    sub_type=item_type_channels, sub_name=channel_name)
            assert channel, f"Cannot find channel {channel_name} in project {project_name}"
            self._channel_id = channel.get(id_key)
        if self._channel_id:
            self._release_request_payload[channel_id_key] = self._channel_id

        # package versions read from a variable set,
        # e.g. release_versions = {"Name": "package.near", "Value": "20.0225.1714"}
        self._packages_variable_set_name = None
        # user selected package versions, e.g. "{'packages': {'package.near': '20.0225.1714'}}"
        self._package_version_dict = None

        self._template = None
        self._selected_packages = None
        self._release_response = None
        self._release_id = None
        self._commits_variable_set_name = "configuration_commits" + dot_sign + project_name
        self._gitlab_url_prefix = self._get_url_prefix(set_name="gitlab_info")
        self._latest_commit_dict = None

    def _get_url_prefix(self, set_name):
        info_service_list_variables = self._common.get_list_variables_by_set_name_or_id(set_name=set_name)
        if info_service_list_variables:
            url_prefix_variable = find_item(lst=info_service_list_variables, key=name_key, value=url_prefix_key)
            if url_prefix_variable:
                return url_prefix_variable.get(value_key)
        return ""

    def _get_deployment_process_template(self):
        logger.info(f"Fetching deployment process template from {self._deployment_process_id} with channel "
                    f"{self._channel_id} in {self._config.space_id}, which is used for defining release and deployment")
        address = f"{item_type_deployment_processes}/{self._deployment_process_id}/template?channel=" \
                  f"{self._channel_id}"
        self._template = self._common.request_octopus_item(address=address)

    def _get_selected_packages(self):
        logger.info(f"getting package information for each step")
        self._selected_packages = []
        for package in self._template.get(packages_key):
            logger.info(f"getting package information for {package.get(action_name_key)} with package "
                        f"{package.get(package_reference_name_key)}")
            address = f"{item_type_feeds}/{package.get(feed_id_key)}/{item_type_packages}/versions?packageId=" \
                      f"{package.get(package_id_key)}&take=1"
            package_detail = self._common.request_octopus_item(address=address)
            selected_package = {action_name_key: package.get(action_name_key),
                                package_reference_name_key: package.get(package_reference_name_key),
                                version_key: package_detail.get(items_key)[0].get(version_key)}
            self._selected_packages.append(selected_package)

    def _update_package_version(self, package, version):
        match_dict = {package_reference_name_key: package}
        replace_dict = {version_key: version}
        replace_list_new_value(lst=self._selected_packages, match_dict=match_dict, replace_dict=replace_dict)

    def _update_selected_packages(self):
        logger.info("update package versions...")
        if self._packages_variable_set_name:
            list_release_versions = self._common.get_list_variables_by_set_name_or_id(
                set_name=self._packages_variable_set_name)
            for package_version in list_release_versions:
                self._update_package_version(package=package_version.get(name_key),
                                             version=package_version.get(value_key))
        if self._package_version_dict:
            for package, version in self._package_version_dict.items():
                self._update_package_version(package=package, version=version)

    def _form_single_commit_note(self, commit_variable):
        date_time = commit_variable.get(name_key)
        commit_json = commit_variable.get(value_key)
        commit_dict = json.loads(commit_json)
        title = ". ".join(commit_dict.get(title_key)) if isinstance(commit_dict.get(title_key), list) else \
            str(commit_dict.get(title_key))
        return f"- {date_time} - [{title}]({self._gitlab_url_prefix}" \
               f"{commit_dict.get(sha_key)}) - {commit_dict.get(author_key)}"

    def _get_prev_release_match_commit_date_time(self, list_releases: list):
        if list_releases:
            for release in list_releases:
                logger.info(f"checking {release.get(id_key)} for project {self._project_id}...")
                if release.get(release_notes_key):
                    logger.info(f"found notes in {release.get(id_key)} and try to get the commit timestamp...")
                    notes_last_line = release.get(release_notes_key).splitlines()[-1]
                    last_line_parsed = parse_string(local_logger=logger, string=notes_last_line)
                    if isinstance(last_line_parsed, dict) and last_line_parsed.get(self._commits_variable_set_name):
                        prev_release_match_commit_date_time = last_line_parsed.get(self._commits_variable_set_name)
                        topic_note = f"\nThe previous release with the commit timestamp " \
                                     f"{prev_release_match_commit_date_time} is {release.get(id_key)} " \
                                     f"(release version: {release.get(version_key)}). "
                        logger.info(topic_note)
                        return topic_note, prev_release_match_commit_date_time
                    else:
                        logger.warning(f"the commit timestamp in {release.get(id_key)} not exist")
                else:
                    logger.warning(f"{release.get(id_key)} has no release notes")
            topic_note = f"\nNo previous release with the commit timestamp in notes was found"
            logger.warning(topic_note)
            return topic_note, ""
        else:
            topic_note = f"\nThis is the first release for project {self._project_id}. "
            logger.info(topic_note)
            return topic_note, ""

    def _generate_commits_notes(self):
        logger.info("generating the release notes for the commits history")
        # find the latest/previous release for this project
        list_releases = self._common.get_project_releases_sorted_list(project_id=self._project_id)
        topic_note, prev_release_match_commit_date_time = \
            self._get_prev_release_match_commit_date_time(list_releases=list_releases)
        list_notes = ["\n========== below is auto-generated notes ==========", topic_note]

        # historical commits since the latest release
        list_configuration_commits = self._common.get_list_variables_by_set_name_or_id(
            set_name=self._commits_variable_set_name)
        if not list_configuration_commits:
            msg = f"\nVariable set {self._commits_variable_set_name} contains NONE historical commits. No commits " \
                  f"can be matched to the releases."
            logger.error(msg)
            list_notes.append(msg)
            return newline_sign.join(list_notes)

        list_configuration_commits_sorted = sorted(list_configuration_commits, key=lambda k: k.get(name_key))
        list_commit_notes = []
        latest_commit_variable = None
        for commit_variable in list_configuration_commits_sorted:
            latest_commit_variable = commit_variable
            commit_note = self._form_single_commit_note(commit_variable=commit_variable)
            list_commit_notes.append(commit_note)
            # if prev release has no matched commit or the commit could not be found, append all commits
            # once the prev release matched commit is found, only append the commits after it
            if prev_release_match_commit_date_time == commit_variable.get(name_key):
                logger.info(f"found a matched timestamp {prev_release_match_commit_date_time} in commits history, "
                            f"so will start to record all the commits after it")
                list_commit_notes = []
        list_notes.append("\nThe gitlab commits since the previous release are: ")
        if not list_commit_notes:
            list_notes.append("None")
        else:
            list_commit_notes.reverse()
            list_notes.extend(list_commit_notes)

        # matched latest commit for the current release
        if latest_commit_variable:
            latest_timestamp = latest_commit_variable.get(name_key)
            self._latest_commit_dict = json.loads(latest_commit_variable.get(value_key))
            self._latest_commit_dict[timestamp_key] = latest_timestamp
            latest_commit_note = self._form_single_commit_note(commit_variable=latest_commit_variable)
            list_notes.append(f"\nThe matched latest gitlab commit for this release is {latest_commit_note}")
            list_notes.append(f"\nBelow is a python dictionary read by Octopus python client in the succeeding "
                              f"releases to identify the gitlab commit for the preceding release and it must be the "
                              f"last line in the release notes. '{self._commits_variable_set_name}' is the variable "
                              f"set name for the commits history and the value is the matched commit timestamp for "
                              f"this release")
            list_notes.append("\n{'" + f"{self._commits_variable_set_name}" + "': '" + f"{latest_timestamp}" + "'}")
        return newline_sign.join(list_notes)

    def _process_notes(self):
        logger.info("process notes...")
        notes = parse_string(local_logger=logger, string=self._notes)
        if isinstance(notes, dict):
            logger.info("the notes is a dictionary, so further process...")
            logger.info(pformat(notes))
            self._packages_variable_set_name = notes.get(release_versions_key)
            self._package_version_dict = notes.get(item_type_packages)
            self._update_selected_packages()
        commit_notes = self._generate_commits_notes()
        if self._notes:
            self._release_request_payload[release_notes_key] = newline_sign.join([self._notes, commit_notes])
        else:
            self._release_request_payload[release_notes_key] = commit_notes

    def _process_package_versions_notes(self):
        self._get_deployment_process_template()
        self._get_selected_packages()
        self._process_notes()

    # release version must be unique for each release
    def create_release(self, release_version=None):
        self._process_package_versions_notes()
        if not release_version:
            release_version = self._template.get(next_version_increment_key)
        self._release_request_payload[version_key] = release_version
        self._release_request_payload[selected_packages_key] = self._selected_packages
        logger.info("the request release payload is")
        logger.info(pformat(self._release_request_payload))
        self._release_response = self._common.request_octopus_item(address=item_type_releases,
                                                                   payload=self._release_request_payload,
                                                                   operation=operation_post)
        if self._latest_commit_dict:
            self._release_response[latest_commit_sha_key] = self._latest_commit_dict.get(sha_key)
        logger.info("the response release payload is")
        logger.info(pformat(self._release_response))
        self._common.save_single_item(item_type=item_type_releases, item=self._release_response)
        self._release_id = self._release_response.get(id_key)
        return self._release_response

    @staticmethod
    def create_deployment_direct(config: Config, environment_name, tenant_name, release_id=None, project_name=None,
                                 comments=None):
        logger.info(f"creating a deployment for {release_id} in space {config.space_id} with environment "
                    f"{environment_name}, tenant {tenant_name} and comments: {comments}")
        common = Common(config=config)

        # TODO project_name
        assert (release_id or project_name), "either release_id or project_name must exist!"
        assert environment_name, "environment_name must not be empty!"
        assert tenant_name, "tenant_name must not be empty!"

        if not release_id:
            logger.info(f"Get the latest release id for project {project_name}")
            project_id = common.get_item_id_by_name(item_type=item_type_projects, item_name=project_name)
            releases_list = common.get_project_releases_sorted_list(project_id=project_id)
            if not releases_list:
                raise ValueError(f"Project {project_name} does not have any releases. Please create a release first")
            release_id = releases_list[0].get(id_key)
            logger.info(f"The latest release id is {release_id}")

        deployment_request_payload = \
            {release_id_key: release_id,
             environment_id_key: common.get_item_id_by_name(item_type=item_type_environments,
                                                            item_name=environment_name),
             tenant_id_key: common.get_item_id_by_name(item_type=item_type_tenants, item_name=tenant_name),
             comments_key: comments}
        logger.info("the request deployment payload is")
        logger.info(pformat(deployment_request_payload))
        deployment_response_payload = common.request_octopus_item(address=item_type_deployments,
                                                                  payload=deployment_request_payload,
                                                                  operation=operation_post)
        logger.info("the response deployment payload is")
        common.log_info_print(local_logger=logger, msg=json.dumps(deployment_response_payload))
        common.save_single_item(item_type=item_type_deployments, item=deployment_response_payload)
        return deployment_response_payload

    def create_deployment_for_current_release(self, config, environment_name=None, tenant_name=None, comments=None):
        return ReleaseDeployment.create_deployment_direct(config=config, release_id=self._release_id,
                                                          environment_name=environment_name, tenant_name=tenant_name,
                                                          comments=comments)

    @property
    def release_id(self):
        logger.info(f"get the release id {self._release_id}")
        return self._release_id

    @property
    def release_response(self):
        logger.info(f"get the release response for {self._release_id}")
        return self._release_response

    def _extract_package_versions(self):
        package_versions_dict = {}
        for package in self._selected_packages:
            if package.get(package_reference_name_key):
                package_versions_dict[package.get(package_reference_name_key)] = package.get(version_key)
        return package_versions_dict

    @staticmethod
    def get_package_versions(config: Config, project_name, channel_name=None, notes=None):
        release = ReleaseDeployment(config=config, project_name=project_name, channel_name=channel_name, notes=notes)
        release._process_package_versions_notes()
        return release._extract_package_versions()

    @staticmethod
    def create_release_direct(config: Config, release_version, project_name, channel_name=None, notes=None):
        common = Common(config=config)
        release = ReleaseDeployment(config=config, project_name=project_name, channel_name=channel_name, notes=notes)
        release.create_release(release_version=release_version)
        common.log_info_print(local_logger=logger, msg=json.dumps(release.release_response))
        return release

    @staticmethod
    def create_release_deployment(config: Config, release_version, project_name, comments, channel_name=None,
                                  notes=None, environment_name=None, tenant_name=None):
        release = ReleaseDeployment.create_release_direct(
            config=config, release_version=release_version, project_name=project_name, channel_name=channel_name,
            notes=notes)
        return release.create_deployment_for_current_release(config=config, environment_name=environment_name,
                                                             tenant_name=tenant_name, comments=comments)
