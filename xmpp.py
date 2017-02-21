import slixmpp
import xml.sax.saxutils


# Provides some helpers to use XMPP
# Joins a room
class Resource(slixmpp.ClientXMPP):
    def __init__(self, user, passwd, room, nick):
        slixmpp.ClientXMPP.__init__(self, user, passwd)
        self.room = room
        self.nick = nick
        self.jids = {}
        self.register_plugin('xep_0045')

        self.add_event_handler("session_start", self.on_session_start)
        self.add_event_handler("groupchat_presence", self.on_groupchat_presence)

    def join_room(self):
        self.plugin['xep_0045'].join_muc(self.room, self.nick)

    def start(self):
        self.connect((self.boundjid.host, 5222))

    def exit(self, sig, frame):
        self.disconnect()

    def send_messages(self, _type, jid, messages):
        if isinstance(messages, str):
            self.send_message(_type, jid, messages)
            return

        for message in messages:
            if message:
                self.send_message(_type, jid, message)

    def send_message(self, _type, jid, message):
        message = message.strip()
        if message == "":
            return
        stanza = self.make_message(jid)
        stanza['type'] = _type
        stanza['body'] = xml.sax.saxutils.escape(message)
        stanza.enable('html')
        stanza['html']['body'] = htmlize(message)
        stanza.send()

    def send_message_to_jid(self, jid, message):
        self.send_messages("chat", jid, message)

    def send_message_to_room(self, room, message):
        self.send_messages("groupchat", room, message)

    def on_session_start(self, event):
        print("Session started: %s" % event)
        print("The full JID is %s" % self.boundjid.full)
        self.join_room()

    def on_groupchat_presence(self, presence):
        room = presence['from'].bare
        nick = presence['from'].resource
        jid = presence['muc']['jid']

        if jid:
            self.jids[nick] = jid
        if nick == self.nick:
            if presence['type'] == 'unavailable':
                self.on_groupchat_leave(room)
            if presence['type'] == 'available':
                print('Room %s joined.' % room)


def htmlize(text):
    text = text.replace('\n', '<br/>')
    return "<body xmlns='http://www.w3.org/1999/xhtml'><p>%s</p></body>" % text

