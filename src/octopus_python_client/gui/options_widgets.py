import copy
import tkinter as tk

from octopus_python_client.actions import ACTIONS_DICT, Actions
from octopus_python_client.common import Common, inside_space_clone_types, item_type_projects, name_key, id_key
from octopus_python_client.utilities.helper import find_item


class OptionsWidgets(tk.Frame):
    NO_TYPES_PER_ROW = 5
    NO_PROJECTS_PER_ROW = 3

    def __init__(self, parent, server: Common, source: Common):
        super().__init__(parent)
        self.server = server
        self.source = source
        self.types_var_dict = None
        self.project_id_var = None
        self.type_var = None
        self.update_step()

    def update_step(self):
        tk.Label(self, text=f"{self.server.config.action} ({ACTIONS_DICT.get(self.server.config.action)})",
                 bd=2, relief="groove").grid(sticky=tk.W)
        if self.server.config.action == Actions.ACTION_CLONE_SPACE:
            self.set_check_types_frame()
        elif self.server.config.action == Actions.ACTION_CLONE_SPACE_ITEM:
            self.set_radio_types_frame()
        elif self.server.config.action == Actions.ACTION_CREATE_RELEASE:
            self.set_radio_projects_frame()

    def select_all_types(self):
        for item_type in inside_space_clone_types:
            self.types_var_dict.get(item_type).set("1")

    def deselect_all_types(self):
        for item_type in inside_space_clone_types:
            self.types_var_dict.get(item_type).set("0")

    def set_radio_projects_frame(self):
        projects_frame = tk.Frame(self)
        tk.Label(projects_frame, text=f"Select a project:", bd=2).grid(row=0, sticky=tk.W, columnspan=2)
        list_projects = self.server.get_list_from_one_type(item_type=item_type_projects)
        list_projects.sort(key=lambda one_project: one_project.get(name_key).lower())
        self.project_id_var = tk.StringVar()
        project = find_item(lst=list_projects, key=id_key, value=self.server.config.project_id)
        if project:
            self.project_id_var.set(self.server.config.project_id)
        else:
            self.project_id_var.set(list_projects[0].get(id_key))
        for index, project in enumerate(list_projects):
            tk.Radiobutton(projects_frame, text=f"{project.get(name_key)}", variable=self.project_id_var,
                           value=project.get(id_key), justify=tk.LEFT, command=lambda *args: None) \
                .grid(row=1 + int(index / OptionsWidgets.NO_PROJECTS_PER_ROW),
                      column=index % OptionsWidgets.NO_PROJECTS_PER_ROW, sticky=tk.W, columnspan=1)
        projects_frame.grid(sticky=tk.W)

    def set_radio_types_frame(self):
        types_frame = tk.Frame(self)
        tk.Label(types_frame, text=f"Select one item type", bd=2).grid(row=0, sticky=tk.W, columnspan=2)
        self.type_var = tk.StringVar()
        self.type_var.set(self.server.config.type)
        list_types = copy.deepcopy(inside_space_clone_types)
        list_types.sort()
        for index, item_type in enumerate(list_types):
            tk.Radiobutton(types_frame, text=f"{item_type}", variable=self.type_var, value=item_type, justify=tk.LEFT,
                           command=lambda *args: None) \
                .grid(row=1 + int(index / OptionsWidgets.NO_TYPES_PER_ROW),
                      column=index % OptionsWidgets.NO_TYPES_PER_ROW, sticky=tk.W, columnspan=1)
        types_frame.grid(sticky=tk.W)

    def set_check_types_frame(self):
        self.types_var_dict = {}
        types_frame = tk.Frame(self)
        tk.Label(types_frame, text=f"Select the item types you want", bd=2).grid(row=0, sticky=tk.W, columnspan=2)
        tk.Button(types_frame, text='Select all types', command=self.select_all_types) \
            .grid(row=0, column=2, sticky=tk.W, columnspan=1)
        tk.Button(types_frame, text='Deselect all types', command=self.deselect_all_types) \
            .grid(row=0, column=3, sticky=tk.W, columnspan=1)
        for index, item_type in enumerate(inside_space_clone_types):
            self.types_var_dict[item_type] = tk.StringVar()
            tk.Checkbutton(types_frame, text=item_type, variable=self.types_var_dict.get(item_type)) \
                .grid(row=int(1 + index / OptionsWidgets.NO_TYPES_PER_ROW),
                      column=index % OptionsWidgets.NO_TYPES_PER_ROW, sticky=tk.W)
            if item_type in self.server.config.types:
                self.types_var_dict.get(item_type).set("1")
            else:
                self.types_var_dict.get(item_type).set("0")
        types_frame.grid(sticky=tk.W)

    def process_config(self):
        if self.server.config.action == Actions.ACTION_CLONE_SPACE:
            self.server.config.types = []
            for item_type in inside_space_clone_types:
                if self.types_var_dict.get(item_type).get() == "1":
                    self.server.config.types.append(item_type)
        elif self.server.config.action == Actions.ACTION_CLONE_SPACE_ITEM:
            self.server.config.type = self.type_var.get()
        elif self.server.config.action == Actions.ACTION_CREATE_RELEASE:
            self.server.config.project_id = self.project_id_var.get()
        self.server.config.save_config()
        return True
