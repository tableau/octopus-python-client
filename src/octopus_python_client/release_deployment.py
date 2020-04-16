import json
import logging
from pprint import pformat

import yaml

from octopus_python_client.common import request_octopus_item, item_type_deployment_processes, verify_space, \
    item_type_projects, get_single_item_by_name, id_key, deployment_process_id_key, item_type_channels, \
    find_sub_by_item, packages_key, action_name_key, package_reference_name_key, feed_id_key, package_id_key, \
    item_type_feeds, item_type_packages, version_key, items_key, get_list_variables_by_set_name_or_id, name_key, \
    value_key, project_id_key, next_version_increment_key, release_notes_key, channel_id_key, selected_packages_key, \
    item_type_releases, save_single_item, item_type_deployments, item_type_tenants, item_type_environments, \
    get_item_id_by_name, tenant_id_key, environment_id_key, release_id_key, comments_key, log_info_print, \
    release_versions_key, url_prefix_key, dot_sign, sha_key, author_key, newline_sign, get_list_items_from_all_items, \
    item_type_library_variable_sets, latest_commit_sha_key, timestamp_key
from octopus_python_client.utilities.helper import replace_list_new_value, parse_string, find_item
from octopus_python_client.utilities.send_requests_to_octopus import operation_post

logger = logging.getLogger(__name__)


