import copy
import os
from pprint import pprint

from octopus_python_client.helper import compare_overwrite, find_item, compare_dicts, load_file, save_file
from octopus_python_client.send_requests_to_octopus import call_octopus, operation_get, operation_post, operation_put, \
    operation_delete

# constants
all_underscore = "all_"
error_message_key = "ErrorMessage"
error_message_resource_not_found = "The resource you requested was not found."
comma_sign = ","
dot_sign = "."
double_hyphen = "--"
file_configuration = "configuration.json"
folder_outer_spaces = "outer_spaces"
folder_configurations = "configurations"
hyphen_sign = "-"
runbook_process_prefix = "RunbookProcess"
slash_all = "/all"
slash_sign = "/"
space_map = "space_map"
underscore_sign = "_"
url_all_pages = "?skip=0&take=2147483647"
yaml_ext = ".yaml"

# dict keys
action_name_key = "ActionName"
actions_key = 'Actions'
api_key_key = "api_key"
canonical_tag_name_key = "CanonicalTagName"
channel_id_key = "ChannelId"
deployment_process_id_key = 'DeploymentProcessId'
donor_package_key = "DonorPackage"
donor_package_step_id_key = "DonorPackageStepId"
environment_id_key = "EnvironmentId"
environment_ids_key = "EnvironmentIds"
feed_id_key = "FeedId"
file_name_key = "Filename"
id_key = 'Id'
included_library_variable_set_ids_key = "IncludedLibraryVariableSetIds"
items_key = 'Items'
life_cycle_id_key = "LifecycleId"
name_key = 'Name'
new_value_key = "NewValue"
octopus_endpoint_key = "octopus_endpoint"
octopus_name_key = "octopus_name"
owner_id_key = "OwnerId"
package_reference_name_key = "PackageReferenceName"
password_key = "password"
project_group_id_key = "ProjectGroupId"
project_id_key = "ProjectId"
published_runbook_snapshot_id_key = "PublishedRunbookSnapshotId"
release_id_key = "ReleaseId"
release_notes_key = "ReleaseNotes"
runbook_id_key = "RunbookId"
runbook_process_id_key = "RunbookProcessId"
secret_key_key = "SecretKey"
selected_packages_key = "SelectedPackages"
steps_key = 'Steps'
space_id_key = "SpaceId"
tags_key = "Tags"
team_id_key = "TeamId"
tenant_id_key = "TenantId"
token_key = "Token"
user_name_key = "user_name"
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
item_type_users = "users"
item_type_variables = "variables"
item_type_variables_names = "variables/names"
item_type_worker_pools = "workerpools"
item_type_workers = "workers"

# some types have the extended types like: /api/users/{id}/permissions
user_ext_types = [item_type_api_keys, item_type_permissions, item_type_permissions_configuration,
                  item_type_teams]  # item_type_permissions_export is csv file
ext_types_map = {item_type_users: user_ext_types}

item_types_with_duplicate_names = \
    {item_type_channels, item_type_tasks, item_type_deployments, item_type_configuration, item_type_spaces}

item_types_without_single_item = \
    {item_type_dashboard, item_type_dashboard_dynamic, item_type_variables, item_type_variables_names}

# must have for a space to work
must_have_types = [item_type_environments]
# these types do not have dependencies on other types
basic_types = [item_type_action_templates, item_type_certificates, item_type_feeds, item_type_machine_policies,
               item_type_machines, item_type_proxies, item_type_subscriptions, item_type_tag_sets,
               item_type_teams, item_type_library_variable_sets, item_type_worker_pools]
# these types have links/dependencies on other types
complex_types = [item_type_workers, item_type_life_cycles, item_type_project_groups, item_type_projects,
                 item_type_runbooks, item_type_tenants, item_type_channels, item_type_project_triggers,
                 item_type_accounts, item_type_build_information]
# these types have only one item in a space; they are mostly space properties
space_single_item_types = [item_type_dashboard_configuration]
# these types are the child type of another type
child_types = [item_type_deployment_processes, item_type_runbook_processes]
# these types needs "/all" to get all items for this type
only_all_types_inside_space = [item_type_variables, item_type_tenant_variables, item_type_machine_roles]
# the other types not cloneable for now
other_types = [item_type_packages, item_type_releases, item_type_interruptions, item_type_user_onboarding,
               item_type_dashboard, item_type_dashboard_dynamic, item_type_deployments, item_type_variables_names,
               item_type_artifacts, item_type_home, item_type_scoped_user_roles, item_type_runbook_snapshots]
