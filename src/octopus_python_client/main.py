import argparse
import logging
import os
import sys

from octopus_python_client.actions import Actions, MIGRATION_LIST
from octopus_python_client.common import item_type_deployment_processes, outer_space_download_types, steps_key, \
    inside_space_download_types, deployment_process_id_key, Common
from octopus_python_client.config import Config, SystemConfig
from octopus_python_client.constants import Constants
from octopus_python_client.deployment_processes import DeploymentProcesses
from octopus_python_client.migration import Migration
from octopus_python_client.projects import Projects
from octopus_python_client.release_deployment import ReleaseDeployment
from octopus_python_client.utilities.helper import log_raise_value_error

logger = logging.getLogger(__name__)


class OctopusClient:

    def __init__(self):
        self._target_config = Config()
        self._target_common = Common(config=self._target_config)
        self._source_config = Config(is_source_server=True)
        self._source_common = Common(config=self._source_config)

    @staticmethod
    def _parse_args():
        parser = argparse.ArgumentParser()
        parser.add_argument("-v", "--version", help="if present, print the version information", action="store_true")
        parser.add_argument("-o", "--endpoint", help="octopus endpoint")
        parser.add_argument("-s", "--space_id_name", help="octopus space id or name")
        parser.add_argument("-m", "--pem", help="octopus endpoint root pem file path; -m=false to disable pem")
        parser.add_argument("-sps", "--spaces",
                            help='list of octopus space id or name, like "my space,Spaces-1,Spaces-2"')
        parser.add_argument("-d", "--data_path",
                            help="the local path for the Octopus server data, 'current' = the current work path")
        parser.add_argument("-k", "--api_key",
                            help="api key for octopus; either api_key or user_name and password are required")
        parser.add_argument("-user", "--user_name",
                            help="user_name for octopus; either api_key or user_name and password are required")
        parser.add_argument("-pass", "--password",
                            help="password for octopus; either api_key or user_name and password are required")
        parser.add_argument("-sre", "--source_endpoint", help="source octopus endpoint for clone")
        parser.add_argument("-srd", "--source_data_path",
                            help="the local path for the source Octopus server data, 'current' = the current work path")
        parser.add_argument("-srk", "--source_api_key",
                            help="api key for octopus; either api_key or user_name and password are required")
        parser.add_argument("-sru", "--source_user_name",
                            help="user_name for octopus; either api_key or user_name and password are required")
        parser.add_argument("-srp", "--source_password",
                            help="password for octopus; either api_key or user_name and password are required")
        parser.add_argument("-srs", "--source_space_id_name",
                            help="source octopus space id or name for clone/migration")
        parser.add_argument("-srm", "--source_pem",
                            help="source octopus endpoint root pem file path; -srm=false to disable pem")
        parser.add_argument("-ld", "--local_data", help="if present, local_data = True; the source server/space "
                                                        "data are stored as YAML files locally", action="store_true")
        parser.add_argument("-a", "--action", help=str(Actions.__dict__.values()))
        parser.add_argument("-ow", "--overwrite", help="if present, overwrite = True", action="store_true")
        parser.add_argument("-ns", "--no_stdout", help="if present, no_stdout = True, means no stdout",
                            action="store_true")
        parser.add_argument("-ts", "--item_types",
                            help="if not item_types and not octopus_space_id, get all item types "
                                 "regardless whether they are above Spaces; if (not item_types) and octopus_space_id, "
                                 "get all item types below octopus_space_id; "
                                 'list like "accounts,actiontemplates,artifacts" is also accepted; '
                                 "item types above Spaces: " + ", ".join(outer_space_download_types) +
                                 "; \nitem types above and under Spaces: " + ", ".join(inside_space_download_types))
        parser.add_argument("-tp", "--item_type", help="one of item types above Spaces: " + ", ".join(
            outer_space_download_types) + "; \nitem types above and under Spaces: " + ", ".join(
            inside_space_download_types))
        parser.add_argument("-nm", "--item_name", help="item name: e.g. project_name")
        parser.add_argument("-id", "--item_id", help="item id: e.g. Lifecycles-1")
        parser.add_argument("-bn", "--base_item_name", help="base item name, either local or on Octopus server")
        parser.add_argument("-pn", "--parent_name", help="parent item name: e.g. project_name")
        parser.add_argument("-pt", "--parent_type", help="parent item type: e.g. projects")
        parser.add_argument("-ct", "--child_type", help=f"child item type: e.g. {item_type_deployment_processes}")
        parser.add_argument("-ck", "--child_id_key", help=f"child id key: e.g. {deployment_process_id_key}")
        parser.add_argument("-sk", "--sub_item_key",
                            help=f"sub-item key: this sub-item is for copy/clone e.g. {steps_key}")
        parser.add_argument("-bp", "--base_parent_name", help="base parent item name: e.g. a base project_name")
        parser.add_argument("-sn", "--step_name", help="step name as in octopus process")
        parser.add_argument("-bs", "--base_step_name", help="base step name as in octopus process for cloning a step")
        parser.add_argument("-ps", "--prev_step_name",
                            help="previous step name in octopus process for the step insertion location")
        parser.add_argument("-tl", "--time_limit_second", help="time limit in second")
        parser.add_argument("-rv", "--release_version", help="release version for creating a new release")
        parser.add_argument("-as", "--add_suffix",
                            help="if present, add suffix to variable sets name")
        parser.add_argument("-rs", "--remove_suffix", help="if present, remove suffix from variable sets name")
        parser.add_argument("-pj", "--project_name", help="project name")
        parser.add_argument("-cn", "--channel_name", help="channel name")
        parser.add_argument("-nt", "--notes", help="notes")
        parser.add_argument("-ri", "--release_id", help="release id for deployment")
        parser.add_argument("-en", "--environment_name", help="environment name, like Integration")
        parser.add_argument("-tn", "--tenant_name", help="tenant name, like cd-near")
        parser.add_argument("-cm", "--comments", help="comments")
        parser.add_argument("-eps", "--excluded_projects", help="comma delimited project names")
        parser.add_argument("-pgs", "--project_groups", help="comma delimited project group names")
        parser.add_argument("-pkg", "--package_history", help="if present, package_history = True", action="store_true")

        args, unknown = parser.parse_known_args()
        return args

    def _process_args_to_configs(self):
        args = self._parse_args()
        if args.action:
            self._target_config.action = args.action
        elif args.version:
            print(SystemConfig.TITLE)
            sys.exit()
        else:
            print(Constants.TO_RUN_GUI)
            sys.exit()

        if args.endpoint:
            self._target_config.endpoint = args.endpoint
        assert self._target_config.endpoint.endswith("/api/"), \
            f"octopus endpoint must end with /api/; {self._target_config.endpoint} is invalid"

        if args.data_path == Config.USE_CURRENT_DATA_PATH:
            self._target_config.data_path = os.getcwd()
        elif args.data_path:
            self._target_config.data_path = args.data_path

        if args.api_key and args.api_key.startswith("API-"):
            self._target_config.api_key = args.api_key
        elif args.api_key or args.api_key == "":
            self._target_common.log_info_print(
                msg=f"The octopus API-KEY does not start with 'API-'; so use user/password instead")
            self._target_config.api_key = ""

        if args.user_name:
            self._target_config.user_name = args.user_name
        if args.password:
            self._target_config.password = args.password
        assert self._target_config.api_key or (self._target_config.user_name and self._target_config.password), \
            f"either api_key or user_name and password are required"

        if args.pem and args.pem.lower() == "false":
            self._target_config.pem = False
        elif args.pem:
            self._target_config.pem = args.pem

        self._target_config.overwrite = args.overwrite
        logger.info(f"self._target_config.overwrite: {self._target_config.overwrite}")
        self._target_config.no_stdout = args.no_stdout
        logger.info(f"self._target_config.no_stdout: {self._target_config.no_stdout}")
        self._target_config.package_history = args.package_history
        logger.info(f"self._target_config.package_history: {self._target_config.package_history}")

        if args.space_id_name:
            self._target_config.space_id = self._target_common.verify_space(space_id_name=args.space_id_name)
            if self._target_config.space_id:
                logger.info(f"the target space_id is: {self._target_config.space_id}")
            else:
                raise ValueError(f"the space id/name {args.space_id_name} you specified does not exist or "
                                 f"you do not have permission to access it on server {self._target_config.endpoint}")

        if args.action != Actions.ACTION_GET_SPACES and not self._target_config.space_id \
                and input(f"Are you sure you want to run a command against {None} space [Y/n]? ") != "Y":
            return

        if args.action in MIGRATION_LIST:
            self._target_common.log_info_print(msg=f"===== Action: {args.action}; processing the source config =====")

            self._source_config.local_data = args.local_data
            logger.info(f"self._source_config.local_data: {self._source_config.local_data}")
            if args.source_endpoint:
                self._source_config.endpoint = args.source_endpoint
            assert self._source_config.local_data or self._source_config.endpoint.endswith("/api/"), \
                f"octopus endpoint must end with /api/; {self._source_config.endpoint} is invalid"

            if args.source_data_path == Config.USE_CURRENT_DATA_PATH:
                self._source_config.data_path = os.getcwd()
            elif args.source_data_path:
                self._source_config.data_path = args.source_data_path
            if args.local_data and self._target_config.endpoint != self._source_config.endpoint \
                    and self._target_config.data_path == self._source_config.data_path:
                raise ValueError(f"the source Octopus server {self._source_config.endpoint} and the target "
                                 f"Octopus server {self._target_config.endpoint} cannot use the same local "
                                 f"path {self._target_config.data_path} if cloning source is the local data")

            if args.source_api_key and args.source_api_key.startswith("API-"):
                self._source_config.api_key = args.source_api_key
            elif args.source_api_key or args.source_api_key == "":
                self._target_common.log_info_print(
                    msg=f"The source octopus API-KEY does not start with 'API-'; so use user/password instead")
                self._source_config.api_key = ""

            if args.source_user_name:
                self._source_config.user_name = args.source_user_name
            if args.source_password:
                self._source_config.password = args.source_password
            assert self._source_config.api_key or (self._source_config.user_name and self._source_config.password), \
                f"either api_key or user_name and password are required"

            if args.source_pem and args.source_pem.lower() == "false":
                self._source_config.pem = False
            elif args.source_pem:
                self._source_config.pem = args.source_pem

            if args.source_space_id_name:
                self._source_config.space_id = self._source_common.verify_space(space_id_name=args.source_space_id_name)
                if self._source_config.space_id:
                    self._target_common.log_info_print(msg=f"The source octopus space_id is: "
                                                           f"{self._source_config.space_id}")
                elif self._source_config.local_data:
                    self._target_common.log_info_print(
                        msg=f"{args.action} from local source data {args.source_space_id_name}")
                    self._source_config.space_id = args.source_space_id_name
            if not self._source_config.space_id and not self._source_config.local_data:
                raise ValueError(f"On Octopus server {self._source_config.endpoint}, the space id/name "
                                 f"{args.source_space_id_name} does not exist or you do not have permission to "
                                 f"access it.")

            if self._source_config.endpoint == self._target_config.endpoint:
                if args.action == Actions.ACTION_CLONE_SERVER:
                    raise ValueError(f"Cannot {args.action} from an endpoint to the same one: "
                                     f"{self._source_config.endpoint}")
                elif self._source_config.space_id == self._target_config.space_id:
                    raise ValueError(f"Cannot {args.action} from a space to the same space "
                                     f"{self._source_config.space_id} on the same Octopus server "
                                     f"{self._source_config.endpoint}")

            if args.action == Actions.ACTION_CLONE_SERVER:
                self._target_common.log_info_print(msg=f"{args.action} from {self._source_config.endpoint} to "
                                                       f"{self._target_config.endpoint}; space ids are cleared")
                self._source_config.space_id = None
                self._target_config.space_id = None
            elif not self._source_config.space_id or not self._target_config.space_id:
                raise ValueError(f"Cannot {args.action} from space {self._source_config.space_id} of the source "
                                 f"Octopus server {self._source_config.endpoint} to space "
                                 f"{self._target_config.space_id} of the target Octopus server "
                                 f"{self._target_config.endpoint}")

            self._source_config.save_config()

        self._target_config.save_config()

        return args

    def run(self):
        args = self._process_args_to_configs()

        if self._target_config.action == Actions.ACTION_GET_SPACES:
            self._target_common.get_spaces_save(item_types_comma_delimited=args.item_types,
                                                space_id_or_name_comma_delimited=args.spaces)
        elif self._target_config.action == Actions.ACTION_GET_TYPES:
            self._target_common.get_types_save(item_types_comma_delimited=args.item_types)
        elif self._target_config.action == Actions.ACTION_GET_TYPE:
            self._target_common.get_one_type_save(item_type=args.item_type)
        elif self._target_config.action == Actions.ACTION_DELETE_TYPE:
            self._target_common.delete_one_type(item_type=args.item_type)
        elif self._target_config.action == Actions.ACTION_DELETE_TYPES:
            self._target_common.delete_types(item_types_comma_delimited=args.item_types)
        elif self._target_config.action == Actions.ACTION_GET:
            self._target_common.get_single_item_by_name_or_id_save(item_type=args.item_type, item_name=args.item_name,
                                                                   item_id=args.item_id)
        elif self._target_config.action == Actions.ACTION_UPDATE:
            self._target_common.update_single_item_save(item_type=args.item_type, item_name=args.item_name,
                                                        item_id=args.item_id)
        elif self._target_config.action == Actions.ACTION_UPDATE_MERGE:
            self._target_common.merge_single_item_save(item_type=args.item_type, item_name=args.item_name,
                                                       item_id=args.item_id, child_id_key=args.child_id_key)
        elif self._target_config.action == Actions.ACTION_CREATE:
            self._target_common.create_single_item_from_local_file(item_type=args.item_type, item_name=args.item_name,
                                                                   local_item_name=args.base_item_name)
        elif self._target_config.action == Actions.ACTION_CLONE:
            self._target_common.clone_single_item_from_remote_item(item_type=args.item_type, item_name=args.item_name,
                                                                   base_item_name=args.base_item_name)
        elif self._target_config.action == Actions.ACTION_DELETE:
            self._target_common.delete_single_item_by_name_or_id(item_type=args.item_type, item_name=args.item_name,
                                                                 item_id=args.item_id)
        elif self._target_config.action == Actions.ACTION_GET_CHILD:
            self._target_common.get_child_item_save(parent_name=args.parent_name, parent_type=args.parent_type,
                                                    child_id_key=args.child_id_key, child_type=args.child_type)
        elif self._target_config.action == Actions.ACTION_UPDATE_CHILD:
            self._target_common.update_child_item_from_local_save(
                parent_name=args.parent_name, parent_type=args.parent_type, child_id_key=args.child_id_key,
                child_type=args.child_type)
        elif self._target_config.action == Actions.ACTION_CLONE_CHILD:
            self._target_common.clone_child_item_from_another_parent_save(
                parent_name=args.parent_name, base_parent_name=args.base_parent_name, parent_type=args.parent_type,
                child_id_key=args.child_id_key, child_type=args.child_type, sub_item_key=args.sub_item_key)
        elif self._target_config.action == Actions.ACTION_CLONE_PROCESS_STEP:
            DeploymentProcesses(config=self._target_config).clone_process_step(
                project_literal_name=args.project_name, step_name=args.step_name, base_step_name=args.base_step_name,
                prev_step_name=args.prev_step_name)
        elif self._target_config.action == Actions.ACTION_DELETE_PROCESS_STEP:
            DeploymentProcesses(config=self._target_config).delete_process_step(project_literal_name=args.project_name,
                                                                                step_name=args.step_name)
        elif self._target_config.action == Actions.ACTION_CLONE_PROJECT:
            Projects(config=self._target_config).clone_project(project_literal_name=args.project_name,
                                                               base_project_name=args.base_item_name)
        elif self._target_config.action == Actions.ACTION_DELETE_PROJECT:
            Projects(config=self._target_config).delete_project(project_literal_name=args.project_name)
        elif self._target_config.action == Actions.ACTION_DELETE_PROJECTS:
            Projects(config=self._target_config).delete_projects(
                project_groups_comma_delimited=args.project_groups,
                excluded_projects_comma_delimited=args.excluded_projects)
        elif self._target_config.action == Actions.ACTION_GET_PROJECT:
            Projects(config=self._target_config).get_project(project_literal_name=args.project_name)
        elif self._target_config.action == Actions.ACTION_PROJECT_UPDATE_VARIABLE_SETS:
            Projects(config=self._target_config).project_update_variable_sets(
                project_literal_name=args.project_name, remove_suffix=args.remove_suffix, add_suffix=args.add_suffix)
        elif self._target_config.action == Actions.ACTION_CLONE_SERVER:
            Migration(src_config=self._source_config, dst_config=self._target_config).clone_server(
                space_id_or_name_comma_delimited=args.spaces, item_types_comma_delimited=args.item_types)
        elif self._target_config.action == Actions.ACTION_CLONE_SPACE:
            Migration(src_config=self._source_config, dst_config=self._target_config).clone_space(
                item_types_comma_delimited=args.item_types)
        elif self._target_config.action == Actions.ACTION_CLONE_SPACE_ITEM:
            Migration(src_config=self._source_config, dst_config=self._target_config).clone_space_item(
                item_type=args.item_type, item_name=args.item_name, item_id=args.item_id)
        elif self._target_config.action == Actions.ACTION_TASK_STATUS:
            self._target_common.get_task_status(task_id=args.item_id)
        elif self._target_config.action == Actions.ACTION_WAIT_TASK:
            self._target_common.wait_task(task_id=args.item_id, time_limit_second=args.time_limit_second)
        elif self._target_config.action == Actions.ACTION_CREATE_RELEASE:
            ReleaseDeployment.create_release_direct(
                config=self._target_config, release_version=args.release_version, project_name=args.project_name,
                channel_name=args.channel_name, notes=args.notes)
        elif self._target_config.action == Actions.ACTION_CREATE_DEPLOYMENT:
            ReleaseDeployment.create_deployment_direct(
                config=self._target_config, release_id=args.release_id, environment_name=args.environment_name,
                tenant_name=args.tenant_name, comments=args.comments, project_name=args.project_name)
        elif self._target_config.action == Actions.ACTION_CREATE_RELEASE_DEPLOYMENT:
            ReleaseDeployment.create_release_deployment(
                config=self._target_config, release_version=args.release_version, project_name=args.project_name,
                channel_name=args.channel_name, notes=args.notes, environment_name=args.environment_name,
                tenant_name=args.tenant_name, comments=args.comments)
        else:
            log_raise_value_error(local_logger=logger, err="We only support actions: " + str(Actions.__dict__.values()))


def main():
    logger.info(f"********** {SystemConfig.TITLE} - start **********")
    OctopusClient().run()
    logger.info(f"********** Octopus deploy python client tool - done **********")


if __name__ == "__main__":
    main()
