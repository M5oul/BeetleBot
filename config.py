from configparser import ConfigParser
from pathlib import Path
import os


class Config:
    """ config/bot.ini contains connexion infos
        config/global/{plugin}.ini contains global plugin configuration
        config/{room}/{plugin}.ini contains specific room settings for a plugin
    """
    def __init__(self):
        os.makedirs("config/global", exist_ok=True)
        self.bot_config = ConfigParser()
        self.bot_config["auth"] = {}
        self.bot_config["auth"]["jid"] = ""
        self.bot_config["auth"]["password"] = ""
        # room: jid
        self.bot_config["rooms"] = {}
        self.bot_config.read('config/bot.ini')

        self.write_config(self.bot_config, 'config/bot.ini')

    def write_config(self, config, filename):
        with open(filename, "w") as fd:
            config.write(fd)

    def get(self, room, plugin):
        global_config = ConfigParser()
        local_config = ConfigParser()
        os.makedirs(os.path.join("config", room), exist_ok=True)
        Path(os.path.join("config", room, plugin + ".ini")).touch(exist_ok=True)
        Path(os.path.join("config/global", plugin + ".ini")).touch(exist_ok=True)
        global_config.read(os.path.join("config/global", plugin + ".ini"))
        local_config.read(os.path.join("config/", room, plugin + ".ini"))
        return global_config, local_config
