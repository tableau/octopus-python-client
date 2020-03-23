import argparse

from octopus_python_client.common import config, get_one_type_save, get_single_item_by_name_or_id_save, \
    update_single_item_save, create_single_item_from_local_file, item_type_deployment_processes, \
    clone_single_item_from_remote_item, delete_single_item_by_name_or_id, get_child_item_save, \
    update_child_item_from_local_save, clone_child_item_from_another_parent_save, get_types_save, \
    item_types_only_ourter_space, item_types_inside_space, deployment_process_id_key, steps_key, \
    merge_single_item_save, delete_one_type, api_key_key, octopus_endpoint_key, octopus_name_key, user_name_key, \
    password_key, double_hyphen, verify_space, get_spaces_save
from octopus_python_client.migration import Migration
from octopus_python_client.processes import clone_process_step, delete_process_step
from octopus_python_client.projects import clone_project, delete_project, get_project, project_update_variable_sets


class Actions:
    action_get_spaces = "get_spaces"  # get all types
    action_get_types = "get_types"  # get all types
    action_get_type = "get_type"  # get all items under one type
    action_delete_type = "delete_type"  # delete all items under one type
    action_get = "get"  # get one item
    action_update = "update"  # update one item
    action_update_merge = "update_merge"  # update one item and merge the existing sub-items
    action_create = "create"  # create a new item
    action_clone = "clone"  # clone a new item
    action_delete = "delete"  # delete an item
    action_get_child = "get_child"  # get a child item
    action_update_child = "update_child"  # update a child item
    action_clone_child = "clone_child"  # clone a child item
    action_clone_process_step = "clone_process_step"  # clone a project process step
    action_delete_process_step = "delete_process_step"  # delete a project process step
    action_clone_project = "clone_project"  # clone a project including process
    action_delete_project = "delete_project"  # delete a project including process
    action_get_project = "get_project"  # get a project including process
    action_project_update_variable_sets = "update_variable_sets"  # update the variable sets for a project
    # clone Octopus single item from one space to another space
    action_clone_space_item = "clone_space_item"
    # clone a few types from one space to another space
    action_clone_space = "clone_space"
    clone_space_actions = {action_clone_space_item, action_clone_space}


