
import os, configparser
from models.signal_manager import register_signal
from config.amadeus_config import USER_CONFIG_DIR


class AmadeusPlugin:
    

    plugin_name: str
    config_parser: configparser.ConfigParser
    plugin_config_path: str


    def __init__(self) -> None:
        self.set_config_parser()
        for name in dir(self):
            if name.startswith('_'):
                continue
            attr = getattr(self, name)
            if callable(attr) and hasattr(attr, '_signal_name'):
                register_signal(attr._signal_name, self, attr)


    def set_config_parser(self):
        self.config_parser = configparser.ConfigParser()
        self.plugin_config_path = os.path.join(USER_CONFIG_DIR, f"{self.plugin_name}_config.ini")
        self.config_parser.add_section(self.plugin_name)
        self.config_parser.set(self.plugin_name, 'active', 'False')


    def write_config(self, overwrite=False):
        if overwrite or not os.path.exists(self.plugin_config_path):
            with open(self.plugin_config_path, 'w') as configfile:
                self.config_parser.write(configfile)


    def read_config(self):
        if os.path.exists(self.plugin_config_path):
            with open(self.plugin_config_path, 'r') as configfile:
                self.config_parser.read_file(configfile)
        self.active = self.config_parser.getboolean(self.plugin_name, 'active', fallback=False)


    async def on_load(self):
        pass


    async def on_started(self):
        pass


    async def on_chat_message(self, message):
        pass


    def set_active(self, active: bool):
        self.active = active
        self.config_parser.set(self.plugin_name, 'active', str(active))