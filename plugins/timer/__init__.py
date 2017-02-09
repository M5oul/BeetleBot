import time
from plugin import Plugin

class Timer(Plugin):
    def __init__(self, core):
        super().__init__(core)
        self.register_command('timer', self.timer)

    def timer(self, delay, *reason):
        """ Usage: !timer delay(in minutes) reason """
        reason = " ".join(reason)
        def callback():
            self.send_message_to_room(reason)
        self.core.schedule(reason, float(delay) * 60, callback)
