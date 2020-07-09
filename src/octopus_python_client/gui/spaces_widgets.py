import tkinter as tk

from octopus_python_client.actions import ACTIONS_DICT, MIGRATION_LIST, Actions
from octopus_python_client.common import Common
from octopus_python_client.constants import Constants
from octopus_python_client.gui.common_widgets import CommonWidgets


class SpacesWidgets(tk.Frame):
    def __init__(self, parent: tk.Frame, server: Common, source: Common, next_button: tk.Button = None,
                 submit_button: tk.Button = None):
        super().__init__(parent)
        self.server = server
        self.source = source

        self.next_button = next_button
        self.submit_button = submit_button

        self.source_space_id_var = None
        self.space_id_var = None
        self.space_ids_var_dict = None
        self.type_var = None

        self.update_step()

    def update_step(self):
        self.space_id_var = None
        self.source_space_id_var = None
        tk.Label(self, text=f"{self.server.config.action} ({ACTIONS_DICT.get(self.server.config.action)})",
                 bd=2, relief="groove").grid(sticky=tk.W)

        if self.server.config.action in MIGRATION_LIST:
            self.source_space_id_var = self.set_radio_spaces_frame(
                server=self.source, title="Select a space on the source server")
            CommonWidgets.directional_separator(parent=self, title=self.server.config.action)

        if self.server.config.action == Actions.ACTION_GET_SPACES:
            spaces_list = self.server.get_list_spaces()
            self.space_ids_var_dict = CommonWidgets.set_check_items_frame(
                parent=self, items_list=spaces_list, default_ids=self.server.config.space_ids, title="Select spaces")

        else:
            self.space_id_var = self.set_radio_spaces_frame(
                server=self.server, title="Select a space on the target server")
            if self.server.config.action == Actions.ACTION_CLONE_PROJECT_RELATED:
                self.type_var = CommonWidgets.set_radio_names_frame(
                    parent=self, list_names=Constants.PROJECT_RELATED_TYPES, default_name=self.server.config.type,
                    title="Select type: ")

    def set_radio_spaces_frame(self, server: Common, title: str = "Select a space: "):
        list_spaces = server.get_list_spaces()
        return CommonWidgets.set_radio_items_frame(
            parent=self, list_items=list_spaces, default_id=server.config.space_id, title=title)

    def process_config(self):
        if self.source_space_id_var:
            self.source.config.space_id = self.source_space_id_var.get()
            self.source.config.save_config()
        if self.type_var:
            self.server.config.type = self.type_var.get()
        if self.space_id_var:
            self.server.config.space_id = self.space_id_var.get()
        if self.space_ids_var_dict:
            self.server.config.space_ids = [space_id for space_id, space_id_var in self.space_ids_var_dict.items()
                                            if space_id_var.get() == CommonWidgets.SELECTED]
        self.server.config.save_config()
        return True
