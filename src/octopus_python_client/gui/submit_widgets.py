import threading
import tkinter as tk
from tkinter import messagebox

from octopus_python_client.actions import Actions, ACTIONS_DICT
from octopus_python_client.common import Common, item_type_channels, project_id_key, name_key, id_key
from octopus_python_client.migration import Migration
from octopus_python_client.release_deployment import ReleaseDeployment


class SubmitWidgets(tk.Frame):
    def __init__(self, parent, server: Common, source: Common):
        super().__init__(parent)
        self.server = server
        self.source = source
        self.overwrite_var = None
        self.channel_id_var = None
        self.release_version_var = None
        self.release_notes_var = None
        self.update_step()

    def update_step(self):
        tk.Label(self, text=f"{self.server.config.action} ({ACTIONS_DICT.get(self.server.config.action)})",
                 bd=2, relief="groove").grid(sticky=tk.W)
        if self.server.config.action == Actions.ACTION_CREATE_RELEASE:
            self.set_create_release_frame(parent_frame=self)
        else:
            self.set_clone_frame()

    def set_create_release_frame(self, parent_frame: tk.Frame):
        release_frame = tk.Frame(parent_frame)
        self.set_channels_frame(parent_frame=release_frame)

        tk.Label(release_frame, text="Release version number: ").grid(sticky=tk.W)
        self.release_version_var = tk.StringVar()
        self.release_version_var.set(self.server.config.release_version)
        tk.Entry(release_frame, width=20, textvariable=self.release_version_var).grid(sticky=tk.W)

        tk.Label(release_frame, text="Release notes: ").grid(sticky=tk.W)
        self.release_notes_var = tk.StringVar()
        self.release_notes_var.set(self.server.config.release_notes)
        tk.Entry(release_frame, width=80, textvariable=self.release_notes_var).grid(sticky=tk.W)

        release_frame.grid(sticky=tk.W)

    def set_channels_frame(self, parent_frame: tk.Frame):
        channels_frame = tk.Frame(parent_frame)
        tk.Label(channels_frame, text=f"Select a channel:", bd=2).grid(row=0, sticky=tk.W)
        list_channels = self.server.get_list_items_by_conditional_id(
            item_type=item_type_channels, condition_key=project_id_key, condition_id=self.server.config.project_id)
        # list_channels.sort(key=lambda one_channel: one_channel.get(name_key))
        self.channel_id_var = tk.StringVar()
        self.channel_id_var.set(self.server.config.channel_id)
        no_channels_per_row = 4
        for index, channel in enumerate(list_channels):
            self.server.config.channels[channel.get(id_key)] = channel.get(name_key)
            tk.Radiobutton(channels_frame, text=f"{channel.get(name_key)}", variable=self.channel_id_var,
                           value=channel.get(id_key), justify=tk.LEFT, command=lambda *args: None) \
                .grid(row=1 + int(index / no_channels_per_row), column=index % no_channels_per_row, sticky=tk.W)
        channels_frame.grid(sticky=tk.W)

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
        if self.server.config.action == Actions.ACTION_CREATE_RELEASE:
            self.server.config.channel_id = self.channel_id_var.get()
            self.server.config.release_version = self.release_version_var.get()
            self.server.config.release_notes = self.release_notes_var.get()
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
        elif self.server.config.action == Actions.ACTION_CREATE_RELEASE:
            project_name = self.server.config.projects.get(self.server.config.project_id)
            channel_name = self.server.config.channels.get(self.server.config.channel_id)
            msg = f"Are you sure you want to create a new release for project {project_name} with release version " \
                  f"{self.server.config.release_version}, and channel {channel_name}, release notes " \
                  f"{self.server.config.release_notes}?"
            if messagebox.askyesno(title=f"{self.server.config.action}", message=msg):
                ReleaseDeployment.create_release_direct(
                    config=self.server.config, release_version=self.server.config.release_version,
                    project_name=project_name, channel_name=channel_name, notes=self.server.config.release_notes)

    def start_run(self):
        threading.Thread(target=self.run_thread).start()
