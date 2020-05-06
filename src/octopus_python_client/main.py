import argparse
import copy
import logging
import os

from octopus_python_client.common import Config, item_type_deployment_processes, outer_space_download_types, \
    inside_space_download_types, deployment_process_id_key, steps_key, api_key_key, octopus_endpoint_key, \
    octopus_name_key, user_name_key, password_key, double_hyphen, Common, runbook_process_prefix, octopus_demo_site
from octopus_python_client.deployment_processes import DeploymentProcesses
from octopus_python_client.migration import Migration
from octopus_python_client.projects import Projects
from octopus_python_client.release_deployment import ReleaseDeployment
from octopus_python_client.utilities.helper import log_raise_value_error

logging.basicConfig(filename=os.path.join(os.getcwd(), "octopus_python_client.log"),
                    filemode='a',
                    format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
                    datefmt='%H:%M:%S',
                    level=logging.INFO)
logger = logging.getLogger(__name__)


class Actions:
    ACTION_GET_SPACES = "get_spaces"  # get all types
    ACTION_GET_TYPES = "get_types"  # get all types
    ACTION_GET_TYPE = "get_type"  # get all items under one type
    ACTION_DELETE_TYPE = "delete_type"  # delete all items under one type
    # delete all items under specified types (if no types specified, delete all cloneable types in reverse order)
    ACTION_DELETE_TYPES = "delete_types"
    ACTION_GET = "get"  # get one item
    ACTION_UPDATE = "update"  # update one item
    ACTION_UPDATE_MERGE = "update_merge"  # update one item and merge the existing sub-items
    ACTION_CREATE = "create"  # create a new item
    ACTION_CLONE = "clone"  # clone a new item
    ACTION_DELETE = "delete"  # delete an item
    ACTION_GET_CHILD = "get_child"  # get a child item
    ACTION_UPDATE_CHILD = "update_child"  # update a child item
    ACTION_CLONE_CHILD = "clone_child"  # clone a child item
    ACTION_CLONE_PROCESS_STEP = "clone_process_step"  # clone a project process step
    ACTION_DELETE_PROCESS_STEP = "delete_process_step"  # delete a project process step
    ACTION_CLONE_PROJECT = "clone_project"  # clone a project including process
    ACTION_DELETE_PROJECT = "delete_project"  # delete a project including process
    ACTION_DELETE_PROJECTS = "delete_projects"  # delete projects inside project groups and excluding projects
    ACTION_GET_PROJECT = "get_project"  # get a project including process
    ACTION_PROJECT_UPDATE_VARIABLE_SETS = "update_variable_sets"  # update the variable sets for a project
    # clone Octopus single item from one space to another space
    ACTION_CLONE_SPACE_ITEM = "clone_space_item"
    # clone a few types from one space to another space
    ACTION_CLONE_SPACE = "clone_space"
    # clone a few types from one server to another server
    ACTION_CLONE_SERVER = "clone_server"
    ACTION_TASK_STATUS = "task_status"
    ACTION_WAIT_TASK = "wait_task"
    ACTION_CREATE_RELEASE = "create_release"
    ACTION_CREATE_DEPLOYMENT = "create_deployment"
    ACTION_CREATE_RELEASE_DEPLOYMENT = "create_release_deployment"


