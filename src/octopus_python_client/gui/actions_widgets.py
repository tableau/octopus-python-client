import tkinter as tk

from octopus_python_client.actions import ACTIONS_DICT
from octopus_python_client.common import Common


class ActionsWidgets(tk.Frame):
    def __init__(self, parent: tk.Frame, server: Common, source: Common, next_button: tk.Button = None,
                 submit_button: tk.Button = None):
        super().__init__(parent)
        self.server = server
        self.source = source

        self.next_button = next_button
        self.submit_button = submit_button

        self.select_action_variable = None

        self.update_step()

    def update_step(self):
        tk.Label(self, text="Action selection", bd=2, relief="groove").pack(side="top", fill="x")
        self.select_action_variable = tk.StringVar()
        self.select_action_variable.set(self.server.config.action)
        for action, description in ACTIONS_DICT.items():
            radio = tk.Radiobutton(self, text=f"{action} ({description})", variable=self.select_action_variable,
                                   value=action, justify=tk.LEFT, command=self.select_action)
            radio.pack(anchor=tk.W)

    def select_action(self):
        self.server.config.action = self.select_action_variable.get()

    def process_config(self):
        self.server.config.action = self.select_action_variable.get()
        self.server.config.save_config()
        return True
