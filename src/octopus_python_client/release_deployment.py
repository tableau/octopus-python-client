import logging
from pprint import pformat

from octopus_python_client.common import request_octopus_item, item_type_deployment_processes, verify_space, \
    item_type_projects, get_single_item_by_name, id_key, deployment_process_id_key, item_type_channels, \
    find_sub_by_item, packages_key, action_name_key, package_reference_name_key, feed_id_key, package_id_key, \
    item_type_feeds, item_type_packages, version_key, items_key, get_list_variables_by_set_name_or_id, name_key, \
    value_key, project_id_key, next_version_increment_key, release_notes_key, channel_id_key, selected_packages_key, \
    item_type_releases, save_single_item, item_type_deployments, item_type_tenants, item_type_environments, \
    get_item_id_by_name, tenant_id_key, environment_id_key, release_id_key, comments_key, log_info_print
from octopus_python_client.utilities.helper import replace_list_new_value, get_dict_from_str
from octopus_python_client.utilities.send_requests_to_octopus import operation_post

logger = logging.getLogger(__name__)


class ReleaseDeployment:
    def __init__(self, project_name=None, channel_name=None, notes=None, space_id_name=None, package_version_dict=None,
                 packages_variable_set_name=None):
        assert space_id_name, "space name/id must not be empty!"
        assert project_name, "project name must not be empty!"

        self._space_id = verify_space(space_id_name=space_id_name)
        assert self._space_id, f"Space {space_id_name} cannot be found or you do not have permission to access!"

        project = get_single_item_by_name(item_type=item_type_projects, item_name=project_name,
                                          space_id=self._space_id)
        assert project, f"Project {project_name} cannot be found or you do not have permission to access!"
        self._project_id = project.get(id_key)
        self._deployment_process_id = project.get(deployment_process_id_key)
        self._release_request_payload = {project_id_key: self._project_id, release_notes_key: notes}

        self._channel_id = ""
        if channel_name:
            channel = find_sub_by_item(item_type=item_type_projects, item_id=self._project_id,
                                       sub_type=item_type_channels, sub_name=channel_name, space_id=self._space_id)
            assert channel, f"Cannot find channel {channel_name} in project {project_name}"
            self._channel_id = channel.get(id_key)
        if self._channel_id:
            self._release_request_payload[channel_id_key] = self._channel_id

        # package versions read from a variable set, e.g. {"Name": "package.near", "Value": "20.0225.1714"}
        self._packages_variable_set_name = packages_variable_set_name

        # user selected package versions, e.g. "{'package.near': '20.0225.1714'}"
        self._package_version_dict = None
        if package_version_dict:
            logger.info(f"converting package version {package_version_dict} to dict...")
            self._package_version_dict = get_dict_from_str(string=package_version_dict)

        self._template = None
        self._selected_packages = None
        self._release_response = None
        self._release_id = None

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
        if self._packages_variable_set_name:
            list_release_versions = get_list_variables_by_set_name_or_id(set_name=self._packages_variable_set_name,
                                                                         space_id=self._space_id)
            for package_version in list_release_versions:
                self._update_package_version(package=package_version.get(name_key),
                                             version=package_version.get(value_key))
        if self._package_version_dict:
            for package, version in self._package_version_dict.items():
                self._update_package_version(package=package, version=version)

    # release version must be unique for each release
    def create_release(self, release_version=None):
        self._get_deployment_process_template()
        self._get_selected_packages()
        self._update_selected_packages()
        if not release_version:
            release_version = self._template.get(next_version_increment_key)
        self._release_request_payload[version_key] = release_version
        self._release_request_payload[selected_packages_key] = self._selected_packages
        logger.info("the request release payload is")
        logger.info(pformat(self._release_request_payload))
        self._release_response = request_octopus_item(payload=self._release_request_payload, space_id=self._space_id,
                                                      address=item_type_releases, action=operation_post)
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
        log_info_print(local_logger=logger, msg=deployment_response_payload)
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
                              space_id_name=None, package_version_json=None, packages_variable_set_name=None):
        release = ReleaseDeployment(
            project_name=project_name, channel_name=channel_name, notes=notes, space_id_name=space_id_name,
            package_version_dict=package_version_json, packages_variable_set_name=packages_variable_set_name)
        release.create_release(release_version=release_version)
        log_info_print(local_logger=logger, msg=release.release_response)
        return release

    @staticmethod
    def create_release_deployment(release_version=None, project_name=None, channel_name=None, notes=None,
                                  space_id_name=None, package_version_json=None, packages_variable_set_name=None,
                                  environment_name=None, tenant_name=None, comments=None):
        release = ReleaseDeployment.create_release_direct(
            release_version=release_version, project_name=project_name, channel_name=channel_name, notes=notes,
            space_id_name=space_id_name, package_version_json=package_version_json,
            packages_variable_set_name=packages_variable_set_name)
        return release.create_deployment_for_current_release(environment_name=environment_name, tenant_name=tenant_name,
                                                             comments=comments)
