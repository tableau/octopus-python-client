import copy
import logging
import os
import time
from pprint import pformat

from octopus_python_client.config import Config
from octopus_python_client.constants import Constants
from octopus_python_client.utilities.helper import compare_overwrite, find_item, load_file, save_file, \
    is_local_same_as_remote2, write_binary_file
from octopus_python_client.utilities.send_requests_to_octopus import call_octopus, operation_get, operation_post, \
    operation_put, operation_delete, operation_get_file, operation_post_file, content_type_key

# constants
all_underscore = "all_"
error_message_key = "ErrorMessage"
error_message_resource_not_found = "The resource you requested was not found."
comma_sign = ","
default_password = "Octopus2020!"
dot_sign = "."
double_hyphen = "--"
environments_prefix = "Environments"
executing_string = "Executing"
folder_outer_spaces = "outer_spaces"
hyphen_sign = "-"
newline_sign = "\n"
package_raw = "raw"
positive_integer_regex = "-[1-9][0-9]*$"
runbook_process_prefix = "RunbookProcess"
slash_all = "/all"
slash_sign = "/"
space_map = "space_map"
success_string = "Success"
tenants_prefix = "Tenants"
underscore_sign = "_"
url_all_pages = "skip=0&take=2147483647"
yaml_ext = ".yaml"

# dict keys
action_name_key = "ActionName"
actions_key = 'Actions'
author_key = "author"
canonical_tag_name_key = "CanonicalTagName"
channel_id_key = "ChannelId"
cloned_from_project_id = "ClonedFromProjectId"
cloned_from_tenant_id_key = "ClonedFromTenantId"
comments_key = "Comments"
deployment_process_id_key = 'DeploymentProcessId'
description_key = "Description"
donor_package_key = "DonorPackage"
donor_package_step_id_key = "DonorPackageStepId"
environment_id_key = "EnvironmentId"
environment_ids_key = "EnvironmentIds"
feed_id_key = "FeedId"
file_extension_key = "FileExtension"
file_key = "file"
file_name_key = "Filename"
id_key = 'Id'
included_library_variable_set_ids_key = "IncludedLibraryVariableSetIds"
is_service_key = "IsService"
items_key = 'Items'
latest_commit_sha_key = "latest_commit_sha"
life_cycle_id_key = "LifecycleId"
name_key = 'Name'
new_value_key = "NewValue"
next_version_increment_key = "NextVersionIncrement"
no_stdout_key = "no_stdout"
owner_id_key = "OwnerId"
overwrite_key = "overwrite"
package_id_key = "PackageId"
package_reference_name_key = "PackageReferenceName"
packages_key = "Packages"
project_group_id_key = "ProjectGroupId"
project_id_key = "ProjectId"
published_runbook_snapshot_id_key = "PublishedRunbookSnapshotId"
release_id_key = "ReleaseId"
release_notes_key = "ReleaseNotes"
release_versions_key = "release_versions"
runbook_id_key = "RunbookId"
runbook_process_id_key = "RunbookProcessId"
scope_values_key = "ScopeValues"
secret_key_key = "SecretKey"
selected_packages_key = "SelectedPackages"
sha_key = "SHA"
state_key = "State"
steps_key = 'Steps'
space_id_key = "SpaceId"
space_managers_team_members = "SpaceManagersTeamMembers"
space_managers_teams = "SpaceManagersTeams"
tags_key = "Tags"
task_id_key = "TaskId"
team_id_key = "TeamId"
tenant_id_key = "TenantId"
timestamp_key = "timestamp"
title_key = "title"
token_key = "Token"
url_prefix_key = "url_prefix"
user_role_id_key = "UserRoleId"
value_key = "Value"
variables_key = "Variables"
variable_set_id_key = "VariableSetId"
version_key = "Version"
versioning_strategy_key = "VersioningStrategy"
worker_pool_id_key = "WorkerPoolId"

# item types
item_type_accounts = "accounts"
item_type_action_templates = "actiontemplates"
item_type_api_keys = "apikeys"
item_type_artifacts = "artifacts"
item_type_build_information = "build-information"
item_type_channels = "channels"
item_type_certificates = "certificates"
item_type_configuration = "configuration"
item_type_dashboard = "dashboard"
item_type_dashboard_configuration = "dashboardconfiguration"
item_type_dashboard_dynamic = "dashboard/dynamic"
item_type_deployments = "deployments"
item_type_deployment_processes = 'deploymentprocesses'
item_type_environments = "environments"
item_type_events = "events"
item_type_feeds = "feeds"
item_type_home = "home"
item_type_interruptions = "interruptions"
item_type_library_variable_sets = "libraryvariablesets"
item_type_life_cycles = "lifecycles"
item_type_logo = "logo"
item_type_machine_policies = "machinepolicies"
item_type_machine_roles = "machineroles"
item_type_machines = "machines"
item_type_packages = "packages"
item_type_permissions = "permissions"
item_type_permissions_configuration = "permissions/configuration"
item_type_permissions_export = "permissions/export"
item_type_project_groups = "projectgroups"
item_type_project_triggers = "projecttriggers"
item_type_projects = "projects"
item_type_proxies = "proxies"
item_type_releases = "releases"
item_type_runbook_processes = "runbookProcesses"
item_type_runbook_snapshots = "runbookSnapshots"  # clone requires package version, so not working now
item_type_runbooks = "runbooks"
item_type_scoped_user_roles = "scopeduserroles"  # the space id should not be null in the response, buggy!
item_type_spaces = 'spaces'
item_type_migration = "migration"
item_type_subscriptions = "subscriptions"
item_type_tag_sets = "tagsets"
item_type_tags = "tags"
item_type_tasks = "tasks"
item_type_teams = "teams"
item_type_tenants = "tenants"
item_type_tenant_variables = "tenantvariables"
item_type_user_onboarding = "useronboarding"
item_type_user_roles = "userroles"
item_type_users = "users"
item_type_variables = "variables"
item_type_variables_names = "variables/names"
item_type_worker_pools = "workerpools"
item_type_workers = "workers"

# messages
remote_local_same_msg = "Remote and local items are the same and no change is needed, exit"

# some types have the extended types like: /api/users/{id}/permissions
user_ext_types = [item_type_api_keys, item_type_permissions, item_type_permissions_configuration,
                  item_type_teams]  # item_type_permissions_export is csv file
ext_types_map = {item_type_users: user_ext_types}

item_types_with_duplicate_names = \
    {item_type_channels, item_type_tasks, item_type_deployments, item_type_configuration, item_type_spaces,
     item_type_runbooks}

item_types_without_single_item = \
    {item_type_dashboard, item_type_dashboard_dynamic, item_type_variables, item_type_variables_names}

# the types are leveled by dependency relationship like a tree;
# the first level has not dependency to other types;
# the second level has dependency on the first level;
# the third level has the dependency on the first and/or the second, and so on;
# TODO item_type_build_information needs investigation (lacks real example as of 4/19/2020)
# TODO item_type_dashboard_configuration is a single data, so no list return, but we can still clone it
# TODO item_type_teams can be cloned from space to space and server to server if users are cloned by outer_space
# TODO item_type_scoped_user_roles (needs userroles)
# bug https://help.octopus.com/t/scopeduserrole-api-does-not-match-swagger-doc/24980
# TODO item_type_packages (need to change requests to get package)
# item_type_library_variable_sets seems like the leaf node but it contains variables with scope of other types
inside_space_level_types = \
    [[item_type_environments, item_type_feeds, item_type_machine_policies, item_type_proxies, item_type_tag_sets,
      item_type_worker_pools],
     [item_type_action_templates, item_type_library_variable_sets, item_type_life_cycles, item_type_packages,
      item_type_project_groups, item_type_workers],  # item_type_teams,
     [item_type_projects],
     [item_type_channels, item_type_runbooks, item_type_tenants],
     [item_type_accounts, item_type_build_information, item_type_certificates, item_type_dashboard_configuration,
      item_type_machines, item_type_project_triggers, item_type_subscriptions]]  # , item_type_scoped_user_roles