# too many items in them, so ignore for now
large_types = [item_type_tasks, item_type_events]
# the types which are cloneable
normal_cloneable_types = must_have_types + basic_types + complex_types
# the types live inside space
item_types_inside_space = normal_cloneable_types + child_types + only_all_types_inside_space + other_types
# the types live outside space (Octopus server types)
item_types_only_ourter_space = \
    ["authentication", "configuration/certificates", "communityactiontemplates", "externalsecuritygroupproviders",
     "featuresconfiguration", "letsencryptconfiguration", "licenses/licenses-current",
     "licenses/licenses-current-status", "maintenanceconfiguration", "octopusservernodes", "performanceconfiguration",
     "permissions/all", "scheduler", "serverconfiguration", "serverconfiguration/settings", "serverstatus",
     "smtpconfiguration", "smtpconfiguration/isconfigured", "upgradeconfiguration", item_type_users, "userroles",
     item_type_configuration, item_type_spaces]
# the sub item map for a specific type; this is for deleting the unused sub items when the item cannot be deleted
# e.g. tagsets: Tags is the key to get the list of the sub items; CanonicalTagName is for printing purpose
item_type_sub_item_map = {item_type_tag_sets: (tags_key, canonical_tag_name_key)}


class Config:
    def __init__(self):
        self.octopus_endpoint = None
        self.octopus_name = None
        self.api_key = None
        self.user_name = None
        self.password = None
        self.code_path = os.path.dirname(os.path.abspath(__file__))
        self.current_path = os.getcwd()
        self.overwrite = False
        self.get_config()

    def get_config(self):
        print("********** Octopus deploy python client tool **********")
        print('code_path: ' + self.code_path)
        print('current working path: ' + self.current_path)
        config_file = os.path.join(self.code_path, folder_configurations, file_configuration)
        config_dict = load_file(config_file)
        self.octopus_endpoint = config_dict.get(octopus_endpoint_key)
        self.octopus_name = config_dict.get(octopus_name_key)
        self.api_key = config_dict.get(api_key_key)
        self.user_name = config_dict.get(user_name_key)
        self.password = config_dict.get(password_key)


config = Config()


def get_list_ids_one_type(item_type=None, space_id=None):
    list_items = get_one_type_to_list(item_type=item_type, space_id=space_id)
    return [item.get(id_key) for item in list_items]


def verify_space(space_id_or_name=None):
    list_spaces = get_one_type_to_list(item_type=item_type_spaces)
    space = find_item(lst=list_spaces, key=id_key, value=space_id_or_name)
    if space:
        return space.get(id_key)
    space = find_single_item_from_list_by_name(list_items=list_spaces, item_name=space_id_or_name)
    if space:
        return space.get(id_key)
    return None


# remove the unnecessary modified date/user information from put and post operations
def pop_last_modified(a_dict=None):
    if isinstance(a_dict, dict):
        a_dict.pop('LastModifiedOn', None)
        a_dict.pop('LastModifiedBy', None)


def always_overwrite_or_compare_overwrite(local_file=None, data=None, overwrite=False):
    if not local_file or not str(data):
        raise ValueError("local_file and data must not be empty")
    if config.overwrite or overwrite:
        save_file(file_path_name=local_file, content=data)
        print(f'A new local file {local_file} was written with the data')
    else:
        compare_overwrite(data=data, local_file=local_file)


# local child item file based on parent item
def get_local_child_file(parent_name=None, child_type=None, space_id=None):
    parent_name = parent_name.replace(slash_sign, underscore_sign)
    child_type = child_type.replace(slash_sign, underscore_sign)
    if space_id:
        return os.path.join(config.current_path, config.octopus_name, space_id, child_type,
                            parent_name + underscore_sign + child_type + yaml_ext)
    else:
        return os.path.join(config.current_path, config.octopus_name, folder_outer_spaces, child_type,
                            parent_name + underscore_sign + child_type + yaml_ext)


# get the local single item file from config.current_path, space_id, item type, file_name;
# for spaces files, no space_id needed
def get_local_single_item_file(item_name=None, item_type=None, space_id=None):
    item_type = item_type.replace(slash_sign, underscore_sign)
    item_name = item_name.replace(slash_sign, underscore_sign)
    if space_id:
        return os.path.join(config.current_path, config.octopus_name, space_id, item_type, item_name + yaml_ext)
    else:
        return os.path.join(config.current_path, config.octopus_name, folder_outer_spaces, item_type,
                            item_name + yaml_ext)


# get the local all items file from config.current_path, space_id, item type;
# for spaces files, no space_id needed
def get_local_all_items_file(item_type=None, space_id=None):
    item_type_name = item_type.replace(slash_sign, underscore_sign)
    if space_id:
        return os.path.join(config.current_path, config.octopus_name, space_id, item_type_name,
                            all_underscore + item_type_name + yaml_ext)
    else:
        return os.path.join(config.current_path, config.octopus_name, folder_outer_spaces, item_type_name,
                            all_underscore + item_type_name + yaml_ext)


# get local item file smartly; three possibilities
# use 'Name'
# use 'Id' if 'Name' not available
# use item_type if neither 'Id' nor 'Name' available
def get_local_single_item_file_from_item(item=None, item_type=None, space_id=None):
    if not item or not item_type:
        raise ValueError("item and item_type must not be empty!")
    if item.get(name_key) and item_type not in item_types_with_duplicate_names:
        local_item_file = get_local_single_item_file(item_name=item[name_key], item_type=item_type, space_id=space_id)
    elif item.get(id_key):
        local_item_file = get_local_single_item_file(item_name=item[id_key], item_type=item_type, space_id=space_id)
    else:
        local_item_file = get_local_single_item_file(item_name=item_type, item_type=item_type, space_id=space_id)
    return local_item_file


