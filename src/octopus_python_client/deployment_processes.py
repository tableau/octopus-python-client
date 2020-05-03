import copy
import logging

from octopus_python_client.common import item_type_deployment_processes, item_type_projects, steps_key, name_key, \
    deployment_process_id_key, id_key, actions_key, Common
from octopus_python_client.utilities.helper import find_index, find_item, log_raise_value_error


class DeploymentProcesses:
    def __init__(self, config, logger=None):
        self.logger = logger if logger else logging.getLogger(self.__class__.__name__)
        self.config = config
        self.common = Common(config=config)

    def get_all_deployment_processes(self):
        return self.common.get_one_type_save(item_type=item_type_deployment_processes)

    def get_deployment_process(self, project_literal_name):
        return self.common.get_child_item_save(
            parent_name=project_literal_name, parent_type=item_type_projects, child_id_key=deployment_process_id_key,
            child_type=item_type_deployment_processes)

    def update_deployment_process(self, project_literal_name):
        self.common.update_child_item_from_local_save(
            parent_name=project_literal_name, parent_type=item_type_projects, child_id_key=deployment_process_id_key,
            child_type=item_type_deployment_processes)

    # clone deployment process from a base project to a project
    def clone_deployment_process(self, project_literal_name, base_project_name):
        self.common.clone_child_item_from_another_parent_save(
            parent_name=project_literal_name, base_parent_name=base_project_name, parent_type=item_type_projects,
            child_id_key=deployment_process_id_key, child_type=item_type_deployment_processes, sub_item_key=steps_key)

    def clone_process_step(self, project_literal_name, step_name, base_step_name, prev_step_name=None):
        if not project_literal_name or not step_name or not base_step_name:
            raise ValueError('Project literal name or step or base step names must not be empty')
        self.common.log_info_print(
            local_logger=self.logger,
            msg=f"clone project {project_literal_name} step from base step {base_step_name} to new step "
                f"{step_name} and place it after step {prev_step_name}")
        process = self.common.get_child_item(
            parent_name=project_literal_name, parent_type=item_type_projects, child_id_key=deployment_process_id_key,
            child_type=item_type_deployment_processes)
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
                log_raise_value_error(local_logger=self.logger, err=f"previous step {prev_step_name} does not exist")
            steps.insert(prev_step_name_index + 1, step)
        else:
            steps.append(step)
        child_item = self.common.put_child_item_save(
            parent_name=project_literal_name, child_type=item_type_deployment_processes, payload=process)
        return child_item

    def delete_process_step(self, project_literal_name, step_name):
        if not project_literal_name or not step_name:
            raise ValueError('Project literal name or step name must not be empty')
        self.common.log_info_print(
            local_logger=self.logger,
            msg=f"deleting step {step_name} of project {project_literal_name} in space {self.config.space_id}")
        process = self.common.get_child_item(parent_name=project_literal_name, parent_type=item_type_projects,
                                             child_id_key=deployment_process_id_key,
                                             child_type=item_type_deployment_processes)
        steps = process[steps_key]
        step_index = find_index(lst=steps, key=name_key, value=step_name)
        if step_index < 0:
            log_raise_value_error(local_logger=self.logger, err=f"step {step_name} does not exit")
        steps.pop(step_index)
        child_item = self.common.put_child_item_save(
            parent_name=project_literal_name, child_type=item_type_deployment_processes, payload=process)
        return child_item
