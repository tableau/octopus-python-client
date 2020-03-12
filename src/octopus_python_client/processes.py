import copy

from octopus_python_client.common import get_one_type_save, item_type_deployment_processes, get_child_item_save, \
    item_type_projects, update_child_item_from_local_save, clone_child_item_from_another_parent_save, get_child_item, \
    put_child_item_save, deployment_process_id_key, steps_key, name_key, id_key, actions_key
from octopus_python_client.helper import find_index, find_item


def get_all_deployment_processes(space_id=None):
    return get_one_type_save(item_type=item_type_deployment_processes, space_id=space_id)


def get_deployment_process(project_literal_name=None, space_id=None):
    return get_child_item_save(parent_name=project_literal_name, parent_type=item_type_projects,
                               child_id_key=deployment_process_id_key, child_type=item_type_deployment_processes,
                               space_id=space_id)


def update_deployment_process(project_literal_name=None, space_id=None):
    update_child_item_from_local_save(parent_name=project_literal_name, parent_type=item_type_projects,
                                      child_id_key=deployment_process_id_key, child_type=item_type_deployment_processes,
                                      space_id=space_id)


# clone deployment process from a base project to a project
def clone_deployment_process(project_literal_name=None, base_project_name=None, space_id=None):
    clone_child_item_from_another_parent_save(parent_name=project_literal_name, base_parent_name=base_project_name,
                                              parent_type=item_type_projects, child_id_key=deployment_process_id_key,
                                              child_type=item_type_deployment_processes, sub_item_key=steps_key,
                                              space_id=space_id)


def clone_process_step(project_literal_name=None, step_name=None, base_step_name=None, prev_step_name=None,
                       space_id=None):
    if not project_literal_name or not step_name or not base_step_name:
        raise ValueError('Project literal name or step or base step names must not be empty')
    process = get_child_item(parent_name=project_literal_name, parent_type=item_type_projects,
                             child_id_key=deployment_process_id_key, child_type=item_type_deployment_processes,
                             space_id=space_id)
    steps = process[steps_key]
    step = copy.deepcopy(find_item(lst=steps, key=name_key, value=base_step_name))
    step[name_key] = step_name
    step[id_key] = ""
    for action in step[actions_key]:
        action[name_key] = step_name
        action[id_key] = ""
    if prev_step_name:
        prev_step_name_index = find_index(lst=steps, key=name_key, value=prev_step_name)
        if prev_step_name_index < 0:
            raise ValueError('previous base step name does not exist')
        steps.insert(prev_step_name_index + 1, step)
    else:
        steps.append(step)
    child_item = put_child_item_save(parent_name=project_literal_name, child_type=item_type_deployment_processes,
                                     payload=process, space_id=space_id)
    return child_item


def delete_process_step(project_literal_name=None, step_name=None, space_id=None):
    if not project_literal_name or not step_name:
        raise ValueError('Project literal name or step name must not be empty')
    process = get_child_item(parent_name=project_literal_name, parent_type=item_type_projects,
                             child_id_key=deployment_process_id_key, child_type=item_type_deployment_processes,
                             space_id=space_id)
    steps = process[steps_key]
    step_index = find_index(lst=steps, key=name_key, value=step_name)
    if step_index < 0:
        raise ValueError('step name does not exist')
    steps.pop(step_index)
    child_item = put_child_item_save(parent_name=project_literal_name, child_type=item_type_deployment_processes,
                                     payload=process, space_id=space_id)
    return child_item