# check if the local item file is the same as the remote item on Octopus server;
# the remote item will be retrieved on the fly
def is_local_same_as_remote(item_type=None, item_name=None, item_id=None, space_id=None):
    if not item_type or not item_name and not item_id:
        raise ValueError("item_type and item_name/item_id must not be empty")
    if item_name:
        remote_item = get_single_item_by_name(item_type=item_type, item_name=item_name, space_id=space_id)
        local_item_file = get_local_single_item_file(item_name=item_name, item_type=item_type, space_id=space_id)
    else:
        remote_item = get_or_delete_single_item_by_id(item_type=item_type, item_id=item_id, space_id=space_id)
        local_item_file = get_local_single_item_file(item_name=item_id, item_type=item_type, space_id=space_id)
    is_same, local_item = is_local_same_as_remote2(remote_item=remote_item, local_item_file=local_item_file)
    return is_same, local_item, remote_item


# check if the local item file is the same as the item on Octopus server
# the remote item is an input
def is_local_same_as_remote2(remote_item=None, local_item_file=None):
    if not remote_item or not local_item_file:
        raise ValueError('remote_item and local_item_file must not be empty')
    local_item = load_file(local_item_file)
    return compare_dicts(local_item, remote_item), local_item


# compare in memory all items with the local all items and overwrite if user wants
def compare_overwrite_multiple_items(items=None, item_type=None, space_id=None, overwrite=False):
    if not item_type:
        raise ValueError('item_type must not be empty')
    local_all_items_file = get_local_all_items_file(item_type=item_type, space_id=space_id)
    print('compare and write: ' + local_all_items_file)
    always_overwrite_or_compare_overwrite(local_file=local_all_items_file, data=items, overwrite=overwrite)


# get all items for an item_type by call Octopus API /api/{space_id}/item_type with 'get' operation
# {space_id} is optional
def get_one_type_ignore_error(item_type=None, space_id=None):
    if not item_type:
        raise ValueError("item_type must not be empty")
    space_url = space_id + slash_sign if space_id else ""
    try:
        if item_type == item_type_home:
            return call_octopus(config=config, url_suffix=space_url)
        if item_type in only_all_types_inside_space:
            url_suffix = space_url + item_type + slash_all
            return call_octopus(config=config, url_suffix=url_suffix)
        else:
            url_suffix = space_url + item_type + url_all_pages
            return call_octopus(config=config, url_suffix=url_suffix)
    except ValueError as err:
        print(err)
        # TODO bug https://help.octopus.com/t/504-gateway-time-out-on-getting-all-variables/24732
        print(f"resource exist for {item_type} in {space_id}, but some error prevents from getting the resource")
        return {}


# get extended types like /api/users/{id}/permissions
def get_ext_types_save(item_type=None, space_id=None, item_ids=None):
    ext_types = ext_types_map.get(item_type)
    print(f"Get extended types {ext_types} of {item_type} in Space {space_id}")
    for ext_type in ext_types:
        ext_items_dict = {}
        for item_id in item_ids:
            address = item_type + slash_sign + item_id + slash_sign + ext_type
            ext_item = request_octopus_item(payload=space_id, space_id=space_id, address=address)
            ext_items_dict[item_id] = ext_item
        ext_file = get_local_single_item_file(item_name=all_underscore + item_type + underscore_sign + ext_type,
                                              item_type=item_type, space_id=space_id)
        save_file(file_path_name=ext_file, content=ext_items_dict)


# then save the all items into a local file (warning for overwrite)
def get_one_type_save(item_type=None, space_id=None, overwrite=False):
    if not item_type:
        raise ValueError("item_type must not be empty")
    all_items = get_one_type_ignore_error(item_type=item_type, space_id=space_id)
    compare_overwrite_multiple_items(items=all_items, item_type=item_type, space_id=space_id, overwrite=overwrite)
    if item_type == item_type_users:
        list_items = get_list_items_from_all_items(all_items=all_items)
        item_ids = [item.get(id_key) for item in list_items]
        get_ext_types_save(item_type=item_type_users, space_id=space_id, item_ids=item_ids)
    return all_items


# delete all items for an item_type by call Octopus API /api/{space_id}/item_type
# then save the all items into a local file (warning for overwrite)
def delete_one_type(item_type=None, space_id=None):
    if not item_type:
        raise ValueError("item_type must not be empty")
    if not config.overwrite:
        if input(f"Delete all items of {item_type} in {space_id} [Y/n]? ") == 'Y':
            config.overwrite = True
        elif input(f"Delete NONE items of {item_type} in {space_id} [Y/n]? ") == 'Y':
            return
    all_items = get_one_type_ignore_error(item_type=item_type, space_id=space_id)
    if item_type in item_types_without_single_item:
        print(f"{item_type} has no sub-single-item, exit")
        return
    for item in get_list_items_from_all_items(all_items=all_items):
        delete_single_item_by_name_or_id(item_type=item_type, item_id=item.get(id_key), space_id=space_id)