class OctopusClient:
    CLONE_ACTIONS_SET = {Actions.ACTION_CLONE_SPACE_ITEM, Actions.ACTION_CLONE_SPACE, Actions.ACTION_CLONE_SERVER}

    def __init__(self):
        self._target_config = Config()
        self._target_common = Common(config=self._target_config)
        self._source_config = None
        self._source_common = None

    @staticmethod
    def _parse_args():
        parser = argparse.ArgumentParser()
        parser.add_argument("-o", double_hyphen + octopus_endpoint_key, help="octopus endpoint")
        parser.add_argument("-s", "--space_id_name", help="octopus space id or name")
        parser.add_argument("-m", "--pem", help="octopus endpoint root pem file path")
        parser.add_argument("-sps", "--spaces",
                            help='list of octopus space id or name, like "my space,Spaces-1,Spaces-2"')
        parser.add_argument("-n", double_hyphen + octopus_name_key,
                            help="customized octopus server name, used for folder name")
        parser.add_argument("-k", double_hyphen + api_key_key,
                            help="api key for octopus; either api_key or user_name and password are required")
        parser.add_argument("-user", double_hyphen + user_name_key,
                            help="user_name for octopus; either api_key or user_name and password are required")
        parser.add_argument("-pass", double_hyphen + password_key,
                            help="password for octopus; either api_key or user_name and password are required")
        parser.add_argument("-sre", "--source_endpoint", help="source octopus endpoint for clone")
        parser.add_argument("-srn", "--source_octopus_name",
                            help="user's source octopus server name, used for folder name to store the local files")
        parser.add_argument("-srk", "--source_api_key",
                            help="api key for octopus; either api_key or user_name and password are required")
        parser.add_argument("-sru", "--source_user_name",
                            help="user_name for octopus; either api_key or user_name and password are required")
        parser.add_argument("-srp", "--source_password",
                            help="password for octopus; either api_key or user_name and password are required")
        parser.add_argument("-srs", "--source_space_id_name",
                            help="source octopus space id or name for clone/migration")
        parser.add_argument("-srm", "--source_pem", help="source octopus endpoint root pem file path")
        parser.add_argument("-lsr", "--local_source", help="if present, local_source = True; the source server/space "
                                                           "data are stored as YAML files locally", action='store_true')
        parser.add_argument("-a", "--action", help=str(Actions.__dict__.values()), required=True)
        parser.add_argument("-ow", "--overwrite", help="if present, overwrite = True", action='store_true')
        parser.add_argument("-ns", "--no_stdout", help="if present, no_stdout = True, means no stdout",
                            action='store_true')
        parser.add_argument("-ts", "--item_types",
                            help='if not item_types and not octopus_space_id, get all item types '
                                 'regardless whether they are above Spaces; if (not item_types) and octopus_space_id, '
                                 'get all item types below octopus_space_id; '
                                 'list like "accounts,actiontemplates,artifacts" is also accepted; '
                                 'item types above Spaces: ' + ", ".join(outer_space_download_types) +
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

        args, unknown = parser.parse_known_args()
        return args

    def _process_args_to_configs(self):
        args = self._parse_args()

        if args.endpoint:
            self._target_config.endpoint = args.endpoint
        assert self._target_config.endpoint.endswith("/api/"), \
            f"octopus endpoint must end with /api/; {self._target_config.endpoint} is invalid"

        if args.octopus_name:
            self._target_config.octopus_name = args.octopus_name
        assert self._target_config.octopus_name, "octopus_name must not be empty"

        if args.api_key:
            self._target_config.api_key = args.api_key
        if args.user_name:
            self._target_config.user_name = args.user_name
        if args.password:
            self._target_config.password = args.password
        assert self._target_config.api_key or (self._target_config.user_name and self._target_config.password), \
            f"either api_key or user_name and password are required"
        if args.pem:
            self._target_config.pem = args.pem

        if args.overwrite:
            self._target_config.overwrite = args.overwrite
        if args.no_stdout:
            self._target_config.no_stdout = args.no_stdout

        if args.space_id_name:
            self._target_config.space_id = self._target_common.verify_space(space_id_name=args.space_id_name)
            if self._target_config.space_id:
                logger.info(f"the target space_id is: {self._target_config.space_id}")
            else:
                raise ValueError(f"the space id/name {args.space_id_name} you specified does not exist or "
                                 f"you do not have permission to access it on server {self._target_config.endpoint}")
        elif args.action != Actions.ACTION_GET_SPACES \
                and input(f"Are you sure you want to run a command against {None} space [Y/n]? ") != 'Y':
            return

        if args.action in OctopusClient.CLONE_ACTIONS_SET:
            self._target_common.log_info_print(msg=f"===== Action: {args.action}; processing the source config =====")
            self._source_config = copy.deepcopy(self._target_config)
            self._source_common = Common(config=self._source_config)

            if args.local_source:
                self._source_config.local_source = args.local_source
            if args.source_endpoint:
                self._source_config.endpoint = args.source_endpoint
            assert self._source_config.local_source or self._source_config.endpoint.endswith("/api/"), \
                f"octopus endpoint must end with /api/; {self._source_config.endpoint} is invalid"

            # TODO Octopus demo site bug: https://demo.octopus.com/api/runbookprocess
            # newer site uses https://server/api/runbookprocesses (runbookprocess vs runbookprocesses)
            if octopus_demo_site == self._source_config.endpoint:
                self._source_config.item_type_runbook_processes = runbook_process_prefix

            if args.source_octopus_name:
                self._source_config.octopus_name = args.source_octopus_name
            assert self._source_config.octopus_name, "source octopus_name must not be empty"
            if self._target_config.endpoint != self._source_config.endpoint \
                    and self._target_config.octopus_name == self._source_config.octopus_name:
                raise ValueError(f"the source Octopus server {self._source_config.endpoint} and the target "
                                 f"Octopus server {self._target_config.endpoint} cannot use the same local "
                                 f"folder name {self._target_config.octopus_name}")

            if args.source_api_key:
                self._source_config.api_key = args.source_api_key
            if args.source_user_name:
                self._source_config.user_name = args.source_user_name
            if args.source_password:
                self._source_config.password = args.source_password
            assert self._source_config.api_key or (self._source_config.user_name and self._source_config.password), \
                f"either api_key or user_name and password are required"
            if args.source_pem:
                self._source_config.pem = args.source_pem

            if args.source_space_id_name:
                self._source_config.space_id = None
                self._source_config.space_id = self._source_common.verify_space(space_id_name=args.source_space_id_name)
                if self._source_config.space_id:
                    self._target_common.log_info_print(msg=f"The source octopus space_id is: "
                                                           f"{self._source_config.space_id}")
                elif self._source_config.local_source:
                    self._target_common.log_info_print(msg=f"{args.action} from nonexistent source space "
                                                           f"{args.source_space_id_name}")
                    self._source_config.space_id = args.source_space_id_name
                else:
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

        return args

    def run(self):
        args = self._process_args_to_configs()

        if args.action == Actions.ACTION_GET_SPACES:
            self._target_common.get_spaces_save(item_types_comma_delimited=args.item_types,
                                                space_id_or_name_comma_delimited=args.spaces)
        elif args.action == Actions.ACTION_GET_TYPES:
            self._target_common.get_types_save(item_types_comma_delimited=args.item_types)
        elif args.action == Actions.ACTION_GET_TYPE:
            self._target_common.get_one_type_save(item_type=args.item_type)
        elif args.action == Actions.ACTION_DELETE_TYPE:
            self._target_common.delete_one_type(item_type=args.item_type)
        elif args.action == Actions.ACTION_DELETE_TYPES:
            self._target_common.delete_types(item_types_comma_delimited=args.item_types)
        elif args.action == Actions.ACTION_GET:
            self._target_common.get_single_item_by_name_or_id_save(item_type=args.item_type, item_name=args.item_name,
                                                                   item_id=args.item_id)
        elif args.action == Actions.ACTION_UPDATE:
            self._target_common.update_single_item_save(item_type=args.item_type, item_name=args.item_name,
                                                        item_id=args.item_id)
        elif args.action == Actions.ACTION_UPDATE_MERGE:
            self._target_common.merge_single_item_save(item_type=args.item_type, item_name=args.item_name,
                                                       item_id=args.item_id, child_id_key=args.child_id_key)
        elif args.action == Actions.ACTION_CREATE:
            self._target_common.create_single_item_from_local_file(item_type=args.item_type, item_name=args.item_name,
                                                                   local_item_name=args.base_item_name)
        elif args.action == Actions.ACTION_CLONE:
            self._target_common.clone_single_item_from_remote_item(item_type=args.item_type, item_name=args.item_name,
                                                                   base_item_name=args.base_item_name)
        elif args.action == Actions.ACTION_DELETE:
            self._target_common.delete_single_item_by_name_or_id(item_type=args.item_type, item_name=args.item_name,
                                                                 item_id=args.item_id)
        elif args.action == Actions.ACTION_GET_CHILD:
            self._target_common.get_child_item_save(parent_name=args.parent_name, parent_type=args.parent_type,
                                                    child_id_key=args.child_id_key, child_type=args.child_type)
        elif args.action == Actions.ACTION_UPDATE_CHILD:
            self._target_common.update_child_item_from_local_save(
                parent_name=args.parent_name, parent_type=args.parent_type, child_id_key=args.child_id_key,
                child_type=args.child_type)
        elif args.action == Actions.ACTION_CLONE_CHILD:
            self._target_common.clone_child_item_from_another_parent_save(
                parent_name=args.parent_name, base_parent_name=args.base_parent_name, parent_type=args.parent_type,
                child_id_key=args.child_id_key, child_type=args.child_type, sub_item_key=args.sub_item_key)
        elif args.action == Actions.ACTION_CLONE_PROCESS_STEP:
            DeploymentProcesses(config=self._target_config).clone_process_step(
                project_literal_name=args.project_name, step_name=args.step_name, base_step_name=args.base_step_name,
                prev_step_name=args.prev_step_name)
        elif args.action == Actions.ACTION_DELETE_PROCESS_STEP:
            DeploymentProcesses(config=self._target_config).delete_process_step(project_literal_name=args.project_name,
                                                                                step_name=args.step_name)
        elif args.action == Actions.ACTION_CLONE_PROJECT:
            Projects(config=self._target_config).clone_project(project_literal_name=args.project_name,
                                                               base_project_name=args.base_item_name)
        elif args.action == Actions.ACTION_DELETE_PROJECT:
            Projects(config=self._target_config).delete_project(project_literal_name=args.project_name)
        elif args.action == Actions.ACTION_DELETE_PROJECTS:
            Projects(config=self._target_config).delete_projects(
                project_groups_comma_delimited=args.project_groups,
                excluded_projects_comma_delimited=args.excluded_projects)
        elif args.action == Actions.ACTION_GET_PROJECT:
            Projects(config=self._target_config).get_project(project_literal_name=args.project_name)
        elif args.action == Actions.ACTION_PROJECT_UPDATE_VARIABLE_SETS:
            Projects(config=self._target_config).project_update_variable_sets(
                project_literal_name=args.project_name, remove_suffix=args.remove_suffix, add_suffix=args.add_suffix)
        elif args.action == Actions.ACTION_CLONE_SERVER:
            Migration(src_config=self._source_config, dst_config=self._target_config).clone_server(
                space_id_or_name_comma_delimited=args.spaces, item_types_comma_delimited=args.item_types)
        elif args.action == Actions.ACTION_CLONE_SPACE:
            Migration(src_config=self._source_config, dst_config=self._target_config).clone_space(
                item_types_comma_delimited=args.item_types)
        elif args.action == Actions.ACTION_CLONE_SPACE_ITEM:
            Migration(src_config=self._source_config, dst_config=self._target_config).clone_space_item(
                item_type=args.item_type, item_name=args.item_name, item_id=args.item_id)
        elif args.action == Actions.ACTION_TASK_STATUS:
            self._target_common.get_task_status(task_id=args.item_id)
        elif args.action == Actions.ACTION_WAIT_TASK:
            self._target_common.wait_task(task_id=args.item_id, time_limit_second=args.time_limit_second)
        elif args.action == Actions.ACTION_CREATE_RELEASE:
            ReleaseDeployment.create_release_direct(
                config=self._target_config, release_version=args.release_version, project_name=args.project_name,
                channel_name=args.channel_name, notes=args.notes)
        elif args.action == Actions.ACTION_CREATE_DEPLOYMENT:
            ReleaseDeployment.create_deployment_direct(
                config=self._target_config, release_id=args.release_id, environment_name=args.environment_name,
                tenant_name=args.tenant_name, comments=args.comments)
        elif args.action == Actions.ACTION_CREATE_RELEASE_DEPLOYMENT:
            ReleaseDeployment.create_release_deployment(
                config=self._target_config, release_version=args.release_version, project_name=args.project_name,
                channel_name=args.channel_name, notes=args.notes, environment_name=args.environment_name,
                tenant_name=args.tenant_name, comments=args.comments)

        else:
            log_raise_value_error(local_logger=logger, err="We only support actions: " + str(Actions.__dict__.values()))


def main():
    logger.info("********** Octopus deploy python client tool - start **********")
    OctopusClient().run()
    logger.info("********** Octopus deploy python client tool - end **********")


if __name__ == "__main__":
    main()
