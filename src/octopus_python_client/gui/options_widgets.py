import tkinter as tk
from tkinter import messagebox

from octopus_python_client.actions import ACTIONS_DICT, Actions
from octopus_python_client.common import Common, inside_space_clone_types, item_type_projects, id_key, \
    project_id_key, inside_space_download_types
from octopus_python_client.gui.common_widgets import CommonWidgets


class OptionsWidgets(tk.Frame):

    def __init__(self, parent: tk.Frame, server: Common, source: Common, next_button: tk.Button = None,
                 submit_button: tk.Button = None):
        super().__init__(parent)
        self.server = server
        self.source = source

        self.next_button = next_button
        self.submit_button = submit_button

        self.project_id_var = None
        self.project_ids_var_dict = None
        self.source_project_id_var = None
        self.type_var = None
        self.types_var_dict = None

        self.update_step()

    def update_step(self):
        tk.Label(self, text=f"{self.server.config.action} ({ACTIONS_DICT.get(self.server.config.action)})",
                 bd=2, relief="groove").grid(sticky=tk.W)
        if self.server.config.action == Actions.ACTION_CLONE_SPACE:
            self.types_var_dict = CommonWidgets.set_check_names_frame(
                self, list_names=inside_space_clone_types, default_names=self.server.config.types,
                title="Select data types:")

        elif self.server.config.action == Actions.ACTION_GET_SPACES:
            self.types_var_dict = CommonWidgets.set_check_names_frame(
                self, list_names=inside_space_download_types, default_names=self.server.config.types,
                title="Select data types:")

        elif self.server.config.action == Actions.ACTION_GET or self.server.config.action == Actions.ACTION_UPDATE:
            self.type_var = CommonWidgets.set_radio_names_frame(
                parent=self, list_names=inside_space_download_types, default_name=self.server.config.type,
                title="Select type: ")

        elif self.server.config.action == Actions.ACTION_CLONE_SPACE_ITEM:
            self.type_var = CommonWidgets.set_radio_names_frame(
                parent=self, list_names=inside_space_clone_types, default_name=self.server.config.type,
                title="Select type: ")

        elif self.server.config.action == Actions.ACTION_CLONE_PROJECT_RELATED:
            self.set_clone_project_related()

        elif self.server.config.action == Actions.ACTION_CREATE_RELEASE \
                or self.server.config.action == Actions.ACTION_CREATE_DEPLOYMENT:
            projects_list = self.server.get_list_from_one_type(item_type=item_type_projects)
            self.project_id_var = CommonWidgets.set_radio_items_frame(
                parent=self, list_items=projects_list, default_id=self.server.config.project_id,
                title=f"Select a project: ")

    def find_source_project_ids_list_with_type(self):
        items_list = self.source.get_list_from_one_type(item_type=self.server.config.type)
        projects_list = self.source.get_list_from_one_type(item_type=item_type_projects)
        project_ids_set = set()
        for item in items_list:
            if item.get(project_id_key):
                project_ids_set.add(item.get(project_id_key))
        return [project for project in projects_list if project.get(id_key) in project_ids_set]

    def set_clone_project_related(self):
        source_projects_list = self.find_source_project_ids_list_with_type()
        if not source_projects_list:
            messagebox.showerror(title=f"No item", message=f"{self.server.config.type} has no item")
            self.next_button.config(state=tk.DISABLED)
            return False
        self.source_project_id_var = CommonWidgets.set_radio_items_frame(
            parent=self, list_items=source_projects_list, default_id=self.source.config.project_id,
            title=f"Select a source project having {self.server.config.type}: ")
        CommonWidgets.directional_separator(parent=self, title=self.server.config.action)
        projects_list = self.server.get_list_from_one_type(item_type=item_type_projects)
        self.project_ids_var_dict = CommonWidgets.set_check_items_frame(
            parent=self, items_list=projects_list, default_ids=self.server.config.project_ids,
            title=f"Select the destination projects to be copied with {self.server.config.type}: ")

    def process_config(self):
        if self.types_var_dict:
            self.server.config.types = [item_type for item_type, item_type_var in self.types_var_dict.items()
                                        if item_type_var.get() == CommonWidgets.SELECTED]
        if self.type_var and self.type_var.get():
            self.server.config.type = self.type_var.get()
        if self.project_id_var and self.project_id_var.get():
            self.server.config.project_id = self.project_id_var.get()
        if self.source_project_id_var and self.source_project_id_var.get():
            self.source.config.project_id = self.source_project_id_var.get()
        if self.project_ids_var_dict:
            self.server.config.project_ids = \
                [project_id for project_id, project_id_var in self.project_ids_var_dict.items()
                 if project_id_var.get() == CommonWidgets.SELECTED]
        self.source.config.save_config()
        self.server.config.save_config()
        return True