# get all items for all item_type(s) by call Octopus API /api/{space_id}/item_type with 'get' operation
# item_types can be None, "", or "projects,tenants" etc
def get_types_save(item_types_comma_delimited=None, space_id=None):
    if item_types_comma_delimited:
        list_item_types = item_types_comma_delimited.split(comma_sign)
    else:
        if space_id:
            list_item_types = item_types_inside_space
        else:
            list_item_types = item_types_inside_space + item_types_only_ourter_space
    if config.overwrite:
        print(f"===== You are downloading {list_item_types} from space {space_id}... ===== ")
    else:
        config.overwrite = \
            input(f"***** You are downloading {list_item_types} from space {space_id}; "
                  f"Some entities may already be downloaded locally; "
                  f"Do you want to overwrite all local existing entities? "
                  f"If no, you will be asked to overwrite or not for each type respectively. [Y/n]: ") == 'Y'
    for item_type in list_item_types:
        get_one_type_save(item_type=item_type, space_id=space_id)


def get_spaces_save(item_types_comma_delimited=None, space_id_or_name_comma_delimited=None):
    if space_id_or_name_comma_delimited:
        list_space_ids_or_names = space_id_or_name_comma_delimited.split(comma_sign)
        list_space_ids = [verify_space(space_id_or_name=space_id_or_name) for space_id_or_name in
                          list_space_ids_or_names]
    else:
        list_space_ids = get_list_ids_one_type(item_type=item_type_spaces) + [None]
    list_space_ids_set = set(list_space_ids)
    if config.overwrite:
        print(f"===== You are downloading spaces {list_space_ids_set}... =====")
    else:
        config.overwrite = \
            input(f"===== You are downloading spaces {list_space_ids_set}; "
                  f"Some entities may already be downloaded locally; "
                  f"Do you want to overwrite all local existing entities? "
                  f"If no, you will be asked to overwrite or not for each type respectively. [Y/n]: ") == 'Y'
    for space_id in list_space_ids_set:
        get_types_save(item_types_comma_delimited=item_types_comma_delimited, space_id=space_id)


# get a single item from Octopus server
# 1. get all items for an item_type by call Octopus API /api/{space_id}/item_type with 'get' operation
# 2. find the matching item for the item_name
def get_single_item_by_name(item_type=None, item_name=None, space_id=None):
    if not item_type or not item_name:
        raise ValueError("item_type and item_name must not be empty")
    print(f"Getting {item_type} {item_name} from {space_id} "
          f"by getting all items first and then find the matched item by name")
    all_items = get_one_type_ignore_error(item_type=item_type, space_id=space_id)
    return find_single_item_from_list_by_name(list_items=all_items.get(items_key, []), item_name=item_name)


# find a single item by name from a list of items
def find_single_item_from_list_by_name(list_items=None, item_name=None):
    print(f"Find {item_name} from list of items...")
    if not list_items:
        print(f"The list is empty, so return")
        return {}
    item = find_item(list_items, name_key, item_name)
    if item.get(id_key):
        print(f"{id_key} for {item_name} is " + item.get(id_key))
    else:
        print(f"{item_name} has no {id_key}; the item is: ")
        pprint(item)
    return item


def save_single_item(item_type=None, item=None, space_id=None):
    if not item_type or not item:
        raise ValueError("item_type and item must not be empty")
    local_item_file = get_local_single_item_file_from_item(item=item, item_type=item_type, space_id=space_id)
    # always_overwrite_or_compare_overwrite(local_file=local_item_file, data=item)
    save_file(file_path_name=local_item_file, content=item)
    print(f'A local file {local_item_file} was saved or overwritten with the data')
    return item


# get tenant variables
def get_tenant_variables(tenant_id=None, space_id=None):
    address = item_type_tenants + slash_sign + tenant_id + slash_sign + item_type_variables
    return request_octopus_item(space_id=space_id, address=address)


# get tenant variables and save to a file
def get_tenant_variables_save(tenant_id=None, space_id=None):
    tenant_variables = get_tenant_variables(tenant_id=tenant_id, space_id=space_id)
    dst_file = get_local_single_item_file(item_name=tenant_id + underscore_sign + item_type_variables,
                                          item_type=item_type_tenant_variables, space_id=space_id)
    save_file(file_path_name=dst_file, content=tenant_variables)
    return tenant_variables


