import getpass
import logging
import threading
import tkinter as tk
from pathlib import Path
from pprint import pformat
from time import strftime, localtime
from tkinter import messagebox

from octopus_python_client.actions import Actions, ACTIONS_DICT
from octopus_python_client.common import Common, item_type_channels, project_id_key, name_key, id_key, \
    item_type_projects, release_versions_key, version_key, item_type_packages, item_type_environments, \
    item_type_tenants, tenant_id_key
from octopus_python_client.constants import Constants
from octopus_python_client.gui.common_widgets import CommonWidgets
from octopus_python_client.migration import Migration
from octopus_python_client.release_deployment import ReleaseDeployment
from octopus_python_client.utilities.helper import find_item

logger = logging.getLogger(__name__)


class SubmitWidgets(tk.Frame):
    DIVIDER_BAR = "|"
    TAS = "tas"

    def __init__(self, parent: tk.Frame, server: Common, source: Common, next_button: tk.Button = None,
                 submit_button: tk.Button = None):
        super().__init__(parent)
        self.server = server
        self.source = source

        self.next_button = next_button
        self.submit_button = submit_button

        self.channel_id_var = None
        self.combobox_var = None
        self.deployment_notes_var = None
        self.env_frame = tk.Frame(self)
        self.env_id_var = None
        self.local_file_var = None
        self.new_item_name_var = None
        self.new_name_entry = None
        self.overwrite_var = None
        self.package_history_var = None
        self.package_name = ""
        self.release_id = ""
        self.release_notes_var = None
        self.release_version_num_var = None
        self.services_versions_text = None
        self.services_versions_vs_name = ""
        self.tenant_frame = tk.Frame(self)
        self.tenant_id_var = None

        self.update_step()

    def update_step(self):
        tk.Label(self, text=f"{self.server.config.action} ({ACTIONS_DICT.get(self.server.config.action)})",
                 bd=2, relief="groove").grid(sticky=tk.W)

        if self.server.config.action == Actions.ACTION_CREATE_RELEASE:
            self.set_create_release_frame()

        elif self.server.config.action == Actions.ACTION_CREATE_DEPLOYMENT:
            self.set_create_deployment_frame()

        elif self.server.config.action == Actions.ACTION_CLONE_PROJECT_RELATED:
            if not self.server.config.project_ids:
                messagebox.showerror(title=f"No project selected", message=f"No destination project was selected!")
                self.submit_button.config(state=tk.DISABLED)
                return
            items_list = self.source.get_list_items_by_conditional_id(
                item_type=self.server.config.type, condition_key=project_id_key,
                condition_id=self.source.config.project_id)
            if self.assert_items_list(items_list=items_list):
                self.set_clone_item_frame(items_list=items_list)

        elif self.server.config.action == Actions.ACTION_CLONE_SPACE \
                or self.server.config.action == Actions.ACTION_GET_SPACES:
            if not self.server.config.types:
                messagebox.showerror(
                    title=f"No types selected",
                    message=f"You must select at least one type")
                self.submit_button.config(state=tk.DISABLED)
                return
            if item_type_packages in self.server.config.types:
                self.set_package_history_widget()
            self.set_overwrite_widget()

        elif self.server.config.action == Actions.ACTION_CLONE_SPACE_ITEM:
            items_list = self.source.get_list_from_one_type(self.server.config.type)
            if self.assert_items_list(items_list=items_list):
                self.set_clone_item_frame(items_list=items_list)

        elif self.server.config.action == Actions.ACTION_GET:
            self.set_get_item_frame()

        elif self.server.config.action == Actions.ACTION_UPDATE:
            self.set_update_item_frame()

        else:
            self.submit_button.config(state=tk.DISABLED)

    def set_create_deployment_frame(self):
        releases_list = self.server.get_project_releases_sorted_list(project_id=self.server.config.project_id)
        project_name = self.server.get_item_name_by_id(item_type=item_type_projects,
                                                       item_id=self.server.config.project_id)
        if not releases_list:
            messagebox.showerror(
                title=f"No release",
                message=f"Project {project_name} does not have any releases. Please create a release first")
            self.submit_button.config(state=tk.DISABLED)
            return
        texts_list = [release.get(version_key) + SubmitWidgets.DIVIDER_BAR + release.get(id_key) for release in
                      releases_list]
        self.combobox_var = CommonWidgets.set_combobox_items_frame(
            parent=self, texts_list=texts_list, bind_func=self.process_release,
            title=f"Select a release for project {project_name} (the latest release is pre-selected)")
        self.deployment_notes_var = tk.StringVar()
        self.deployment_notes_var.set(self.server.config.deployment_notes)
        CommonWidgets.set_text_entry(parent=self, title="Deployment comments:", text_var=self.deployment_notes_var)
        self.process_release()

    def process_release(self, event=None):
        logger.info(msg=str(event))
        if SubmitWidgets.DIVIDER_BAR in self.combobox_var.get():
            release_version_id = self.combobox_var.get().split(SubmitWidgets.DIVIDER_BAR)
            self.release_id = release_version_id[1]
        else:
            self.release_id = self.combobox_var.get()
        promotion_information_dict = self.server.get_deployment_information(release_id=self.release_id)
        envs_list = promotion_information_dict.get("PromoteTo")
        tenants_list = promotion_information_dict.get("TenantPromotions")

        self.env_frame.destroy()
        self.tenant_frame.destroy()

        self.env_frame = tk.Frame(self)
        self.env_id_var = CommonWidgets.set_radio_items_frame(
            parent=self.env_frame, list_items=envs_list, title=f"Select an environment:")
        self.env_frame.grid(sticky=tk.W)

        self.tenant_frame = tk.Frame(self)
        self.tenant_id_var = CommonWidgets.set_radio_items_frame(
            parent=self.tenant_frame, list_items=tenants_list, default_id=self.server.config.tenant_id,
            title=f"Select a tenant:")
        self.tenant_frame.grid(sticky=tk.W)

    def set_release_notes(self, event=None):
        logger.info(msg=str(event))
        release_notes = "{'packages':{'" + self.package_name + "':'" + self.combobox_var.get() + \
                        "'},'release_versions':'" + self.services_versions_vs_name + "'}"
        self.release_notes_var.set(release_notes)
        self.server.config.package_version = self.combobox_var.get()
        self.update_services_versions()

    def set_services_versions_frame(self, project_name: str):
        tk.Label(self, text="Service versions pinned in Octopus variable set:").grid(sticky=tk.W)
        services_versions_vs_name_var = tk.StringVar()
        services_versions_vs_name_entry = tk.Entry(self, width=CommonWidgets.WIDTH_40,
                                                   textvariable=services_versions_vs_name_var)
        services_versions_vs_name_entry.grid(sticky=tk.W)
        services_versions_vs_name_entry.config(state=CommonWidgets.READ_ONLY)
        services_versions_vs_name_var.set(self.services_versions_vs_name)

        self.package_name = f"{SubmitWidgets.TAS}.{project_name}"
        package_history_list = self.server.get_package_history_list_by_name(package_name=self.package_name)
        package_versions_list = [package.get(version_key) for package in package_history_list]
        self.combobox_var = CommonWidgets.set_combobox_items_frame(
            parent=self, texts_list=package_versions_list, bind_func=self.set_release_notes,
            default_text=self.server.config.package_version, title=f"Select {self.package_name} version:",
            width=CommonWidgets.WIDTH_20)

    def set_release_notes_entry(self):
        tk.Label(self, text="Release notes (grayed out if the release notes is a python dictionary and used for pinning"
                            " package versions):").grid(sticky=tk.W)
        self.release_notes_var = tk.StringVar()
        # self.release_notes_var.set(self.server.config.release_notes)
        release_notes_entry = tk.Entry(self, width=CommonWidgets.WIDTH_120, textvariable=self.release_notes_var)
        release_notes_entry.grid(sticky=tk.W)
        return release_notes_entry

    def update_services_versions(self):
        self.services_versions_text.config(state=tk.NORMAL)
        self.services_versions_text.delete(1.0, tk.END)
        project_name = self.server.get_item_name_by_id(item_type=item_type_projects,
                                                       item_id=self.server.config.project_id)
        channel_name = self.server.get_item_name_by_id(item_type=item_type_channels, item_id=self.channel_id_var.get())
        select_packages_dict = ReleaseDeployment.get_package_versions(
            config=self.server.config, project_name=project_name, channel_name=channel_name,
            notes=self.release_notes_var.get())
        self.services_versions_text.insert(tk.END, pformat(select_packages_dict))
        self.services_versions_text.config(state=tk.DISABLED)

    def set_services_versions_textbox(self):
        tk.Label(self, text="The package versions which will be used for creating the new release:").grid(sticky=tk.W)
        self.services_versions_text = tk.Text(self, width=CommonWidgets.WIDTH_80, height=CommonWidgets.HEIGHT_7)
        self.services_versions_text.grid(sticky=tk.W)

    def set_create_release_frame(self):
        self.set_radio_channels_frame()

        tk.Label(self, text="Release version number: ").grid(sticky=tk.W)
        self.release_version_num_var = tk.StringVar()
        local_time = strftime("%Y.%m%d.%H%M%S", localtime())
        current_user = getpass.getuser()
        self.release_version_num_var.set(f"{local_time}-{current_user}")
        tk.Entry(self, width=CommonWidgets.WIDTH_40, textvariable=self.release_version_num_var).grid(sticky=tk.W)

        project_name = self.server.get_item_name_by_id(
            item_type=item_type_projects, item_id=self.server.config.project_id)
        self.services_versions_vs_name = release_versions_key + "." + project_name
        services_versions_list = self.server.get_list_variables_by_set_name_or_id(
            set_name=self.services_versions_vs_name)
        if services_versions_list:
            self.set_services_versions_frame(project_name=project_name)
            self.set_release_notes_entry().config(state=CommonWidgets.READ_ONLY)
            self.set_services_versions_textbox()
            self.set_release_notes()
        else:
            self.set_release_notes_entry()

    def set_get_item_frame(self):
        items_list = self.server.get_list_from_one_type(self.server.config.type)
        if self.assert_items_list(items_list=items_list):
            self.set_combobox_items_frame(items_list=items_list, common=self.server, bind_func=self.set_local_file)
            self.set_update_file_path_frame()
            self.set_local_file()
            self.set_check_package_overwrite()

    def set_update_item_frame(self):
        items_list = self.server.get_list_from_one_type(self.server.config.type)
        if self.assert_items_list(items_list=items_list):
            self.set_combobox_items_frame(items_list=items_list, common=self.server,
                                          bind_func=self.set_check_local_file)
            self.set_update_file_path_frame()
            self.set_check_local_file()

    def set_update_file_path_frame(self):
        tk.Label(self, text="The local file as the configuration").grid(sticky=tk.W)
        self.local_file_var = tk.StringVar()
        tk.Entry(self, width=CommonWidgets.WIDTH_120, textvariable=self.local_file_var, state=CommonWidgets.READ_ONLY) \
            .grid(sticky=tk.W)

    def assert_items_list(self, items_list: list):
        if not items_list or len(items_list) == 0:
            messagebox.showerror(title=f"No item", message=f"{self.server.config.type} has no item")
            self.submit_button.config(state=tk.DISABLED)
            return False
        return True

    def set_clone_item_frame(self, items_list: list):
        self.set_combobox_items_frame(items_list=items_list, common=self.source, bind_func=self.set_new_item_name)
        self.set_new_name_item_frame()
        self.set_new_item_name()
        self.set_check_package_overwrite()

    def set_check_package_overwrite(self):
        if item_type_packages == self.server.config.type:
            self.set_package_history_widget()
        self.set_overwrite_widget()

    def set_new_name_item_frame(self):
        tk.Label(self, text="New item name to be cloned (grayed out if the item has no name): ").grid(sticky=tk.W)
        self.new_item_name_var = tk.StringVar()
        self.new_name_entry = tk.Entry(self, width=CommonWidgets.WIDTH_40, textvariable=self.new_item_name_var)
        self.new_name_entry.grid(sticky=tk.W)

    def set_combobox_items_frame(self, items_list: list, common: Common, bind_func):
        default_item = find_item(lst=items_list, key=id_key, value=common.config.item_id)
        default_text = SubmitWidgets.construct_item_name_id_text(item=default_item)
        texts_list = [SubmitWidgets.construct_item_name_id_text(item=item) for item in items_list]
        self.combobox_var = CommonWidgets.set_combobox_items_frame(
            parent=self, texts_list=texts_list, bind_func=bind_func, default_text=default_text,
            title=f"Select an item for type {self.server.config.type} (item name|id, or version|id or id only:")

    def set_new_item_name(self, event=None):
        logger.info(msg=str(event))
        self.server.log_info_print(f"split {self.combobox_var.get()}")
        item_name, item_id = SubmitWidgets.split_item_name_id(self.combobox_var.get())
        if item_name:
            self.new_item_name_var.set(item_name)
        else:
            self.new_name_entry.config(state=CommonWidgets.READ_ONLY)
        self.source.config.item_id = item_id
        self.source.config.item_name = ""
        self.server.log_info_print(f"item_id: {item_id}")

    def set_check_local_file(self, event=None):
        logger.info(msg=str(event))
        local_file = self.set_local_file()
        self.check_local_file(local_file=local_file)

    def set_local_file(self, event=None):
        logger.info(msg=str(event))
        item_name, item_id = SubmitWidgets.split_item_name_id(self.combobox_var.get())
        self.server.config.item_id = item_id
        self.server.config.item_name = item_name
        local_file = self.server.get_local_single_item_file_smartly(
            item_type=self.server.config.type, item_name=item_name, item_id=item_id)
        self.local_file_var.set(local_file)
        return local_file

    def check_local_file(self, local_file):
        if Path(local_file).is_file():
            self.submit_button.config(state=tk.NORMAL)
        else:
            messagebox.showerror(title=f"File not exist", message=f"{local_file} does not exist")
            self.submit_button.config(state=tk.DISABLED)

    @staticmethod
    def split_item_name_id(item_name_id: str):
        if SubmitWidgets.DIVIDER_BAR in item_name_id:
            item_name_id_list = item_name_id.split(SubmitWidgets.DIVIDER_BAR)
            item_name = item_name_id_list[0]
            item_id = item_name_id_list[1]
        else:
            item_name = ""
            item_id = item_name_id
        return item_name, item_id

    @staticmethod
    def construct_item_name_id_text(item):
        if not item:
            return None
        elif isinstance(item, str):
            return item
        elif item.get(name_key) and item.get(id_key):
            return item.get(name_key) + SubmitWidgets.DIVIDER_BAR + item.get(id_key)
        elif item.get(tenant_id_key) and item.get(Constants.TENANT_NAME_KEY):
            return item.get(Constants.TENANT_NAME_KEY) + SubmitWidgets.DIVIDER_BAR + item.get(tenant_id_key)
        elif item.get(id_key):
            return item.get(id_key)
        else:
            return ""

    def set_radio_channels_frame(self):
        channels_list = self.server.get_list_items_by_conditional_id(
            item_type=item_type_channels, condition_key=project_id_key, condition_id=self.server.config.project_id)
        default_channel = find_item(lst=channels_list, key=Constants.IS_DEFAULT, value=True)
        if default_channel:
            default_channel_id = default_channel.get(id_key)
        else:
            default_channel_id = self.server.config.channel_id
        self.channel_id_var = CommonWidgets.set_radio_items_frame(
            parent=self, list_items=channels_list, default_id=default_channel_id,
            title=f"Select a channel (default one is pre-selected):")

    def set_overwrite_widget(self):
        self.overwrite_var = tk.StringVar()
        tk.Checkbutton(self, text="Overwrite the existing entities of the same names, including the referenced entities"
                                  " (will skip if unchecked)", variable=self.overwrite_var).grid(sticky=tk.W)
        self.overwrite_var.set(CommonWidgets.SELECTED if self.server.config.overwrite else CommonWidgets.UNSELECTED)

    def set_package_history_widget(self):
        self.package_history_var = tk.StringVar()
        tk.Checkbutton(
            self, text="Clone/download all historical versions of the packages (clone/download only the latest version "
                       "if unchecked)", variable=self.package_history_var).grid(sticky=tk.W)
        self.package_history_var.set(
            CommonWidgets.SELECTED if self.server.config.package_history else CommonWidgets.UNSELECTED)

    def process_config(self):
        if self.overwrite_var:
            self.server.config.overwrite = True if self.overwrite_var.get() == CommonWidgets.SELECTED else False
        if self.channel_id_var:
            self.server.config.channel_id = self.channel_id_var.get()
        if self.release_version_num_var:
            self.server.config.release_version = self.release_version_num_var.get()
        if self.release_notes_var:
            self.server.config.release_notes = self.release_notes_var.get()
        if self.package_history_var:
            self.server.config.package_history = \
                True if self.package_history_var.get() == CommonWidgets.SELECTED else False
        if self.tenant_id_var:
            self.server.config.tenant_id = self.tenant_id_var.get()
        if self.deployment_notes_var:
            self.server.config.deployment_notes = self.deployment_notes_var.get()
        self.server.config.save_config()
        self.source.config.save_config()
        return True

    def run_thread(self):
        run_action = False
        historical_package_msg = f"\nThe historical versions of packages will " \
                                 f"{'' if self.server.config.package_history else 'NOT '}be downloaded. "
        overwrite_msg = f"\nThe existing entities will {'' if self.server.config.overwrite else 'NOT '}be overwritten."
        if self.server.config.action == Actions.ACTION_CLONE_SPACE:
            msg = f"Are you sure you want to clone types {self.server.config.types} from " \
                  f"{self.source.config.space_id} on server {self.source.config.endpoint} to " \
                  f"{self.server.config.space_id} on server {self.server.config.endpoint}?"
            msg += (historical_package_msg if item_type_packages in self.server.config.types else "")
            msg += overwrite_msg
            if messagebox.askyesno(title=f"{self.server.config.action}", message=msg):
                run_action = True
                Migration(src_config=self.source.config, dst_config=self.server.config).clone_space_types()

        elif self.server.config.action == Actions.ACTION_CLONE_SPACE_ITEM:
            # msg = f"cloning {item_type} {item_badge} from {self._src_config.space_id} on server "
            # f"{self._src_config.endpoint} to {self._dst_config.space_id} on server {self._dst_config.endpoint}")
            msg = f"Are you sure you want to clone type {self.server.config.type} of {self.combobox_var.get()}" \
                  f" from {self.source.config.space_id} on server {self.source.config.endpoint} to " \
                  f"{self.new_item_name_var.get()} in {self.server.config.space_id} on server " \
                  f"{self.server.config.endpoint}?"
            msg += (historical_package_msg if item_type_packages == self.server.config.type else "")
            msg += overwrite_msg
            if messagebox.askyesno(title=f"{self.server.config.action}", message=msg):
                run_action = True
                pars_dict = None
                if self.new_item_name_var.get():
                    pars_dict = {Constants.NEW_ITEM_NAME_KEY: self.new_item_name_var.get()}
                Migration(src_config=self.source.config, dst_config=self.server.config) \
                    .clone_space_item_new_name(pars_dict=pars_dict)

        elif self.server.config.action == Actions.ACTION_CLONE_PROJECT_RELATED:
            msg = f"Are you sure you want to clone type {self.server.config.type} of {self.combobox_var.get()}" \
                  f" from {self.source.config.space_id} on server {self.source.config.endpoint} to " \
                  f"{self.new_item_name_var.get()} in projects {self.server.config.project_ids} in " \
                  f"{self.server.config.space_id} on server {self.server.config.endpoint}?"
            msg += overwrite_msg
            if messagebox.askyesno(title=f"{self.server.config.action}", message=msg):
                run_action = True
                pars_dict = {Constants.NEW_ITEM_NAME_KEY: self.new_item_name_var.get(),
                             Constants.PROJECT_IDS_KEY: self.server.config.project_ids}
                Migration(src_config=self.source.config, dst_config=self.server.config) \
                    .clone_space_item_new_name(pars_dict=pars_dict)

        elif self.server.config.action == Actions.ACTION_CREATE_RELEASE:
            project_name = self.server.get_or_delete_single_item_by_id(
                item_type=item_type_projects, item_id=self.server.config.project_id).get(name_key)
            channel_name = self.server.get_or_delete_single_item_by_id(
                item_type=item_type_channels, item_id=self.server.config.channel_id).get(name_key)
            msg = f"Are you sure you want to create a new release for project {project_name} with release version " \
                  f"{self.server.config.release_version}, and channel {channel_name}, release notes " \
                  f"{self.server.config.release_notes}?"
            if messagebox.askyesno(title=f"{self.server.config.action}", message=msg):
                run_action = True
                ReleaseDeployment.create_release_direct(
                    config=self.server.config, release_version=self.server.config.release_version,
                    project_name=project_name, channel_name=channel_name, notes=self.server.config.release_notes)

        elif self.server.config.action == Actions.ACTION_CREATE_DEPLOYMENT:
            project_name = self.server.get_item_name_by_id(
                item_type=item_type_projects, item_id=self.server.config.project_id)
            env_name = self.server.get_item_name_by_id(
                item_type=item_type_environments, item_id=self.env_id_var.get())
            tenant_name = self.server.get_item_name_by_id(
                item_type=item_type_tenants, item_id=self.tenant_id_var.get())
            msg = f"Are you sure you want to create a new deployment for {self.release_id} in project {project_name} " \
                  f"with environment {env_name}, tenant {tenant_name} and comments {self.deployment_notes_var.get()}?"
            if messagebox.askyesno(title=f"{self.server.config.action}", message=msg):
                run_action = True
                ReleaseDeployment.create_deployment_direct(
                    config=self.server.config, environment_name=env_name, tenant_name=tenant_name,
                    release_id=self.release_id, project_name=project_name, comments=self.deployment_notes_var.get())

        elif self.server.config.action == Actions.ACTION_GET_SPACES:
            msg = f"Are you sure you want to download types {self.server.config.types} from spaces " \
                  f"{self.server.config.space_ids} on server {self.server.config.endpoint}?"
            msg += (historical_package_msg if item_type_packages in self.server.config.types else "")
            msg += overwrite_msg
            if messagebox.askyesno(title=f"{self.server.config.action}", message=msg):
                run_action = True
                spaces_ids = ",".join(self.server.config.space_ids)
                types = ",".join(self.server.config.types)
                self.server.get_spaces_save(space_id_or_name_comma_delimited=spaces_ids,
                                            item_types_comma_delimited=types)

        elif self.server.config.action == Actions.ACTION_GET:
            msg = f"Are you sure you want to download item {self.server.config.item_id} from space " \
                  f"{self.server.config.space_id} on server {self.server.config.endpoint} to local file " \
                  f"{self.local_file_var.get()}?"
            msg += (historical_package_msg if item_type_packages == self.server.config.type else "")
            msg += overwrite_msg
            if messagebox.askyesno(title=f"{self.server.config.action}", message=msg):
                run_action = True
                self.server.get_single_item_by_name_or_id_save(
                    item_type=self.server.config.type, item_id=self.server.config.item_id)

        elif self.server.config.action == Actions.ACTION_UPDATE:
            msg = f"Are you sure you want to update item {self.server.config.item_name} {self.server.config.item_id} " \
                  f"from local file {self.local_file_var.get()} to space {self.server.config.space_id} on server " \
                  f"{self.server.config.endpoint}?"
            if messagebox.askyesno(title=f"{self.server.config.action}", message=msg):
                run_action = True
                self.server.update_single_item_save(
                    item_type=self.server.config.type, item_name=self.server.config.item_name,
                    item_id=self.server.config.item_id)

        else:
            self.server.log_info_print("not a valid action")

        if run_action:
            messagebox.showinfo(
                title="Done!",
                message=f"{self.server.config.action} ({ACTIONS_DICT.get(self.server.config.action)}) is done!")

    def start_run(self):
        threading.Thread(target=self.run_thread).start()
