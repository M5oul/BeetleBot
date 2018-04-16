# Toto

## Basic configuration

Create a `config` directory and ad a `bot.ini` file with the following config:

```ini
[auth]
jid = bot@foo.bar
password = Mypwd

[rooms]
discussion@muc.foo.bar = toto
jokes@muc.foo.bar = toto
```

## Plugins

Right now the bot will load every plugin it finds in the plugins directory.
Each plugin can either have a global configuration or a configuration by room.

Global configurations should go in a `config/global/plugin_name.ini` file.
Per room configurations should go in a `config/room_jid/plugin_name.ini` file.