# put/post tenant variables
def put_post_tenant_variables_save(tenant_id=None, space_id=None, tenant_variables=None):
    address = item_type_tenants + slash_sign + tenant_id + slash_sign + item_type_variables
    remote_tenant_variables = request_octopus_item(space_id=space_id, address=address)
    if remote_tenant_variables:
        remote_tenant_variables = request_octopus_item(payload=tenant_variables, space_id=space_id, address=address,
                                                       action=operation_put)
    else:
        # TODO add a log to see if any "POST" exist, it may be an Octopus bug
        remote_tenant_variables = request_octopus_item(payload=tenant_variables, space_id=space_id, address=address,
                                                       action=operation_post)
    tenant_variables_file = get_local_single_item_file(item_name=tenant_id + underscore_sign + item_type_variables,
                                                       item_type=item_type_tenant_variables, space_id=space_id)
    save_file(file_path_name=tenant_variables_file, content=remote_tenant_variables)
    return remote_tenant_variables


def get_single_item_by_name_or_id(item_type=None, item_name=None, item_id=None, space_id=None):
    if not item_type or not item_name and not item_id:
        raise ValueError("item_type and item_name/item_id must not be empty")
    if item_name:
        return get_single_item_by_name(item_type=item_type, item_name=item_name, space_id=space_id)
    elif item_id:
        return get_or_delete_single_item_by_id(item_type=item_type, item_id=item_id, space_id=space_id)
    else:
        raise ValueError("Either item_name or item_id must be present")


# get a single item from Octopus server
# if item_name
# 1. get all items for an item_type by call Octopus API /api/{space_id}/item_type with 'get' operation
# 2. find the matching item for the item_name
# 3. save the single item into a local file (warning for overwrite)
# if item_id
# get a single item from Octopus server for the item which cannot be searched by the item_name (like deployment process)
# by directly calling the Octopus API /api/{space_id}/item_type/{id} with 'get'
# since there is no 'Name' in some of the json response, we have to use 'Id' as the file name to save it
def get_single_item_by_name_or_id_save(item_type=None, item_name=None, item_id=None, space_id=None):
    item = get_single_item_by_name_or_id(item_type=item_type, item_name=item_name, item_id=item_id, space_id=space_id)
    save_single_item(item_type=item_type, item=item, space_id=space_id)
    # process child items
    if item_type == item_type_projects:
        print(f"the item type is {item_type_projects}, so also get its deployment_process and variables")
        get_single_item_by_name_or_id_save(item_type=item_type_deployment_processes,
                                           item_id=item.get(deployment_process_id_key), space_id=space_id)
        get_single_item_by_name_or_id_save(item_type=item_type_variables, item_id=item.get(variable_set_id_key),
                                           space_id=space_id)
    elif item_type == item_type_library_variable_sets:
        get_single_item_by_name_or_id_save(item_type=item_type_variables, item_id=item.get(variable_set_id_key),
                                           space_id=space_id)
    elif item_type == item_type_tenants:
        get_tenant_variables_save(tenant_id=item.get(id_key), space_id=space_id)
    return item


# a single item from Octopus server for the item which cannot be searched by the item_name (like deployment process)
# by directly calling the Octopus API /api/{space_id}/item_type/{id}
def get_or_delete_single_item_by_id(item_type=None, item_id=None, action=operation_get, space_id=None):
    if not item_type or not item_id:
        raise ValueError("item_type and item_id must not be empty")
    print(f"{action} {item_type} {item_id} in {space_id}...")
    space_url = space_id + slash_sign if space_id else ""
    url_suffix = space_url + item_type + slash_sign + item_id
    return call_octopus(operation=action, config=config, url_suffix=url_suffix)


def get_list_items_from_all_items(all_items=None):
    # the case where the payload has a metadata and a list
    if isinstance(all_items, dict) and isinstance(all_items.get(items_key), list):
        print(f"the payload is a dict, so get the list of items first by {items_key}")
        return all_items.get(items_key)
    elif isinstance(all_items, list):
        print("the payload is a list")
        return all_items
    return []


# post a single item by call Octopus API /api/{space_id}/item_type with 'post'
def post_single_item(item_type=None, payload=None, space_id=None):
    if not item_type or not payload:
        raise ValueError("item_type and playload must not be empty")
    space_url = space_id + slash_sign if space_id else ""
    url_suffix = space_url + item_type
    item = call_octopus(operation=operation_post, payload=payload, config=config, url_suffix=url_suffix)
    pop_last_modified(item)
    # print(f"{item_type} {id_key} is " + item[id_key])
    return item


# post a single item by call Octopus API /api/{space_id}/item_type with 'post' operation
# then save the item locally
def post_single_item_save(item_type=None, payload=None, space_id=None):
    item = post_single_item(item_type=item_type, payload=payload, space_id=space_id)
    if not item.get(name_key) and payload.get(name_key):
        item[name_key] = payload[name_key]
    local_item_file = get_local_single_item_file_from_item(item=item, item_type=item_type, space_id=space_id)
    always_overwrite_or_compare_overwrite(local_file=local_item_file, data=item, overwrite=True)
    return item


