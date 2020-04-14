import copy
import logging
import re
from time import gmtime, strftime

from octopus_python_client.common import name_key, tags_key, id_key, item_type_tag_sets, post_single_item_save, \
    item_type_projects, get_list_items_from_file, item_type_deployment_processes, deployment_process_id_key, config, \
    put_single_item_save, normal_cloneable_types, get_list_items_from_all_items, version_key, must_have_types, \
    item_type_library_variable_sets, item_type_variables, variable_set_id_key, get_or_delete_single_item_by_id, \
    item_type_tenant_variables, canonical_tag_name_key, item_type_tags, tenant_id_key, item_type_migration, space_map, \
    get_local_single_item_file, put_single_item, item_type_tenants, slash_sign, underscore_sign, item_type_feeds, \
    secret_key_key, new_value_key, hyphen_sign, item_type_channels, project_id_key, item_type_releases, \
    item_type_artifacts, file_name_key, put_post_tenant_variables_save, get_one_type_to_list, runbook_process_id_key, \
    item_type_runbooks, item_type_accounts, token_key, comma_sign, space_id_key, published_runbook_snapshot_id_key, \
    item_type_scoped_user_roles, user_role_id_key, team_id_key, item_type_runbook_processes, runbook_process_prefix, \
    item_id_prefix_to_type_dict, positive_integer_regex, prepare_project_versioning_strategy, log_info_print, \
    get_one_type_ignore_error, get_single_item_by_name_or_id, log_warn_print, item_types_inside_space
from octopus_python_client.utilities.helper import find_item, save_file, find_matched_sub_list, log_raise_value_error

logger = logging.getLogger(__name__)