# these types are the child type of another type
inside_space_child_types = [item_type_deployment_processes, item_type_runbook_processes]
# these types needs "/all" to get all items for this type
inside_space_only_all_types = [item_type_variables, item_type_tenant_variables, item_type_machine_roles]
# the other types not cloneable for now
inside_space_other_types = \
    [item_type_releases, item_type_interruptions, item_type_user_onboarding, item_type_dashboard,
     item_type_dashboard_dynamic, item_type_deployments, item_type_variables_names, item_type_artifacts, item_type_home,
     item_type_runbook_snapshots]

# too many items in them, so do not download or clone for now
inside_space_large_types = [item_type_tasks, item_type_events]

# the cloneable types which is the flattened inside_space_level_types and the order is maintained
inside_space_clone_types = sum(inside_space_level_types, [])

# the types live inside space
inside_space_download_types = inside_space_clone_types + inside_space_child_types + inside_space_only_all_types + \
                              inside_space_other_types
inside_space_download_types.sort()

# the types live outside space (Octopus server types)
# clone the outer space; this could disable the administrator's permission on the destination server
outer_space_level_types = \
    [[item_type_users, item_type_user_roles],
     [item_type_teams],
     [item_type_spaces],
     [item_type_scoped_user_roles]]

# the cloneable types which is the flattened outer_space_level_types and the order is maintained
outer_space_clone_types = sum(outer_space_level_types, [])

outer_space_download_types = \
    ["authentication", "configuration/certificates", "communityactiontemplates", "externalsecuritygroupproviders",
     "featuresconfiguration", "letsencryptconfiguration", "licenses/licenses-current",
     "licenses/licenses-current-status", "maintenanceconfiguration", "octopusservernodes", "performanceconfiguration",
     "permissions/all", "scheduler", "serverconfiguration", "serverconfiguration/settings", "serverstatus",
     "smtpconfiguration", "smtpconfiguration/isconfigured", "upgradeconfiguration", item_type_configuration,
     item_type_spaces] + sum(outer_space_level_types, [])

# the sub item map for a specific type; this is for deleting the unused sub items when the item cannot be deleted
# e.g. tagsets: Tags is the key to get the list of the sub items; CanonicalTagName is for printing purpose
item_type_sub_item_map = {item_type_tag_sets: (tags_key, canonical_tag_name_key)}
item_id_prefix_to_type_dict = {environments_prefix: item_type_environments, tenants_prefix: item_type_tenants}

# the item types with logo
item_types_with_logo = {item_type_action_templates, item_type_projects, item_type_tenants}


