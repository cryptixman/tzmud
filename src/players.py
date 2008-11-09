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


'''Player objects.

Players subclass the Character class.

'''


import hashlib
import time

from twisted.internet import reactor

from persistent.list import PersistentList

from db import TZODB, TZIndex, TZDict
dbroot = TZODB().root

from colors import blue

from share import Character

import actions

import rooms
import mobs

import tzprotocol


class PlayerIndex(TZIndex):
    'Player names are unique, so create a 2nd index by player name.'

    def index(self):
        return dbroot['players']['_index']

playerindex = PlayerIndex()
get = playerindex.get

def add(player):
    'Add the given player to the indexes.'

    dbroot['players'][player.name] = player
    playerindex.add(player)

def remove(player):
    'Remove the given player from the indexes.'

    del dbroot['players'][player.name]
    playerindex.remove(player)

def getname(name):
    'Return the player with the given name.'

    return dbroot['players'].get(name, None)

def ls():
    'Return a list of all the players.'

    return playerindex.ls()

def names():
    'Return a list of the names of all the players.'

    k = dbroot['players'].keys()
    k.remove('_index')
    return k


class Player(Character):
    'Base class for all players.'

    def __init__(self, name, short='', long=''):
        Character.__init__(self, name, short, long)
        add(self)

        self.pwhash = None
        self.user_settings = TZDict()

        self.logged_in = False
        self.created = time.time()
        self.last = None
        self.active = None

    def destroy(self):
        'Get rid of this player and remove it from the indexes.'

        room = self.room
        if room is not None:
            room.rmplayer(self)
        remove(self)
        Character.destroy(self)

    def move(self, room):
        '''Remove player from its current room and
            put it in the destination room.

        Any time the player changes rooms, this method should
            be used. Never change the player's room manually.

        '''

        leaving = rooms.get(self._rid)
        if leaving is not None:
            leaving.rmplayer(self)

        room.addplayer(self)
        self._rid = room.tzid
        tzprotocol.TZ.playerclient(self).room = room

    def set_password(self, pwtext):
        'Save the hashed password.'

        hasher = hashlib.md5()
        hasher.update(pwtext)
        pwhash = hasher.digest()

        self.pwhash = pwhash

    def check_password(self, pwtext):
        'Return True if the hash of the given text matches the hashed password.'

        hasher = hashlib.md5()
        hasher.update(pwtext)
        pwhash = hasher.digest()

        if pwhash == self.pwhash:
            return True
        else:
            return False

    def info(self):
        '''Return a multiline message (a list of strings) with detailed
        information about this player.

        '''

        msg = []
        if self.room is None:
            status = 'Not logged in'
        else:
            status = 'Currently logged in'
        msg.append('Player ' + self.name + ' (' + str(self.tzid) + ')'
                        + '  [' + status + ']')

        created = time.ctime(self.created)
        last = self.last and time.ctime(self.last) or 'Never'
        active = self.active and time.ctime(self.active) or 'Never'

        msg.append('    created     :   ' + created)
        msg.append('    last login  :   ' + last)
        msg.append('    last active :   ' + active)

        return msg

    def message(self, *args):
        'Send a message this this player.'

        tzprotocol.TZ.playerclient(self).message(*args)

    def mlmessage(self, msgs):
        'Send a multiline message to this player.'

        tzprotocol.TZ.playerclient(self).mlmessage(msgs)

    def __str__(self):
        'Return the colorized name of this player.'

        return blue(self.name)

    def __repr__(self):
        return '''\
Player (%s): %s  [%s]
    %s
    %s

    Inventory:
        %s

    Home: %s

''' % (self.tzid, self.name, 'room %s' % self._rid or 'Not logged in',
            self.short,
            self.long,
            [item for item in self.items()],
            self.home)


    # Near actions
    def near_look(self, info):
        'Someone has "look"ed near this player.'

        looker = info['actor']
        lookee = info['actee']
        if lookee == self:
            self.message(looker, 'looks at you.')
        else:
            self.message(looker, 'looks at', lookee, '.')

    def near_get(self, info):
        'Someone has "get"ted near this player.'

        getter = info['actor']
        item = info['item']
        self.message(getter, 'gets', item, '.')

    def near_drop(self, info):
        'Someone has "drop"ped near this player.'

        dropper = info['actor']
        item = info['item']
        self.message(dropper, 'drops', item, '.')

    def near_wear(self, info):
        'Someone has "wear"ed near this player.'

        wearer = info['actor']
        item = info['item']
        self.message(wearer, 'wears', item, '.')

    def near_unwear(self, info):
        'Someone has "remove"d near this player.'

        wearer = info['actor']
        item = info['item']
        self.message(wearer, 'removes', item, '.')

    def near_put(self, info):
        'Someone has "put" something in a container near this player.'

        putter = info['actor']
        item = info['item']
        container = info['container']
        self.message(putter, 'puts', item, 'in', container, '.')

    def near_take(self, info):
        'Someone has "take"n something from a container near this player.'

        taker = info['actor']
        item = info['item']
        container = info['container']
        self.message(taker, 'takes', item, 'from', container, '.')

    def near_leave(self, info):
        'Someone has "leave"ed near this player.'

        leaver = info['actor']
        x = info['tox']
        self.message(leaver, 'leaves to', x, '.')
        if self.following == leaver:
            self.message('You follow', leaver, '.')
            reactor.callLater(0, self._follow, leaver, x)

    def _follow(self, leaver, x):
        'Override Character._follow to show room name when arriving.'

        Character._follow(self, leaver, x)
        self.message(self.room)

    def near_arrive(self, info):
        'Someone has "arrive"d near this player.'

        arriver = info['actor']
        x = info['fromx']
        if x is not None:
            self.message(arriver, 'arrives from', x, '.')
        else:
            self.message(arriver, 'arrives as if from nowhere.')

    def near_say(self, info):
        'Someone has "say"ed near this player.'

        speaker = info['actor']
        raw = info['raw']
        verb = info['verb'] + 's'
        quoted = '"' + raw + '"'
        self.message(speaker, verb+',', quoted)

    def near_shout(self, info):
        'Someone has "shout"ed near this player.'

        shouter = info['actor']
        raw = info['raw']
        x = info.get('fromx', None)
        if x is None:
            msg = str(shouter) + ' shouts, "' + raw + '"'
        else:
            msg = 'You hear a shout from ' + str(x) + '.'
        self.message(msg)

    def near_emote(self, info):
        'Someone has "emote"d near this player.'

        emoter = info['actor']
        raw = info['raw']
        self.message(emoter, raw)

    def near_quit(self, info):
        'Someone has "quit" near this player.'

        quitter = info['actor']
        self.message(quitter, 'quits.')

    def near_teleport(self, info):
        wizard = info['actor']
        #wizard.room.action(dict(act='emote', actor=wizard, raw=msg))
        self.message(wizard, 'waves his hands around mysteriously.')

    def near_teleport_character_away(self, info):
        'Someone has "teleport"ed away from near this player.'

        teleporter = info['character']
        if teleporter != self:
            self.message(teleporter, 'disappears.')
        else:
            self.message('You feel yourself being ripped away from where you are...')

    def near_teleport_character_in(self, info):
        'Someone has "teleport"ed in near this player.'

        teleporter = info['character']
        if teleporter != self:
            self.message(teleporter, 'appears.')
        else:
            self.message('You have been teleported.')

    def near_teleport_item_away(self, info):
        'Something has been "teleport"ed away from near this player.'

        item = info['item']
        self.message(item, 'disappears.')

    def near_teleport_item_in(self, info):
        'Something has been "teleport"ed in near this player.'

        item = info['item']
        self.message(item, 'appears.')

    def near_sleep(self, info):
        'Someone has gone to sleep near this player.'

        sleeper = info['actor']
        self.message(sleeper, 'goes to sleep.')

    def near_awake(self, info):
        'Someone has woken up near this player.'

        sleeper = info['actor']
        self.message(sleeper, 'wakes up.')

    def near_clone_item(self, info):
        'Someone has "clone"d some item near this player.'

        cloner = info['actor']
        item = info['item']
        self.message(cloner, "mumbles something you can't quite make out and ... ")
        self.message(cloner, 'now has', item, '.')

    def near_clone_mob(self, info):
        'Someone has "clone"d some mob near this player.'

        cloner = info['actor']
        mob = info['mob']
        self.message(cloner, "mumbles something you can't quite make out and ... ")
        self.message(mob, 'has appeared.')

    def near_destroy_item(self, info):
        'Someone has "destroy"ed some item near this player.'

        destroyer = info['actor']
        item = info['item']
        self.message(destroyer, "mumbles something you can't quite make out and ... ")
        self.message(item, 'disappears.')

    def near_destroy_mob(self, info):
        'Someone has "destroy"ed some mob near this player.'

        destroyer = info['actor']
        mob = info['mob']
        self.message(destroyer, "mumbles something you can't quite make out and ... ")
        self.message(mob, 'disappears.')

    def near_lock(self, info):
        'Someone has "lock"ed  or "unlock"ed a door near this player.'

        locker = info['actor']
        action = info['action']
        door = info['door']

        if action=='lock':
            self.message(locker, 'locks the door', door, '.')
        elif action=='unlock':
            self.message(locker, 'unlocks the door', door, '.')
        else:
            self.message(locker, 'trys a key in door', door, '.')

    def near_dig(self, info):
        'Someone has "dig"ged a new area near this player.'

        digger = info['actor']
        x = info['exit']
        self.message(digger, 'digs a new exit', x, '.')

    def near_use(self, info):
        'Someone has used something near this player.'

        #check for a customized message first
        custom = info.get('custom', None)
        if custom is not None:
            self.message(custom % info)
        else:
            user = info['actor']
            item = info['item']
            target = info.get('target', None)
            if target is None:
                self.message(user, 'uses the', item, '.')
            else:
                self.message(user, 'uses the', item, 'on', target, '.')


if __name__ == '__main__':
    update()
