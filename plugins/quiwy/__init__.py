from xml.sax.saxutils import escape
from plugin import Plugin

class Quiwy(Plugin):
    def __init__(self, core):
        super().__init__(core)
        self.user_list = []

    def on_groupchat_presence(self, presence):
        nick = presence['from'].resource
        jid = presence['muc']['jid']
        if presence['type'] == 'unavailable':
            users.remove(jid)
            return

        if presence['type'] == 'available':
            if jid not in user_list:
                user_list.append(jid)
                if jid.bare == 'quiwy@jappix.com':
                    return escape("Quiwy tu sens pas bon <3")