class Migration:
    def __init__(self):
        self.__src_space_id = None
        self.__dst_space_id = None
        self.__dst_id_payload_dict = {}
        self.__dst_tenant_variables_payload_dict = {}
        self.__src_id_payload_dict = {}
        self.__src_id_type_dict = {}
        self.__src_id_vs_dst_id_dict = {}
        self.__src_tenant_variables_payload_dict = {}
        self.__type_dst_list_items_dict = {}
        self.__type_full_func_dict = {}
        self.__type_post_func_dict = {}
        self.__type_prep_func_dict = {}
        self.__type_src_list_items_dict = {}

    # search the type in the space and see if the matched item already exists
    def __find_matched_dst_item_by_src_item(self, src_item_with_dst_ids=None, item_type=None):
        logger.info(f"Look for the matched destination {item_type} {src_item_with_dst_ids.get(name_key)} in "
                    f"{self.__dst_space_id}")
        dst_list_items = get_one_type_to_list(item_type=item_type, space_id=self.__dst_space_id)
        item_name = src_item_with_dst_ids.get(name_key)
        match_dict = None
        # "channels" and "runbooks" are special, the name is not unique across a space;
        # we must use both name and project id to find the match
        if item_type == item_type_channels or item_type == item_type_runbooks:
            match_dict = {name_key: item_name, project_id_key: src_item_with_dst_ids.get(project_id_key)}
        # type "releases" has no name and is unique by "Version" and "ProjectId"
        elif item_type == item_type_releases:
            match_dict = {version_key: src_item_with_dst_ids.get(version_key),
                          project_id_key: src_item_with_dst_ids.get(project_id_key)}
        # TODO cloning scopeduserroles is not working and may not be necessary; some space id is null;
        elif item_type == item_type_scoped_user_roles:
            match_dict = {user_role_id_key: src_item_with_dst_ids.get(user_role_id_key),
                          team_id_key: src_item_with_dst_ids.get(team_id_key)}
        # TODO type "artifacts" has no name and unique by Filename and ServerTaskId, so it is not cloneable
        elif item_type == item_type_artifacts:
            return find_item(lst=dst_list_items, key=file_name_key, value=src_item_with_dst_ids.get(file_name_key))
        elif item_name:
            match_dict = {name_key: item_name}
        else:
            log_raise_value_error(local_logger=logger, item=src_item_with_dst_ids,
                                  err=f"{item_type} does not have name or other keys for matching!")
        matched_sub_list = find_matched_sub_list(lst=dst_list_items, match_dict=match_dict, ignore_case=True)
        if matched_sub_list and len(matched_sub_list) > 1:
            log_raise_value_error(local_logger=logger, item=matched_sub_list,
                                  err=f"For {item_type} {item_name}, more than one item found in {self.__dst_space_id}")
        return matched_sub_list[0] if matched_sub_list else {}

    # For tagsets, if the destination space already have the same tagset,
    # each tag of each tagset must use the destination Tag ID not the source Tag ID,
    # so we have to replace each tag id with the destination ones,
    # otherwise it shows"Tag Id is in invalid format."
    # For additional Tag ID in source, we need to remove the ID from the source tag
    def __prepare_tag_set(self, src_item=None):
        src_list_tags = src_item.get(tags_key, [])
        # the source tag id should be all removed
        for src_tag in src_list_tags:
            src_tag.pop(id_key, None)
        dst_tag_set = self.__find_matched_dst_item_by_src_item(src_item_with_dst_ids=src_item,
                                                               item_type=item_type_tag_sets)
        if dst_tag_set:
            dst_list_tags = dst_tag_set.get(tags_key, [])
            for src_tag in src_list_tags:
                matched_dst_tag = find_item(lst=dst_list_tags, key=name_key, value=src_tag.get(name_key))
                if matched_dst_tag:
                    src_tag[id_key] = matched_dst_tag.get(id_key)

    # we do not want to clone the child items first;
    # child items will be created automatically when parent item is created
    def __prepare_project(self, src_item=None):
        logger.info(f"prepare {item_type_projects} {src_item.get(name_key)} for migrating to {self.__dst_space_id}")
        src_item.pop(deployment_process_id_key, None)
        src_item.pop(variable_set_id_key, None)
        prepare_project_versioning_strategy(project=src_item)

    # we do not want to clone the child items first;
    # child items will be created automatically when parent item is created
    def __prepare_library_variable_set(self, src_item=None):
        logger.info(f"prepare {item_type_library_variable_sets} {src_item.get(name_key)} for migrating to "
                    f"{self.__dst_space_id}")
        src_item.pop(variable_set_id_key, None)

    # SecretKey: NewValue: null; must be replaced by a placeholder string
    def __prepare_feed(self, src_item=None):
        logger.info(f"prepare {item_type_feeds} {src_item.get(name_key)} for migrating to {self.__dst_space_id}")
        if secret_key_key in src_item and not src_item.get(secret_key_key).get(new_value_key):
            src_item.get(secret_key_key)[new_value_key] = hyphen_sign
            logger.info(f"assigned a placeholder {hyphen_sign} to {new_value_key} for {secret_key_key}")

    # Token: NewValue: null; must be replaced by a placeholder string
    def __prepare_account(self, src_item=None):
        logger.info(f"prepare {item_type_accounts} {src_item.get(name_key)} for migrating to {self.__dst_space_id}")
        if token_key in src_item and not src_item.get(token_key).get(new_value_key):
            src_item.get(token_key)[new_value_key] = hyphen_sign
            logger.info(f"assigned a placeholder {hyphen_sign} to {new_value_key} for {token_key}")

    # runbook is a new type introduced in Octopus 2019.11; the older Octopus server may not support it
    # Need to upgrade Octopus server to the latest version
    def __prepare_runbook(self, src_item=None):
        logger.info(f"prepare {item_type_runbooks} {src_item.get(name_key)} {src_item.get(id_key)} for migrating to "
                    f"{self.__dst_space_id}: popping {runbook_process_id_key}")
        src_item.pop(runbook_process_id_key, None)
        src_item.pop(published_runbook_snapshot_id_key, None)

    def __clone_item_to_space(self, item_type=None, item_name=None, item_id=None):
        item_badge = item_name if item_name else item_id
        logger.info(f"clone {item_type} {item_badge} from {self.__src_space_id} to {self.__dst_space_id}")

        full_process = self.__type_full_func_dict.get(item_type)
        if full_process:
            return full_process(item_type=item_type, item_name=item_name, item_id=item_id)

        # find the source item in file/memory
        src_item = {}
        if item_name:
            src_list_items = self.__type_src_list_items_dict.get(item_type)
            src_item = find_item(lst=src_list_items, key=name_key, value=item_name)
        if not src_item:
            src_item = self.__src_id_payload_dict.get(item_id)
        if not src_item:
            raise ValueError(f"{item_type} {item_badge} does not exist in the source space")

        return self.__create_item_to_space(item_type=item_type, src_item=src_item)

    def __create_item_to_space(self, item_type=None, src_item=None):
        src_id_value = src_item.get(id_key)
        src_item_name = src_item.get(name_key)

        if src_id_value in self.__src_id_vs_dst_id_dict:
            dst_id_value = self.__src_id_vs_dst_id_dict.get(src_id_value)
            log_info_print(local_logger=logger,
                           msg=f"{item_type} {src_item_name} {src_id_value} has already been cloned to space "
                               f"{self.__dst_space_id} as {dst_id_value} in this session; skip it")
            return dst_id_value

        log_info_print(local_logger=logger, msg=f"cloning {item_type} {src_item_name} {src_id_value} to space "
                                                f"{self.__dst_space_id}")
        logger.info(f"preprocessing {item_type} {src_id_value} with the new references in {self.__dst_space_id}...")
        # do not modify the items in memory
        src_item_copy = copy.deepcopy(src_item)

        # some type needs additional prep-processing
        prep_process = self.__type_prep_func_dict.get(item_type)
        if prep_process:
            logger.info(f"special preprocessing for {item_type} {src_id_value} with function {prep_process}")
            prep_process(src_item=src_item_copy)

        # since the destination "Id: Self-2" has not been created and saved into map
        # we do not want to recursively replace the "Id: Self-1" of the payload;
        # it would cause infinite stack and overflow
        src_item_copy.pop(id_key, None)

        self.__replace_ids(dict_list=src_item_copy)

        logger.info(f"check if {item_type} {src_id_value} already exists in {self.__dst_space_id}")
        dst_item = self.__find_matched_dst_item_by_src_item(src_item_with_dst_ids=src_item_copy, item_type=item_type)
        dst_item_exist = True if dst_item else False
        if dst_item_exist:
            if config.overwrite:
                logger.info(f"{self.__dst_space_id} already has {item_type} {src_id_value}, overwriting it...")
                src_item_copy[id_key] = dst_item.get(id_key)

                # TODO bug in Octopus: PUT a runbook with null RunbookProcessId will remove RunbookProcessId from dst
                if item_type == item_type_runbooks and src_item.get(runbook_process_id_key):
                    matched_runbook_process_id = runbook_process_prefix + hyphen_sign + dst_item.get(id_key)
                    logger.info(f"Reassign process id {matched_runbook_process_id} for {src_item_copy.get(id_key)}")
                    src_item_copy[runbook_process_id_key] = matched_runbook_process_id

                dst_item = put_single_item_save(item_type=item_type, payload=src_item_copy,
                                                space_id=self.__dst_space_id)
            else:
                log_info_print(local_logger=logger,
                               msg=f"{self.__dst_space_id} already has {item_type} {src_id_value}, skipping it...")
        else:
            logger.info(f"{self.__dst_space_id} does not have {item_type} {src_id_value}, so creating it...")
            dst_item = post_single_item_save(item_type=item_type, payload=src_item_copy, space_id=self.__dst_space_id)

        dst_id_value = dst_item.get(id_key)
        logger.info(f"add the id pair ({src_id_value}, {dst_id_value}) to the id map")
        self.__src_id_vs_dst_id_dict[src_id_value] = dst_id_value
        self.__dst_id_payload_dict[dst_id_value] = dst_item

        post_process = self.__type_post_func_dict.get(item_type)
        if post_process and (not dst_item_exist or config.overwrite):
            logger.info(f"Additional processing for {item_type} {src_id_value} with function {post_process}")
            post_process(src_id=src_id_value, dst_id=dst_id_value)

        return dst_id_value

    def __clone_type_to_space(self, item_type=None):
        if not item_type:
            raise ValueError("item_type must not be empty!")
        log_info_print(local_logger=logger,
                       msg=f"cloning items in type {item_type} from {self.__src_space_id} to {self.__dst_space_id}")
        src_list_items = self.__type_src_list_items_dict.get(item_type)
        if not src_list_items:
            logger.warning(f"{item_type} has no items in {self.__src_space_id}, so skip processing it")
            return

        for src_item in src_list_items:
            self.__create_item_to_space(item_type=item_type, src_item=src_item)

        logger.info(f"Get the updated {item_type} in {self.__dst_space_id}")
        dst_all_items = get_one_type_ignore_error(item_type=item_type, space_id=self.__dst_space_id)
        dst_list_items = get_list_items_from_all_items(all_items=dst_all_items)
        self.__type_dst_list_items_dict[item_type] = dst_list_items

    # some id like "Environments-123" should be removed if this is not referenced anyway
    # most likely the entity has been removed and the reference is broken
    # TODO it is a dangerous operation; find a better way to warn people to fix the source space first
    def __check_broken_item_id(self, string=None):
        # if the string is one of the src or dst item ids, it is valid
        if string in self.__src_id_vs_dst_id_dict.keys() or string in self.__src_id_vs_dst_id_dict.values():
            return False
        for id_prefix, item_type in item_id_prefix_to_type_dict.items():
            pattern = r"{}".format("^" + id_prefix + positive_integer_regex)
            if re.match(pattern, string):
                log_warn_print(local_logger=logger, msg=f"***** Please remove the broken reference id {string} in "
                                                        f"source space {self.__src_space_id} *****")
                return True
        return False

    # recursively replace the old link id with the new link id
    # issue: if someone crazy names an environment name as "Environments-1", not "Development" or "Prod" etc,
    # it could cause the environment renamed as "Environment-10"
    # if id_links_map contains "Environments-1" as the key and "Environments-10" as the value
    def __replace_ids(self, dict_list=None):
        if isinstance(dict_list, dict):
            logger.info(f"dict_list is a dict, replace ids or delete broken ids")
            # directly use dict_list.items() or dict_list.keys() could cause unexpected result
            # due to dict.pop(key) while iterating
            keys = copy.deepcopy(list(dict_list.keys()))
            for key in keys:
                value = dict_list.get(key)
                if isinstance(value, str):
                    if value in self.__src_id_vs_dst_id_dict:
                        dict_list[key] = self.__src_id_vs_dst_id_dict.get(value)
                        logger.info(f"the reference value {value} has already been created in the destination space "
                                    f"and was replaced with {dict_list.get(key)}")
                    elif value in self.__src_id_payload_dict:
                        logger.info(f"the reference value {value} exists in the source space but has not been cloned "
                                    f"into the destination space, so clone it first in the destination space")
                        dict_list[key] = self.__clone_item_to_space(item_type=self.__src_id_type_dict.get(value),
                                                                    item_id=value)
                        logger.info(f"the reference value {value} was cloned/found and replaced with "
                                    f"{dict_list.get(key)}")
                    # remove the broken reference ids
                    elif self.__check_broken_item_id(string=value):
                        logger.warning(f"the reference value {value} is a broken reference id, so assign null to it")
                        dict_list[key] = None
                else:
                    self.__replace_ids(dict_list=value)
                if isinstance(key, str):
                    if key in self.__src_id_vs_dst_id_dict:
                        new_key = self.__src_id_vs_dst_id_dict.get(key)
                        dict_list[new_key] = dict_list.pop(key)
                        logger.info(f"the reference key {key} has already been created in the destination space "
                                    f"and was replaced with {new_key}")
                    elif key in self.__src_id_payload_dict:
                        logger.info(f"the reference key {key} exists in the source space but has not been cloned "
                                    f"into the destination space, so clone it first in the destination space")
                        new_key = self.__clone_item_to_space(item_type=self.__src_id_type_dict.get(key), item_id=key)
                        dict_list[new_key] = dict_list.pop(key)
                        logger.info(f"the reference key {key} was cloned/found and replaced with {new_key}")
                    # remove the broken reference ids
                    elif self.__check_broken_item_id(string=key):
                        logger.warning(f"Key {value} is a broken reference id, so pop it")
                        dict_list.pop(key)
                else:
                    self.__replace_ids(dict_list=key)
        elif isinstance(dict_list, list):
            logger.info(f"dict_list is a list, replace ids or delete broken ids")
            # we must do reversely to avoid unexpected result on deleting by index
            for index in range(len(dict_list) - 1, -1, -1):
                element = dict_list[index]
                if isinstance(element, str):
                    if element in self.__src_id_vs_dst_id_dict:
                        dict_list[index] = self.__src_id_vs_dst_id_dict.get(element)
                        logger.info(f"the reference element {element} has already been created in the destination "
                                    f"space and was replaced with {dict_list[index]}")
                    elif element in self.__src_id_payload_dict:
                        logger.info(f"the reference element {element} exists in the source space but has not been "
                                    f"cloned into the destination space, so clone it first in the destination space")
                        dict_list[index] = self.__clone_item_to_space(item_type=self.__src_id_type_dict.get(element),
                                                                      item_id=element)
                        logger.info(f"the reference element {element} was cloned/found and replaced with "
                                    f"{dict_list[index]}")
                    elif self.__check_broken_item_id(string=element):
                        logger.warning(f"element {element} is a broken reference id, so delete it; index {index}")
                        del dict_list[index]
                else:
                    self.__replace_ids(dict_list=element)
        # None, boolean, integer, float etc
        else:
            logger.info(f"the type is {type(dict_list)} and value is {dict_list}; skip it")

    def __clone_child(self, src_parent_id=None, dst_parent_id=None, child_type=None, child_id_key=None):
        # source item
        parent_type = self.__src_id_type_dict.get(src_parent_id)
        src_parent = self.__src_id_payload_dict.get(src_parent_id)
        src_child_id = src_parent.get(child_id_key)
        parent_name = src_parent.get(name_key)

        # destination item
        dst_parent = self.__dst_id_payload_dict.get(dst_parent_id)
        dst_child_id = dst_parent.get(child_id_key)
        self.__src_id_vs_dst_id_dict[src_child_id] = dst_child_id

        logger.info(f"clone {parent_type} {parent_name}'s {child_id_key} {src_child_id} from {self.__src_space_id} to "
                    f"{self.__dst_space_id}")
        src_child = self.__src_id_payload_dict.get(src_child_id)
        # TODO Octopus bug https://help.octopus.com/t/504-gateway-time-out-on-getting-all-variables/24732
        if not src_child:
            logger.warning(f"{src_child_id} does not exist in the memory, so get it from {self.__src_space_id}")
            src_child = get_single_item_by_name_or_id(item_type=child_type, item_id=src_child_id,
                                                      space_id=self.__src_space_id)
            self.__src_id_payload_dict[src_child_id] = src_child
        dst_child = get_or_delete_single_item_by_id(item_type=child_type, item_id=dst_child_id,
                                                    space_id=self.__dst_space_id)
        src_child_copy = copy.deepcopy(src_child)
        src_child_copy[version_key] = dst_child.get(version_key)
        self.__replace_ids(dict_list=src_child_copy)
        # an Octopus bug: "PUT" variables does not return ScopeValues;
        # so have to run "GET" again after "PUT" to save values
        put_single_item(item_type=child_type, payload=src_child_copy, space_id=self.__dst_space_id)
        dst_child = get_single_item_by_name_or_id(item_type=child_type, item_id=dst_child_id,
                                                  space_id=self.__dst_space_id)
        self.__dst_id_payload_dict[dst_child_id] = dst_child
        return dst_child_id

    # deployment processes are not really created as new; once a project is created, the deployment process is
    # created automatically; so we need to copy the deployment processes from the source space into the destination
    # space matching the same projects; the API call is "PUT" not "POST"
    # same for the variables
    def __post_process_project(self, src_id=None, dst_id=None):
        logger.info(f"clone {item_type_deployment_processes} from {item_type_projects} {src_id} to {dst_id} in "
                    f"{self.__dst_space_id}")
        self.__clone_child(src_parent_id=src_id, dst_parent_id=dst_id, child_type=item_type_deployment_processes,
                           child_id_key=deployment_process_id_key)
        logger.info(f"clone {item_type_variables} from {item_type_projects} {src_id} to {dst_id} in "
                    f"{self.__dst_space_id}")
        self.__clone_child(src_parent_id=src_id, dst_parent_id=dst_id, child_type=item_type_variables,
                           child_id_key=variable_set_id_key)

    def __post_process_library_variable_set(self, src_id=None, dst_id=None):
        logger.info(f"clone {item_type_variables} from {item_type_library_variable_sets} {src_id} to {dst_id} in "
                    f"{self.__dst_space_id}")
        self.__clone_child(src_parent_id=src_id, dst_parent_id=dst_id, child_type=item_type_variables,
                           child_id_key=variable_set_id_key)

    def __post_process_runbook(self, src_id=None, dst_id=None):
        logger.info(f"clone {item_type_runbook_processes} from {item_type_runbooks} {src_id} to {dst_id} in "
                    f"{self.__dst_space_id}")
        self.__clone_child(src_parent_id=src_id, dst_parent_id=dst_id, child_type=item_type_runbook_processes,
                           child_id_key=runbook_process_id_key)

    # tenant variables is special and its id is also tenant id, such as "Tenants-401"
    # so you have to use a separate map to store the tenants variables
    # also put/post tenant variables uses a different url from put variables
    def __post_process_tenant_variables(self, src_id=None, dst_id=None):
        logger.info(f"clone {item_type_tenant_variables} from {item_type_tenants} {src_id} in {self.__src_space_id} "
                    f"to {dst_id} in {self.__dst_space_id}")
        src_tenant_variables = self.__src_tenant_variables_payload_dict.get(src_id)
        src_tenant_variables_copy = copy.deepcopy(src_tenant_variables)

        self.__replace_ids(dict_list=src_tenant_variables_copy)

        dst_tenant_variables = put_post_tenant_variables_save(tenant_id=dst_id, space_id=self.__dst_space_id,
                                                              tenant_variables=src_tenant_variables_copy)

        self.__dst_tenant_variables_payload_dict[dst_id] = dst_tenant_variables

    def __full_process_tags(self, item_type=None, item_name=None, item_id=None):
        logger.info(f"full process - clone {item_type} {item_name} {item_id} to {self.__dst_space_id}")
        tag_set_name = item_id.split(slash_sign)[0]
        src_list_tag_sets = self.__type_src_list_items_dict.get(item_type_tag_sets)
        src_tag_set = find_item(lst=src_list_tag_sets, key=name_key, value=tag_set_name)
        src_tag = self.__src_id_payload_dict.get(item_id)
        src_tag_copy = copy.deepcopy(src_tag)
        src_tag_copy.pop(id_key, None)
        dst_tag_set = self.__find_matched_dst_item_by_src_item(src_item_with_dst_ids=src_tag_set,
                                                               item_type=item_type_tag_sets)
        if dst_tag_set:
            logger.info(f"{item_type_tag_sets} {dst_tag_set.get(name_key)} exists in {self.__dst_space_id}, "
                        f"so try to find {item_id}")
            if not find_item(lst=dst_tag_set.get(tags_key), key=canonical_tag_name_key, value=item_id):
                logger.info(f"{item_type_tag_sets} {dst_tag_set.get(name_key)} does not have {item_id} in "
                            f"{self.__dst_space_id}, add it")
                dst_tag_set.get(tags_key).append(src_tag_copy)
                dst_tag_set = put_single_item_save(item_type=item_type_tag_sets, payload=dst_tag_set,
                                                   space_id=self.__dst_space_id,
                                                   overwrite=True)
            else:
                logger.info(f"{item_type_tag_sets} {dst_tag_set.get(name_key)} already has {item_id} in "
                            f"{self.__dst_space_id}, skip")
        else:
            logger.info(f"{item_type_tag_sets} {dst_tag_set.get(name_key)} does not exist in {self.__dst_space_id}, "
                        f"so create it with {item_type_tags} {item_id}")
            dst_tag_set = copy.deepcopy(src_tag_set)
            dst_tag_set.pop(id_key, None)
            dst_tag_set[tags_key] = [src_tag_copy]
            dst_tag_set = post_single_item_save(item_type=item_type_tag_sets, payload=dst_tag_set,
                                                space_id=self.__dst_space_id)
        self.__src_id_vs_dst_id_dict[item_id] = item_id
        self.__dst_id_payload_dict[item_id] = find_item(lst=dst_tag_set.get(tags_key), key=canonical_tag_name_key,
                                                        value=item_id)
        return item_id

    def __load_types(self, fake_space=False):
        if fake_space:
            log_info_print(local_logger=logger,
                           msg=f"Reading files {item_types_inside_space} from fake space {self.__src_space_id}...")
        else:
            log_info_print(local_logger=logger,
                           msg=f"Downloading {item_types_inside_space} from space {self.__src_space_id}...")
        actual_src_space_id = None
        for item_type in item_types_inside_space:
            log_info_print(local_logger=logger, msg=f"loading type {item_type} from space {self.__src_space_id}")
            # for cloning space from another Octopus server
            if fake_space:
                logger.info(f"Loading {item_type} in source fake space {self.__src_space_id} from the local file...")
                src_list_items = get_list_items_from_file(item_type=item_type, space_id=self.__src_space_id)
            # for cloning space to space on the same Octopus server
            else:
                logger.info(f"Loading {item_type} from source space {self.__src_space_id}...")
                src_list_items = get_one_type_to_list(item_type=item_type, space_id=self.__src_space_id)
            self.__type_src_list_items_dict[item_type] = src_list_items
            for src_item in src_list_items:
                if not actual_src_space_id and fake_space and item_type == item_type_projects \
                        and src_item.get(space_id_key):
                    actual_src_space_id = src_item.get(space_id_key)
                    logger.info(f"the actual source space id is {actual_src_space_id}; the fake one is "
                                f"{self.__src_space_id}")
                # TODO some items are a pure list of strings, they might be useful in the future, like variables/names
                if isinstance(src_item, str):
                    logger.warning(f"{item_type} {src_item} is ignored when loading")
                elif isinstance(src_item, dict) and src_item.get(id_key):
                    self.__src_id_payload_dict[src_item.get(id_key)] = src_item
                    self.__src_id_type_dict[src_item.get(id_key)] = item_type
                elif isinstance(src_item, dict) and src_item.get(tenant_id_key):
                    self.__src_tenant_variables_payload_dict[src_item.get(tenant_id_key)] = src_item
                else:
                    log_raise_value_error(local_logger=logger, item=src_item, err=f"{item_type} is not valid")
        if fake_space and not actual_src_space_id:
            log_raise_value_error(local_logger=logger, err=f"Could not find an actual space id inside the fake space "
                                                           f"{self.__src_space_id}")
        return actual_src_space_id if actual_src_space_id else self.__src_space_id

    def __prep_tag_sets(self):
        log_info_print(local_logger=logger, msg="prepare for all tags")
        src_list_tag_sets = self.__type_src_list_items_dict.get(item_type_tag_sets)
        for src_tag_set in src_list_tag_sets:
            for src_tag in src_tag_set.get(tags_key):
                canonical_tag_name = src_tag.get(canonical_tag_name_key)
                self.__src_id_payload_dict[canonical_tag_name] = src_tag
                self.__src_id_type_dict[canonical_tag_name] = item_type_tags

    def __initialize_maps(self, src_space_id=None, dst_space_id=None, fake_space=False):
        log_info_print(local_logger=logger,
                       msg=f"initialize the map for cloning from space {src_space_id} to {dst_space_id}; the source "
                           f"space is {'fake' if fake_space else 'real'}")
        self.__src_space_id = src_space_id
        self.__dst_space_id = dst_space_id

        self.__type_prep_func_dict[item_type_tag_sets] = self.__prepare_tag_set
        self.__type_prep_func_dict[item_type_projects] = self.__prepare_project
        self.__type_prep_func_dict[item_type_library_variable_sets] = self.__prepare_library_variable_set
        self.__type_prep_func_dict[item_type_feeds] = self.__prepare_feed
        self.__type_prep_func_dict[item_type_runbooks] = self.__prepare_runbook
        self.__type_prep_func_dict[item_type_accounts] = self.__prepare_account

        self.__type_post_func_dict[item_type_projects] = self.__post_process_project
        self.__type_post_func_dict[item_type_library_variable_sets] = self.__post_process_library_variable_set
        self.__type_post_func_dict[item_type_tenants] = self.__post_process_tenant_variables
        self.__type_post_func_dict[item_type_runbooks] = self.__post_process_runbook

        self.__type_full_func_dict[item_type_tags] = self.__full_process_tags

        actual_src_space_id = self.__load_types(fake_space=fake_space)

        if fake_space:
            self.__src_id_vs_dst_id_dict[actual_src_space_id] = dst_space_id
        else:
            self.__src_id_vs_dst_id_dict[src_space_id] = dst_space_id

        self.__prep_tag_sets()

    def __save_space_map(self):
        log_info_print(local_logger=logger, msg=f"")
        current_time = strftime("%Y-%m-%d-%H-%M-%S", gmtime())
        local_file = get_local_single_item_file(item_name=space_map + underscore_sign + current_time,
                                                item_type=item_type_migration, space_id=self.__dst_space_id)
        log_info_print(local_logger=logger, msg=f"writing item id map to {local_file}...")
        save_file(file_path_name=local_file, content=self.__src_id_vs_dst_id_dict)

    def clone_space(self, src_space_id=None, dst_space_id=None, item_types_comma_delimited=None, fake_space=False):
        if item_types_comma_delimited:
            process_types = must_have_types + item_types_comma_delimited.split(comma_sign)
        else:
            process_types = normal_cloneable_types
        log_info_print(local_logger=logger, msg=f"cloning {process_types} from {src_space_id} to {dst_space_id}...")
        if not config.overwrite:
            config.overwrite = input(f"You are cloning {process_types} from {src_space_id} to {dst_space_id}; "
                                     f"Some entities may already exist in {dst_space_id}; "
                                     f"Do you want to overwrite the existing entities? "
                                     f"If no, we will skip the existing entities. [Y/n]: ") == 'Y'
        self.__initialize_maps(src_space_id=src_space_id, dst_space_id=dst_space_id, fake_space=fake_space)
        for item_type in process_types:
            if item_type in normal_cloneable_types:
                self.__clone_type_to_space(item_type=item_type)
        self.__save_space_map()

    def clone_space_item(self, src_space_id=None, dst_space_id=None, item_type=None, item_name=None, item_id=None,
                         fake_space=False):
        item_badge = item_name if item_name else item_id
        log_info_print(local_logger=logger,
                       msg=f"cloning {item_type} {item_badge} from {src_space_id} to {dst_space_id}...")
        if not config.overwrite:
            config.overwrite = input(
                f"You are cloning {item_type} {item_badge} from {src_space_id} to {dst_space_id}; "
                f"Some entities may already exist in {dst_space_id}; "
                f"Do you want to overwrite the existing entities? "
                f"If no, we will skip the existing entities. [Y/n]: ") == 'Y'
        self.__initialize_maps(src_space_id=src_space_id, dst_space_id=dst_space_id, fake_space=fake_space)
        if item_type in normal_cloneable_types:
            self.__clone_item_to_space(item_type=item_type, item_name=item_name, item_id=item_id)
        self.__save_space_map()


if __name__ == "__main__":
    migration = Migration()
