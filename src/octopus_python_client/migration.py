import copy
import glob
import logging
import os
import re
from time import gmtime, strftime

from octopus_python_client.common import name_key, tags_key, id_key, item_type_tag_sets, item_type_projects, Common, \
    item_type_deployment_processes, deployment_process_id_key, scope_values_key, inside_space_download_types, \
    inside_space_clone_types, version_key, item_type_library_variable_sets, item_type_variables, variable_set_id_key, \
    item_type_tenant_variables, canonical_tag_name_key, item_type_tags, tenant_id_key, item_type_migration, space_map, \
    item_type_tenants, slash_sign, underscore_sign, item_type_feeds, secret_key_key, new_value_key, hyphen_sign, \
    item_type_channels, project_id_key, item_type_releases, item_type_artifacts, file_name_key, item_type_runbooks, \
    runbook_process_id_key, item_type_accounts, token_key, space_id_key, item_type_packages, \
    item_type_scoped_user_roles, user_role_id_key, runbook_process_prefix, published_runbook_snapshot_id_key, \
    item_id_prefix_to_type_dict, positive_integer_regex, team_id_key, outer_space_clone_types, item_type_users, \
    item_type_spaces, default_password, is_service_key, space_managers_teams, item_type_teams, package_id_key, \
    comma_sign, cloned_from_project_id, item_type_runbook_processes, item_type_project_triggers, file_extension_key, \
    feed_id_key, item_types_with_logo, item_type_logo
from octopus_python_client.config import Config
from octopus_python_client.constants import Constants
from octopus_python_client.utilities.helper import find_item, save_file, find_matched_sub_list, log_raise_value_error
from octopus_python_client.utilities.send_requests_to_octopus import login_payload_user_name_key, \
    login_payload_password_key


