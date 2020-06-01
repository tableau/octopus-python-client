import threading
import tkinter as tk
from tkinter import messagebox, ttk

from octopus_python_client.actions import Actions, ACTIONS_DICT
from octopus_python_client.common import Common, item_type_channels, project_id_key, name_key, id_key, \
    item_type_projects
from octopus_python_client.migration import Migration
from octopus_python_client.release_deployment import ReleaseDeployment
from octopus_python_client.utilities.helper import find_item, find_index


class SubmitWidgets(tk.Frame):
    NO_ITEMS_PER_ROW = 6
    DIVIDER_BAR = "|"

    def __init__(self, parent, server: Common, source: Common):
        super().__init__(parent)
        self.server = server
        self.source = source

        self.channel_id_var = None
        self.list_items = []
        self.new_item_name_var = None
        self.overwrite_var = None
        self.release_version_var = None
        self.release_notes_var = None
        self.item_id_name_var = None
        self.has_item_name = None

        self.update_step()

    def update_step(self):
        tk.Label(self, text=f"{self.server.config.action} ({ACTIONS_DICT.get(self.server.config.action)})",
                 bd=2, relief="groove").grid(sticky=tk.W)
        if self.server.config.action == Actions.ACTION_CREATE_RELEASE:
            self.set_create_release_frame(parent_frame=self)
        elif self.server.config.action == Actions.ACTION_CLONE_SPACE_ITEM:
            self.set_clone_space_item_frame(parent_frame=self)
        else:
            self.set_clone_space_frame()

    def set_create_release_frame(self, parent_frame: tk.Frame):
        release_frame = tk.Frame(parent_frame)
        self.set_radio_channels_frame(parent_frame=release_frame)

        tk.Label(release_frame, text="Release version number: ").grid(sticky=tk.W)
        self.release_version_var = tk.StringVar()
        self.release_version_var.set(self.server.config.release_version)
        tk.Entry(release_frame, width=20, textvariable=self.release_version_var).grid(sticky=tk.W)

        tk.Label(release_frame, text="Release notes: ").grid(sticky=tk.W)
        self.release_notes_var = tk.StringVar()
        self.release_notes_var.set(self.server.config.release_notes)
        tk.Entry(release_frame, width=80, textvariable=self.release_notes_var).grid(sticky=tk.W)

        release_frame.grid(sticky=tk.W)

    def set_clone_space_item_frame(self, parent_frame: tk.Frame):
        space_item_frame = tk.Frame(parent_frame)
        if not self.set_combobox_items_frame(parent_frame=space_item_frame, source=self.source, server=self.server):
            return

        tk.Label(space_item_frame, text="New item name to be cloned: ").grid(sticky=tk.W)
        tk.Entry(space_item_frame, width=40, textvariable=self.new_item_name_var).grid(sticky=tk.W)
        self.set_new_item_name()

        self.set_overwrite_widget(parent_frame=space_item_frame)
        space_item_frame.grid(sticky=tk.W)

    def set_new_item_name(self, event=None):
        self.server.log_info_print(msg=str(event))
        if self.has_item_name:
            item_name_id = self.item_id_name_var.get().split(SubmitWidgets.DIVIDER_BAR)
            item_name = item_name_id[0]
            self.new_item_name_var.set(item_name)
            item_id = item_name_id[1]
        else:
            item_id = self.item_id_name_var.get()
        self.source.config.item_id = item_id

    def set_combobox_items_frame(self, parent_frame: tk.Frame, source: Common, server: Common):
        items_frame = tk.Frame(parent_frame)
        tk.Label(items_frame, text=f"Select an item for type {server.config.type} (item name|id):", bd=2) \
            .grid(sticky=tk.W)
        self.list_items = source.get_list_from_one_type(server.config.type)
        if not self.list_items:
            messagebox.showerror(title=f"No item", message=f"{server.config.type} has no item")
            return False

        self.new_item_name_var = tk.StringVar()
        self.item_id_name_var = tk.StringVar()
        item_combobox = ttk.Combobox(items_frame, width=80, textvariable=self.item_id_name_var)

        if self.list_items[0].get(name_key):
            self.has_item_name = True
            self.list_items.sort(key=lambda one_item: one_item.get(name_key).lower())
            list_name_ids = [item.get(name_key) + SubmitWidgets.DIVIDER_BAR + item.get(id_key) for item in
                             self.list_items]
            item_combobox["values"] = tuple(list_name_ids)
        else:
            self.has_item_name = False
            self.list_items.sort(key=lambda one_item: one_item.get(id_key).lower())
            list_ids = [item.get(id_key) for item in self.list_items]
            item_combobox["values"] = tuple(list_ids)

        index = find_index(lst=self.list_items, key=id_key, value=self.source.config.item_id)
        item_combobox.current(0 if index < 0 else index)

        item_combobox.grid(sticky=tk.W)
        item_combobox.bind("<<ComboboxSelected>>", self.set_new_item_name)
        items_frame.grid(sticky=tk.W)
        return True

    def set_radio_channels_frame(self, parent_frame: tk.Frame):
        channels_frame = tk.Frame(parent_frame)
        tk.Label(channels_frame, text=f"Select a channel:", bd=2).grid(row=0, sticky=tk.W)
        list_channels = self.server.get_list_items_by_conditional_id(
            item_type=item_type_channels, condition_key=project_id_key, condition_id=self.server.config.project_id)
        # list_channels.sort(key=lambda one_channel: one_channel.get(name_key))
        self.channel_id_var = tk.StringVar()
        channel = find_item(lst=list_channels, key=id_key, value=self.server.config.channel_id)
        if channel:
            self.channel_id_var.set(self.server.config.channel_id)
        else:
            self.channel_id_var.set(list_channels[0].get(id_key))
        no_channels_per_row = 4
        for index, channel in enumerate(list_channels):
            tk.Radiobutton(channels_frame, text=f"{channel.get(name_key)}", variable=self.channel_id_var,
                           value=channel.get(id_key), justify=tk.LEFT, command=lambda *args: None) \
                .grid(row=1 + int(index / no_channels_per_row), column=index % no_channels_per_row, sticky=tk.W)
        channels_frame.grid(sticky=tk.W)

    def set_clone_space_frame(self):
        clone_frame = tk.Frame(self)
        tk.Label(clone_frame, text=f"Options", bd=2).grid(row=0, sticky=tk.W)
        self.set_overwrite_widget(parent_frame=clone_frame)
        clone_frame.grid(sticky=tk.W)

    def set_overwrite_widget(self, parent_frame: tk.Frame):
        self.overwrite_var = tk.StringVar()
        tk.Checkbutton(parent_frame, text="Overwrite the existing entities with the same name (skip if unchecked)",
                       variable=self.overwrite_var).grid(sticky=tk.W)
        self.overwrite_var.set("1" if self.server.config.overwrite else "0")

    def process_config(self):
        if self.overwrite_var:
            self.server.config.overwrite = True if self.overwrite_var.get() == "1" else False
        if self.server.config.action == Actions.ACTION_CREATE_RELEASE:
            self.server.config.channel_id = self.channel_id_var.get()
            self.server.config.release_version = self.release_version_var.get()
            self.server.config.release_notes = self.release_notes_var.get()
        self.server.config.save_config()
        self.source.config.save_config()
        return True

    def run_thread(self):
        if self.server.config.action == Actions.ACTION_CLONE_SPACE:
            msg = f"Are you sure you want to clone types {self.server.config.types} from " \
                  f"{self.source.config.space_id} on server {self.source.config.endpoint} to " \
                  f"{self.server.config.space_id} on server {self.server.config.endpoint}? " \
                  f"The existing entities with the same name will " \
                  f"{' ' if self.server.config.overwrite else 'NOT '}be overwritten."
            if messagebox.askyesno(title=f"{self.server.config.action}", message=msg):
                Migration(src_config=self.source.config, dst_config=self.server.config).clone_space_types()
        elif self.server.config.action == Actions.ACTION_CLONE_SPACE_ITEM and self.item_id_name_var:
            # msg = f"cloning {item_type} {item_badge} from {self._src_config.space_id} on server "
            # f"{self._src_config.endpoint} to {self._dst_config.space_id} on server {self._dst_config.endpoint}")
            msg = f"Are you sure you want to clone type {self.server.config.type} of {self.item_id_name_var.get()}" \
                  f" from {self.source.config.space_id} on server {self.source.config.endpoint} to " \
                  f"{self.new_item_name_var.get()} in {self.server.config.space_id} on server " \
                  f"{self.server.config.endpoint}? The existing entities with the same name will " \
                  f"{' ' if self.server.config.overwrite else 'NOT '}be overwritten."
            if messagebox.askyesno(title=f"{self.server.config.action}", message=msg):
                Migration(src_config=self.source.config, dst_config=self.server.config) \
                    .clone_space_item_new_name(new_item_name=self.new_item_name_var.get())
        elif self.server.config.action == Actions.ACTION_CREATE_RELEASE:
            project_name = self.server.get_or_delete_single_item_by_id(
                item_type=item_type_projects, item_id=self.server.config.project_id).get(name_key)
            channel_name = self.server.get_or_delete_single_item_by_id(
                item_type=item_type_channels, item_id=self.server.config.channel_id).get(name_key)
            msg = f"Are you sure you want to create a new release for project {project_name} with release version " \
                  f"{self.server.config.release_version}, and channel {channel_name}, release notes " \
                  f"{self.server.config.release_notes}?"
            if messagebox.askyesno(title=f"{self.server.config.action}", message=msg):
                ReleaseDeployment.create_release_direct(
                    config=self.server.config, release_version=self.server.config.release_version,
                    project_name=project_name, channel_name=channel_name, notes=self.server.config.release_notes)

    def start_run(self):
        threading.Thread(target=self.run_thread).start()
