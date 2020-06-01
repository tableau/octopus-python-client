import copy
import logging
import os
from pathlib import Path

from octopus_python_client.actions import Actions
from octopus_python_client.utilities.helper import load_file, save_file

logging.basicConfig(filename=os.path.join(os.getcwd(), "octopus_python_client.log"),
                    filemode="a",
                    format="%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s",
                    datefmt="%H:%M:%S",
                    level=logging.INFO)


class BaseConfig:
    API_KEY = "api_key"
    ENDPOINT = "endpoint"
    PASSWORD = "password"
    USER_NAME = "user_name"
    DATA_PATH = "data_path"

    def __init__(self, is_source_server: bool = False):
        self.api_key = ""
        self.endpoint = ""
        self.is_source_server = is_source_server
        self.item_id = ""
        self.item_name = ""
        self.password = ""
        self.pem = False
        self.space_id = ""
        self.user_name = ""
        self.data_path = os.getcwd()
        self._base_config_dict = copy.deepcopy(self.__dict__)


class Config(BaseConfig):
    _BASE_CONFIG_DICT_KEY = "_base_config_dict"
    CONFIG_FILE_KEY = "config_file"
    CONFIGURATIONS_FOLDER = "configurations"
    DEFAULT_CONFIGURATION_FILE_NAME = "configuration.json"
    USE_CURRENT_DATA_PATH = "current"
    LOCAL_DATA_KEY = "local_data"
    LOGGER = logging.getLogger("Config")
    SOURCE_SERVER_JSON = "source_server.json"

    def __init__(self, configuration_file_name: str = None, is_source_server: bool = False):
        super().__init__(is_source_server=is_source_server)
        self.action = Actions.ACTION_GET_SPACES
        self.channel_id = ""
        self.local_data = False
        self.no_stdout = False
        self.overwrite = False
        self.package = False
        self.project_id = ""
        self.release_version = ""
        self.prev_releases = []
        self.release_notes = ""
        self.type = ""
        self.types = []

        configuration_file_name = configuration_file_name if configuration_file_name else \
            (Config.SOURCE_SERVER_JSON if is_source_server else Config.DEFAULT_CONFIGURATION_FILE_NAME)
        code_path = os.path.dirname(os.path.abspath(__file__))
        self.config_file = os.path.join(code_path, Config.CONFIGURATIONS_FOLDER, configuration_file_name)
        self.load_config()

    def load_config(self):
        if Path(self.config_file).is_file():
            Config.LOGGER.info(f"loading configuration from {self.config_file}...")
            config_dict = load_file(self.config_file)
            data_path = self.data_path
            self.__dict__.update(config_dict)
            if not self.data_path:
                self.data_path = data_path
        else:
            Config.LOGGER.info(f"configuration file {self.config_file} does not exist.")

    def save_config(self):
        if self.is_source_server:
            self._base_config_dict.update(
                (k, self.__dict__[k]) for k in self._base_config_dict.keys() & self.__dict__.keys())
            self._base_config_dict[Config.LOCAL_DATA_KEY] = self.local_data
            save_file(file_path_name=self.config_file, content=self._base_config_dict)
        else:
            config_dict = copy.deepcopy(self.__dict__)
            config_dict.pop(Config.CONFIG_FILE_KEY, None)
            config_dict.pop(Config._BASE_CONFIG_DICT_KEY, None)
            save_file(file_path_name=self.config_file, content=config_dict)


if __name__ == "__main__":
    print(Config.LOGGER.name)
    source_config = Config(configuration_file_name="source_server.json", is_source_server=True)
    print(source_config.__dict__)
    source_config.save_config()
    main_config = Config()
    main_config.save_config()
