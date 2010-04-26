# Copyright 2008 Lee Harr
#
# This file is part of TZMud.
#
# TZMud is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# TZMud is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with TZMud.  If not, see <http://www.gnu.org/licenses/>.


'''The Twisted protocol.'''

from textwrap import TextWrapper
wrapper = TextWrapper()
wrapper.replace_whitespace = False
wrapper.subsequent_indent = '    '
wrap = wrapper.wrap

import re
class Wrapper(TextWrapper):
    def _wrap_chunks(self, chunks):
        lines = []
        if self.width <= 0:
            raise ValueError("invalid width %r (must be > 0)" % self.width)
        chunks.reverse()
        while chunks:
            cur_line = []
            cur_len = 0
            if lines:
                indent = self.subsequent_indent
            else:
                indent = self.initial_indent
            width = self.width - len(indent)
            if chunks[-1].strip() == '' and lines:
                del chunks[-1]
            while chunks:
                chunk = chunks[-1]
                l = self.ansilen(chunk)
                if cur_len + l <= width:
                    cur_line.append(chunks.pop())
                    cur_len += l
                else:
                    break
            if chunks and self.ansilen(chunks[-1]) > width:
                self._handle_long_word(chunks, cur_line, cur_len, width)
            if cur_line and cur_line[-1].strip() == '':
                del cur_line[-1]
            if cur_line:
                lines.append(indent + ''.join(cur_line))
        return lines

    def ansilen(self, chunk):
        if not '\x1b' in chunk:
            return len(chunk)
        else:
            return len(re.sub('\x1b.*?m', '', chunk))

ansiwrapper = Wrapper()
ansiwrapper.replace_whitespace = False
ansiwrapper.subsequent_indent = '    '
ansiwrap = ansiwrapper.wrap


import hashlib
import time

from twisted.protocols import basic
from twisted.internet import reactor

import conf

from db import TZODB, TZIndex
commit = TZODB().commit
abort = TZODB().abort

tzindex = TZIndex()

import colors

import actions
import wizard
import admin

import players
import rooms

import parse




