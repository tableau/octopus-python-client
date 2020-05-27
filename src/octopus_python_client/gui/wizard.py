import tkinter as tk

from octopus_python_client.common import Common
from octopus_python_client.gui.actions_widgets import ActionsWidgets
from octopus_python_client.gui.options_widgets import OptionsWidgets
from octopus_python_client.gui.servers_widgets import ServersWidgets
from octopus_python_client.gui.spaces_widgets import SpacesWidgets
from octopus_python_client.gui.submit_widgets import SubmitWidgets


class Wizard(tk.Frame):
    def __init__(self, parent, server: Common, source: Common):
        super().__init__(parent)

        self.server = server
        self.source = source

        self.current_step_index = None
        self.current_step_widgets = None
        self.steps = [ActionsWidgets, ServersWidgets, SpacesWidgets, OptionsWidgets, SubmitWidgets]

        self.button_frame = tk.Frame(self, bd=1, relief="raised")
        self.back_button = tk.Button(self.button_frame, text="<< Back", command=self.back)
        self.next_button = tk.Button(self.button_frame, text="Next >>", command=self.next)
        self.submit_button = tk.Button(self.button_frame, text="Submit", command=self.submit)
        self.button_frame.pack(side="bottom", fill="x")

        self.content_frame = tk.Frame(self)
        self.show_step(0)
        self.content_frame.pack(side="top", fill="both", expand=True)

    def show_step(self, step):

        if self.current_step_widgets is not None:
            # remove current step
            self.current_step_widgets.pack_forget()

        self.current_step_index = step
        self.current_step_widgets = self.steps[step](self.content_frame, server=self.server, source=self.source)
        self.current_step_widgets.pack(fill="both", expand=True)

        if step == 0:
            # first step
            self.back_button.pack_forget()
            self.next_button.pack(side="right")
            self.submit_button.pack_forget()

        elif step == len(self.steps) - 1:
            # last step
            self.back_button.pack(side="left")
            self.next_button.pack_forget()
            self.submit_button.pack(side="right")

        else:
            # all other steps
            self.back_button.pack(side="left")
            self.next_button.pack(side="right")
            self.submit_button.pack_forget()

    def next(self):
        if self.current_step_widgets.process_config():
            self.show_step(self.current_step_index + 1)

    def back(self):
        if self.current_step_widgets.process_config():
            self.show_step(self.current_step_index - 1)

    def submit(self):
        self.current_step_widgets.process_config()
        self.current_step_widgets.start_run()
