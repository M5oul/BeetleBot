class Plugin:
    def __init__(self, core):
        self.commands = {}
        self.core = core

    def register_command(self, name, command):
        self.commands[name] = command

    def send_message_to_room(self, message):
        self.core.send_message_to_room(self.core.room, message)

    def send_message_to_jid(self, jid, message):
        self.core.send_message_to_jid(jid, message)

