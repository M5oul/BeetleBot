from github import Github as GithubAPI
from xml.sax.saxutils import escape
from plugin import Plugin
import configparser
import datetime
import json
import requests

class Github(Plugin):
    _load_once = True

    def __init__(self, core):
        super().__init__(core)
        # In case it was reloaded
        self.core.cancel_schedule('Get github notifs')

        self.register_private_command("register", self.register)
        self.keys = configparser.ConfigParser()
        self.keys['keys'] = {}
        # Read config file to get users / keys
        self.keys.read('github.ini')

        # { jid: datetime }
        self.last_update = {}
        self.githubs = {}

        for jid, key in self.keys['keys'].items():
            self.githubs[jid] = GithubAPI(key)
            self.last_update[jid] = None

        # Start timed event to get notification
        self.core.schedule('Get github notifs', 60, self.get_notifs, repeat=True)

    def write_config(self):
        with open('github.ini', 'w') as configfile:
            self.keys.write(configfile)

    def register(self, key, jid):
        """ Usage: !register api_key """
        self.last_update[str(jid.bare)] = None
        self.keys['keys'][str(jid.bare)] = key
        self.githubs[str(jid.bare)] = GithubAPI(key)
        self.write_config()

    def unregister(self, jid):
        del self.last_update[str(jid.bare)]
        del self.keys['keys'][str(jid.bare)]
        del self.githubs[str(jid.bare)]
        self.write_config()

    def get_notifs(self):
        for jid, gh in self.githubs.items():
            for notif in gh.get_user().get_notifications():
                if self.last_update[jid] is None or notif.updated_at > self.last_update[jid]:
                    headers = {"Authorization": "token {}".format(self.keys['keys'][jid])}
                    try:
                        url = requests.get(notif.subject.latest_comment_url, headers=headers).json()['html_url']
                    except:
                        url = "Can't find the URL because reasons..."
                    message = "New notification for {}: {}\n <a href='{url}'>{url}</a>".format(escape(notif.repository.name), escape(notif.subject.title), url=escape(url))
                    self.send_message_to_jid(jid, message)
            self.last_update[jid] = datetime.datetime.utcnow()