class TZ(basic.LineReceiver):
    'Twisted protocol. One is created for each client connection.'

    delimiter = '\n'

    def __init__(self):
        zodb = TZODB()
        self.dbroot = zodb.root
        self.login_failures = 0

    def connectionMade(self):
        'A new connection. Send out the MOTD.'

        print "Got new client!"
        self.logged_in = False
        self.room = None
        self.factory.clients.append(self)

        self.motd()

    def motd(self):
        'Message of the day.'

        lines = open('MOTD').readlines()

        for line in lines:
            self.simessage(line.rstrip())

    def login(self, r):
        'Log a player in if possible.'

        try:
            player_name, pwtext = r.split()
        except ValueError:
            self.simessage('Must log in with "login <name> <password>"')
        else:
            player = players.getname(player_name)
            if player is None:
                self.simessage('Incorrect user name or password.')
                self.login_failures += 1
                print 'player', player_name, 'does not exist'
            elif player.logged_in:
                if player.check_password(pwtext):
                    self.simessage('Player already logged in.')
                    self.simessage('Use "purge <name> <password>" to disconnect other session.')
                    print 'player', player.name, 'already logged in'
            else:
                if player.check_password(pwtext):
                #if True:
                    self.logged_in = True
                    player.logged_in = True
                    self.player = player
                    player.last = time.time()
                    player.following = None
                    self.factory._player_protocols[player_name] = self

                    wizard.cmd_teleport(self, {})
                    reactor.callLater(0.6, actions.cmd_look, self,
                                        dict(verb='look'))
                    print 'player', player.name, 'logged in'
                else:
                    self.simessage('Incorrect user name or password.')
                    print 'player', player.name, 'wrong password'
                    self.login_failures += 1

            if self.login_failures >= 3:
                self.transport.loseConnection()

    def create(self, r):
        'Create a new account.'

        try:
            player_name, pwtext = r.split()
        except ValueError:
            self.simessage('Create account with "create <name> <password>"')
        else:
            existing = players.getname(player_name)
            if existing:
                self.simessage('Name already in use.')
            elif player_name=='quit':
                self.simessage('Cannot use the name "quit"')
            else:
                player = players.Player(player_name)
                player.set_password(pwtext)
                if len(players.ls()) == 1:
                    admin.add(player)

                self.simessage('Account created.')
                self.simessage('Log in with "login <name> <password>"')

    def purge(self, r):
        'Disconnect other session with this account logged in.'

        try:
            player_name, pwtext = r.split()
        except ValueError:
            self.simessage('Incorrect user name or password.')
        else:
            player = players.getname(player_name)
            if player.check_password(pwtext):
                if player.logged_in:
                    self._purge(player)
                    self.simessage('Connection purged.')
                    self.simessage('Log in with "login <name> <password>"')
                else:
                    self.simessage('Player is not logged in.')
            else:
                self.simessage('Incorrect user name or password.')

    def connectionLost(self, reason):
        'Client has disconnected.'

        print "Lost a client!"
        self.factory.clients.remove(self)

        try:
            room = self.room
            room.action(dict(act='quit', actor=self.player))

            self.room.rmplayer(self.player)
            self.player._rid = None
            self.player.logged_in = False
        except:
            #print 'TZ.connectionLost ABORT'
            abort()
        else:
            #print 'TZ.connectionLost COMMIT'
            commit()

        if hasattr(self, 'player'):
            del self.factory._player_protocols[self.player.name]

    def lineReceived(self, line):
        '''Called each time a new line of input is received from the client.

        Except for "login" and "create", if the player is logged in,
            the line is sent to the parser, then dispatched to the
            proper command section if possible.

        Each line received begins a new database transaction, and
            only if the entire command runs without errors will the
            transaction be committed. Any problems will result in a
            rollback so that the database will always be consistent.

        '''

        line = line.strip()
        #print "received", repr(line)
        if not line:
            return

        try:
            if not self.logged_in and line=='quit':
                self.transport.loseConnection()
            elif not self.logged_in and line.startswith('login '):
                self.login(line[6:])

            elif not self.logged_in and line.startswith('create '):
                self.create(line[7:])

            elif not self.logged_in and line.startswith('purge '):
                self.purge(line[6:])

            elif not self.logged_in:
                self.simessage('Must log in with "login <name> <password>"')

            else:
                t = time.time()
                self.player.active = t
                #print 'player active at ', time.ctime(t)

                # normal command dispatch
                section = actions

                cmd = '##nocmd'
                rest = ''
                if line[0] == '!':
                    if admin.verify(self.player):
                        section = admin
                        line = line[1:]
                    else:
                        self.message('Admin only.')
                        return

                else:
                    try:
                        result = parse.full_parser.parseString(line)
                    except parse.ParseException:
                        cmd = '##parseproblem'
                    else:
                        cmd = result.asDict().get('verb', '##noverb')
                        section = globals()[result['section']]

                        if section==wizard and not wizard.verify(self.player):
                            self.message('Wizards only.')
                            return

                        rest = result.asDict()
                        #print 'rest', rest

                if cmd == '##nocmd':
                    parts = line.split()
                    cmd = parts[0]
                    try:
                        rest = ' '.join(parts[1:])
                    except IndexError:
                        rest = None

                self.dispatch(section, cmd, rest)

        except Exception, e:
            abort()
            print 'lineReceived ABORTING TRANSACTION'
            if conf.debug:
                self.simessage('Debug')
                self.simlmessage(e)
                import traceback
                print traceback.format_exc()
            try:
                if self.logged_in:
                    if self.room.tzid != self.player._rid:
                        print 'WARNING: Room mismatch. Trying to correct.'
                        room = tzindex.get(self.player._rid)
                        if self.player not in room.players():
                            room.addplayer(self.player)
                        self.player._rid = room.tzid
                        self.room = room
            except:
                print 'Cannot recover from error.'
                raise

        else:
            #print 'lineReceived COMMIT'
            commit()


    def dispatch(self, section, cmd, rest):
        '''Call the appropriate function if possible.

        If the given section does not have the specified command, check
            if the current room has an exit with that name and try to
            go there.

        '''

        try:
            func_name = 'cmd_%s' % cmd
            func = getattr(section, func_name)

        except AttributeError:
            if section==actions:
                actions.cmd_go(self, dict(objname=cmd))
            else:
                self.message("What's that?")
            return

        try:
            if rest:
                func(self, rest)
            else:
                func(self)
        except Exception, e:
            import traceback
            traceback.print_exc()
            self.message('I am having trouble with that command.')
            if section==wizard:
                prefix = '@'
            elif section==admin:
                prefix = '!'
            else:
                prefix = ''
            self.message('Try "%shelp %s"' % (prefix, cmd))

            if conf.debug:
                self.simessage('Debug')
                self.simlmessage(e)

            #raise
            #self.dispatch(section, 'help', {'topic':cmd})

    def simessage(self, msg=''):
        'Send simple line to client. Used before player has logged in.'

        self.transport.write(msg + '\r\n')

    def message(self, *args, **kw):
        'Send line to client, possibly indented and colorized.'

        indent = kw.get('indent', 0)
        color = kw.get('color', True)

        strs = map(str, args)

        if strs and strs[-1] in ('.', '?', '!'):
            punctuation = strs.pop()
        else:
            punctuation = ''

        msg = ' '.join(strs)

        if punctuation:
            msg += punctuation

        cset = self.player.user_settings.get('ansi', False)
        if color and cset:
            msg = msg % colors.yes
            wrapped = ansiwrap(msg)
        else:
            msg = msg % colors.no
            wrapped = wrap(msg)

        if wrapped:
            for line in wrapped:
                self.transport.write(' '*indent + line + '\r\n')
        else:
            self.transport.write('\r\n')

    def mlmessage(self, lines, indent=0, color=True):
        'Send a multi-line message.'

        for line in lines:
            self.message(line, indent=indent, color=color)

    def simlmessage(self, lines):
        for line in lines:
            self.simessage(line)

    def broadcast(self, msg='', indent=0, color=True):
        'Send a message to all connected clients.'

        for client in self.factory.clients:
            if not client.logged_in:
                continue
            client.message(msg, indent=indent, color=color)

    def columns(self, items, color=None):
        'Send list of strings out as a multi-column list.'

        # determine the longest word in the given list
        maxlen = 0
        for i in items:
            l = len(i)
            if l > maxlen:
                maxlen = l

        width = maxlen + 2
        cols = (70 / width) - 1

        filled_items = [item.ljust(width, ' ') for item in items]
        if color is not None:
            filled_items = [color(item) for item in filled_items]
        from itertools import izip, chain, repeat
        for row in izip(*[chain(filled_items, repeat('', cols-1))]*cols):
            self.message('  '.join(row), indent=4)

    def columns_v(self, items, color=None):
        '''Send list of strings out as a multi-column list.

        The columns are printed vertically, such that an
            alphabetized list would be read top-to-bottom,
            then left to right.

        '''

        # determine the longest word in the given list
        maxlen = 0
        for i in items:
            l = len(i)
            if l > maxlen:
                maxlen = l

        li = len(items)
        width = maxlen + 2
        cols = (70 / width) - 1
        rows = li / cols
        if li % cols:
            rows += 1

        columns = []
        n = 0
        for i in range(li % cols):
            columns.append(items[n:n+rows])
            n += rows
        for i in range(li % cols, cols):
            if not li % cols:
                end = n + rows
            else:
                end = n + rows - 1
            columns.append(items[n:end])
            if not li % cols:
                n += rows
            else:
                n += rows - 1

        reordered = []
        for r in range(rows):
            for column in columns:
                try:
                    reordered.append(column[r])
                except IndexError:
                    pass

        items = reordered

        filled_items = [item.ljust(width, ' ') for item in items]
        if color is not None:
            filled_items = [color(item) for item in filled_items]
        from itertools import izip, chain, repeat
        for row in izip(*[chain(filled_items, repeat('', cols-1))]*cols):
            self.message('  '.join(row), indent=4)

    @classmethod
    def who(cls):
        'Return list of names of players connected right now.'

        names = cls.factory._player_protocols.keys()
        return [players.getname(name) for name in names]

    @classmethod
    def clients(cls):
        'Return list of all connected client protocols.'

        return cls.factory.clients

    @classmethod
    def roomclients(cls, room):
        'Return list of client protocols with players in the given room.'

        return [client for client in cls.clients if client.room==room]

    @classmethod
    def playerclient(cls, player):
        'Return the protocol of the given player.'

        return cls.factory._player_protocols.get(player.name, None)

    @classmethod
    def purge_all(cls):
        'Disconnect all players.'

        for player in players.ls():
            cls._purge(player)

    @classmethod
    def _purge(cls, player):
        'Disconnect given player.'

        if player.logged_in:
            client = cls.playerclient(player)
            if client is not None:
                client.transport.loseConnection()
            player.logged_in = False