# put a single item by call Octopus API /api/{space_id}/item_type/{id} with 'put' operation
def put_single_item(item_type=None, payload=None, space_id=None):
    if not item_type or not payload:
        raise ValueError("item_type and playload must not be empty")
    space_url = space_id + slash_sign if space_id else ""
    # some type has no id like http://server/api/Spaces-1/dashboardconfiguration
    url_suffix = space_url + item_type + (slash_sign + payload.get(id_key) if payload.get(id_key) else "")
    item = call_octopus(operation=operation_put, payload=payload, config=config, url_suffix=url_suffix)
    pop_last_modified(item)
    print(f"{item_type} {id_key} is " + item[id_key])
    return item


# put a single item by call Octopus API /api/{space_id}/item_type/{id} with 'put' operation
# then save the item locally
def put_single_item_save(item_type=None, payload=None, space_id=None, overwrite=False):
    item_info = payload.get(name_key) if payload.get(name_key) else payload.get(id_key)
    if config.overwrite or overwrite \
            or input(f"Are you sure you want to update {item_type} {item_info} in {space_id} [Y/n]: ") == 'Y':
        item = put_single_item(item_type=item_type, payload=payload, space_id=space_id)
        local_item_file = get_local_single_item_file_from_item(item=item, item_type=item_type, space_id=space_id)
        save_file(file_path_name=local_item_file, content=item)
        return item
    return payload


# put a child-item by call Octopus API /api/{space_id}/child_type/{id} with 'put' operation
# then save the item locally
def put_child_item_save(parent_name=None, child_type=None, payload=None, space_id=None):
    child_item = put_single_item(item_type=child_type, payload=payload, space_id=space_id)
    local_child_file = get_local_child_file(parent_name=parent_name, child_type=child_type, space_id=space_id)
    save_file(file_path_name=local_child_file, content=child_item)
    return child_item


# update an item on Octopus server
# 1. check if the local item file is the same as the remote item on Octopus server
# 2. if same, exit, otherwise continue to ask if user wants to update the item on Octopus server using the local item
# 3. if user input 'Y', update the item on Octopus and save the remote item locally
def update_single_item_save(item_type=None, item_name=None, item_id=None, space_id=None):
    if not item_type or not item_name and not item_id:
        raise ValueError("item_type and item_name/item_id must not be empty")
    is_same, local_item, remote_item = is_local_same_as_remote(item_type=item_type, item_name=item_name,
                                                               item_id=item_id, space_id=space_id)
    if is_same:
        print("No change was made, exit")
        return local_item
    return put_single_item_save(item_type=item_type, payload=local_item, space_id=space_id)


def delete_file(file_name=None):
    print(f"Removing {file_name}")
    try:
        os.remove(file_name)
    except OSError:
        print(f"{file_name} does not exit")
        pass


# delete unused sub items if the item cannot be deleted due to some sub items are being used
def delete_sub_items(item_type=None, item_name=None, item_id=None, space_id=None):
    item_badge = item_name if item_name else item_id
    sub_item_tuple = item_type_sub_item_map.get(item_type)
    if not sub_item_tuple:
        print(f"{item_type} {item_badge} does not have sub items for deleting; exit")
        return
    print(f"Deleting the unused sub items of {item_type} {item_badge} in {space_id}...")
    item = get_single_item_by_name_or_id(item_type=item_type, item_name=item_name, item_id=item_id, space_id=space_id)
    if not item:
        print(f"{item_type} {item_badge} does not exist in {space_id}; exit")
        return
    index = 0
    sub_items_key = sub_item_tuple[0]
    sub_item_name_key = sub_item_tuple[1]
    while index < len(item.get(sub_items_key)):
        item_copy = copy.deepcopy(item)
        sub_item = item_copy.get(sub_items_key).pop(index)
        try:
            item = put_single_item(item_type=item_type, payload=item_copy, space_id=space_id)
            print(f"sub item with {sub_item_name_key}: {sub_item.get(sub_item_name_key)} was deleted")
        except ValueError as err:
            print(err)
            print(f"sub item with {sub_item_name_key}: {sub_item.get(sub_item_name_key)} cannot be deleted; skip it")
            index += 1
    print(f"----- completed deleting sub items -----")


# delete a single item
def delete_single_item_by_name_or_id(item_type=None, item_name=None, item_id=None, space_id=None):
    if not item_type or not item_name and not item_id:
        raise ValueError("item_type and item_name/item_id must not be empty")
    item_info = item_name if item_name else item_id

    item = get_single_item_by_name_or_id(item_type=item_type, item_name=item_name, item_id=item_id, space_id=space_id)

    if not item:
        print(f"{item_type} {item_info} does not exist in {space_id}; exit")
        return

    if not config.overwrite and input(f"Are you sure to delete {item_type} {item_info} in {space_id} [Y/n]: ") != 'Y':
        return

    print(f"deleting {item_type} {item_info} in {space_id}...")
    try:
        get_or_delete_single_item_by_id(item_type=item_type, item_id=item.get(id_key), action=operation_delete,
                                        space_id=space_id)
    except ValueError as err:
        print(err)
        print(f"try to delete unused sub items of {item_type} {item_info} in {space_id}...")
        delete_sub_items(item_type=item_type, item_id=item.get(id_key), space_id=space_id)


