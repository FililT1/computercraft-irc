#! /usr/bin/env python3

import irc.bot
import irc.client
import sys
import threading
import collections
import itertools

class Messages:
    """This stores numbered chat messages, and only a limited amount. When it
    exceeds the maximum, old messages are removed. When a message is removed, the
    newer messages keep their indexes."""
    def __init__(self, maxlen=500):
        self.msgs = collections.deque(maxlen=maxlen)
        self.indexoffset = 0
        self.lock = threading.RLock()

    def append(self, nick, text):
        with self.lock:
            idx = len(self.msgs) + self.indexoffset
            if len(self.msgs) == self.msgs.maxlen:
                self.indexoffset += 1
            self.msgs.append((idx, nick, text))

    def get(self, start, end):
        """Get the range of messages from the inclusive start index to the
        exclusive end index. Any integers will be accepted for start and end,
        so it acts identically to a slice. None is also accepted."""
        with self.lock:
            minindex = self.indexoffset
            if start is not None and start < minindex:
                start = minindex
            if end is not None and end < minindex:
                end = minindex

            if len(self.msgs) == self.msgs.maxlen:
                if start is not None:
                    start -= self.indexoffset
                if end is not None:
                    end -= self.indexoffset
            sliced = collections.deque(itertools.islice(self.msgs, start, end))
            return sliced

class IRCAgent(irc.bot.SingleServerIRCBot):
    def __init__(self, server, port, channel, nickname):
        super().__init__([(server, port)], nickname, nickname)
        self.target = channel
        self.nickname = nickname
        self.messages = Messages(500)

    def getMessages(self, start=None, end=None):
        """Get a range of messages, by default selecting everything."""
        return self.messages.get(start, end)
        
    def sendMessage(self, text):
        """Send the text to the channel"""
        if self.connection.is_connected():
            self.connection.privmsg(self.target, text)
            self.messages.append(self.nickname, text)
            return True
        else:
            return False

    def getUsers(self):
        channel = self.channels.get(self.target)
        return channel.users() if channel else {}

    def getOps(self):
        channel = self.channels.get(self.target)
        return channel.opers() if channel else {}

    def getHalfOps(self):
        channel = self.channels.get(self.target)
        return channel.halfops() if channel else {}

    def getVoiced(self):
        channel = self.channels.get(self.target)
        return channel.voiced() if channel else {}

    def on_welcome(self, connection, event):
        if irc.client.is_channel(self.target):
            connection.join(self.target)

    def on_join(self, connection, event):
        pass

    def on_disconnect(self, connection, event):
        sys.exit(0)

    def on_privmsg(self, connection, event):
        """Treat private messages like public but append pm to the sender nick"""
        msgsource = event.source
        nick = "pm: " + msgsource.split('!')[0]
        body = event.arguments[0]
        self.messages.append(nick, body)

    def on_pubmsg(self, connection, event):
        msgsource = event.source
        nick = msgsource.split('!')[0]
        body = event.arguments[0]
        self.messages.append(nick, body)
