import tkinter as tk
from tkinter import messagebox, filedialog

from octopus_python_client.actions import ACTIONS_DICT, MIGRATION_LIST
from octopus_python_client.common import Common
from octopus_python_client.config import Config
from octopus_python_client.gui.common_widgets import CommonWidgets


class ServersWidgets(tk.Frame):
    def __init__(self, parent: tk.Frame, server: Common, source: Common, next_button: tk.Button = None,
                 submit_button: tk.Button = None):
        super().__init__(parent)

        self.server = server
        self.source = source

        self.next_button = next_button
        self.submit_button = submit_button

        self.local_data_var = None
        self.source_var_dict = None
        self.target_var_dict = None

        self.update_step()

    def update_step(self):
        self.target_var_dict = {}
        self.source_var_dict = {}
        tk.Label(self, text=f"{self.server.config.action} ({ACTIONS_DICT.get(self.server.config.action)})",
                 bd=2, relief="groove").grid(sticky=tk.W)
        if self.server.config.action in MIGRATION_LIST:
            self.source_var_dict = self.set_server_frame(config=self.source.config)
            # 'The source server data is loaded from local files, not directly from server'
            self.local_data_var = tk.StringVar()
            tk.Checkbutton(self, text="The source Octopus data is loaded from local files, not from Octopus server",
                           variable=self.local_data_var, state=tk.NORMAL).grid(sticky=tk.EW)
            self.local_data_var.set(self.source.config.local_data)
            CommonWidgets.directional_separator(parent=self, title=self.server.config.action)
        self.target_var_dict = self.set_server_frame(config=self.server.config)

    @staticmethod
    def file_dialog_ask_dir(tk_var: tk.StringVar):
        a_dir = filedialog.askdirectory(initialdir=tk_var.get(), title="Select path")
        if a_dir:
            tk_var.set(a_dir)

    def set_server_frame(self, config: Config):
        server_frame = tk.Frame(self)

        title = f"Octopus {'source' if config.is_source_server else 'target'} server"
        tk.Label(server_frame, text=title).grid(row=0, column=0, sticky=tk.EW, columnspan=8)

        tk.Label(server_frame, text="Server endpoint (must end with /api/)") \
            .grid(row=1, column=0, sticky=tk.E, columnspan=4)
        endpoint_variable = tk.StringVar()
        tk.Entry(server_frame, width=60, textvariable=endpoint_variable) \
            .grid(row=1, column=4, columnspan=4, sticky=tk.W)
        endpoint_variable.set(config.endpoint if config.endpoint else "")

        tk.Label(server_frame, text="API-KEY (must start with API-)").grid(row=2, column=0, sticky=tk.E, columnspan=4)
        api_key_variable = tk.StringVar()
        tk.Entry(server_frame, width=CommonWidgets.WIDTH_40, show="*", textvariable=api_key_variable) \
            .grid(row=2, column=4, columnspan=4, sticky=tk.W)
        api_key_variable.set(config.api_key if config.api_key else "")

        tk.Label(server_frame, text="user_name/password NOT used if API-KEY exists: ") \
            .grid(row=3, column=0, sticky=tk.E, columnspan=4)

        tk.Label(server_frame, text="user_name").grid(row=3, column=4, sticky=tk.E, columnspan=1)
        user_name_variable = tk.StringVar()
        tk.Entry(server_frame, width=CommonWidgets.WIDTH_10, textvariable=user_name_variable) \
            .grid(row=3, column=5, sticky=tk.W, columnspan=1)
        user_name_variable.set(config.user_name if config.user_name else "")

        tk.Label(server_frame, text="password").grid(row=3, column=6, columnspan=1, sticky=tk.E)
        password_variable = tk.StringVar()
        tk.Entry(server_frame, width=CommonWidgets.WIDTH_10, show="*", textvariable=password_variable) \
            .grid(row=3, column=7, sticky=tk.W, columnspan=1)
        password_variable.set(config.password if config.password else "")

        tk.Label(server_frame, text="Local path to store data for single Octopus server") \
            .grid(row=4, column=0, sticky=tk.E, columnspan=4)
        data_path_variable = tk.StringVar()
        tk.Entry(server_frame, width=60, textvariable=data_path_variable) \
            .grid(row=4, column=4, sticky=tk.W, columnspan=4)
        data_path_variable.set(config.data_path if config.data_path else "")

        tk.Button(server_frame, text='Select path',
                  command=lambda: self.file_dialog_ask_dir(tk_var=data_path_variable)) \
            .grid(row=4, column=8, sticky=tk.W, columnspan=1)

        server_frame.grid(sticky=tk.W)
        return {Config.ENDPOINT: endpoint_variable, Config.API_KEY: api_key_variable,
                Config.USER_NAME: user_name_variable, Config.PASSWORD: password_variable,
                Config.DATA_PATH: data_path_variable}

    @staticmethod
    def verify_spaces(server: Common):
        if not server.get_list_spaces():
            messagebox.showerror(
                title="No Spaces!",
                message=f"No spaces can be found on {'source' if server.config.is_source_server else 'target'} "
                        f"server {server.config.endpoint}. Please check your permission and/or credential")
            return False
        return True

    def process_config(self):
        if self.source_var_dict:
            source_config_dict = {}
            for key, variable in self.source_var_dict.items():
                source_config_dict[key] = variable.get()
            self.source.config.__dict__.update(source_config_dict)
            self.source.config.local_data = True if self.local_data_var.get() == CommonWidgets.SELECTED else False
            if not ServersWidgets.verify_spaces(server=self.source):
                return False
            self.source.config.save_config()
        target_config_dict = {}
        for key, variable in self.target_var_dict.items():
            target_config_dict[key] = variable.get()
        self.server.config.__dict__.update(target_config_dict)
        if not ServersWidgets.verify_spaces(server=self.server):
            return False
        self.server.config.save_config()
        return True