# create a new single item from a local file
def create_single_item_from_local_file(item_type=None, item_name=None, local_item_name=None, space_id=None):
    if not item_type or not local_item_name:
        raise ValueError('item_type and local_item_name must not be empty')

    # load local item file
    local_item_file = get_local_single_item_file(item_name=local_item_name, item_type=item_type, space_id=space_id)
    base_item = load_file(local_item_file)

    # create a new item from the local item
    if item_name:
        print(f"Create {item_name} based on local item file {local_item_file}")
        base_item[name_key] = item_name
    remote = post_single_item_save(item_type=item_type, payload=base_item, space_id=space_id)
    return remote


# create a new single item from an item on Octopus server
def clone_single_item_from_remote_item(item_type=None, item_name=None, base_item_name=None, space_id=None):
    if not item_type or not item_name or not base_item_name:
        raise ValueError('item_type and item_name and base_item_name must not be empty')

    # read the remote base item
    print(f"Create {item_name} based on remote item {base_item_name}")
    base_item = get_single_item_by_name(item_type=item_type, item_name=base_item_name, space_id=space_id)
    if item_type == item_type_projects:
        base_item.pop(versioning_strategy_key, None)

    # create a new item from the remote item
    base_item[name_key] = item_name
    item = post_single_item_save(item_type=item_type, payload=base_item, space_id=space_id)
    return item


# get a single child-item of a parent item; the child-item has no 'Name' field, e.g. deployment processes of projects
def get_child_item(parent_name=None, parent_type=None, child_id_key=None, child_type=None, space_id=None):
    parent = get_single_item_by_name(item_type=parent_type, item_name=parent_name, space_id=space_id)
    return get_or_delete_single_item_by_id(item_type=child_type, item_id=parent.get(child_id_key), space_id=space_id)


# get a single child-item of a parent item; the child-item has no 'Name' field
# save the child-item into a local file with the file name of parent_name_child_type
def get_child_item_save(parent_name=None, parent_type=None, child_id_key=None, child_type=None, space_id=None):
    child_item = get_child_item(parent_name=parent_name, parent_type=parent_type, child_id_key=child_id_key,
                                child_type=child_type, space_id=space_id)
    local_child_file = get_local_child_file(parent_name=parent_name, child_type=child_type, space_id=space_id)
    always_overwrite_or_compare_overwrite(local_file=local_child_file, data=child_item)
    return child_item


# update a single child-item of a parent item; the child-item has no 'Name' field
# 1. check if the local child-item file is the same as the remote child-item on Octopus server
# 2. if same, exit, otherwise ask if user wants to update the child-item on Octopus server using the local child-item
# 3. if user input 'Y', update the child-item on Octopus and save the remote child-item locally, otherwise exit
def update_child_item_from_local_save(parent_name=None, parent_type=None, child_id_key=None, child_type=None,
                                      space_id=None):
    remote_child_item = get_child_item(parent_name=parent_name, parent_type=parent_type, child_id_key=child_id_key,
                                       child_type=child_type, space_id=space_id)
    local_child_file = get_local_child_file(parent_name=parent_name, child_type=child_type, space_id=space_id)
    is_same, local_child_item = is_local_same_as_remote2(remote_item=remote_child_item,
                                                         local_item_file=local_child_file)
    if is_same:
        print("No change was made, exit")
        return
    if config.overwrite or input(f"Are you sure you want to update {child_type} for {parent_name} [Y/n]: ") == 'Y':
        child_item = put_single_item(item_type=child_type, payload=local_child_item, space_id=space_id)
        save_file(file_path_name=local_child_file, content=child_item)


# clone a child-item of a parent-item from another parent-item
def clone_child_item_from_another_parent_save(parent_name=None, base_parent_name=None, parent_type=None,
                                              child_id_key=None, child_type=None, sub_item_key=None, space_id=None,
                                              dst_space_id=None):
    if not dst_space_id:
        dst_space_id = space_id
    print(f"Clone {parent_type} {base_parent_name}'s child item {child_type} in {space_id} "
          f"to {parent_type} {parent_name} in {dst_space_id}")
    base_child_item = get_child_item(parent_name=base_parent_name, parent_type=parent_type, child_id_key=child_id_key,
                                     child_type=child_type, space_id=space_id)
    return __clone_child_item_save(dst_space_id=dst_space_id, parent_name=parent_name,
                                   parent_type=parent_type, child_type=child_type, child_id_key=child_id_key,
                                   sub_item_key=sub_item_key, base_child_item=base_child_item,
                                   overwrite=config.overwrite)