def _parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("-o", double_hyphen + octopus_endpoint_key, help="octopus endpoint")
    parser.add_argument("-s", "--space_id_name", help="octopus space id or name")
    parser.add_argument("-ss", "--spaces",
                        help='list of octopus space id or name, like "my_space,Spaces-1,Spaces-2"')
    parser.add_argument("-ds", "--dst_space_id_name", help="destination octopus space id or name for clone/migration")
    parser.add_argument("-n", double_hyphen + octopus_name_key,
                        help="customized octopus server name, used for folder name")
    parser.add_argument("-k", double_hyphen + api_key_key,
                        help="api key for octopus; either api_key or user_name and password are required")
    parser.add_argument("-u", double_hyphen + user_name_key,
                        help="user_name for octopus; either api_key or user_name and password are required")
    parser.add_argument("-p", double_hyphen + password_key,
                        help="password for octopus; either api_key or user_name and password are required")
    parser.add_argument("-a", "--action", help=str(Actions.__dict__.values()), required=True)
    parser.add_argument("-ow", "--overwrite", help="if present, overwrite = True", action='store_true')
    parser.add_argument("-ts", "--item_types",
                        help='if not item_types and not octopus_space_id, get all item types '
                             'regardless whether they are above Spaces; if (not item_types) and octopus_space_id, '
                             'get all item types below octopus_space_id; '
                             'list like "accounts,actiontemplates,artifacts" is also accepted; '
                             'item types above Spaces: ' + ", ".join(item_types_only_ourter_space) +
                             "; \nitem types above and under Spaces: " + ", ".join(item_types_inside_space))
    parser.add_argument("-tp", "--item_type", help="one of item types above Spaces: " + ", ".join(
        item_types_only_ourter_space) + "; \nitem types above and under Spaces: " + ", ".join(item_types_inside_space))
    parser.add_argument("-nm", "--item_name", help="item name: e.g. project_name")
    parser.add_argument("-id", "--item_id", help="item id: e.g. Lifecycles-1")
    parser.add_argument("-bn", "--base_item_name", help="base item name, either local or on Octopus server")
    parser.add_argument("-pn", "--parent_name", help="parent item name: e.g. project_name")
    parser.add_argument("-pt", "--parent_type", help="parent item type: e.g. projects")
    parser.add_argument("-ct", "--child_type", help=f"child item type: e.g. {item_type_deployment_processes}")
    parser.add_argument("-ck", "--child_id_key", help=f"child id key: e.g. {deployment_process_id_key}")
    parser.add_argument("-sk", "--sub_item_key", help=f"sub-item key: this sub-item is for copy/clone e.g. {steps_key}")
    parser.add_argument("-bp", "--base_parent_name", help="base parent item name: e.g. a base project_name")
    parser.add_argument("-sn", "--step_name", help="step name as in octopus process")
    parser.add_argument("-bs", "--base_step_name", help="base step name as in octopus process for cloning a step")
    parser.add_argument("-ps", "--prev_step_name",
                        help="previous step name in octopus process for the step insertion location")
    parser.add_argument("-sf", "--suffix", help="variable sets name suffix")
    parser.add_argument("-rs", "--remove_suffix",
                        help="if present, remove suffix from variable sets name, otherwise add suffix",
                        action='store_true')
    parser.add_argument("-rn", "--release_number", help="release number, it could a build number from QE team")
    parser.add_argument("-pj", "--project_name", help="project name")
    parser.add_argument("-cn", "--channel_name", help="channel name")
    parser.add_argument("-bv", "--branch_version", help="service branch version, like 'near.20.0224.2005'")
    parser.add_argument("-nt", "--notes", help="notes")
    parser.add_argument("-ri", "--release_id", help="release id for deployment")
    parser.add_argument("-en", "--environment_name", help="environment name, like Integration")
    parser.add_argument("-tn", "--tenant_name", help="tenant name, like cd-near")

    args, unknown = parser.parse_known_args()
    return args


