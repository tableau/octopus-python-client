import tkinter as tk
from tkinter import ttk, messagebox

from octopus_python_client.actions import Actions
from octopus_python_client.common import Common, inside_space_clone_types
from octopus_python_client.config import Config
from octopus_python_client.migration import Migration


class ActionsWidgets(tk.Frame):
    def __init__(self, parent, server: Common, source: Common):
        super().__init__(parent)
        self.server = server
        self.source = source
        self.select_action_variable = tk.StringVar()

        self.update_step()

    def update_step(self):
        tk.Label(self, text="Action selection", bd=2, relief="groove").pack(side="top", fill="x")
        self.select_action_variable.set(self.server.config.action)
        for action, description in Actions.ACTIONS_DICT.items():
            radio = tk.Radiobutton(self, text=f"{action} ({description})", variable=self.select_action_variable,
                                   value=action, justify=tk.LEFT, command=self.select_action)
            radio.pack(anchor=tk.W)

    def select_action(self):
        self.server.config.action = self.select_action_variable.get()

    def process_config(self):
        self.server.config.action = self.select_action_variable.get()
        self.server.config.save_config()
        return True


class ServersWidgets(tk.Frame):
    def __init__(self, parent, server: Common, source: Common):
        super().__init__(parent)

        self.server = server
        self.source = source
        self.local_data = tk.StringVar()
        self.target_variables = {}
        self.source_variables = {}
        self.update_step()

    def update_step(self):
        self.target_variables = {}
        self.source_variables = {}
        tk.Label(self, text=f"{self.server.config.action} ({Actions.ACTIONS_DICT.get(self.server.config.action)})",
                 bd=2, relief="groove").grid(sticky=tk.W)
        if self.server.config.action in Actions.MIGRATION_LIST:
            self.source_variables = self.set_server_frame(config=self.source.config)
            # 'The source server data is loaded from local files, not directly from server'
            tk.Checkbutton(self, text="The source Octopus data is loaded from local files, not from Octopus server",
                           variable=self.local_data).grid(sticky=tk.EW)
            self.local_data.set(self.source.config.local_data)
            ttk.Separator(self, orient=tk.HORIZONTAL).grid(sticky=tk.EW)
            tk.Label(self, text=f"\u21D3     \u21D3     \u21D3     \u21D3     \u21D3      {self.server.config.action}"
                                f"      \u21D3     \u21D3     \u21D3     \u21D3     \u21D3",
                     bd=2, relief="groove").grid(sticky=tk.EW)
            ttk.Separator(self, orient=tk.HORIZONTAL).grid(sticky=tk.EW)
        self.target_variables = self.set_server_frame(config=self.server.config)

    def set_server_frame(self, config: Config):
        server_frame = tk.Frame(self)

        title = f"Octopus {'source' if config.is_source_server else 'target'} server"
        tk.Label(server_frame, text=title).grid(row=0, column=0, sticky=tk.EW, columnspan=8)

        tk.Label(server_frame, text="Server endpoint (must end with /api/)") \
            .grid(row=1, column=0, sticky=tk.E, columnspan=4)
        endpoint_variable = tk.StringVar()
        tk.Entry(server_frame, width=40, textvariable=endpoint_variable) \
            .grid(row=1, column=4, columnspan=4, sticky=tk.W)
        endpoint_variable.set(config.endpoint if config.endpoint else "")

        tk.Label(server_frame, text="API-KEY (must start with API-)").grid(row=2, column=0, sticky=tk.E, columnspan=4)
        api_key_variable = tk.StringVar()
        tk.Entry(server_frame, width=40, show="*", textvariable=api_key_variable) \
            .grid(row=2, column=4, columnspan=4, sticky=tk.W)
        api_key_variable.set(config.api_key if config.api_key else "")

        tk.Label(server_frame, text="user_name/password NOT used if API-KEY exists: ") \
            .grid(row=3, column=0, sticky=tk.E, columnspan=4)

        tk.Label(server_frame, text="user_name").grid(row=3, column=4, sticky=tk.W, columnspan=1)
        user_name_variable = tk.StringVar()
        tk.Entry(server_frame, width=10, textvariable=user_name_variable) \
            .grid(row=3, column=5, sticky=tk.W, columnspan=1)
        user_name_variable.set(config.user_name if config.user_name else "")

        tk.Label(server_frame, text="password").grid(row=3, column=6, columnspan=1, sticky=tk.E)
        password_variable = tk.StringVar()
        tk.Entry(server_frame, width=10, show="*", textvariable=password_variable) \
            .grid(row=3, column=7, sticky=tk.E, columnspan=1)
        password_variable.set(config.password if config.password else "")

        tk.Label(server_frame, text="Local path to store data for single Octopus server") \
            .grid(row=4, column=0, sticky=tk.E, columnspan=4)
        data_path_variable = tk.StringVar()
        tk.Entry(server_frame, width=40, textvariable=data_path_variable) \
            .grid(row=4, column=4, sticky=tk.W, columnspan=4)
        data_path_variable.set(config.data_path if config.data_path else "")

        server_frame.grid(sticky=tk.W)
        return {Config.ENDPOINT: endpoint_variable, Config.API_KEY: api_key_variable,
                Config.USER_NAME: user_name_variable, Config.PASSWORD: password_variable,
                Config.DATA_PATH: data_path_variable}

    @staticmethod
    def verify_spaces(server: Common):
        list_spaces = server.get_list_spaces()
        server.config.spaces = Common.convert_spaces(list_spaces=list_spaces)
        if not server.config.spaces:
            messagebox.showerror(
                "No Spaces!", f"No spaces can be found on {'source' if server.config.is_source_server else 'target'} "
                              f"server {server.config.endpoint}. Please check your permission and/or credential")
            return False
        return True

    def process_config(self):
        if self.source_variables:
            source_config_dict = {}
            for key, variable in self.source_variables.items():
                source_config_dict[key] = variable.get()
            self.source.config.__dict__.update(source_config_dict)
            self.source.config.local_data = True if self.local_data.get() == "1" else False
            if not ServersWidgets.verify_spaces(server=self.source):
                return False
            self.source.config.save_config()
        target_config_dict = {}
        for key, variable in self.target_variables.items():
            target_config_dict[key] = variable.get()
        self.server.config.__dict__.update(target_config_dict)
        if not ServersWidgets.verify_spaces(server=self.server):
            return False
        self.server.config.save_config()
        return True


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