def clone_item_by_id_replace_sub_item_save(item_type=None, src_item=None, dst_item_id=None, sub_item_key=None,
                                           dst_space_id=None):
    src_item_id = src_item.get(id_key)
    print(f"By replacing {sub_item_key}, clone {item_type} {src_item_id} "
          f"from memory to {dst_item_id} in {dst_space_id}...")
    dst_item = get_or_delete_single_item_by_id(item_type=item_type, item_id=dst_item_id, space_id=dst_space_id)
    dst_item[sub_item_key] = src_item.get(sub_item_key)
    dst_item = put_single_item_save(item_type=item_type, payload=dst_item, space_id=dst_space_id, overwrite=True)
    return dst_item


def __clone_child_item_save(dst_space_id=None, parent_name=None, parent_type=None, child_type=None,
                            child_id_key=None, sub_item_key=None, base_child_item=None, overwrite=False):
    print(f"Cloning child item {child_type} {base_child_item.get(id_key)} from memory to {parent_type} {parent_name} "
          f"in {dst_space_id}...")
    if config.overwrite or overwrite or input(f"Are you sure you want to clone child item {child_type} "
                                              f"{base_child_item.get(id_key)} from memory to {parent_type} "
                                              f"{parent_name} in {dst_space_id} [Y/n]: ") == 'Y':
        dst_parent = get_single_item_by_name(item_type=parent_type, item_name=parent_name, space_id=dst_space_id)
        dst_child_id = dst_parent.get(child_id_key)
        dst_child_item = clone_item_by_id_replace_sub_item_save(item_type=child_type, src_item=base_child_item,
                                                                dst_item_id=dst_child_id, sub_item_key=sub_item_key,
                                                                dst_space_id=dst_space_id)
        return dst_child_item


def merge_local_to_remote(source_item=None, target_item=None, child_id_key=None):
    source_children = source_item[child_id_key]
    target_children = target_item[child_id_key]
    target_children_names = set()
    for target_child in target_children:
        target_children_names.add(target_child[name_key])
    for source_child in source_children:
        if not source_child[name_key] in target_children_names:
            source_child[id_key] = ""
            target_children.append(source_child)


def merge_single_item_save(item_type=None, item_name=None, item_id=None, child_id_key=None, space_id=None):
    if not item_type or not item_name and not item_id or not child_id_key:
        raise ValueError("item_type and item_name/item_id and child_id_key must not be empty")
    is_same, local_item, remote_item = is_local_same_as_remote(item_type=item_type, item_name=item_name,
                                                               item_id=item_id, space_id=space_id)
    if is_same:
        print("No change was made, exit")
        return local_item
    merge_local_to_remote(source_item=local_item, target_item=remote_item, child_id_key=child_id_key)
    return put_single_item_save(item_type=item_type, payload=remote_item, space_id=space_id)


def get_list_items_from_file(item_type=None, space_id=None):
    if not item_type:
        raise ValueError("item_type must not be empty!")
    all_items_file = get_local_all_items_file(item_type=item_type, space_id=space_id)
    print(f"load all_items file {all_items_file}...")
    all_items = load_file(all_items_file)
    return get_list_items_from_all_items(all_items=all_items)


def find_child_item_from_list(parent=None, list_items=None, child_id_key=None):
    item_id_value = parent.get(child_id_key)
    print(f"Find {parent.get(name_key)}'s child item with ({child_id_key} = {item_id_value})")
    return find_item(lst=list_items, key=id_key, value=item_id_value)


# request an item by calling Octopus API /api/{space_id}/address
def request_octopus_item(payload=None, space_id=None, address=None, action=operation_get):
    space_url = space_id + slash_sign if space_id else ""
    url_suffix = space_url + address
    item = call_octopus(operation=action, payload=payload, config=config, url_suffix=url_suffix)
    pop_last_modified(item)
    return item


def find_sub_by_item(item_type=None, item_id=None, sub_type=None, sub_name=None, space_id=None):
    address = item_type + slash_sign + item_id + slash_sign + sub_type
    sub_items = request_octopus_item(payload=None, space_id=space_id, address=address, action=operation_get)
    list_sub_items = get_list_items_from_all_items(all_items=sub_items)
    return find_item(lst=list_sub_items, key=name_key, value=sub_name)


def get_item_id_by_name(item_type=None, item_name=None, space_id=None):
    item = get_single_item_by_name(item_type=item_type, item_name=item_name, space_id=space_id)
    return item.get(id_key)


def get_list_variables_by_set_name_or_id(set_name=None, set_id=None, space_id=None):
    if set_name:
        library_variable_set = \
            get_single_item_by_name(item_type=item_type_library_variable_sets, item_name=set_name, space_id=space_id)
        set_id = library_variable_set.get(variable_set_id_key)
    variables_dict = \
        get_or_delete_single_item_by_id(item_type=item_type_variables, item_id=set_id, space_id=space_id)
    return variables_dict.get(variables_key)


def get_one_type_to_list(item_type=None, space_id=None):
    all_items = get_one_type_ignore_error(item_type=item_type, space_id=space_id)
    return get_list_items_from_all_items(all_items=all_items)
