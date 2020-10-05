from octopus_python_client.constants import Constants


class Actions:
    ACTION_CLONE = "clone"  # clone a new item
    ACTION_CLONE_CHILD = "clone_child"  # clone a child item
    ACTION_CLONE_PROCESS_STEP = "clone_process_step"  # clone a project process step
    ACTION_CLONE_PROJECT = "clone_project"  # clone a project including process
    ACTION_CLONE_PROJECT_RELATED = "clone_project_related"  # clone a project related items from a project to projects
    ACTION_CLONE_SERVER = "clone_server"  # clone a few types from one server to another server
    ACTION_CLONE_SPACE = "clone_space"  # clone a few types from one space to another space
    ACTION_CLONE_SPACE_ITEM = "clone_space_item"  # clone Octopus single item from one space to another space
    ACTION_CREATE = "create"  # create a new item
    ACTION_CREATE_DEPLOYMENT = "create_deployment"
    ACTION_CREATE_RELEASE = "create_release"
    ACTION_CREATE_RELEASE_DEPLOYMENT = "create_release_deployment"
    ACTION_DELETE = "delete"  # delete an item
    ACTION_DELETE_PROCESS_STEP = "delete_process_step"  # delete a project process step
    ACTION_DELETE_PROJECT = "delete_project"  # delete a project including process
    ACTION_DELETE_PROJECTS = "delete_projects"  # delete projects inside project groups and excluding projects
    ACTION_DELETE_TYPE = "delete_type"  # delete all items_dict under one type
    ACTION_DELETE_TYPES = "delete_types"  # delete all items_dict under specified types (or delete all types)
    ACTION_GET = "get"  # get one item
    ACTION_GET_CHILD = "get_child"  # get a child item
    ACTION_GET_PROJECT = "get_project"  # get a project including process
    ACTION_GET_SPACES = "get_spaces"  # get multiple spaces
    ACTION_GET_TYPE = "get_type"  # get all items_dict under one type
    ACTION_GET_TYPES = "get_types"  # get all types
    ACTION_PROJECT_UPDATE_VARIABLE_SETS = "update_variable_sets"  # update the variable sets for a project
    ACTION_TASK_STATUS = "task_status"
    ACTION_UPDATE = "update"  # update one item
    ACTION_UPDATE_CHILD = "update_child"  # update a child item
    ACTION_UPDATE_MERGE = "update_merge"  # update one item and merge the existing sub-items_dict
    ACTION_WAIT_TASK = "wait_task"


ACTIONS_DICT = {
    # Actions.ACTION_GET_SPACES: "download the data of multiple types in a number of spaces or all spaces",
    # Actions.ACTION_GET_TYPES: "download the data of multiple types in one space",
    Actions.ACTION_CLONE_SPACE: "clone multiple types from one space to another space on the same server or the "
                                "different server",
    Actions.ACTION_CLONE_SPACE_ITEM: "clone one item of a specific type within a space, to another space, or to another"
                                     " server",
    Actions.ACTION_CLONE_PROJECT_RELATED: f"clone project related items {Constants.PROJECT_RELATED_TYPES} from one "
                                          f"project to other projects",
    Actions.ACTION_CREATE_RELEASE: "create a new release for a project",
    Actions.ACTION_CREATE_DEPLOYMENT: "create a new deployment for a release of a project",
    Actions.ACTION_GET_SPACES: "download data and configurations from one or more Octopus spaces to local files",
    Actions.ACTION_GET: "download single item data/configuration from Octopus server to a local file",
    Actions.ACTION_UPDATE: "update single item data/configuration on Octopus server from a local file"
}

MIGRATION_LIST = [Actions.ACTION_CLONE_PROJECT_RELATED, Actions.ACTION_CLONE_SPACE_ITEM, Actions.ACTION_CLONE_SPACE,
                  Actions.ACTION_CLONE_SERVER]