class ReleaseDeployment:
    def __init__(self, project_name=None, channel_name=None, notes=None, space_id_name=None):
        assert space_id_name, "space name/id must not be empty!"
        assert project_name, "project name must not be empty!"

        self._space_id = verify_space(space_id_name=space_id_name)
        assert self._space_id, f"Space {space_id_name} cannot be found or you do not have permission to access!"

        project = get_single_item_by_name(item_type=item_type_projects, item_name=project_name,
                                          space_id=self._space_id)
        assert project, f"Project {project_name} cannot be found or you do not have permission to access!"
        self._project_id = project.get(id_key)
        self._deployment_process_id = project.get(deployment_process_id_key)
        self._notes = notes
        self._release_request_payload = {project_id_key: self._project_id, release_notes_key: notes}

        self._channel_id = ""
        if channel_name:
            channel = find_sub_by_item(item_type=item_type_projects, item_id=self._project_id,
                                       sub_type=item_type_channels, sub_name=channel_name, space_id=self._space_id)
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

    def _get_url_prefix(self, set_name=None):
        info_service_list_variables = get_list_variables_by_set_name_or_id(set_name=set_name,
                                                                           space_id=self._space_id)
        if info_service_list_variables:
            url_prefix_variable = find_item(lst=info_service_list_variables, key=name_key, value=url_prefix_key)
            if url_prefix_variable:
                return url_prefix_variable.get(value_key)
        return ""

    def _get_deployment_process_template(self):
        logger.info(f"Fetching deployment process template from {self._deployment_process_id} with channel "
                    f"{self._channel_id} in {self._space_id}, which is used for defining release and deployment")
        address = f"{item_type_deployment_processes}/{self._deployment_process_id}/template?channel=" \
                  f"{self._channel_id}"
        self._template = request_octopus_item(space_id=self._space_id, address=address)

    def _get_selected_packages(self):
        logger.info(f"getting package information for each step")
        self._selected_packages = []
        for package in self._template.get(packages_key):
            logger.info(f"getting package information for {package.get(action_name_key)} with package "
                        f"{package.get(package_reference_name_key)}")
            address = f"{item_type_feeds}/{package.get(feed_id_key)}/{item_type_packages}/versions?packageId=" \
                      f"{package.get(package_id_key)}&take=1"
            package_detail = request_octopus_item(space_id=self._space_id, address=address)
            selected_package = {action_name_key: package.get(action_name_key),
                                package_reference_name_key: package.get(package_reference_name_key),
                                version_key: package_detail.get(items_key)[0].get(version_key)}
            self._selected_packages.append(selected_package)

    def _update_package_version(self, package=None, version=None):
        match_dict = {package_reference_name_key: package}
        replace_dict = {version_key: version}
        replace_list_new_value(lst=self._selected_packages, match_dict=match_dict, replace_dict=replace_dict)

    def _update_selected_packages(self):
        logger.info("update package versions...")
        if self._packages_variable_set_name:
            list_release_versions = get_list_variables_by_set_name_or_id(set_name=self._packages_variable_set_name,
                                                                         space_id=self._space_id)
            for package_version in list_release_versions:
                self._update_package_version(package=package_version.get(name_key),
                                             version=package_version.get(value_key))
        if self._package_version_dict:
            for package, version in self._package_version_dict.items():
                self._update_package_version(package=package, version=version)

    def _form_single_commit_note(self, commit_variable=None):
        date_time = commit_variable.get(name_key)
        commit_yaml = commit_variable.get(value_key)
        commit_dict = yaml.safe_load(commit_yaml)
        return f"- {date_time} - {sha_key}: [{commit_dict.get(sha_key)}]({self._gitlab_url_prefix}" \
               f"{commit_dict.get(sha_key)}) - {commit_dict.get(author_key)}"

    def _generate_commits_notes(self):
        logger.info("generating the release notes for the commits history")
        # find the latest/previous release for this project
        logger.info(f"loading all releases from project {self._project_id}")
        address = f"{item_type_projects}/{self._project_id}/{item_type_releases}"
        releases = request_octopus_item(space_id=self._space_id, address=address)
        list_releases = get_list_items_from_all_items(all_items=releases)
        prev_release_match_commit_date_time = ""
        list_notes = ["\n========== below is auto-generated notes =========="]
        if list_releases:
            prev_release = max(list_releases, key=lambda release: release.get(id_key))
            logger.info(f"the latest release for project {self._project_id} is {prev_release.get(id_key)}")
            if prev_release.get(release_notes_key):
                logger.info(f"found the notes in the previous release {prev_release.get(id_key)} and try to get the"
                            f" commit timestamp...")
                notes_last_line = prev_release.get(release_notes_key).splitlines()[-1]
                last_line_parsed = parse_string(local_logger=logger, string=notes_last_line)
                if isinstance(last_line_parsed, dict) and last_line_parsed.get(self._commits_variable_set_name):
                    prev_release_match_commit_date_time = last_line_parsed.get(self._commits_variable_set_name)
                    logger.info(f"the commit timestamp in the previous release {prev_release.get(id_key)} is "
                                f"{prev_release_match_commit_date_time}")
                else:
                    logger.warning(f"the commit timestamp in the previous release {prev_release.get(id_key)} not exist")
            else:
                logger.warning(f"previous release {prev_release.get(id_key)} has no release notes")
            topic_note = f"\nThe previous release is {prev_release.get(id_key)} (release version: " \
                         f"{prev_release.get(version_key)}). "
        else:
            logger.info(f"project {self._project_id} has no existing releases")
            topic_note = f"\nThis is the first release for this project. "
        list_notes.append(topic_note)

        # historical commits since the latest release
        list_configuration_commits = get_list_variables_by_set_name_or_id(
            set_name=self._commits_variable_set_name, space_id=self._space_id)
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
            list_notes.extend(list_commit_notes)

        # matched latest commit for the current release
        if latest_commit_variable:
            latest_timestamp = latest_commit_variable.get(name_key)
            self._latest_commit_dict = yaml.safe_load(latest_commit_variable.get(value_key))
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
        if get_single_item_by_name(item_type=item_type_library_variable_sets,
                                   item_name=self._commits_variable_set_name, space_id=self._space_id):
            commit_notes = self._generate_commits_notes()
            self._release_request_payload[release_notes_key] = newline_sign.join([self._notes, commit_notes])

    # release version must be unique for each release
    def create_release(self, release_version=None):
        self._get_deployment_process_template()
        self._get_selected_packages()
        self._process_notes()
        if not release_version:
            release_version = self._template.get(next_version_increment_key)
        self._release_request_payload[version_key] = release_version
        self._release_request_payload[selected_packages_key] = self._selected_packages
        logger.info("the request release payload is")
        logger.info(pformat(self._release_request_payload))
        self._release_response = request_octopus_item(payload=self._release_request_payload, space_id=self._space_id,
                                                      address=item_type_releases, action=operation_post)
        if self._latest_commit_dict:
            self._release_response[latest_commit_sha_key] = self._latest_commit_dict.get(sha_key)
        logger.info("the response release payload is")
        logger.info(pformat(self._release_response))
        save_single_item(item_type=item_type_releases, item=self._release_response, space_id=self._space_id)
        self._release_id = self._release_response.get(id_key)
        return self._release_response

    @staticmethod
    def create_deployment_direct(release_id=None, environment_name=None, tenant_name=None, space_id_name=None,
                                 comments=None):
        logger.info(f"creating a deployment for {release_id} in space {space_id_name} with environment "
                    f"{environment_name}, tenant {tenant_name} and comments: {comments}")

        assert release_id, "release_id must not be empty!"
        assert space_id_name, "space id/name must not be empty!"
        assert environment_name, "environment_name must not be empty!"
        assert tenant_name, "tenant_name must not be empty!"

        space_id = verify_space(space_id_name=space_id_name)
        assert space_id, f"Space {space_id_name} cannot be found or you do not have permission to access!"

        deployment_request_payload = {release_id_key: release_id,
                                      environment_id_key: get_item_id_by_name(item_type=item_type_environments,
                                                                              item_name=environment_name,
                                                                              space_id=space_id),
                                      tenant_id_key: get_item_id_by_name(item_type=item_type_tenants,
                                                                         item_name=tenant_name,
                                                                         space_id=space_id),
                                      comments_key: comments}
        logger.info("the request deployment payload is")
        logger.info(pformat(deployment_request_payload))
        deployment_response_payload = request_octopus_item(payload=deployment_request_payload, space_id=space_id,
                                                           address=item_type_deployments, action=operation_post)
        logger.info("the response deployment payload is")
        log_info_print(local_logger=logger, msg=json.dumps(deployment_response_payload))
        save_single_item(item_type=item_type_deployments, item=deployment_response_payload, space_id=space_id)
        return deployment_response_payload

    def create_deployment_for_current_release(self, environment_name=None, tenant_name=None, comments=None):
        return self.create_deployment_direct(
            release_id=self._release_id, environment_name=environment_name, tenant_name=tenant_name,
            space_id_name=self._space_id, comments=comments)

    @property
    def release_id(self):
        logger.info(f"get the release id {self._release_id}")
        return self._release_id

    @property
    def release_response(self):
        logger.info(f"get the release response for {self._release_id}")
        return self._release_response

    @staticmethod
    def create_release_direct(release_version=None, project_name=None, channel_name=None, notes=None,
                              space_id_name=None):
        release = ReleaseDeployment(project_name=project_name, channel_name=channel_name, notes=notes,
                                    space_id_name=space_id_name)
        release.create_release(release_version=release_version)
        log_info_print(local_logger=logger, msg=json.dumps(release.release_response))
        return release

    @staticmethod
    def create_release_deployment(release_version=None, project_name=None, channel_name=None, notes=None,
                                  space_id_name=None, environment_name=None, tenant_name=None, comments=None):
        release = ReleaseDeployment.create_release_direct(release_version=release_version, project_name=project_name,
                                                          channel_name=channel_name, notes=notes,
                                                          space_id_name=space_id_name)
        return release.create_deployment_for_current_release(environment_name=environment_name, tenant_name=tenant_name,
                                                             comments=comments)
