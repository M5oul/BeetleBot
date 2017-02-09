import asyncio
import json
import logging
import re
import shlex
import slixmpp
import sys
import xml.sax.saxutils
import os
import importlib
import inspect
from plugin import Plugin


logging.basicConfig(level=logging.WARNING, format='%(levelname)-8s %(message)s')

__version__ = "0.3.1"


class Toto(slixmpp.ClientXMPP):
    def __init__(self, room, nick):
        slixmpp.ClientXMPP.__init__(self, "", "")

        self.register_plugin('xep_0045')
        self.register_plugin('xep_0308')
        self.room = room
        self.nick = nick
        self.joined = False

        # {room_names: [message, message]}
        self.messages_to_send_on_join = {}
        self.affiliations = {}
        self.jids = {}

        #print("Connecting to %s" % (cnf['main']['jid']))

        self.add_event_handler("session_start", self.on_session_start)
        self.add_event_handler("groupchat_presence", self.on_groupchat_presence)
        self.add_event_handler("groupchat_message", self.on_groupchat_message)
        self.add_event_handler("message", self.on_message)

        self.plugins = {}
        self.commands = {'help': self.cmd_help,
                         'load': self.load_plugin,
                         'unload': self.unload_plugin,
                         'reload': self.reload_plugin,
                         }
        self.private_commands = {'help': self.cmd_help_private,
                                }
        self.load_all_plugins()

    def gen_help(self, commands):
        message = ""
        for _, command in sorted(commands.items()):
            if command.__doc__:
                message += command.__doc__ + "\n"

        return message

    def cmd_help(self):
        """ Usage: !help """
        return self.gen_help(self.commands)

    def cmd_help_private(self, jid):
        """ Usage: !help """
        commands = self.commands.copy()
        commands.update(self.private_commands)
        return self.gen_help(commands)

    def load_all_plugins(self):
        for plugin in os.listdir('plugins'):
            try:
                print(self.load_plugin(plugin))
            except:
                self.send_message_to_room(self.room, "Can't load %s" % plugin)

    def reload_plugin(self, name):
        """ Usage: !reload plugin_name """
        self.unload_plugin(name)
        self.load_plugin(name)
        return 'Reloaded ' + name

    def load_plugin(self, name):
        """ Usage: !load plugin_name """
        importlib.invalidate_caches()
        module = importlib.import_module('plugins.' + name)
        attrs = [getattr(module, name) for name in dir(module)]
        plugins = [attr for attr in attrs if inspect.isclass(attr) and Plugin in attr.__bases__]
        if not plugins:
            return "Failed to load " + name
        plugin = plugins[0](self)
        self.plugins[name] = plugin
        self.commands.update(plugin.commands)
        self.private_commands.update(plugin.private_commands)
        return 'Loaded ' + name

    def unload_plugin(self, name):
        """ Usage: !unload plugin_name """
        for command in self.plugins[name].commands:
            del self.commands[command]
        for command in self.plugins[name].private_commands:
            del self.private_commands[command]
        del self.plugins[name]
        to_del = set()
        for mod in sys.modules:
            if mod.startswith('plugins.' + name):
                to_del.add(mod)
        for mod in to_del:
            del sys.modules[mod]
        return 'Unloaded ', name

    def join_room(self):
        self.plugin['xep_0045'].joinMUC(self.room, self.nick)

    def start(self):
        self.connect((self.boundjid.host, 5222))

    def exit(self, sig, frame):
        self.disconnect()

    def send_message_to_jid(self, jid, message):
        message = message.strip()
        stanza = self.make_message(jid)
        stanza['type'] = 'chat'
        stanza['body'] = message
        stanza.send()

    def send_message_to_room(self, room, message):
        message = message.strip()
        if message == "":
            return
        if not self.joined:
            self.join_room()
        else:
            stanza = self.make_message(room)
            stanza['type'] = 'groupchat'
            stanza['body'] = xml.sax.saxutils.escape(message)
            stanza.enable('html')
            stanza['html']['body'] = htmlize(message)
            stanza.send()

    def on_session_start(self, event):
        print("Session started: %s" % event)
        print("The full JID is %s" % self.boundjid.full)
        self.join_room()

    def on_message(self, message):
        if message['type'] != 'chat':
            return
        if message['from'].bare == self.room:
            nick = message['from'].resource
            jid = self.jids.get(nick, None)
        else:
            jid = message['from'].bare
        if not jid:
            self.send_message_to_jid(message['from'], "I can't see your real JID")
            return

        for plugin in self.plugins.values():
            try:
                plugin.on_received_message(jid, message)
            except Exception as e:
                pass
        to_send = self.execute_command(jid, self.private_commands, message['body'], pass_jid=True)
        if not to_send:
            to_send = self.execute_command(jid, self.commands, message['body'])

        if to_send:
            self.send_message_to_jid(message['from'], to_send)

    def on_groupchat_presence(self, presence):
        room = presence['from'].bare
        affiliation = presence['muc']['affiliation']
        nick = presence['from'].resource
        jid = presence['muc']['jid']

        for plugin in self.plugins.values():
            try:
                self.send_message_to_room(self.room, plugin.on_groupchat_presence(presence))
            except Exception as e:
                pass

        if affiliation:
            if room not in self.affiliations:
                self.affiliations[room] = {}
            self.affiliations[room][nick] = affiliation
        if jid:
            self.jids[nick] = jid
        if nick == self.nick:
            if presence['type'] == 'unavailable':
                self.on_groupchat_leave(room)
            if presence['type'] == 'available':
                print('Room %s joined.' % room)
                self.joined = True

    def get_affilation(self, room, nick):
        return self.affiliations.get(room, {}).get(nick, None)

    def execute_command(self, jid, commands, message_body, pass_jid=False):
        to_send = ""
        for name, command in commands.items():
            if re.match(r"^!\b{}\b".format(name), message_body):
                # len("!name ") == len(name) + 2
                args = shlex.split(message_body[len(name) + 2:])
                if pass_jid:
                    to_send = command(*args, jid=jid)
                else:
                    to_send = command(*args)
                break

        return to_send

    def on_groupchat_message(self, message):
        nick = message['from'].resource
        if nick == self.nick:
            return
        if message['replace']['id']:  # Correction ?
            return
        jid = self.jids.get(nick, None)
        if not jid:
            to_send = "No, i cannot see your real JID"
        else:
            to_send = self.execute_command(jid, self.commands, message['body'])

        if to_send:
            self.send_message_to_room(self.room, to_send)

    def on_groupchat_leave(self, room):
        """
        Just keep track of the fact that we are not in the room anymore, so
        that we know that we need to rejoin it if we want to send a message
        in it, later.
        """
        print("Left room %s" % room)
        self.joined = False


def htmlize(text):
    text = text.replace('\n', '<br/>')
    return "<body xmlns='http://www.w3.org/1999/xhtml'><p>%s</p></body>" % text

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    bot = Toto("", "")
    bot.start()
    loop.run_forever()

