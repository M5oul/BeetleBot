import random
from plugin import Plugin

class Random(Plugin):
    def __init__(self, core):
        super().__init__(core)
        self.register_command("choice", self.chose)

    def chose(self, *args):
        """ Usage: !choice choice1 choice2 """
        if not args:
            message = "?"
        else:
            message = random.choice(args)
        self.send_message_to_room(message)