class OptionsWidgets(tk.Frame):
    def __init__(self, parent, server: Common, source: Common):
        super().__init__(parent)
        self.server = server
        self.source = source
        self.types_var_dict = {}
        self.update_step()

    def update_step(self):
        tk.Label(self, text=f"{self.server.config.action} ({Actions.ACTIONS_DICT.get(self.server.config.action)})",
                 bd=2, relief="groove").grid(sticky=tk.W)
        self.set_types_frame()

    def select_all_types(self):
        for item_type in inside_space_clone_types:
            self.types_var_dict.get(item_type).set("1")

    def deselect_all_types(self):
        for item_type in inside_space_clone_types:
            self.types_var_dict.get(item_type).set("0")

    def set_types_frame(self):
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
                .grid(row=int(1 + index / 5), column=index % 5, sticky=tk.W)
            if item_type in self.server.config.types:
                self.types_var_dict.get(item_type).set("1")
            else:
                self.types_var_dict.get(item_type).set("0")
        types_frame.grid(sticky=tk.W)

    def process_config(self):
        self.server.config.types = []
        for item_type in inside_space_clone_types:
            if self.types_var_dict.get(item_type).get() == "1":
                self.server.config.types.append(item_type)
        self.server.config.save_config()
        return True


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

    def submit(self):
        if self.server.config.action == Actions.ACTION_CLONE_SPACE:
            msg = f"Are you sure you want to clone types {self.server.config.types} from " \
                  f"{self.source.config.space_id} '{self.source.config.spaces.get(self.source.config.space_id)}' on " \
                  f"server {self.source.config.endpoint} to {self.server.config.space_id} " \
                  f"'{self.server.config.spaces.get(self.server.config.space_id)}' on server " \
                  f"{self.server.config.endpoint}? The existing entities with the same name will " \
                  f"{' ' if self.server.config.overwrite else 'NOT '}be overwritten."
            if messagebox.askyesno(title=f"{self.server.config.action}", message=msg):
                Migration(src_config=self.source.config, dst_config=self.server.config).clone_space_types()


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
        self.current_step_widgets.submit()


class MainGUI:
    SOURCE_SERVER_JSON = "source_server.json"

    def __init__(self, width: int = 800, height: int = 600):
        self.width = width
        self.height = height
        self.config = Config()
        self.server = Common(config=self.config)
        self.source_config = Config(configuration_file_name=MainGUI.SOURCE_SERVER_JSON, is_source_server=True)
        self.source = Common(config=self.source_config)

    def set_gui(self):
        window = tk.Tk()
        window.title('Octopus python client')
        window.option_add("*font", "calibri 14")
        window["bg"] = "black"

        # window.geometry('800x600')

        wiz = Wizard(window, server=self.server, source=self.source)
        wiz.pack()

        window.mainloop()


if __name__ == "__main__":
    MainGUI().set_gui()
