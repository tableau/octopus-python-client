import threading
import tkinter as tk
from tkinter import messagebox

from octopus_python_client.actions import Actions
from octopus_python_client.common import Common
from octopus_python_client.migration import Migration


class SubmitWidgets(tk.Frame):
    def __init__(self, parent, server: Common, source: Common):
        super().__init__(parent)
        self.server = server
        self.source = source
        self.overwrite_var = None
        self.update_step()

    def update_step(self):
        tk.Label(self, text=f"{self.server.config.action} ({Actions.ACTIONS_DICT.get(self.server.config.action)})",
                 bd=2, relief="groove").grid(sticky=tk.W)
        self.set_clone_frame()

    def set_clone_frame(self):
        clone_frame = tk.Frame(self)
        self.overwrite_var = tk.StringVar()
        tk.Label(clone_frame, text=f"Options", bd=2).grid(row=0, sticky=tk.W)
        tk.Checkbutton(clone_frame, text="Overwrite the existing entities with the same name (skip if unchecked)",
                       variable=self.overwrite_var).grid(sticky=tk.W)
        self.overwrite_var.set("1" if self.server.config.overwrite else "0")
        clone_frame.grid(sticky=tk.W)

    def process_config(self):
        if self.overwrite_var:
            self.server.config.overwrite = True if self.overwrite_var.get() == "1" else False
            self.server.config.save_config()
        return True

    def run_thread(self):
        if self.server.config.action == Actions.ACTION_CLONE_SPACE:
            msg = f"Are you sure you want to clone types {self.server.config.types} from " \
                  f"{self.source.config.space_id} '{self.source.config.spaces.get(self.source.config.space_id)}' on " \
                  f"server {self.source.config.endpoint} to {self.server.config.space_id} " \
                  f"'{self.server.config.spaces.get(self.server.config.space_id)}' on server " \
                  f"{self.server.config.endpoint}? The existing entities with the same name will " \
                  f"{' ' if self.server.config.overwrite else 'NOT '}be overwritten."
            if messagebox.askyesno(title=f"{self.server.config.action}", message=msg):
                Migration(src_config=self.source.config, dst_config=self.server.config).clone_space_types()

    def start_run(self):
        threading.Thread(target=self.run_thread).start()
