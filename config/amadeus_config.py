import os, configparser
from models.singleton import SingletonMeta
from twitchAPI.type import AuthScope


USER_CONFIG_DIR = os.path.normpath(os.path.expanduser("~") + "/.amadeus_config/")
MAIN_CONFIG_PATH = os.path.join(USER_CONFIG_DIR, "config.ini")


class Amadeus_Config(metaclass=SingletonMeta):
    def __init__(self) -> None:
        self.config_parser = configparser.ConfigParser()

        if not os.path.exists(USER_CONFIG_DIR):
            os.makedirs(USER_CONFIG_DIR)

        if not os.path.exists(MAIN_CONFIG_PATH):
            self.config_parser['OBS'] = {
                'obs_host': '',
                'obs_port': '',
                'obs_password': '',
            }
            self.config_parser['TWITCH'] = {
                'client_id': '',
                'client_secret': '',
                'target_channel': '',
                'twitch_bot_username': '',
                'scopes': 'chat:read,chat:edit,channel:read:redemptions,channel:manage:redemptions,moderator:read:followers,channel:read:subscriptions,channel:moderate,moderator:manage:shoutouts'
            }
            with open(MAIN_CONFIG_PATH, 'w') as configfile:
                self.config_parser.write(configfile)
        
        with open(MAIN_CONFIG_PATH, 'r') as configfile:
            self.config_parser.read_file(configfile)
            self.obs_host = self.config_parser.get('OBS', 'obs_host')
            self.obs_port = int(self.config_parser.get('OBS', 'obs_port'))
            self.obs_password = self.config_parser.get('OBS', 'obs_password')
            self.twitch_bot_username = self.config_parser.get('TWITCH', 'twitch_bot_username')
            self.target_channel = self.config_parser.get('TWITCH', 'target_channel')
            self.client_id = self.config_parser.get('TWITCH', 'client_id')
            self.client_secret = self.config_parser.get('TWITCH', 'client_secret')
            self.scopes = [AuthScope(scope) for scope in self.config_parser.get('TWITCH', 'scopes').split(',')]
            

    def __repr__(self) -> str:
        return f"Amadeus_Config(obs_host={self.obs_host}, obs_port={self.obs_port}, obs_password={self.obs_password})"