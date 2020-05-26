import tkinter as tk
from tkinter import ttk

from octopus_python_client.actions import Actions
from octopus_python_client.common import Common


class SpacesWidgets(tk.Frame):
    def __init__(self, parent, server: Common, source: Common):
        super().__init__(parent)
        self.server = server
        self.source = source
        self.space_id_variable = None
        self.source_space_id_variable = None
        self.update_step()

    def update_step(self):
        self.space_id_variable = None
        self.source_space_id_variable = None
        tk.Label(self, text=f"{self.server.config.action} ({Actions.ACTIONS_DICT.get(self.server.config.action)})",
                 bd=2, relief="groove").grid(sticky=tk.W)
        if self.server.config.action in Actions.MIGRATION_LIST:
            self.source_space_id_variable = self.set_spaces_frame(server=self.source)
            ttk.Separator(self, orient=tk.HORIZONTAL).grid(sticky=tk.EW)
            tk.Label(self, text=f"\u21D3     \u21D3     \u21D3     \u21D3     \u21D3      {self.server.config.action}"
                                f"      \u21D3     \u21D3     \u21D3     \u21D3     \u21D3",
                     bd=2, relief="groove").grid(sticky=tk.EW)
            ttk.Separator(self, orient=tk.HORIZONTAL).grid(sticky=tk.EW)
        self.space_id_variable = self.set_spaces_frame(server=self.server)

    def select_action(self):
        pass

    def set_spaces_frame(self, server: Common):
        spaces_frame = tk.Frame(self)
        space_id_variable = tk.StringVar()
        space_id_variable.set(server.config.space_id)
        space_id_list = list(server.config.spaces.keys())
        space_id_list.sort(key=lambda sid: int(sid.split("-")[1]))
        for index, space_id in enumerate(space_id_list):
            tk.Radiobutton(spaces_frame, text=f"{space_id} {server.config.spaces.get(space_id)}",
                           variable=space_id_variable, value=space_id, justify=tk.LEFT, command=self.select_action) \
                .grid(row=int(index / 3), column=index % 3, sticky=tk.W, columnspan=1)
        spaces_frame.grid(sticky=tk.W)
        return space_id_variable

    def process_config(self):
        if self.source_space_id_variable:
            self.source.config.space_id = self.source_space_id_variable.get()
            self.source.config.save_config()
        self.server.config.space_id = self.space_id_variable.get()
        self.server.config.save_config()
        return True