class Common:
    def __init__(self, config: Config, logger: logging.Logger = None):
        self.config = config
        self.logger = logger if logger else logging.getLogger(self.__class__.__name__)

    def log_info_print(self, msg, local_logger=None, item=None):
        if not local_logger:
            local_logger = self.logger
        local_logger.info(msg)
        if not self.config.no_stdout:
            print(msg)
        if item:
            local_logger.info(pformat(item))

    def log_warn_print(self, msg, local_logger=None, item=None):
        if not local_logger:
            local_logger = self.logger
        local_logger.warning(msg)
        if not self.config.no_stdout:
            print(msg)
        if item:
            local_logger.info(pformat(item))

    def log_error_print(self, msg, local_logger=None, item=None):
        if not local_logger:
            local_logger = self.logger
        local_logger.error(msg)
        if not self.config.no_stdout:
            print(msg)
        if item:
            local_logger.info(pformat(item))

    @staticmethod
    def convert_spaces(list_spaces: list):
        space_dict = {}
        for space in list_spaces:
            space_dict[space.get(id_key)] = space.get(name_key)
        return space_dict

    # TODO even after the migration supports packages; we still need to pop VersioningStrategy for cloning project
    # It is a chicken and egg issue; when the project was cloned the first time, the deployment processes is empty;
    # So the DonorPackageStepId which is a deployment process Actions id, is still a broken link, so need to remove;
    # Once the deployment processes is cloned, we need to clone the project again with VersioningStrategy
    # so I decide to keep removing VersioningStrategy for now, until we can run 2-pass project cloning
    def prepare_project_versioning_strategy(self, project):
        self.logger.warning(f"prepare project {project.get(name_key)} for cloning by removing packages from "
                            f"{versioning_strategy_key}; {donor_package_step_id_key} "
                            f"{project.get(versioning_strategy_key).get(donor_package_step_id_key)} is a broken link "
                            f"before deployment processes is cloned")
        project.get(versioning_strategy_key)[donor_package_key] = None
        project.get(versioning_strategy_key)[donor_package_step_id_key] = None

    def get_list_ids_one_type(self, item_type):
        list_items = self.get_list_from_one_type(item_type=item_type)
        return [item.get(id_key) for item in list_items]

    def get_list_spaces(self):
        try:
            all_spaces, headers = call_octopus(config=self.config, url_suffix=item_type_spaces)
            return self.get_list_items_from_all_items(all_items=all_spaces)
        except Exception as err:
            self.log_error_print(msg=f"Cannot get the spaces for {self.config.endpoint}; {err}")
            return []

    def verify_space(self, space_id_name):
        list_spaces = self.get_list_spaces()
        space = find_item(lst=list_spaces, key=id_key, value=space_id_name)
        if space:
            return space.get(id_key)
        space = self.find_single_item_from_list_by_name(list_items=list_spaces, item_name=space_id_name)
        if space:
            return space.get(id_key)
        self.log_error_print(item=list_spaces, msg=f"{space_id_name} not found")
        return None

    # remove the unnecessary modified date/user information from put and post operations
    @staticmethod
    def pop_last_modified(a_dict):
        if isinstance(a_dict, dict):
            a_dict.pop('LastModifiedOn', None)
            a_dict.pop('LastModifiedBy', None)

    def always_overwrite_or_compare_overwrite(self, local_file, data):
        if not local_file or not str(data):
            raise ValueError("local_file and data must not be empty")
        if self.config.overwrite:
            save_file(file_path_name=local_file, content=data)
            self.logger.info(f'A new local file {local_file} was written with the data')
        else:
            compare_overwrite(data=data, local_file=local_file)

    # local child item file based on parent item
    def get_local_child_file(self, parent_name, child_type):
        parent_name = parent_name.replace(slash_sign, underscore_sign)
        child_type = child_type.replace(slash_sign, underscore_sign)
        if self.config.space_id:
            return os.path.join(self.config.data_path, self.config.space_id, child_type,
                                parent_name + underscore_sign + child_type + yaml_ext)
        else:
            return os.path.join(self.config.data_path, folder_outer_spaces, child_type,
                                parent_name + underscore_sign + child_type + yaml_ext)

    # get the local single item file from self.config.data_path, space_id, item type, file_name;
    # for spaces files, no space_id needed
    def get_local_single_item_file(self, item_name, item_type, no_ext=False):
        item_type = item_type.replace(slash_sign, underscore_sign)
        item_name = item_name.replace(slash_sign, underscore_sign)
        if self.config.space_id:
            return os.path.join(self.config.data_path, self.config.space_id, item_type,
                                item_name + ("" if no_ext else yaml_ext))
        else:
            return os.path.join(self.config.data_path, folder_outer_spaces, item_type,
                                item_name + ("" if no_ext else yaml_ext))

    # get the local all items file from self.config.data_path, space_id, item type;
    # for spaces files, no space_id needed
    def get_local_all_items_file(self, item_type):
        item_type_name = item_type.replace(slash_sign, underscore_sign)
        if self.config.space_id:
            return os.path.join(self.config.data_path, self.config.space_id,
                                item_type_name, all_underscore + item_type_name + yaml_ext)
        else:
            return os.path.join(self.config.data_path, folder_outer_spaces, item_type_name,
                                all_underscore + item_type_name + yaml_ext)

    def get_local_single_item_file_from_item(self, item, item_type):
        if not item or not item_type:
            raise ValueError("item and item_type must not be empty!")
        return self.get_local_single_item_file_smartly(
            item_type=item_type, item_name=item.get(name_key), item_id=item.get(id_key))

    def get_local_single_item_file_smartly(self, item_type, item_name=None, item_id=None):
        if not item_type:
            raise ValueError("item_type must not be empty!")
        if item_name and item_id:
            return self.get_local_single_item_file(item_name=item_id + "_" + item_name, item_type=item_type)
        elif item_id:
            return self.get_local_single_item_file(item_name=item_id, item_type=item_type)
        elif item_name:
            return self.get_local_single_item_file(item_name=item_name, item_type=item_type)
        else:
            return self.get_local_single_item_file(item_name=item_type, item_type=item_type)

    # check if the local item file is the same as the remote item on Octopus server;
    # the remote item will be retrieved on the fly
    def is_local_same_as_remote(self, item_type, item_name=None, item_id=None):
        if not item_type or not item_name and not item_id:
            raise ValueError("item_type and item_name/item_id must not be empty")
        if item_name:
            remote_item = self.get_single_item_by_name(item_type=item_type, item_name=item_name)
            local_item_file = self.get_local_single_item_file(item_name=item_name, item_type=item_type)
        else:
            remote_item = self.get_or_delete_single_item_by_id(item_type=item_type, item_id=item_id)
            local_item_file = self.get_local_single_item_file(item_name=item_id, item_type=item_type)
        is_same, local_item = is_local_same_as_remote2(remote_item=remote_item, local_item_file=local_item_file)
        return is_same, local_item, remote_item

    # compare in memory all items with the local all items and overwrite if user wants
    def compare_overwrite_multiple_items(self, items, item_type):
        if not item_type:
            raise ValueError('item_type must not be empty')
        local_all_items_file = self.get_local_all_items_file(item_type=item_type)
        self.logger.info('compare and write: ' + local_all_items_file)
        self.always_overwrite_or_compare_overwrite(local_file=local_all_items_file, data=items)
        return local_all_items_file

    # get all items for an item_type by call Octopus API /api/{space_id}/item_type with 'get' operation
    # {space_id} is optional
    def get_one_type_ignore_error(self, item_type):
        if not item_type:
            raise ValueError("item_type must not be empty")
        self.logger.info(f"getting all items of {item_type} in space {self.config.space_id}")
        space_url = self.config.space_id + slash_sign if self.config.space_id else ""
        try:
            if item_type == item_type_home:
                self.logger.info(f"getting space {self.config.space_id} home page")
                all_items, headers = call_octopus(config=self.config, url_suffix=space_url)
            elif item_type in inside_space_only_all_types:
                self.logger.info(f"{item_type} can only be downloaded by {slash_all}")
                url_suffix = space_url + item_type + slash_all
                all_items, headers = call_octopus(config=self.config, url_suffix=url_suffix)
            else:
                url_suffix = space_url + item_type + "?" + url_all_pages
                all_items, headers = call_octopus(config=self.config, url_suffix=url_suffix)
            return all_items
        except Exception as err:
            # TODO bug https://help.octopus.com/t/504-gateway-time-out-on-getting-all-variables/24732
            self.log_error_print(msg=err)
            return {}

    # get extended types like /api/users/{id}/permissions
    def get_ext_types_save(self, item_type, item_ids):
        ext_types = ext_types_map.get(item_type)
        self.logger.info(f"Get extended types {ext_types} of {item_type} in Space {self.config.space_id}")
        for ext_type in ext_types:
            ext_items_dict = {}
            for item_id in item_ids:
                address = item_type + slash_sign + item_id + slash_sign + ext_type
                ext_item = self.request_octopus_item(address=address)
                ext_items_dict[item_id] = ext_item
            ext_file = \
                self.get_local_single_item_file(item_name=all_underscore + item_type + underscore_sign + ext_type,
                                                item_type=item_type)
            save_file(file_path_name=ext_file, content=ext_items_dict)

    def download_historical_packages(self, package_dict):
        self.log_info_print(msg=f"downloading all historical versions of {package_dict.get(package_id_key)}")
        package_history_list = self.get_package_history_list(package_dict)
        for historical_package in package_history_list:
            self.log_info_print(msg=f"downloading {historical_package.get(id_key)}")
            historical_package[file_extension_key] = package_dict.get(file_extension_key)
            self.save_package(package_dict=historical_package)

    # then save the all items into a local file (warning for overwrite)
    def get_one_type_save(self, item_type):
        if not item_type:
            raise ValueError("item_type must not be empty")
        self.log_info_print(msg=f"downloading {item_type} in space {self.config.space_id}...")
        all_items = self.get_one_type_ignore_error(item_type=item_type)
        local_all_items_file = self.compare_overwrite_multiple_items(items=all_items, item_type=item_type)
        self.log_info_print(msg=f"saved all {item_type} to local file {local_all_items_file}")
        if item_type == item_type_users:
            list_users = self.get_list_items_from_all_items(all_items=all_items)
            user_ids = [user.get(id_key) for user in list_users]
            self.get_ext_types_save(item_type=item_type_users, item_ids=user_ids)
        elif item_type == item_type_packages:
            packages_list = self.get_list_items_from_all_items(all_items=all_items)
            for package in packages_list:
                self.log_info_print(msg=f"downloading {package.get(id_key)}...")
                if self.config.package_history:
                    self.download_historical_packages(package_dict=package)
                else:
                    self.log_info_print(msg=f"downloading the latest version of {package.get(id_key)}")
                    self.save_package(package_dict=package)
        if item_type in item_types_with_logo:
            items_list = self.get_list_items_from_all_items(all_items=all_items)
            for item in items_list:
                self.save_logo(item_type=item_type, item_id=item.get(id_key))
        return all_items

    def delete_types(self, item_types_comma_delimited=None):
        # always delete the parent types before deleting dependency types, otherwise deleting parent will fail
        if item_types_comma_delimited:
            selected_types = item_types_comma_delimited.split(comma_sign)
            list_item_types = []
            for item_type in reversed(inside_space_clone_types):
                if item_type in selected_types:
                    list_item_types.append(item_type)
            self.logger.info(f"deleting reordered specified types {list_item_types}")
        else:
            list_item_types = list(reversed(inside_space_clone_types))
            self.logger.info(
                f"no item types specified, so deleting all cloneable types {list_item_types} in reverse order")
        if not self.config.overwrite:
            if input(f"Are you sure to delete item types {list_item_types} in {self.config.space_id}? [Y/n]: ") == 'Y':
                self.config.overwrite = True
            else:
                return
        self.log_info_print(msg=f"deleting item types {list_item_types} in space {self.config.space_id}...")
        for item_type in list_item_types:
            self.delete_one_type(item_type=item_type)

    # delete all items for an item_type by call Octopus API /api/{space_id}/item_type
    # then save the all items into a local file (warning for overwrite)
    def delete_one_type(self, item_type):
        if not item_type:
            raise ValueError("item_type must not be empty")
        self.log_info_print(msg=f"deleting all {item_type} in space {self.config.space_id}...")
        if not self.config.overwrite:
            if input(f"Delete all items of {item_type} in {self.config.space_id} [Y/n]? ") == 'Y':
                self.config.overwrite = True
            elif input(f"Delete NONE items of {item_type} in {self.config.space_id} [Y/n]? ") == 'Y':
                return
        all_items = self.get_one_type_ignore_error(item_type=item_type)
        if item_type in item_types_without_single_item:
            self.log_info_print(msg=f"{item_type} has no sub-single-item, skip")
            return
        list_items = self.get_list_items_from_all_items(all_items=all_items)
        if list_items:
            for item in list_items:
                self.log_info_print(msg=f"try to delete {item_type} '{item.get(name_key)}' {item.get(id_key)} in "
                                        f"{self.config.space_id}...")
                self.delete_single_item_by_name_or_id(item_type=item_type, item_id=item.get(id_key))
        else:
            self.log_info_print(msg=f"{item_type} does not include single item to delete, skip")

    # get all items for all item_type(s) by call Octopus API /api/{space_id}/item_type with 'get' operation
    # item_types can be None, "", or "projects,tenants" etc
    def get_types_save(self, item_types_comma_delimited=None):
        if item_types_comma_delimited:
            list_item_types = item_types_comma_delimited.split(comma_sign)
        else:
            if self.config.space_id:
                list_item_types = inside_space_download_types
            else:
                list_item_types = inside_space_download_types + outer_space_download_types
        self.log_info_print(f"===== You are downloading {list_item_types} from space {self.config.space_id}... ===== ")
        if not self.config.overwrite:
            self.log_info_print(msg=f"if the data has been downloaded to the local files, they may be skipped.")
        for item_type in list_item_types:
            self.get_one_type_save(item_type=item_type)

    def get_list_spaces_ids_sorted(self, space_id_or_name_comma_delimited=None):
        if space_id_or_name_comma_delimited:
            list_space_ids_or_names = space_id_or_name_comma_delimited.split(comma_sign)
            list_space_ids = [self.verify_space(space_id_name=space_id_or_name) for space_id_or_name in
                              list_space_ids_or_names]
        else:
            list_space_ids = [space.get(id_key) for space in self.get_list_spaces()]
        return sorted(list(set(list_space_ids)))

    def get_spaces_save(self, space_id_or_name_comma_delimited=None, item_types_comma_delimited=None):
        list_space_ids_sorted = self.get_list_spaces_ids_sorted(
            space_id_or_name_comma_delimited=space_id_or_name_comma_delimited)
        # if user does not specify the spaces, we also download the outer space for user
        if not space_id_or_name_comma_delimited:
            list_space_ids_sorted = [None] + list_space_ids_sorted
        self.log_info_print(f"===== You are downloading spaces {list_space_ids_sorted}... =====")
        if not self.config.overwrite:
            self.log_info_print(msg=f"if the data has been downloaded to the local files, they may be skipped.")
        for space_id in list_space_ids_sorted:
            self.config.space_id = space_id
            self.get_types_save(item_types_comma_delimited=item_types_comma_delimited)

    # get a single item from Octopus server
    # 1. get all items for an item_type by call Octopus API /api/{space_id}/item_type with 'get' operation
    # 2. find the matching item for the item_name
    def get_single_item_by_name(self, item_type, item_name):
        if not item_type or not item_name:
            raise ValueError("item_type and item_name must not be empty")
        self.logger.info(f"Getting {item_type} {item_name} from {self.config.space_id} "
                         f"by getting all items first and then find the matched item by name")
        all_items = self.get_one_type_ignore_error(item_type=item_type)
        return self.find_single_item_from_list_by_name(list_items=all_items.get(items_key, []), item_name=item_name)

    # find a single item by name from a list of items
    def find_single_item_from_list_by_name(self, list_items=None, item_name=None):
        self.logger.info(f"Find {item_name} from list of items...")
        if not list_items:
            self.logger.info(f"The list is empty, so return")
            return {}
        item = find_item(list_items, name_key, item_name)
        if not item:
            self.logger.info(f"{item_name} does not exist")
            return {}
        if item.get(id_key):
            self.logger.info(f"{id_key} for {item_name} is " + item.get(id_key))
        else:
            self.logger.info(f"{item_name} has no {id_key}; the item is: ")
            self.logger.warning(pformat(item))
        return item

    def save_single_item(self, item_type, item):
        if not item_type or not item:
            raise ValueError("item_type and item must not be empty")
        local_item_file = self.get_local_single_item_file_from_item(item=item, item_type=item_type)
        # always_overwrite_or_compare_overwrite(local_file=local_item_file, data=item)
        save_file(file_path_name=local_item_file, content=item)
        self.logger.info(f'A local file {local_item_file} was saved or overwritten with the data')
        return local_item_file

    # get tenant variables
    def get_tenant_variables(self, tenant_id):
        address = item_type_tenants + slash_sign + tenant_id + slash_sign + item_type_variables
        return self.request_octopus_item(address=address)

    def get_tenant_variables_local_file_path(self, tenant_variables):
        return self.get_local_single_item_file_smartly(
            item_name=tenant_variables.get(Constants.TENANT_NAME_KEY), item_id=tenant_variables.get(tenant_id_key),
            item_type=item_type_tenant_variables)

    # get tenant variables and save to a file
    def get_tenant_variables_save(self, tenant_id):
        self.logger.info(f"getting and saving {item_type_tenant_variables} for tenant {tenant_id} in space "
                         f"{self.config.space_id}")
        tenant_variables = self.get_tenant_variables(tenant_id=tenant_id)
        dst_file = self.get_tenant_variables_local_file_path(tenant_variables=tenant_variables)
        save_file(file_path_name=dst_file, content=tenant_variables)
        self.log_info_print(msg=f"saved {item_type_tenant_variables} for tenant {tenant_id} to {dst_file}")
        return tenant_variables

    # TODO this function do not change the tenant variables, it might be Octopus server bug
    # Test throught POSTMAN and do not see anything gets updated either
    # http://localhost/api/Spaces-5/tenants/Tenants-301/variables
    def put_post_tenant_variables(self, tenant_id, tenant_variables):
        self.logger.info(f"put or post tenant variables for an existing tenant {tenant_id} in {self.config.space_id}")
        address = item_type_tenants + slash_sign + tenant_id + slash_sign + item_type_variables
        remote_tenant_variables = self.request_octopus_item(address=address)
        if remote_tenant_variables:
            self.logger.info(f"the tenant variables exist in {tenant_id} in {self.config.space_id}, so overwrite")
            self.logger.info(f"tenant {tenant_id} has existing variables, so put the variables")
            remote_tenant_variables = self.request_octopus_item(address=address, payload=tenant_variables,
                                                                operation=operation_put)
        else:
            # TODO add a log to see if any "POST" exist, it may be an Octopus bug
            self.logger.warning(f"tenant {tenant_id} has no variables, so post the variables")
            remote_tenant_variables = self.request_octopus_item(address=address, payload=tenant_variables,
                                                                operation=operation_post)
        return remote_tenant_variables

    # put/post tenant variables and save to local file
    def put_post_tenant_variables_save(self, tenant_id, tenant_variables):
        self.logger.info(f"put or post tenant variables for an existing tenant {tenant_id} in {self.config.space_id} "
                         f"and save to a file")
        remote_tenant_variables = self.put_post_tenant_variables(tenant_id=tenant_id, tenant_variables=tenant_variables)
        tenant_variables_file = self.get_tenant_variables_local_file_path(tenant_variables=tenant_variables)
        save_file(file_path_name=tenant_variables_file, content=remote_tenant_variables)
        return remote_tenant_variables

    def get_single_item_by_name_or_id(self, item_type, item_name=None, item_id=None):
        if not item_type or not item_name and not item_id:
            raise ValueError("item_type and item_name/item_id must not be empty")
        if item_name:
            return self.get_single_item_by_name(item_type=item_type, item_name=item_name)
        elif item_id:
            return self.get_or_delete_single_item_by_id(item_type=item_type, item_id=item_id)
        else:
            raise ValueError("Either item_name or item_id must be present")

    # get a single item from Octopus server
    # if item_name
    # 1. get all items for an item_type by call Octopus API /api/{space_id}/item_type with 'get' operation
    # 2. find the matching item for the item_name
    # 3. save the single item into a local file (warning for overwrite)
    # if item_id,
    # get a single item from Octopus server for the item which cannot be searched by the item_name
    # (like deployment process)
    # by directly calling the Octopus API /api/{space_id}/item_type/{id} with 'get'
    # since there is no 'Name' in some of the json response, we have to use 'Id' as the file name to save it
    def get_single_item_by_name_or_id_save(self, item_type, item_name=None, item_id=None):
        item_badge = item_name if item_name else item_id
        self.log_info_print(msg=f"Getting {item_type} {item_badge} in space {self.config.space_id} and saving file...")
        if item_type == item_type_tenant_variables:
            item = {id_key: item_id, name_key: item_name}
        else:
            item = self.get_single_item_by_name_or_id(item_type=item_type, item_name=item_name, item_id=item_id)
            local_item_file = self.save_single_item(item_type=item_type, item=item)
            self.log_info_print(msg=f"Saved {item_type} {item_badge} to {local_item_file}")
        # process child items
        if item_type == item_type_projects:
            self.log_info_print(f"For item type {item_type_projects}, also get its deployment_process and variables...")
            self.get_single_item_by_name_or_id_save(item_type=item_type_deployment_processes,
                                                    item_id=item.get(deployment_process_id_key))
            self.get_single_item_by_name_or_id_save(item_type=item_type_variables,
                                                    item_id=item.get(variable_set_id_key))
        elif item_type == item_type_library_variable_sets:
            self.log_info_print(f"For item type{item_type_library_variable_sets}, also get variables")
            self.get_single_item_by_name_or_id_save(item_type=item_type_variables,
                                                    item_id=item.get(variable_set_id_key))
        elif item_type == item_type_tenants or item_type == item_type_tenant_variables:
            self.log_info_print(f"For item type {item_type_tenants}, get variables")
            self.get_tenant_variables_save(tenant_id=item.get(id_key))
        elif item_type == item_type_packages:
            self.log_info_print(f"For item type {item_type_packages}, also download the package")
            if self.config.package_history:
                self.download_historical_packages(package_dict=item)
            else:
                self.log_info_print(msg=f"downloading the latest version of {item.get(id_key)}")
                self.save_package(package_dict=item)
        if item_type in item_types_with_logo:
            self.log_info_print(f"For item type {item_types_with_logo}, also download the logo image")
            self.save_logo(item_type=item_type, item_id=item.get(id_key))
        return item

    # a single item from Octopus server for the item which cannot be searched by the item_name (like deployment process)
    # by directly calling the Octopus API /api/{space_id}/item_type/{id}
    def get_or_delete_single_item_by_id(self, item_type, item_id, action=operation_get):
        self.logger.info(f"{action} {item_type} {item_id} in {self.config.space_id}...")
        if not item_type or not item_id:
            raise ValueError("item_type and item_id must not be empty")
        space_url = self.config.space_id + slash_sign if self.config.space_id else ""
        url_suffix = space_url + item_type + slash_sign + item_id
        item, headers = call_octopus(operation=action, config=self.config, url_suffix=url_suffix)
        return item

    def get_list_items_from_all_items(self, all_items):
        self.logger.info(f"getting the list of items from the payload")
        # the case where the payload has a metadata and a list
        if isinstance(all_items, dict) and isinstance(all_items.get(items_key), list):
            self.logger.info(f"the payload is a dict, so get the list of items first by {items_key}")
            return all_items.get(items_key)
        elif isinstance(all_items, list):
            self.logger.info("the payload is a list")
            return all_items
        return []

    # post a single item by call Octopus API /api/{space_id}/item_type with 'post'
    def post_single_item(self, item_type, payload):
        if not item_type or not payload:
            raise ValueError("item_type and playload must not be empty")
        space_url = self.config.space_id + slash_sign if self.config.space_id else ""
        url_suffix = space_url + item_type
        item, headers = call_octopus(operation=operation_post, payload=payload, config=self.config,
                                     url_suffix=url_suffix)
        Common.pop_last_modified(item)
        return item

    # post a single item by call Octopus API /api/{space_id}/item_type with 'post' operation
    # then save the item locally
    def post_single_item_save(self, item_type, payload):
        item_badge = payload.get(name_key) if payload.get(name_key) else payload.get(id_key)
        self.logger.info(f"posting a new {item_type} {item_badge} in space {self.config.space_id} and saving file")
        item = self.post_single_item(item_type=item_type, payload=payload)
        if not item.get(name_key) and payload.get(name_key):
            self.logger.warning(f"the new item has no name, so the input item name {payload.get(name_key)} is used")
            item[name_key] = payload.get(name_key)
        self.save_single_item(item_type=item_type, item=item)
        return item

    # put a single item by call Octopus API /api/{space_id}/item_type/{id} with 'put' operation
    def put_single_item(self, item_type, payload):
        if not item_type or not payload:
            raise ValueError("item_type and playload must not be empty")
        self.logger.info(f"put a single {item_type} {payload.get(id_key)} to space {self.config.space_id}")
        space_url = self.config.space_id + slash_sign if self.config.space_id else ""
        # some type has no id like http://server/api/Spaces-1/dashboardconfiguration
        url_suffix = space_url + item_type + (slash_sign + payload.get(id_key) if payload.get(id_key) else "")
        item, headers = call_octopus(operation=operation_put, payload=payload, config=self.config,
                                     url_suffix=url_suffix)
        Common.pop_last_modified(item)
        self.logger.info(f"{item_type} {id_key} is " + item[id_key])
        return item

    # put a single item by call Octopus API /api/{space_id}/item_type/{id} with 'put' operation
    # then save the item locally
    def put_single_item_save(self, item_type, payload):
        item_info = payload.get(name_key) if payload.get(name_key) else payload.get(id_key)
        self.logger.info(f"updating {item_type} {item_info} in {self.config.space_id} and saving to a local file...")
        item = self.put_single_item(item_type=item_type, payload=payload)
        self.save_single_item(item_type=item_type, item=item)
        return item

    # put a child-item by call Octopus API /api/{space_id}/child_type/{id} with 'put' operation
    # then save the item locally
    def put_child_item_save(self, parent_name, child_type, payload):
        self.logger.info(f"put child {child_type} {payload.get(id_key)} of parent {parent_name} in space"
                         f"{self.config.space_id}")
        child_item = self.put_single_item(item_type=child_type, payload=payload)
        local_child_file = self.get_local_child_file(parent_name=parent_name, child_type=child_type)
        save_file(file_path_name=local_child_file, content=child_item)
        return child_item

    # update an item on Octopus server
    # 1. check if the local item file is the same as the remote item on Octopus server
    # 2. if same, exit, otherwise continue to ask if user wants to update item on Octopus server using the local item
    # 3. if user input 'Y', update the item on Octopus and save the remote item locally
    def update_single_item_save(self, item_type, item_name=None, item_id=None):
        if not item_type or not item_name and not item_id:
            raise ValueError("item_type and item_name/item_id must not be empty")
        local_file = self.get_local_single_item_file_smartly(item_type=item_type, item_name=item_name, item_id=item_id)
        self.log_info_print(msg=f"updating {item_type} {item_name if item_name else item_id} in space "
                                f"{self.config.space_id} from local file {local_file}")
        local_item = load_file(local_file)
        if item_type == item_type_tenant_variables:
            item = self.put_post_tenant_variables_save(tenant_id=item_id, tenant_variables=local_item)
        else:
            item = self.put_single_item_save(item_type=item_type, payload=local_item)
        self.log_info_print(msg=f"update succeeded")
        return item

    # delete unused sub items if the item cannot be deleted due to some sub items are being used
    def delete_sub_items(self, item_type, item_name=None, item_id=None):
        item_badge = item_name if item_name else item_id
        sub_item_tuple = item_type_sub_item_map.get(item_type)
        if not sub_item_tuple:
            self.logger.warning(f"{item_type} {item_badge} does not have sub items for deleting; exit")
            return
        item = self.get_single_item_by_name_or_id(item_type=item_type, item_name=item_name, item_id=item_id)
        if not item:
            self.logger.warning(f"{item_type} {item_badge} does not exist in {self.config.space_id}; exit")
            return
        sub_items_key = sub_item_tuple[0]
        sub_item_name_key = sub_item_tuple[1]
        self.log_info_print(msg=f"deleting the unused sub items {sub_items_key} of {item_type} {item_badge} in "
                                f"{self.config.space_id}...")
        index = 0
        while index < len(item.get(sub_items_key)):
            item_copy = copy.deepcopy(item)
            sub_item = item_copy.get(sub_items_key).pop(index)
            try:
                item = self.put_single_item(item_type=item_type, payload=item_copy)
                self.log_info_print(msg=f"sub item with {sub_item_name_key}: {sub_item.get(sub_item_name_key)} was "
                                        f"deleted")
            except ValueError as err:
                self.logger.warning(err)
                self.log_info_print(msg=f"sub item with {sub_item_name_key}: "
                                        f"{sub_item.get(sub_item_name_key)} cannot be deleted; skip it")
                index += 1
        self.logger.info(f"----- completed deleting sub items -----")

    # delete a single item
    def delete_single_item_by_name_or_id(self, item_type, item_name=None, item_id=None):
        if not item_type or not item_name and not item_id:
            raise ValueError("item_type and item_name/item_id must not be empty")
        item_info = item_name if item_name else item_id
        item = self.get_single_item_by_name_or_id(item_type=item_type, item_name=item_name, item_id=item_id)
        if not item:
            self.logger.warning(f"{item_type} {item_info} does not exist in {self.config.space_id}; exit")
            return
        if not self.config.overwrite and input(
                f"Are you sure to delete {item_type} {item_info} in {self.config.space_id} [Y/n]: ") != 'Y':
            return
        try:
            self.get_or_delete_single_item_by_id(item_type=item_type, item_id=item.get(id_key), action=operation_delete)
            self.log_info_print(msg=f"{item_type} {item_info} was deleted")
        except ValueError as err:
            self.log_warn_print(msg=str(err))
            self.log_info_print(msg=f"{item_type} {item_info} cannot be deleted and try to delete unused sub items in "
                                    f"{self.config.space_id}...")
            self.delete_sub_items(item_type=item_type, item_id=item.get(id_key))

    # create a new single item from a local file
    def create_single_item_from_local_file(self, item_type, local_item_name, item_name=None):
        if not item_type or not local_item_name:
            raise ValueError('item_type and local_item_name must not be empty')
        self.log_info_print(msg=f"creating a new {item_type} {item_name} in space {self.config.space_id} from a local "
                                f"file named {local_item_name}")
        # load local item file
        local_item_file = self.get_local_single_item_file(item_name=local_item_name, item_type=item_type)
        local_item = load_file(local_item_file)
        # rename item if needed
        if item_name:
            self.logger.info(f"Rename local item to {item_name}")
            local_item[name_key] = item_name
        remote = self.post_single_item_save(item_type=item_type, payload=local_item)
        return remote

    # create a new single item from an item on Octopus server
    def clone_single_item_from_remote_item(self, item_type, item_name, base_item_name):
        if not item_type or not item_name or not base_item_name:
            raise ValueError('item_type and item_name and base_item_name must not be empty')
        # read the remote base item
        self.log_info_print(msg=f"cloning {item_type} {item_name} in space {self.config.space_id} based on remote item "
                                f"{base_item_name}")
        base_item = self.get_single_item_by_name(item_type=item_type, item_name=base_item_name)
        if item_type == item_type_projects:
            self.prepare_project_versioning_strategy(project=base_item)
        # create a new item from the remote item
        base_item[name_key] = item_name
        item = self.post_single_item_save(item_type=item_type, payload=base_item)
        return item

    # get a single child-item of a parent item; the child-item has no 'Name' field, e.g. deployment processes of project
    def get_child_item(self, parent_name, parent_type, child_id_key, child_type):
        self.logger.info(f"getting child {child_type} of parent {parent_type} {parent_name} by {child_id_key} in "
                         f"{self.config.space_id}")
        parent = self.get_single_item_by_name(item_type=parent_type, item_name=parent_name)
        return self.get_or_delete_single_item_by_id(item_type=child_type, item_id=parent.get(child_id_key))

    # get a single child-item of a parent item; the child-item has no 'Name' field
    # save the child-item into a local file with the file name of parent_name_child_type
    def get_child_item_save(self, parent_name, parent_type, child_id_key, child_type):
        self.log_info_print(msg=f"getting child {child_type} of parent {parent_type} {parent_name} by "
                                f"{child_id_key} in {self.config.space_id}")
        child_item = self.get_child_item(parent_name=parent_name, parent_type=parent_type, child_id_key=child_id_key,
                                         child_type=child_type)
        local_child_file = self.get_local_child_file(parent_name=parent_name, child_type=child_type)
        self.always_overwrite_or_compare_overwrite(local_file=local_child_file, data=child_item)
        return child_item

    # update a single child-item of a parent item; the child-item has no 'Name' field
    # 1. check if the local child-item file is the same as the remote child-item on Octopus server
    # 2. if same, exit, otherwise ask if user wants to update the child-item on Octopus server using a local child-item
    # 3. if user input 'Y', update the child-item on Octopus and save the remote child-item locally, otherwise exit
    def update_child_item_from_local_save(self, parent_name, parent_type, child_id_key, child_type):
        self.log_info_print(msg=f"update child {child_type} of {parent_type} {parent_name} in {self.config.space_id} by"
                                f" {child_id_key}")
        remote_child_item = self.get_child_item(parent_name=parent_name, parent_type=parent_type,
                                                child_id_key=child_id_key, child_type=child_type)
        local_child_file = self.get_local_child_file(parent_name=parent_name, child_type=child_type)
        is_same, local_child_item = is_local_same_as_remote2(remote_item=remote_child_item,
                                                             local_item_file=local_child_file)
        if is_same:
            self.log_info_print(msg=remote_local_same_msg)
            return
        child_item = self.put_single_item(item_type=child_type, payload=local_child_item)
        save_file(file_path_name=local_child_file, content=child_item)

    # clone a child-item of a parent-item from another parent-item
    def clone_child_item_from_another_parent_save(self, parent_name, base_parent_name, parent_type,
                                                  child_id_key, child_type, sub_item_key):
        self.logger.info(f"Clone {parent_type} {base_parent_name}'s child item {child_type} in {self.config.space_id} "
                         f"to {parent_type} {parent_name} in {self.config.space_id}")
        base_child_item = self.get_child_item(parent_name=base_parent_name, parent_type=parent_type,
                                              child_id_key=child_id_key, child_type=child_type)
        return self._clone_child_item_save(parent_name=parent_name, parent_type=parent_type, child_type=child_type,
                                           child_id_key=child_id_key, sub_item_key=sub_item_key,
                                           base_child_item=base_child_item)

    def clone_item_by_id_replace_sub_item_save(self, item_type, src_item, dst_item_id, sub_item_key):
        src_item_id = src_item.get(id_key)
        self.logger.info(f"By replacing {sub_item_key}, clone {item_type} {src_item_id} from memory to "
                         f"{dst_item_id} in {self.config.space_id}...")
        dst_item = self.get_or_delete_single_item_by_id(item_type=item_type, item_id=dst_item_id)
        dst_item[sub_item_key] = src_item.get(sub_item_key)
        dst_item = self.put_single_item_save(item_type=item_type, payload=dst_item)
        return dst_item

    def _clone_child_item_save(self, parent_name, parent_type, child_type, child_id_key, sub_item_key, base_child_item):
        self.logger.info(f"Cloning child item {child_type} {base_child_item.get(id_key)} from memory to {parent_type} "
                         f"{parent_name} in {self.config.space_id}...")
        dst_parent = self.get_single_item_by_name(item_type=parent_type, item_name=parent_name)
        dst_child_id = dst_parent.get(child_id_key)
        dst_child_item = self.clone_item_by_id_replace_sub_item_save(
            item_type=child_type, src_item=base_child_item, dst_item_id=dst_child_id, sub_item_key=sub_item_key)
        return dst_child_item

    def merge_local_to_remote(self, source_item, target_item, child_id_key):
        self.log_info_print(item=[source_item, target_item], msg=f"merge local item to remote item by {child_id_key}")
        source_children = source_item[child_id_key]
        target_children = target_item[child_id_key]
        target_children_names = set()
        for target_child in target_children:
            target_children_names.add(target_child[name_key])
        for source_child in source_children:
            if not source_child[name_key] in target_children_names:
                source_child[id_key] = ""
                target_children.append(source_child)

    def merge_single_item_save(self, item_type, item_name, item_id, child_id_key):
        if not item_type or not item_name and not item_id or not child_id_key:
            raise ValueError("item_type and item_name/item_id and child_id_key must not be empty")
        self.log_info_print(msg=f"merging {item_type} {item_name if item_name else item_id} for child {child_id_key} "
                                f"in space {self.config.space_id} from local file...")
        is_same, local_item, remote_item = self.is_local_same_as_remote(
            item_type=item_type, item_name=item_name, item_id=item_id)
        if is_same:
            self.log_info_print(msg=remote_local_same_msg)
            return local_item
        self.merge_local_to_remote(source_item=local_item, target_item=remote_item, child_id_key=child_id_key)
        return self.put_single_item_save(item_type=item_type, payload=remote_item)

    def get_list_items_from_file(self, item_type):
        if not item_type:
            raise ValueError("item_type must not be empty!")
        all_items_file = self.get_local_all_items_file(item_type=item_type)
        self.logger.info(f"load all_items file {all_items_file}...")
        all_items = load_file(all_items_file)
        return self.get_list_items_from_all_items(all_items=all_items)

    def find_child_item_from_list(self, parent, list_items, child_id_key):
        item_id_value = parent.get(child_id_key)
        self.logger.info(f"Find {parent.get(name_key)}'s child item with ({child_id_key} = {item_id_value})")
        return find_item(lst=list_items, key=id_key, value=item_id_value)

    # request an item by calling Octopus API /api/{space_id}/address
    def request_octopus_item(self, address, payload=None, operation=operation_get, files=None):
        space_url = self.config.space_id + slash_sign if self.config.space_id else ""
        url_suffix = space_url + address
        item, headers = call_octopus(operation=operation, payload=payload, config=self.config, url_suffix=url_suffix,
                                     files=files)
        Common.pop_last_modified(item)
        return item

    def find_sub_by_item(self, item_type, item_id, sub_type, sub_name):
        address = item_type + slash_sign + item_id + slash_sign + sub_type
        sub_items = self.request_octopus_item(address=address, payload=None, operation=operation_get)
        list_sub_items = self.get_list_items_from_all_items(all_items=sub_items)
        return find_item(lst=list_sub_items, key=name_key, value=sub_name)

    def get_item_id_by_name(self, item_type, item_name):
        item = self.get_single_item_by_name(item_type=item_type, item_name=item_name)
        return item.get(id_key)

    def get_list_variables_by_set_name_or_id(self, set_name=None, set_id=None):
        if set_name:
            library_variable_set = \
                self.get_single_item_by_name(item_type=item_type_library_variable_sets, item_name=set_name)
            if not library_variable_set:
                self.logger.info(f"library variable set {set_name} could not be found in space {self.config.space_id}")
                return []
            set_id = library_variable_set.get(variable_set_id_key)
        variables_dict = \
            self.get_or_delete_single_item_by_id(item_type=item_type_variables, item_id=set_id)
        return variables_dict.get(variables_key)

    def get_list_from_one_type(self, item_type):
        all_items = self.get_one_type_ignore_error(item_type=item_type)
        return self.get_list_items_from_all_items(all_items=all_items)

    def get_task_status(self, task_id):
        self.logger.info(f"check the status of task {task_id} in space {self.config.space_id}")
        task = self.get_or_delete_single_item_by_id(item_type=item_type_tasks, item_id=task_id)
        self.save_single_item(item_type=item_type_tasks, item=task)
        self.logger.info(f"the task's status is {task.get(state_key)} and description is: {task.get(description_key)}")
        self.log_info_print(msg=f"{task.get(state_key)}")
        return task.get(state_key)

    def wait_task(self, task_id, time_limit_second=600):
        self.log_info_print(msg=f"wait for task {task_id} in space {self.config.space_id} to complete until time out "
                                f"at {time_limit_second} seconds")
        counter = 0
        while self.get_task_status(task_id=task_id) == executing_string:
            self.log_info_print(msg=f"{counter} seconds")
            if counter > time_limit_second:
                self.log_info_print(msg=f"task {task_id} takes longer than {time_limit_second} seconds and times out")
                return executing_string
            time.sleep(1)
            counter += 1
        status = self.get_task_status(task_id=task_id)
        self.log_info_print(msg=f"task {task_id} in space {self.config.space_id} completes with status {status} at "
                                f"{counter} seconds")
        return status

    @staticmethod
    def construct_package_name(package_dict):
        return f"{package_dict.get(package_id_key)}.{package_dict.get(version_key)}" \
               f"{package_dict.get(file_extension_key)}"

    def get_package_file(self, package_dict):
        file_name = Common.construct_package_name(package_dict=package_dict)
        return self.get_local_single_item_file(item_name=file_name, item_type=item_type_packages, no_ext=True)

    def open_local_package(self, package_dict):
        local_file = self.get_package_file(package_dict=package_dict)
        self.logger.info(f"loading the package from a local file {local_file}")
        return open(local_file, 'rb')

    def get_package(self, package_id):
        try:
            self.logger.info(f"get package {package_id} from space {self.config.space_id} on server "
                             f"{self.config.endpoint}")
            address = f"{item_type_packages}/{package_id}/{package_raw}"
            return self.request_octopus_item(address=address, operation=operation_get_file)
        except Exception as err:
            self.log_error_print(msg=f"Failed to get package {package_id} from space {self.config.space_id} on server "
                                     f"{self.config.endpoint} with {err}")
            return None

    def save_package(self, package_dict):
        if not isinstance(package_dict, dict):
            self.log_error_print(msg=f"package information is missing and cannot save the package")
            return
        content = self.get_package(package_id=package_dict.get(id_key))
        if not content:
            self.log_error_print(msg=f"the package {package_dict.get(id_key)} has no content and cannot be saved")
            return
        package_file = self.get_package_file(package_dict)
        write_binary_file(local_file=package_file, content=content)
        self.log_info_print(msg=f"saved package {package_dict.get(id_key)} to local file {package_file}")

    def post_package(self, file_name, content):
        self.logger.info(f"post package {file_name} to space {self.config.space_id} on server {self.config.endpoint}")
        if self.config.overwrite:
            self.log_info_print(msg=f"overwriting the existing package {file_name} if it exists")
            address = f"{item_type_packages}/{package_raw}?overwriteMode=OverwriteExisting"
        else:
            self.log_info_print(msg=f"skipping the existing package {file_name} if it exists")
            address = f"{item_type_packages}/{package_raw}?overwriteMode=IgnoreIfExists"
        return self.request_octopus_item(address=address, operation=operation_post_file,
                                         files={file_key: (file_name, content)})

    def get_list_items_by_conditional_id(self, item_type: str, condition_key: str, condition_id: str):
        self.logger.info(f"find the list of {item_type} by {condition_key} == {condition_id}")
        list_all_items = self.get_list_from_one_type(item_type=item_type)
        list_items = []
        for item in list_all_items:
            if item.get(condition_key) == condition_id:
                list_items.append(item)
        return list_items

    def get_item_name_by_id(self, item_type: str, item_id: str):
        item = self.get_or_delete_single_item_by_id(item_type=item_type, item_id=item_id)
        return item.get(name_key)

    def get_package_history_list(self, package_dict: dict):
        if package_dict:
            address = f"feeds/{package_dict.get(feed_id_key)}/packages/versions?packageId=" \
                      f"{package_dict.get(package_id_key)}&{url_all_pages}"
            package_history_dict = self.request_octopus_item(address=address)
            return self.get_list_items_from_all_items(all_items=package_history_dict)
        else:
            return []

    def get_package_history_list_by_name(self, package_name: str):
        packages_list = self.get_list_from_one_type(item_type=item_type_packages)
        package_dict = find_item(lst=packages_list, key=package_id_key, value=package_name)
        return self.get_package_history_list(package_dict=package_dict)

    def get_project_releases_sorted_list(self, project_id: str):
        self.logger.info(f"loading all releases from project {project_id}")
        address = f"{item_type_projects}/{project_id}/{item_type_releases}"
        releases = self.request_octopus_item(address=address)
        releases_list = self.get_list_items_from_all_items(all_items=releases)
        # In literal string: Releases-10000 < Releases-9999 so converting to integer to compare
        releases_list.sort(key=lambda one_release: int(one_release.get(id_key).split(hyphen_sign)[1]), reverse=True)
        return releases_list

    def get_deployment_information(self, release_id: str):
        self.logger.info(f"Gets all of the information necessary for creating or editing a deployment for {release_id}")
        address = f"{item_type_releases}/{release_id}/{item_type_deployments}/template"
        return self.request_octopus_item(address=address)

    def get_octopus_file(self, address):
        space_url = self.config.space_id + slash_sign if self.config.space_id else ""
        url_suffix = space_url + address
        content, headers = call_octopus(operation=operation_get_file, config=self.config, url_suffix=url_suffix)
        ext = headers.get(content_type_key).split("/")[-1]
        # TODO neither .svg nor .svg+xml can be posted to Octopus server. Error: Invalid image provided
        if "+" in ext:
            ext = ext.split("+")[0]
        return content, ext

    def get_logo(self, item_type, item_id):
        try:
            self.logger.info(f"get logo for {item_type} {item_id}")
            address = f"{item_type}/{item_id}/{item_type_logo}"
            return self.get_octopus_file(address=address)
        except Exception as err:
            self.log_error_print(msg=f"Failed to get logo for {item_type} {item_id} with {err}")
            return None, None

    def save_logo(self, item_type, item_id):
        content, ext = self.get_logo(item_type=item_type, item_id=item_id)
        if not content:
            self.log_error_print(msg=f"{item_type} {item_id} has no logo and cannot be saved")
            return
        logo_file = self.local_logo_file(item_type=item_type, item_id=item_id, ext=ext)
        self.logger.info(f"saving logo for {item_type} {item_id} to local file {logo_file}")
        write_binary_file(local_file=logo_file, content=content)
        self.log_info_print(msg=f"saved logo of {item_type} {item_id} to local file {logo_file}")

    def local_logo_file(self, item_type, item_id, ext):
        return self.get_local_single_item_file(
            item_name=f"{item_id}_{item_type_logo}.{ext}", item_type=item_type, no_ext=True)

    def post_logo(self, item_type, item_id, file_name, content):
        self.log_info_print(f"post logo {file_name} to {item_type} {item_id}")
        if self.config.overwrite:
            self.log_info_print(msg=f"overwriting the existing logo")
            address = f"{item_type}/{item_id}/{item_type_logo}?overwriteMode=OverwriteExisting"
        else:
            self.log_info_print(msg=f"skipping the existing logo if it exists")
            address = f"{item_type}/{item_id}/{item_type_logo}?overwriteMode=IgnoreIfExists"
        return self.request_octopus_item(address=address, operation=operation_post_file,
                                         files={file_key: (file_name, content)})
