import logging
import copy

from octopus_python_client.common import item_type_projects, get_one_type_save, get_single_item_by_name_or_id_save, \
    delete_single_item_by_name_or_id, update_single_item_save, create_single_item_from_local_file, \
    clone_single_item_from_remote_item, item_type_library_variable_sets, included_library_variable_set_ids_key, \
    id_key, name_key, put_single_item_save, get_one_type_ignore_error, get_list_items_from_all_items, log_info_print
from octopus_python_client.processes import clone_deployment_process
from octopus_python_client.utilities.helper import find_item, compare_lists

logger = logging.getLogger(__name__)


def get_all_projects(space_id=None):
    return get_one_type_save(item_type=item_type_projects, space_id=space_id)


def get_project(project_literal_name=None, space_id=None):
    log_info_print(local_logger=logger, msg=f"get and save project {project_literal_name} in space {space_id}...")
    project = get_single_item_by_name_or_id_save(item_type=item_type_projects, item_name=project_literal_name,
                                                 space_id=space_id)
    return project


def update_project(project_literal_name=None, space_id=None):
    update_single_item_save(item_type=item_type_projects, item_name=project_literal_name, space_id=space_id)


def create_project_from_local_file(project_literal_name=None, local_project_name=None, space_id=None):
    return create_single_item_from_local_file(item_type=item_type_projects, item_name=project_literal_name,
                                              local_item_name=local_project_name, space_id=space_id)


def clone_project(project_literal_name=None, base_project_name=None, space_id=None):
    log_info_print(local_logger=logger,
                   msg=f"clone project from {base_project_name} to {project_literal_name} inside space {space_id}")
    clone_single_item_from_remote_item(item_type=item_type_projects, item_name=project_literal_name,
                                       base_item_name=base_project_name, space_id=space_id)
    clone_deployment_process(project_literal_name=project_literal_name, base_project_name=base_project_name,
                             space_id=space_id)


def delete_project(project_literal_name=None, space_id=None):
    log_info_print(local_logger=logger, msg=f"delete project {project_literal_name} in space {space_id}")
    delete_single_item_by_name_or_id(item_type=item_type_projects, item_name=project_literal_name, space_id=space_id)


def process_suffix(name, remove_suffix, add_suffix):
    if remove_suffix and name.endswith(remove_suffix):
        name = name[:-len(remove_suffix)]
    if add_suffix:
        name += add_suffix
    return name


def project_update_variable_sets(project_literal_name, space_id, remove_suffix, add_suffix):
    if not project_literal_name:
        raise ValueError("project name must not be empty")
    if not add_suffix and not remove_suffix:
        raise ValueError("add_suffix and remove_suffix can not be both empty")
    log_info_print(local_logger=logger, msg=f"===== updating {space_id}'s project {project_literal_name}'s variable sets by the following operation(s)")
    if remove_suffix:
        log_info_print(local_logger=logger, msg=f"removing a suffix {remove_suffix}")
    if add_suffix:
        log_info_print(local_logger=logger, msg=f"adding a suffix {add_suffix}")

    all_variable_sets = get_one_type_ignore_error(item_type=item_type_library_variable_sets, space_id=space_id)
    library_variable_sets = get_list_items_from_all_items(all_items=all_variable_sets)
    project = get_project(project_literal_name, space_id=space_id)
    project_variable_sets_ids = project.get(included_library_variable_set_ids_key, [])
    logger.info("original variable sets id:")
    logger.info(project_variable_sets_ids)
    mapped_ids = copy.deepcopy(project_variable_sets_ids)
    for index, id in enumerate(project_variable_sets_ids):
        variable_set = find_item(lst=library_variable_sets, key=id_key, value=id)
        variable_set_name = variable_set.get(name_key)
        variable_set_name_updated = process_suffix(name=variable_set_name, remove_suffix=remove_suffix, add_suffix=add_suffix)
        new_variable_set_in_library_variable_sets = find_item(lst=library_variable_sets, key=name_key, value=variable_set_name_updated)
        if new_variable_set_in_library_variable_sets:
            logger.info(f"{new_variable_set_in_library_variable_sets.get(id_key)} found in variable sets")
            mapped_ids[index] = new_variable_set_in_library_variable_sets.get(id_key)
    logger.info("mapped variable sets id:")
    logger.info(mapped_ids)
    no_change = compare_lists(project_variable_sets_ids, mapped_ids)
    if no_change:
        logger.info(f"The variable sets have no change")
        return project
    project[included_library_variable_set_ids_key] = mapped_ids
    return put_single_item_save(item_type=item_type_projects, payload=project, space_id=space_id)