class Migration:
    def __init__(self, src_config: Config, dst_config: Config, logger: logging.Logger = None):
        self.logger = logger if logger else logging.getLogger(self.__class__.__name__)
        self._src_config = src_config
        self._dst_config = dst_config
        self._src_common = Common(config=src_config)
        self._dst_common = Common(config=dst_config)

        self._all_types = inside_space_download_types
        self._dst_id_payload_dict = {}
        self._dst_tenant_variables_payload_dict = {}
        self._project_id = None
        self._spaces_dict = {}
        self._src_id_payload_dict = {}
        self._src_id_type_dict = {}
        self._src_id_vs_dst_id_dict = {}
        self._src_tenant_variables_payload_dict = {}
        self._type_dst_list_items_dict = {}
        self._type_full_func_dict = {}
        self._type_post_func_dict = {}
        self._type_prep_func_dict = {}
        self._type_src_list_items_dict = {}

    # search the type in the space and see if the matched item already exists
    def _find_matched_dst_item_by_src_item(self, src_item_with_dst_ids, item_type):
        self.logger.info(f"Look for the matched destination {item_type} {src_item_with_dst_ids.get(name_key)} in "
                         f"{self._dst_config.space_id}")
        dst_list_items = self._dst_common.get_list_from_one_type(item_type=item_type)
        item_name = src_item_with_dst_ids.get(name_key)
        match_dict = None
        # "channels" and "runbooks" are special, the name is not unique across a space;
        # we must use both name and project id to find the match
        if item_type == item_type_channels or item_type == item_type_runbooks or \
                item_type == item_type_project_triggers:
            match_dict = {name_key: item_name, project_id_key: src_item_with_dst_ids.get(project_id_key)}
        # type "releases" has no name and is unique by "Version" and "ProjectId"
        elif item_type == item_type_releases:
            match_dict = {version_key: src_item_with_dst_ids.get(version_key),
                          project_id_key: src_item_with_dst_ids.get(project_id_key)}
        # https://help.octopus.com/t/scopeduserrole-api-does-not-match-swagger-doc/24980
        elif item_type == item_type_scoped_user_roles:
            match_dict = {user_role_id_key: src_item_with_dst_ids.get(user_role_id_key),
                          team_id_key: src_item_with_dst_ids.get(team_id_key)}
            if src_item_with_dst_ids.get(space_id_key):
                match_dict[space_id_key] = src_item_with_dst_ids.get(space_id_key)
        # TODO type "artifacts" has no name and unique by Filename and ServerTaskId, so it is not cloneable
        elif item_type == item_type_artifacts:
            return find_item(lst=dst_list_items, key=file_name_key, value=src_item_with_dst_ids.get(file_name_key))
        elif item_type == item_type_users:
            match_dict = {login_payload_user_name_key: src_item_with_dst_ids.get(login_payload_user_name_key)}
        elif item_type == item_type_teams and src_item_with_dst_ids.get(space_id_key):
            match_dict = {name_key: item_name, space_id_key: src_item_with_dst_ids.get(space_id_key)}
        elif item_type == item_type_packages:
            match_dict = {package_id_key: src_item_with_dst_ids.get(package_id_key),
                          version_key: src_item_with_dst_ids.get(version_key)}
        elif item_name:
            match_dict = {name_key: item_name}
        else:
            log_raise_value_error(local_logger=self.logger, item=src_item_with_dst_ids,
                                  err=f"{item_type} does not have name or other keys for matching!")
        matched_sub_list = find_matched_sub_list(lst=dst_list_items, match_dict=match_dict, ignore_case=True)
        if matched_sub_list:
            if len(matched_sub_list) > 1:
                if item_type == item_type_scoped_user_roles:
                    self._dst_common.log_info_print(
                        local_logger=self.logger, item=matched_sub_list,
                        msg=f"{item_type_scoped_user_roles} could have multiple matched items in the destination space."
                            f" They are mostly just duplicate, so just return the first matched one")
                    return matched_sub_list[0]
                else:
                    log_raise_value_error(local_logger=self.logger, item=matched_sub_list,
                                          err=f"For {item_type} {item_name}, more than one item found in "
                                              f"{self._dst_config.space_id}")
            else:
                return matched_sub_list[0]
        else:
            return {}

    # For tagsets, if the destination space already have the same tagset,
    # each tag of each tagset must use the destination Tag ID not the source Tag ID,
    # so we have to replace each tag id with the destination ones,
    # otherwise it shows"Tag Id is in invalid format."
    # For additional Tag ID in source, we need to remove the ID from the source tag
    def _prepare_tag_set(self, src_item):
        src_list_tags = src_item.get(tags_key, [])
        # the source tag id should be all removed
        for src_tag in src_list_tags:
            src_tag.pop(id_key, None)
        dst_tag_set = self._find_matched_dst_item_by_src_item(src_item_with_dst_ids=src_item,
                                                              item_type=item_type_tag_sets)
        if dst_tag_set:
            dst_list_tags = dst_tag_set.get(tags_key, [])
            for src_tag in src_list_tags:
                matched_dst_tag = find_item(lst=dst_list_tags, key=name_key, value=src_tag.get(name_key))
                if matched_dst_tag:
                    src_tag[id_key] = matched_dst_tag.get(id_key)

    # we do not want to clone the child items first;
    # child items will be created automatically when parent item is created
    def _prepare_project(self, src_item):
        self.logger.info(
            f"prepare {item_type_projects} {src_item.get(name_key)} for migrating to {self._dst_config.space_id}")
        src_item.pop(deployment_process_id_key, None)
        src_item.pop(variable_set_id_key, None)
        src_item.pop(cloned_from_project_id, None)  # to avoid clone projects we do not need
        self._dst_common.prepare_project_versioning_strategy(project=src_item)

    # we do not want to clone the child items first;
    # child items will be created automatically when parent item is created
    def _prepare_library_variable_set(self, src_item):
        self.logger.info(f"prepare {item_type_library_variable_sets} {src_item.get(name_key)} for migrating to "
                         f"{self._dst_config.space_id}")
        src_item.pop(variable_set_id_key, None)

    def _replace_secrets(self, src_item):
        if secret_key_key in src_item and not src_item.get(secret_key_key).get(new_value_key):
            src_item.get(secret_key_key)[new_value_key] = default_password
            self.logger.info(f"assigned a placeholder {default_password} to {new_value_key} for {secret_key_key}")
        if token_key in src_item and not src_item.get(token_key).get(new_value_key):
            src_item.get(token_key)[new_value_key] = default_password
            self.logger.info(f"assigned a placeholder {default_password} to {new_value_key} for {token_key}")

    # SecretKey: NewValue: null; must be replaced by a placeholder string
    def _prepare_feed(self, src_item):
        self.logger.info(
            f"prepare {item_type_feeds} {src_item.get(name_key)} for migrating to {self._dst_config.space_id}")
        self._replace_secrets(src_item=src_item)

    # Token: NewValue: null; must be replaced by a placeholder string
    def _prepare_account(self, src_item):
        self.logger.info(
            f"prepare {item_type_accounts} {src_item.get(name_key)} for migrating to {self._dst_config.space_id}")
        self._replace_secrets(src_item=src_item)

    # runbook is a new type introduced in Octopus 2019.11; the older Octopus server may not support it
    # Need to upgrade Octopus server to the latest version
    def _prepare_runbook(self, src_item):
        self.logger.info(
            f"prepare {item_type_runbooks} {src_item.get(name_key)} {src_item.get(id_key)} for migrating to "
            f"{self._dst_config.space_id}: popping {runbook_process_id_key}")
        src_item.pop(runbook_process_id_key, None)
        src_item.pop(published_runbook_snapshot_id_key, None)

    def _prepare_space(self, src_item):
        # self.logger.info(f"prepare {item_type_spaces} {src_item.get(name_key)} {src_item.get(id_key)} for migrating "
        #                  f"from {self._src_config.endpoint} to {self._dst_config.endpoint} by popping "
        #                  f"{space_managers_team_members} and {space_managers_teams}")
        # src_item.pop(space_managers_team_members, None)
        # src_item.pop(space_managers_teams, None)
        self.logger.info(f"prepare {item_type_spaces} {src_item.get(name_key)} {src_item.get(id_key)} for migrating "
                         f"from {self._src_config.endpoint} to {self._dst_config.endpoint} by removing space default "
                         f"team in {space_managers_teams}")
        list_team_ids = src_item.get(space_managers_teams)
        if list_team_ids:
            for i in range(len(list_team_ids) - 1, -1, -1):
                if list_team_ids[i].endswith(src_item.get(id_key)):
                    del list_team_ids[i]

    def _prepare_user(self, src_item):
        self.logger.info(f"prepare {item_type_users} {src_item.get(login_payload_user_name_key)} {src_item.get(id_key)}"
                         f" for migrating from {self._src_config.endpoint} to {self._dst_config.space_id} by adding "
                         f"default {login_payload_password_key} as {default_password}")
        if not src_item.get(is_service_key):
            src_item[login_payload_password_key] = default_password

    def _clone_item_to_space(self, item_type, item_name=None, item_id=None, pars_dict: dict = None):
        item_badge = item_name if item_name else item_id
        self.logger.info(
            f"clone {item_type} {item_badge} from {self._src_config.space_id} to {self._dst_config.space_id} with "
            f"parameters {pars_dict}")

        full_process = self._type_full_func_dict.get(item_type)
        if full_process:
            self.logger.info(
                f"Special full processing for {item_type} {item_name} {item_id} in space {self._dst_config.space_id} "
                f"with function {full_process.__name__}")
            return full_process(item_type=item_type, item_name=item_name, item_id=item_id, pars_dict=pars_dict)

        # find the source item in file/memory
        src_item = {}
        if item_name:
            src_list_items = self._type_src_list_items_dict.get(item_type)
            src_item = find_item(lst=src_list_items, key=name_key, value=item_name)
        if not src_item:
            src_item = self._src_id_payload_dict.get(item_id)
        if not src_item:
            raise ValueError(f"{item_type} {item_badge} does not exist in the source space")

        if src_item.get(name_key) and pars_dict and pars_dict.get(Constants.NEW_ITEM_NAME_KEY):
            msg = f"clone/rename {item_type} {src_item.get(name_key)} to {pars_dict.get(Constants.NEW_ITEM_NAME_KEY)}"
            self._dst_common.log_info_print(msg=msg)
            src_item[name_key] = pars_dict.get(Constants.NEW_ITEM_NAME_KEY)

        if src_item.get(project_id_key) and pars_dict and isinstance(pars_dict.get(Constants.PROJECT_IDS_KEY), list):
            msg = f"cloning {item_type} {src_item.get(name_key)} to {pars_dict.get(Constants.PROJECT_IDS_KEY)}"
            self._dst_common.log_info_print(msg=msg)
            for project_id in pars_dict.get(Constants.PROJECT_IDS_KEY):
                self._project_id = project_id
                msg = f"cloning {item_type} {src_item.get(name_key)} to {project_id}"
                self._dst_common.log_info_print(msg=msg)
                src_item[project_id_key] = project_id
                # the same child item needs to be cloned again for the next project
                self._src_id_vs_dst_id_dict.pop(item_id, None)
                # the destination project should not be cloned to itself
                self._src_id_vs_dst_id_dict[project_id] = project_id
                self._create_item_to_space(item_type=item_type, src_item=src_item)
                self._project_id = None
            return

        return self._create_item_to_space(item_type=item_type, src_item=src_item)

    def _clone_single_package(self, src_package_copy_dict):
        if self._src_config.local_data:
            self._dst_common.log_info_print(
                local_logger=self.logger,
                msg=f"loading file from {self._src_config.data_path}/{self._src_config.space_id}/"
                    f"{item_type_packages}/{src_package_copy_dict.get(id_key)}")
            content = self._src_common.open_local_package(package_dict=src_package_copy_dict)
        else:
            content = self._src_common.get_package(src_package_copy_dict.get(id_key))
        file_name = Common.construct_package_name(package_dict=src_package_copy_dict)
        dst_package = self._dst_common.post_package(file_name=file_name, content=content)
        if isinstance(dst_package, dict) and dst_package.get(id_key):
            self._dst_common.log_info_print(msg=f"the destination package {file_name} was created or overwritten")
            self._src_id_vs_dst_id_dict[src_package_copy_dict.get(id_key)] = dst_package.get(id_key)
            return dst_package
        else:
            self._dst_common.log_info_print(msg=f"the destination package {file_name} existed and was skipped")
            self._src_id_vs_dst_id_dict[src_package_copy_dict.get(id_key)] = src_package_copy_dict.get(id_key)
            return src_package_copy_dict

    def _clone_package(self, src_package_copy_dict: dict, src_package_dict: dict):
        # TODO fix clone historical packages from local_data
        if self._dst_config.package_history and not self._src_config.local_data:
            self._dst_common.log_info_print(
                msg=f"cloning all versions of {item_type_packages} {src_package_dict.get(package_id_key)}...")
            package_history_list = self._src_common.get_package_history_list(package_dict=src_package_dict)
            package_history_list.reverse()
            dst_package = {}
            for package_dict in package_history_list:
                self._dst_common.log_info_print(msg=f"cloning {item_type_packages} {package_dict.get(id_key)}...")
                package_dict[file_extension_key] = src_package_copy_dict.get(file_extension_key)
                package_dict[feed_id_key] = src_package_copy_dict.get(feed_id_key)
                dst_package = self._clone_single_package(src_package_copy_dict=package_dict)
            return dst_package
        else:
            self._dst_common.log_info_print(
                msg=f"cloning the latest version of {item_type_packages} {src_package_dict.get(id_key)}...")
            src_package_copy_dict[id_key] = src_package_dict.get(id_key)
            return self._clone_single_package(src_package_copy_dict=src_package_copy_dict)

    def _put_post_item_to_space(self, item_type, src_item_copy, src_item):
        src_id_value = src_item.get(id_key)
        src_item_name = src_item.get(name_key)
        self.logger.info(
            f"check if {item_type} {src_item_name} {src_id_value} in space {self._src_config.space_id} already exists"
            f" in space {self._dst_config.space_id}")
        dst_item = self._find_matched_dst_item_by_src_item(src_item_with_dst_ids=src_item_copy, item_type=item_type)
        dst_item_exist = True if dst_item else False
        if dst_item_exist:
            if self._dst_config.overwrite:
                self._dst_common.log_info_print(
                    local_logger=self.logger,
                    msg=f"destination space {self._dst_config.space_id} already has {item_type} {src_item_name} "
                        f"{dst_item.get(id_key)}, overwriting it per user request...")
                src_item_copy[id_key] = dst_item.get(id_key)

                # TODO bug in Octopus: PUT a runbook with null RunbookProcessId will remove RunbookProcessId from dst
                if item_type == item_type_runbooks and src_item.get(runbook_process_id_key):
                    matched_runbook_process_id = runbook_process_prefix + hyphen_sign + dst_item.get(id_key)
                    self.logger.warning(f"TODO bug in Octopus: PUT a runbook with null RunbookProcessId will remove "
                                        f"RunbookProcessId from dst; Reassign process id {matched_runbook_process_id} "
                                        f"for {src_item_copy.get(id_key)}")
                    src_item_copy[runbook_process_id_key] = matched_runbook_process_id

                # # TODO for update/put the version must match (maybe need later)
                # # dst_item.get(version_key) could be zero
                # if dst_item.get(version_key) is not None:
                #     self.logger.info(f"{version_key} is updated to {dst_item.get(version_key)}")
                #     src_item_copy[version_key] = dst_item.get(version_key)

                # sometimes, overwrite may not be successful due to different reasons, we can skip in most cases
                try:
                    dst_item = self._dst_common.put_single_item(item_type=item_type, payload=src_item_copy)
                    self._dst_common.log_info_print(
                        local_logger=self.logger,
                        msg=f"{item_type} {src_item_name} {src_id_value} in space {self._src_config.space_id} "
                            f"overwrote {dst_item.get(id_key)} in {self._dst_config.space_id} successfully")
                except Exception as err:
                    self._dst_common.log_error_print(
                        local_logger=self.logger, item=src_item_copy,
                        msg=f"Failed to overwrite from {item_type} {src_item_name} {src_id_value} in space "
                            f"{self._src_config.space_id} to {dst_item.get(id_key)} in {self._dst_config.space_id} "
                            f"with {err}")
            else:
                self._dst_common.log_info_print(local_logger=self.logger,
                                                msg=f"{self._dst_config.space_id} already has {item_type} "
                                                    f"{src_item_name} {dst_item.get(id_key)}, skip it per user request")
        else:
            self.logger.info(f"destination space {self._dst_config.space_id} does not have {item_type} {src_item_name} "
                             f"{src_id_value} from space {self._src_config.space_id}, so creating it...")
            # ignore error and continue to process other items
            try:
                dst_item = self._dst_common.post_single_item(item_type=item_type, payload=src_item_copy)
                self._dst_common.log_info_print(
                    local_logger=self.logger,
                    msg=f"{item_type} {src_item_name} {src_id_value} in space {self._src_config.space_id} was cloned "
                        f"to space {self._dst_config.space_id} as {dst_item.get(id_key)} successfully")
            except Exception as err:
                self._dst_common.log_error_print(
                    local_logger=self.logger, item=src_item_copy,
                    msg=f"Failed to clone {item_type} {src_item_name} {src_id_value} from space "
                        f"{self._src_config.space_id} to space {self._dst_config.space_id} with {err}")
                return None, False
        return dst_item, dst_item_exist

    def _create_item_to_space(self, item_type, src_item):
        src_id_value = src_item.get(id_key)
        src_item_name = src_item.get(name_key)

        if src_id_value in self._src_id_vs_dst_id_dict:
            dst_id_value = self._src_id_vs_dst_id_dict.get(src_id_value)
            self._dst_common.log_info_print(
                local_logger=self.logger,
                msg=f"{item_type} {src_item_name} {src_id_value} in space {self._src_config.space_id} has already "
                    f"been cloned to space {self._dst_config.space_id} as {dst_id_value} in this session; skip it")
            return dst_id_value

        self._dst_common.log_info_print(local_logger=self.logger,
                                        msg=f"cloning {item_type} {src_item_name} {src_id_value} in space "
                                            f"{self._src_config.space_id} to space {self._dst_config.space_id}")
        self.logger.info(
            f"preprocessing {item_type} {src_item_name} {src_id_value} in space {self._src_config.space_id} with the "
            f"new references in {self._dst_config.space_id}...")
        # do not modify the items in memory
        src_item_copy = copy.deepcopy(src_item)

        # some type needs additional prep-processing
        prep_process = self._type_prep_func_dict.get(item_type)
        if prep_process:
            self.logger.info(f"special preprocessing for {item_type} {src_item_name} {src_id_value} in space "
                             f"{self._src_config.space_id} with function {prep_process.__name__}")
            prep_process(src_item=src_item_copy)

        # since the destination "Id: Self-2" has not been created and saved into map
        # we do not want to recursively replace the "Id: Self-1" of the payload;
        # it would cause infinite stack and overflow
        src_item_copy.pop(id_key, None)

        self._replace_ids(dict_list=src_item_copy)

        if item_type == item_type_packages:
            try:
                dst_item = self._clone_package(src_package_copy_dict=src_item_copy, src_package_dict=src_item)
            except Exception as err:
                self._dst_common.log_error_print(
                    local_logger=self.logger, item=src_item_copy,
                    msg=f"Failed to clone package {src_item.get(id_key)}; is history packages enabled? "
                        f"{self._dst_config.package_history}; error: {err}")
                dst_item = {}
            return dst_item.get(id_key)

        dst_item, dst_item_exist = self._put_post_item_to_space(item_type=item_type, src_item_copy=src_item_copy,
                                                                src_item=src_item)
        if not dst_item:
            return None
        dst_id_value = dst_item.get(id_key)
        self.logger.info(f"add the id pair ({src_id_value}, {dst_id_value}) to the id map")
        self._src_id_vs_dst_id_dict[src_id_value] = dst_id_value
        if item_type == item_type_spaces:
            self._spaces_dict[src_id_value] = dst_id_value
        self._dst_id_payload_dict[dst_id_value] = dst_item

        post_process = self._type_post_func_dict.get(item_type)
        if post_process and (not dst_item_exist or self._dst_config.overwrite):
            self._dst_common.log_info_print(
                local_logger=self.logger,
                msg=f"Additional post-processing for {item_type} {src_item_name} {dst_id_value} in space "
                    f"{self._dst_config.space_id} with function {post_process.__name__}")
            post_process(src_id=src_id_value, dst_id=dst_id_value)

        if item_type in item_types_with_logo and (not dst_item_exist or self._dst_config.overwrite):
            try:
                self._clone_logos(item_type=item_type, src_id=src_id_value, dst_id=dst_id_value)
            except Exception as err:
                self._dst_common.log_error_print(
                    local_logger=self.logger,
                    msg=f"Failed to clone logo for {item_type} {src_id_value} to {dst_id_value} with {err}")

        return dst_id_value

    def _clone_logos(self, item_type: str, src_id: str, dst_id: str):
        self._dst_common.log_info_print(
            local_logger=self.logger, msg=f"cloning logo for type {item_type} from {src_id} to {dst_id}")
        if self._src_config.local_data:
            pattern = self._src_common.local_logo_file(item_type=item_type, item_id=src_id, ext="*")
            local_logo_files = glob.glob(pattern)
            if not local_logo_files or len(local_logo_files) == 0:
                self._dst_common.log_info_print(
                    local_logger=self.logger, msg=f"no logo file found for {item_type} {src_id}")
                return
            self._dst_common.log_info_print(local_logger=self.logger, msg=f"loading logo file {local_logo_files[0]}")
            content = open(local_logo_files[0], 'rb')
            file_name = os.path.basename(local_logo_files[0])
        else:
            content, ext = self._src_common.get_logo(item_type=item_type, item_id=src_id)
            file_name = f"{src_id}_{item_type_logo}.{ext}"
            self._dst_common.log_info_print(local_logger=self.logger, msg=f"named in-memory logo image as {file_name}")
        dst_response = self._dst_common.post_logo(
            item_type=item_type, item_id=dst_id, file_name=file_name, content=content)
        self._dst_common.log_info_print(
            local_logger=self.logger, item=dst_response, msg=f"logo was cloned successfully")

    def _clone_type_to_space(self, item_type):
        if not item_type:
            raise ValueError("item_type must not be empty!")
        self._dst_common.log_info_print(local_logger=self.logger,
                                        msg=f"cloning items in type {item_type} from {self._src_config.space_id} to "
                                            f"{self._dst_config.space_id}")
        src_list_items = self._type_src_list_items_dict.get(item_type)
        if not src_list_items:
            self.logger.warning(f"{item_type} has no items in {self._src_config.space_id}, so skip processing it")
            return

        for src_item in src_list_items:
            self._create_item_to_space(item_type=item_type, src_item=src_item)

        self.logger.info(f"Get the updated {item_type} in {self._dst_config.space_id}")
        dst_all_items = self._dst_common.get_one_type_ignore_error(item_type=item_type)
        dst_list_items = self._dst_common.get_list_items_from_all_items(all_items=dst_all_items)
        self._type_dst_list_items_dict[item_type] = dst_list_items

    # some id like "Environments-123" should be removed if this is not referenced anyway
    # most likely the entity has been removed and the reference is broken
    # TODO it is a dangerous operation; find a better way to warn people to fix the source space first
    def _check_broken_item_id(self, string):
        # if the string is one of the src or dst item ids, it is valid
        if string in self._src_id_vs_dst_id_dict.keys() or string in self._src_id_vs_dst_id_dict.values():
            return False
        for id_prefix, item_type in item_id_prefix_to_type_dict.items():
            pattern = r"{}".format("^" + id_prefix + positive_integer_regex)
            if re.match(pattern, string):
                msg = f"***** Please remove the broken reference id {string} in source space " \
                      f"{self._src_config.space_id} *****"
                self._dst_common.log_warn_print(local_logger=self.logger, msg=msg)
                return True
        return False

    # recursively replace the old link id with the new link id
    # issue: if someone crazy names an environment name as "Environments-1", not "Development" or "Prod" etc,
    # it could cause the environment renamed as "Environment-10"
    # if id_links_map contains "Environments-1" as the key and "Environments-10" as the value
    def _replace_ids(self, dict_list):
        if isinstance(dict_list, dict):
            # self.logger.info(f"dict_list is a dict, replace ids or delete broken ids")
            # directly use dict_list.items() or dict_list.keys() could cause unexpected result
            # due to dict.pop(key) while iterating
            keys = copy.deepcopy(list(dict_list.keys()))
            for key in keys:
                value = dict_list.get(key)
                if isinstance(value, str):
                    if value in self._src_id_vs_dst_id_dict:
                        dict_list[key] = self._src_id_vs_dst_id_dict.get(value)
                        self.logger.info(
                            f"the reference value {value} has already been created in space {self._dst_config.space_id}"
                            f" as {dict_list.get(key)}")
                    elif value in self._src_id_payload_dict:
                        self.logger.info(
                            f"the reference value {value} exists in the source space but has not been cloned "
                            f"into the destination space, so clone it first in the destination space")
                        dict_list[key] = self._clone_item_to_space(item_type=self._src_id_type_dict.get(value),
                                                                   item_id=value)
                        self.logger.info(f"the reference value {value} was cloned/found and replaced with "
                                         f"{dict_list.get(key)}")
                    # remove the broken reference ids
                    elif self._check_broken_item_id(string=value):
                        self.logger.warning(
                            f"the reference value {value} is a broken reference id, so assign null to it")
                        dict_list[key] = None
                else:
                    self._replace_ids(dict_list=value)
                if isinstance(key, str):
                    if key in self._src_id_vs_dst_id_dict:
                        new_key = self._src_id_vs_dst_id_dict.get(key)
                        dict_list[new_key] = dict_list.pop(key)
                        self.logger.info(f"the reference key {key} has already been created in space "
                                         f"{self._dst_config.space_id} as {new_key}")
                    elif key in self._src_id_payload_dict:
                        self.logger.info(f"the reference key {key} exists in the source space but has not been cloned "
                                         f"into the destination space, so clone it first in the destination space")
                        new_key = self._clone_item_to_space(item_type=self._src_id_type_dict.get(key), item_id=key)
                        dict_list[new_key] = dict_list.pop(key)
                        self.logger.info(f"the reference key {key} was cloned/found and replaced with {new_key}")
                    # remove the broken reference ids
                    elif self._check_broken_item_id(string=key):
                        self.logger.warning(f"Key {value} is a broken reference id, so pop it")
                        dict_list.pop(key)
                else:
                    self._replace_ids(dict_list=key)
        elif isinstance(dict_list, list):
            # self.logger.info(f"dict_list is a list, replace ids or delete broken ids")
            # we must do reversely to avoid unexpected result on deleting by index
            for index in range(len(dict_list) - 1, -1, -1):
                element = dict_list[index]
                if isinstance(element, str):
                    if element in self._src_id_vs_dst_id_dict:
                        dict_list[index] = self._src_id_vs_dst_id_dict.get(element)
                        self.logger.info(
                            f"the reference element {element} has already been created in space "
                            f"{self._dst_config.space_id} as {dict_list[index]}")
                    elif element in self._src_id_payload_dict:
                        self.logger.info(
                            f"the reference element {element} exists in the source space but has not been "
                            f"cloned into the destination space, so clone it first in the destination space")
                        dict_list[index] = self._clone_item_to_space(item_type=self._src_id_type_dict.get(element),
                                                                     item_id=element)
                        self.logger.info(f"the reference element {element} was cloned/found and replaced with "
                                         f"{dict_list[index]}")
                    elif self._check_broken_item_id(string=element):
                        self.logger.warning(f"element {element} is a broken reference id, so delete it; index {index}")
                        del dict_list[index]
                else:
                    self._replace_ids(dict_list=element)
        # None, boolean, integer, float etc
        else:
            pass
            # self.logger.info(f"the type is {type(dict_list)} and value is {dict_list}; skip it")

    def _clone_child(self, src_parent_id, dst_parent_id, child_type, child_id_key):
        # source item
        parent_type = self._src_id_type_dict.get(src_parent_id)
        src_parent = self._src_id_payload_dict.get(src_parent_id)
        src_child_id = src_parent.get(child_id_key)
        parent_name = src_parent.get(name_key)

        # destination item
        dst_parent = self._dst_id_payload_dict.get(dst_parent_id)
        dst_child_id = dst_parent.get(child_id_key)
        self._src_id_vs_dst_id_dict[src_child_id] = dst_child_id

        self.logger.info(
            f"cloning {parent_type} {parent_name}'s {child_id_key} {src_child_id} from {self._src_config.space_id} to "
            f"{self._dst_config.space_id}...")
        src_child = self._src_id_payload_dict.get(src_child_id)

        # ignore cloning child error due to permission and other misc issues
        try:
            # TODO Octopus bug https://help.octopus.com/t/504-gateway-time-out-on-getting-all-variables/24732
            if not src_child:
                self.logger.warning(
                    f"{src_child_id} does not exist in the memory, so get it from {self._src_config.space_id}")
                src_child = self._src_common.get_single_item_by_name_or_id(item_type=child_type, item_id=src_child_id)
                self._src_id_payload_dict[src_child_id] = src_child
            dst_child = self._dst_common.get_single_item_by_name_or_id(item_type=child_type, item_id=dst_child_id)
        except Exception as err:
            self._dst_common.log_error_print(local_logger=self.logger, msg=err)
            return dst_child_id

        src_child_copy = copy.deepcopy(src_child)
        # this is for cloning runbooks, channels, or projecttriggers from one project to other projects
        if src_child_copy.get(project_id_key) and self._project_id:
            src_child_copy[project_id_key] = self._project_id

        # TODO ScopeValues seems redundant in variables; ScopeValues defines a general scope to be used for variable set
        # but ScopeValues does not scope a specific variable at all; ScopeValues in variable set payload not very useful
        # if ScopeValues is not popped, all scopes will be cloned recursively even if some of them are not used at all  
        src_child_copy.pop(scope_values_key, None)

        self._replace_ids(dict_list=src_child_copy)

        # for update/put the version must match; dst_child.get(version_key) could be zero
        if dst_child.get(version_key) is not None:
            self.logger.info(f"child {version_key} is updated to {dst_child.get(version_key)}")
            src_child_copy[version_key] = dst_child.get(version_key)

        # sometimes, overwrite may not be successful due to different reasons, we can skip in most cases
        try:
            dst_child = self._dst_common.put_single_item(item_type=child_type, payload=src_child_copy)
            self._dst_common.log_info_print(
                local_logger=self.logger,
                msg=f"Finished overwriting {parent_type} {parent_name}'s {child_type} {src_child_id} from "
                    f"{self._src_config.space_id} to {self._dst_config.space_id} as {dst_child_id} successfully")
        except Exception as err:
            self._dst_common.log_error_print(
                local_logger=self.logger, item=src_child_copy,
                msg=f"Failed to overwrite {parent_type} {parent_name}'s {child_type} {src_child_id} from "
                    f"{self._src_config.space_id} to {self._dst_config.space_id} as {dst_child_id} with {err}")

        self._dst_id_payload_dict[dst_child_id] = dst_child
        return dst_child_id

    # deployment processes are not really created as new; once a project is created, the deployment process is
    # created automatically; so we need to copy the deployment processes from the source space into the destination
    # space matching the same projects; the API call is "PUT" not "POST"
    # same for the variables
    def _post_process_project(self, src_id, dst_id):
        self._dst_common.log_info_print(
            local_logger=self.logger,
            msg=f"clone {item_type_deployment_processes} from {item_type_projects} {src_id} in "
                f"{self._src_config.space_id} to {dst_id} in {self._dst_config.space_id}")
        self._clone_child(src_parent_id=src_id, dst_parent_id=dst_id, child_type=item_type_deployment_processes,
                          child_id_key=deployment_process_id_key)
        self._dst_common.log_info_print(
            local_logger=self.logger,
            msg=f"clone {item_type_variables} from {item_type_projects} {src_id} in {self._src_config.space_id} "
                f"to {dst_id} in {self._dst_config.space_id}")
        self._clone_child(src_parent_id=src_id, dst_parent_id=dst_id, child_type=item_type_variables,
                          child_id_key=variable_set_id_key)

    def _post_process_library_variable_set(self, src_id, dst_id):
        self._dst_common.log_info_print(
            local_logger=self.logger,
            msg=f"clone {item_type_variables} from {item_type_library_variable_sets} {src_id} in "
                f"{self._src_config.space_id} to {dst_id} in {self._dst_config.space_id}")
        self._clone_child(src_parent_id=src_id, dst_parent_id=dst_id, child_type=item_type_variables,
                          child_id_key=variable_set_id_key)

    def _post_process_runbook(self, src_id, dst_id):
        self._dst_common.log_info_print(
            local_logger=self.logger,
            msg=f"clone {item_type_runbook_processes} from {item_type_runbooks} {src_id} in "
                f"{self._src_config.space_id} to {dst_id} in {self._dst_config.space_id}")
        self._clone_child(src_parent_id=src_id, dst_parent_id=dst_id, child_id_key=runbook_process_id_key,
                          child_type=item_type_runbook_processes)

    # tenant variables is special and its id is also tenant id, such as "Tenants-401"
    # so you have to use a separate map to store the tenants variables
    # also put/post tenant variables uses a different url from put variables
    def _post_process_tenant_variables(self, src_id, dst_id):
        self._dst_common.log_info_print(local_logger=self.logger,
                                        msg=f"clone {item_type_tenant_variables} from {item_type_tenants} {src_id} in "
                                            f"{self._src_config.space_id} to {dst_id} in {self._dst_config.space_id}")
        src_tenant_variables = self._src_tenant_variables_payload_dict.get(src_id)
        src_tenant_variables_copy = copy.deepcopy(src_tenant_variables)

        self._replace_ids(dict_list=src_tenant_variables_copy)

        # sometimes, overwrite may not be successful due to different reasons, we can skip in most cases
        try:
            dst_tenant_variables = \
                self._dst_common.put_post_tenant_variables(tenant_id=dst_id, tenant_variables=src_tenant_variables_copy)
            self._dst_common.log_info_print(
                local_logger=self.logger,
                msg=f"Finished overwriting {item_type_tenant_variables} from {item_type_tenants} {src_id} in "
                    f"{self._src_config.space_id} to {dst_id} in {self._dst_config.space_id} successfully")
        except Exception as err:
            dst_tenant_variables = self._dst_common.get_tenant_variables(tenant_id=dst_id)
            self._dst_common.log_error_print(
                local_logger=self.logger, item=src_tenant_variables_copy,
                msg=f"Failed to overwrite {item_type_tenant_variables} from {item_type_tenants} {src_id} in "
                    f"{self._src_config.space_id} to {dst_id} in {self._dst_config.space_id} with {err}")

        self._dst_tenant_variables_payload_dict[dst_id] = dst_tenant_variables

    # TODO how to process new item name in pars_dict
    def _full_process_tags(self, item_type, item_id, item_name=None, pars_dict: dict = None):
        self._dst_common.log_info_print(
            local_logger=self.logger,
            msg=f"special full process - clone {item_type} {item_name} {item_id} from {self._src_config.space_id} "
                f"to {self._dst_config.space_id}; TODO: tags need to honor parameters {pars_dict}")
        tag_set_name = item_id.split(slash_sign)[0]
        src_list_tag_sets = self._type_src_list_items_dict.get(item_type_tag_sets)
        src_tag_set = find_item(lst=src_list_tag_sets, key=name_key, value=tag_set_name)
        src_tag = self._src_id_payload_dict.get(item_id)
        src_tag_copy = copy.deepcopy(src_tag)
        src_tag_copy.pop(id_key, None)
        dst_tag_set = self._find_matched_dst_item_by_src_item(src_item_with_dst_ids=src_tag_set,
                                                              item_type=item_type_tag_sets)
        if dst_tag_set:
            self.logger.info(f"{item_type_tag_sets} {dst_tag_set.get(name_key)} exists in {self._dst_config.space_id}, "
                             f"so try to find {item_id}")
            if not find_item(lst=dst_tag_set.get(tags_key), key=canonical_tag_name_key, value=item_id):
                self.logger.info(f"{item_type_tag_sets} {dst_tag_set.get(name_key)} does not have {item_id} in "
                                 f"{self._dst_config.space_id}, add it")
                dst_tag_set.get(tags_key).append(src_tag_copy)
                try:
                    dst_tag_set = self._dst_common.put_single_item(item_type=item_type_tag_sets, payload=dst_tag_set)
                    self._dst_common.log_info_print(
                        local_logger=self.logger,
                        msg=f"overwrote {item_type} {item_name} {item_id} from {self._src_config.space_id} to "
                            f"{self._dst_config.space_id} successfully")
                except Exception as err:
                    self._dst_common.log_error_print(
                        local_logger=self.logger, item=dst_tag_set,
                        msg=f"Failed to overwrite {item_type} {item_name} {item_id} from {self._src_config.space_id} to"
                            f" {self._dst_config.space_id} unsuccessfully with {err}")
            else:
                self.logger.info(f"{item_type_tag_sets} {dst_tag_set.get(name_key)} already has {item_id} in "
                                 f"{self._dst_config.space_id}, skip")
        else:
            self.logger.info(
                f"{item_type_tag_sets} {dst_tag_set.get(name_key)} does not exist in {self._dst_config.space_id}, "
                f"so create it with {item_type_tags} {item_id}")
            dst_tag_set = copy.deepcopy(src_tag_set)
            dst_tag_set.pop(id_key, None)
            dst_tag_set[tags_key] = [src_tag_copy]
            # ignore error and continue to process other items
            try:
                dst_tag_set = self._dst_common.post_single_item(item_type=item_type_tag_sets, payload=dst_tag_set)
                self._dst_common.log_info_print(
                    local_logger=self.logger,
                    msg=f"cloned {item_type} {item_name} {item_id} from {self._src_config.space_id} to "
                        f"{self._dst_config.space_id} successfully")
            except Exception as err:
                self._dst_common.log_error_print(
                    local_logger=self.logger, item=dst_tag_set,
                    msg=f"Failed to clone {item_type} {item_name} {item_id} from {self._src_config.space_id} to "
                        f"{self._dst_config.space_id} with {err}")
        self._src_id_vs_dst_id_dict[item_id] = item_id
        self._dst_id_payload_dict[item_id] = find_item(lst=dst_tag_set.get(tags_key), key=canonical_tag_name_key,
                                                       value=item_id)
        return item_id

    def _load_types(self):
        if self._src_config.local_data:
            self._dst_common.log_info_print(
                local_logger=self.logger,
                msg=f"Reading files {self._all_types} from local source {self._src_config.space_id}...")
        else:
            self._dst_common.log_info_print(
                local_logger=self.logger,
                msg=f"Downloading {self._all_types} from space {self._src_config.space_id}...")
        actual_src_space_id = None
        for item_type in self._all_types:
            if self._src_config.local_data:
                self._dst_common.log_info_print(
                    local_logger=self.logger,
                    msg=f"Loading {item_type} in {self._src_config.space_id} from the local file...")
                src_list_items = self._src_common.get_list_items_from_file(item_type=item_type)
            else:
                self._dst_common.log_info_print(
                    local_logger=self.logger,
                    msg=f"Loading {item_type} from source space {self._src_config.space_id}...")
                src_list_items = self._src_common.get_list_from_one_type(item_type=item_type)
            selected_src_list_items = []
            for src_item in src_list_items:
                if not actual_src_space_id and self._src_config.local_data and item_type == item_type_projects \
                        and src_item.get(space_id_key):
                    actual_src_space_id = src_item.get(space_id_key)
                    self.logger.info(f"the actual source space id is {actual_src_space_id}; the local one is "
                                     f"{self._src_config.space_id}")
                if not self._src_config.space_id and src_item.get(space_id_key) \
                        or item_type == item_type_scoped_user_roles \
                        and self._src_config.space_id != src_item.get(space_id_key):
                    self.logger.info(f"skip loading {item_type} - source space id {self._src_config.space_id} - source "
                                     f"item space id {src_item.get(space_id_key)}")
                    continue
                # TODO some items are a pure list of strings, they might be useful in the future, like variables/names
                if isinstance(src_item, str):
                    self.logger.warning(f"{item_type} {src_item} is ignored when loading")
                elif isinstance(src_item, dict) and src_item.get(id_key):
                    self._src_id_payload_dict[src_item.get(id_key)] = src_item
                    self._src_id_type_dict[src_item.get(id_key)] = item_type
                    selected_src_list_items.append(src_item)
                elif isinstance(src_item, dict) and src_item.get(tenant_id_key):
                    self._src_tenant_variables_payload_dict[src_item.get(tenant_id_key)] = src_item
                else:
                    log_raise_value_error(local_logger=self.logger, item=src_item, err=f"{item_type} is not valid")
            self._type_src_list_items_dict[item_type] = selected_src_list_items
        if self._src_config.local_data and not actual_src_space_id:
            log_raise_value_error(local_logger=self.logger,
                                  err=f"Could not find an actual space id inside the local source "
                                      f"{self._src_config.space_id}")
        return actual_src_space_id if actual_src_space_id else self._src_config.space_id

    def _prep_tag_sets(self):
        self._dst_common.log_info_print(local_logger=self.logger, msg="prepare for all tags")
        src_list_tag_sets = self._type_src_list_items_dict.get(item_type_tag_sets)
        for src_tag_set in src_list_tag_sets:
            for src_tag in src_tag_set.get(tags_key):
                canonical_tag_name = src_tag.get(canonical_tag_name_key)
                self._src_id_payload_dict[canonical_tag_name] = src_tag
                self._src_id_type_dict[canonical_tag_name] = item_type_tags

    def _initialize_maps(self):
        self._dst_common.log_info_print(local_logger=self.logger,
                                        msg=f"initialize the map")
        self._type_prep_func_dict[item_type_accounts] = self._prepare_account
        self._type_prep_func_dict[item_type_feeds] = self._prepare_feed
        self._type_prep_func_dict[item_type_library_variable_sets] = self._prepare_library_variable_set
        self._type_prep_func_dict[item_type_projects] = self._prepare_project
        self._type_prep_func_dict[item_type_runbooks] = self._prepare_runbook
        self._type_prep_func_dict[item_type_spaces] = self._prepare_space
        self._type_prep_func_dict[item_type_tag_sets] = self._prepare_tag_set
        self._type_prep_func_dict[item_type_users] = self._prepare_user

        self._type_post_func_dict[item_type_library_variable_sets] = self._post_process_library_variable_set
        self._type_post_func_dict[item_type_projects] = self._post_process_project
        self._type_post_func_dict[item_type_runbooks] = self._post_process_runbook
        self._type_post_func_dict[item_type_tenants] = self._post_process_tenant_variables

        self._type_full_func_dict[item_type_tags] = self._full_process_tags

        actual_src_space_id = self._load_types()

        if self._src_config.local_data:
            self._src_id_vs_dst_id_dict[actual_src_space_id] = self._dst_config.space_id
        else:
            self._src_id_vs_dst_id_dict[self._src_config.space_id] = self._dst_config.space_id

        if item_type_tag_sets in self._all_types:
            self._prep_tag_sets()

    def _save_space_map(self):
        current_time = strftime("%Y-%m-%d-%H-%M-%S", gmtime())
        local_file = self._dst_common.get_local_single_item_file(item_name=space_map + underscore_sign + current_time,
                                                                 item_type=item_type_migration)
        self._dst_common.log_info_print(local_logger=self.logger, msg=f"writing item id map to {local_file}")
        save_file(file_path_name=local_file, content=self._src_id_vs_dst_id_dict)
        self._dst_common.log_info_print(local_logger=self.logger, msg=f"***** data migration/clone is DONE! *****")

    def clone_space(self, item_types_comma_delimited=None):
        if item_types_comma_delimited:
            process_types = item_types_comma_delimited.split(comma_sign)
        else:
            process_types = inside_space_clone_types
        self._dst_common.log_info_print(
            local_logger=self.logger,
            msg=f"cloning types {process_types} from {self._src_config.space_id} on server {self._src_config.endpoint}"
                f" to {self._dst_config.space_id} on server {self._dst_config.endpoint}")
        if not self._dst_config.overwrite:
            self._dst_config.overwrite = input(
                f"Some entities may already exist in {self._dst_config.space_id} on server {self._dst_config.endpoint};"
                f" Do you want to overwrite the existing entities? "
                f"If no, we will skip the existing entities. [Y/n]: ") == 'Y'
        self._dst_config.types = process_types
        self.clone_space_types()

    def clone_space_types(self):
        self._dst_common.log_info_print(
            local_logger=self.logger,
            msg=f"cloning types {self._dst_config.types} from {self._src_config.space_id} on server "
                f"{self._src_config.endpoint} to {self._dst_config.space_id} on server {self._dst_config.endpoint}")
        self._all_types = inside_space_download_types
        self._initialize_maps()
        for item_type in self._dst_config.types:
            if item_type in inside_space_clone_types:
                self._clone_type_to_space(item_type=item_type)
        self._save_space_map()

    def clone_space_item(self, item_type, item_name=None, item_id=None):
        item_badge = item_name if item_name else item_id
        self._dst_common.log_info_print(
            local_logger=self.logger,
            msg=f"cloning {item_type} {item_badge} from {self._src_config.space_id} on server "
                f"{self._src_config.endpoint} to {self._dst_config.space_id} on server {self._dst_config.endpoint}")
        if not self._dst_config.overwrite:
            self._dst_config.overwrite = input(
                f"Some entities may already exist in {self._dst_config.space_id} on server {self._dst_config.endpoint};"
                f" Do you want to overwrite the existing entities? "
                f"If no, we will skip the existing entities. [Y/n]: ") == 'Y'
        self._dst_config.type = item_type
        self._src_config.item_id = item_id
        self._src_config.item_name = item_name
        self.clone_space_item_new_name()

    def clone_space_item_new_name(self, pars_dict: dict = None):
        item_type = self._dst_config.type
        item_name = self._src_config.item_name
        item_id = self._src_config.item_id
        item_badge = item_name if item_name else item_id
        self._dst_common.log_info_print(
            local_logger=self.logger,
            msg=f"cloning {item_type} {item_badge} from {self._src_config.space_id} on server "
                f"{self._src_config.endpoint} to {self._dst_config.space_id} on server {self._dst_config.endpoint}"
                f"with parameters {pars_dict}")
        self._all_types = inside_space_download_types
        self._initialize_maps()
        if item_type in inside_space_clone_types:
            self._clone_item_to_space(item_type=item_type, item_name=item_name, item_id=item_id, pars_dict=pars_dict)
        self._save_space_map()

    def clone_server(self, space_id_or_name_comma_delimited=None, item_types_comma_delimited=None):
        list_space_ids = self._src_common.get_list_spaces_ids_sorted(
            space_id_or_name_comma_delimited=space_id_or_name_comma_delimited)
        self._dst_common.log_info_print(
            local_logger=self.logger,
            msg=f"cloning outer space and {list_space_ids} for item types {item_types_comma_delimited} from server "
                f"{self._src_config.endpoint} to server {self._dst_config.endpoint}")

        if input(f"Are you sure you want to clone server to server? If yes, your permission on the destination "
                 f"server could be overwritten and revoked (default password is {default_password} [Y/n]: ") != 'Y':
            return

        if not self._dst_config.overwrite:
            self._dst_config.overwrite = input(
                f"Some entities may already exist in server {self._dst_config.endpoint}; "
                f"Do you want to overwrite the existing entities? "
                f"If no, we will skip the existing entities. [Y/n]: ") == 'Y'

        # outer space
        self._all_types = outer_space_clone_types
        self._initialize_maps()
        for item_type in outer_space_clone_types:
            self._clone_type_to_space(item_type=item_type)
        self._dst_common.log_info_print(item=self._spaces_dict,
                                        msg=f"see log for space id map from source server to dest server")

        # inside space
        for src_space_id in list_space_ids:
            dst_space_id = self._spaces_dict.get(src_space_id)
            self._dst_common.log_info_print(msg=f"clone {src_space_id} on server {self._src_config.endpoint} to "
                                                f"{dst_space_id} on server {self._dst_config.endpoint}")
            self._src_config.space_id = src_space_id
            self._dst_config.space_id = dst_space_id
            self.clone_space(item_types_comma_delimited=item_types_comma_delimited)
        self._save_space_map()