def run():
    args = _parse_args()

    if args.octopus_endpoint:
        config.octopus_endpoint = args.octopus_endpoint
    if not config.octopus_endpoint:
        raise ValueError("octopus_endpoint must not be empty")

    if args.octopus_name:
        config.octopus_name = args.octopus_name
    if not config.octopus_name:
        raise ValueError("octopus_name must not be empty")

    if args.api_key:
        config.api_key = args.api_key
    if args.user_name:
        config.user_name = args.user_name
    if args.password:
        config.password = args.password

    if not config.api_key and not (config.user_name and config.password):
        raise ValueError(f"either api_key or user_name and password are required")

    print('config.octopus_endpoint: ' + config.octopus_endpoint)
    print('config.octopus_name: ' + config.octopus_name)

    # verify space id/name
    dst_space_id = None
    if args.dst_space_id_name:
        dst_space_id = verify_space(space_id_or_name=args.dst_space_id_name)
        if dst_space_id:
            print(f"destination space_id is: {dst_space_id}")
        else:
            raise ValueError(f"the destination space id/name {args.dst_space_id_name} you specified does not exist "
                             f"or you may not have permission to access it")

    space_id = None
    fake_space = False
    if args.space_id_name:
        space_id = verify_space(space_id_or_name=args.space_id_name)
        if space_id:
            print(f"octopus space_id is: {space_id}")
        elif args.action not in Actions.clone_space_actions:
            raise ValueError(f"the space id/name {args.space_id_name} you specified does not exist "
                             f"or you may not have permission to access it")
        elif input(f"Are you sure you want to {args.action} from nonexistent space {args.space_id_name} [Y/n]?") == 'Y':
            space_id = args.space_id_name
            fake_space = True
        else:
            return
    elif args.action != Actions.action_get_spaces \
            and input(f"Are you sure you want to run a command against null space [Y/n]? ") != 'Y':
        return

    if args.overwrite:
        config.overwrite = args.overwrite

    if args.action == Actions.action_get_spaces:
        get_spaces_save(item_types_comma_delimited=args.item_types, space_id_or_name_comma_delimited=args.spaces)
    elif args.action == Actions.action_get_types:
        get_types_save(item_types_comma_delimited=args.item_types, space_id=space_id)
    elif args.action == Actions.action_get_type:
        get_one_type_save(item_type=args.item_type, space_id=space_id)
    elif args.action == Actions.action_delete_type:
        delete_one_type(item_type=args.item_type, space_id=space_id)
    elif args.action == Actions.action_get:
        get_single_item_by_name_or_id_save(item_type=args.item_type, item_name=args.item_name, item_id=args.item_id,
                                           space_id=space_id)
    elif args.action == Actions.action_update:
        update_single_item_save(item_type=args.item_type, item_name=args.item_name, item_id=args.item_id,
                                space_id=space_id)
    elif args.action == Actions.action_update_merge:
        merge_single_item_save(item_type=args.item_type, item_name=args.item_name, item_id=args.item_id,
                               child_id_key=args.child_id_key, space_id=space_id)
    elif args.action == Actions.action_create:
        create_single_item_from_local_file(item_type=args.item_type, item_name=args.item_name,
                                           local_item_name=args.base_item_name, space_id=space_id)
    elif args.action == Actions.action_clone:
        clone_single_item_from_remote_item(item_type=args.item_type, item_name=args.item_name,
                                           base_item_name=args.base_item_name, space_id=space_id)
    elif args.action == Actions.action_delete:
        delete_single_item_by_name_or_id(item_type=args.item_type, item_name=args.item_name, item_id=args.item_id,
                                         space_id=space_id)
    elif args.action == Actions.action_get_child:
        get_child_item_save(parent_name=args.parent_name, parent_type=args.parent_type, child_id_key=args.child_id_key,
                            child_type=args.child_type, space_id=space_id)
    elif args.action == Actions.action_update_child:
        update_child_item_from_local_save(parent_name=args.parent_name, parent_type=args.parent_type,
                                          child_id_key=args.child_id_key, child_type=args.child_type,
                                          space_id=space_id)
    elif args.action == Actions.action_clone_child:
        clone_child_item_from_another_parent_save(parent_name=args.parent_name, base_parent_name=args.base_parent_name,
                                                  parent_type=args.parent_type, child_id_key=args.child_id_key,
                                                  child_type=args.child_type, sub_item_key=args.sub_item_key,
                                                  space_id=space_id)
    elif args.action == Actions.action_clone_process_step:
        clone_process_step(project_literal_name=args.parent_name, step_name=args.step_name,
                           base_step_name=args.base_step_name, prev_step_name=args.prev_step_name,
                           space_id=space_id)
    elif args.action == Actions.action_delete_process_step:
        delete_process_step(project_literal_name=args.parent_name, step_name=args.step_name, space_id=space_id)
    elif args.action == Actions.action_clone_project:
        clone_project(project_literal_name=args.item_name, base_project_name=args.base_item_name,
                      space_id=space_id)
    elif args.action == Actions.action_delete_project:
        delete_project(project_literal_name=args.item_name, space_id=space_id)
    elif args.action == Actions.action_get_project:
        get_project(project_literal_name=args.item_name, space_id=space_id)
    elif args.action == Actions.action_project_update_variable_sets:
        project_update_variable_sets(project_literal_name=args.item_name, suffix=args.suffix, space_id=space_id,
                                     remove_suffix=args.remove_suffix)
    elif args.action == Actions.action_clone_space:
        Migration().clone_space(src_space_id=space_id, dst_space_id=dst_space_id,
                                item_types_comma_delimited=args.item_types, fake_space=fake_space)
    elif args.action == Actions.action_clone_space_item:
        Migration().clone_space_item(src_space_id=space_id, dst_space_id=dst_space_id, item_type=args.item_type,
                                     item_name=args.item_name, item_id=args.item_id, fake_space=fake_space)

    else:
        raise ValueError("We only support operations: " + str(Actions.__dict__.values()))


if __name__ == "__main__":
    run()
