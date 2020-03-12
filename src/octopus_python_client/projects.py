from octopus_python_client.common import item_type_projects, get_one_type_save, get_single_item_by_name_or_id_save, \
    delete_single_item_by_name_or_id, update_single_item_save, create_single_item_from_local_file, \
    clone_single_item_from_remote_item, item_type_library_variable_sets, included_library_variable_set_ids_key, \
    id_key, name_key, put_single_item_save, get_one_type, get_list_items_from_all_items
from octopus_python_client.helper import find_item, compare_lists
from octopus_python_client.processes import clone_deployment_process


def get_all_projects(space_id=None):
    return get_one_type_save(item_type=item_type_projects, space_id=space_id)


def get_project(project_literal_name=None, space_id=None):
    project = get_single_item_by_name_or_id_save(item_type=item_type_projects, item_name=project_literal_name,
                                                 space_id=space_id)
    return project


def update_project(project_literal_name=None, space_id=None):
    update_single_item_save(item_type=item_type_projects, item_name=project_literal_name, space_id=space_id)


def create_project_from_local_file(project_literal_name=None, local_project_name=None, space_id=None):
    return create_single_item_from_local_file(item_type=item_type_projects, item_name=project_literal_name,
                                              local_item_name=local_project_name, space_id=space_id)


def clone_project(project_literal_name=None, base_project_name=None, space_id=None):
    clone_single_item_from_remote_item(item_type=item_type_projects, item_name=project_literal_name,
                                       base_item_name=base_project_name, space_id=space_id)
    clone_deployment_process(project_literal_name=project_literal_name, base_project_name=base_project_name,
                             space_id=space_id)


def delete_project(project_literal_name=None, space_id=None):
    delete_single_item_by_name_or_id(item_type=item_type_projects, item_name=project_literal_name, space_id=space_id)


def process_suffix(name=None, suffix=None, remove_suffix=False):
    dot_suffix = '.' + suffix
    if not remove_suffix:
        return name + dot_suffix
    elif name.endswith(dot_suffix):
        return name[:-len(dot_suffix)]
    return name


def project_update_variable_sets(project_literal_name=None, suffix=None, space_id=None, remove_suffix=False):
    if not project_literal_name or not suffix:
        raise ValueError("project name or suffix must not be empty")
    print(f"===== updating {space_id}'s project {project_literal_name}'s variable sets by "
          f"{'removing' if remove_suffix else 'adding'} a suffix {suffix}")
    all_variable_sets = get_one_type(item_type=item_type_library_variable_sets, space_id=space_id)
    list_variable_sets = get_list_items_from_all_items(all_items=all_variable_sets)
    project = get_project(project_literal_name, space_id=space_id)
    variable_sets_ids = project.get(included_library_variable_set_ids_key, [])
    print("========= original variable sets id =========")
    print(variable_sets_ids)
    mapped_ids = []
    for variable_set_id in variable_sets_ids:
        variable_set = find_item(lst=list_variable_sets, key=id_key, value=variable_set_id)
        variable_set_name = variable_set.get(name_key)
        variable_set_name_suffix = process_suffix(name=variable_set_name, suffix=suffix, remove_suffix=remove_suffix)
        variable_set_suffix = find_item(lst=list_variable_sets, key=name_key, value=variable_set_name_suffix)
        if variable_set_suffix:
            mapped_ids.append(variable_set_suffix.get(id_key))
        else:
            mapped_ids.append(variable_set_id)
    print("========= mapped variable sets id =========")
    print(mapped_ids)
    no_change = compare_lists(variable_sets_ids, mapped_ids)
    if no_change:
        print(f"The variable sets have no change")
        return project
    project[included_library_variable_set_ids_key] = mapped_ids
    return put_single_item_save(item_type=item_type_projects, payload=project, space_id=space_id)
