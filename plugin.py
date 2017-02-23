class PluginMetaclass(type):
    def __new__(cls, name, bases, namespace):
        for k, v in namespace.items():
            if callable(v):
                v.__plugin__ = name
        return type.__new__(cls, name, bases, namespace)

class Plugin(metaclass=PluginMetaclass):
    def __init__(self, core):
        self.commands = {}
        self.private_commands = {}
        self.core = core

    def register_command(self, name, command):
        self.commands[name] = command

    def register_private_command(self, name, command):
        self.private_commands[name] = command

    def send_message_to_room(self, message):
        self.core.send_message_to_room(self.core.room, message)

    def send_message_to_jid(self, jid, message):
        self.core.send_message_to_jid(jid, message)

    def on_deletion(self):
        pass

