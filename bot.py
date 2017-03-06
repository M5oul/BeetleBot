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
from plugin import Plugin, PluginMetaclass
from xmpp import Resource


logging.basicConfig(level=logging.WARNING, format='%(levelname)-8s %(message)s')
__version__ = "0.3.1"

PLUGINS_LOADED = []


class PluginNotLoaded(Exception):
    pass


class Toto(Resource, metaclass=PluginMetaclass):
    def __init__(self, room, nick):
        Resource.__init__(self, "", "", room, nick)

        self.register_plugin('xep_0071')
        self.register_plugin('xep_0308')

        # {room_names: [message, message]}
        self.messages_to_send_on_join = {}
        self.jids = {}
        self.plugins = {}

        #print("Connecting to %s" % (cnf['main']['jid']))

        self.add_event_handler("groupchat_message", self.on_groupchat_message)
        self.add_event_handler("message", self.on_message)

        self.commands = {'help': self.cmd_help,
                         'load': self.load_plugin,
                         'unload': self.unload_plugin,
                         'reload': self.reload_plugin,
                         }
        self.private_commands = {'help': self.cmd_help_private,
                                }

    def gen_help(self, commands):
        message = ""
        current_plugin = None

        for _, command in sorted(commands.items(), key=lambda x: x[1].__plugin__):
            if current_plugin != command.__plugin__:
                message += "\n"
                message += "<span style='color: orange'> [" + command.__plugin__ + "]</span>\n"
                current_plugin = command.__plugin__

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
            print(self.load_plugin(plugin))

    def reload_plugin(self, name):
        """ Usage: !reload plugin_name """
        try:
            self.unload_plugin(name, _raise=True)
        except PluginNotLoaded:
            pass
        self.load_plugin(name)
        return 'Reloaded ' + name

    def load_plugin(self, name):
        """ Usage: !load plugin_name """
        importlib.invalidate_caches()
        try:
            module = importlib.import_module('plugins.' + name)
        except ModuleNotFoundError:
            return "Can't find module " + name

        attrs = [getattr(module, name) for name in dir(module)]
        plugins = [attr for attr in attrs if inspect.isclass(attr) and Plugin in attr.__bases__]
        if not plugins:
            return "Failed to load " + name

        if name in PLUGINS_LOADED and plugins[0]._load_once:
            return "Can't load twice"

        PLUGINS_LOADED.append(name)

        plugin = plugins[0](self)
        self.plugins[name] = plugin
        self.commands.update(plugin.commands)
        self.private_commands.update(plugin.private_commands)
        return 'Loaded ' + name

    def unload_plugin(self, name, _raise=False):
        """ Usage: !unload plugin_name """
        if name not in self.plugins:
            if _raise:
                raise PluginNotLoaded
            else:
                return name + " is not loaded"

        for command in self.plugins[name].commands:
            del self.commands[command]
        for command in self.plugins[name].private_commands:
            del self.private_commands[command]
        self.plugins[name].on_deletion()
        del self.plugins[name]
        to_del = set()
        for mod in sys.modules:
            if mod.startswith('plugins.' + name):
                to_del.add(mod)

        for mod in to_del:
            del sys.modules[mod]
        PLUGINS_LOADED.remove(name)
        return 'Unloaded ' + name

    def on_session_start(self, event):
        super().on_session_start(event)
        self.load_all_plugins()

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
        super().on_groupchat_presence(presence)

        for plugin in self.plugins.values():
            try:
                self.send_message_to_room(self.room, plugin.on_groupchat_presence(presence))
            except Exception as e:
                pass

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
        to_send = self.execute_command(jid, self.commands, message['body'])

        if to_send:
            self.send_message_to_room(self.room, to_send)

        for plugin in self.plugins.values():
            try:
                plugin.on_received_groupchat_message(jid, message)
            except AttributeError:
                pass


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    bot = Toto("discussion@muc.bananium.fr", "toto")
    bot.start()
    loop.run_forever()

