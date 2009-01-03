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


import os
import hashlib
import time

from twisted.internet import reactor

from persistent.list import PersistentList

from db import TZODB, TZIndex, TZDict
dbroot = TZODB().root

from colors import blue

from share import Character, str_attr

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

def isplayer(obj):
    return obj in ls()


class Player(Character):
    'Base class for all players.'

    name = str_attr('name', blank_ok=False, setonce=True)

    def __init__(self, name, short='', long=''):
        Character.__init__(self, name, short, long)
        add(self)

        self.pwhash = None
        self.user_settings = TZDict()

        self.logged_in = False
        self.created = time.time()
        self.last = None
        self.active = None

        self._bse = 'Player'

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
        salt = hashlib.md5(os.urandom(4)).hexdigest()[:8]
        hasher.update(salt)
        pwhash = '{pw_v1}' + hasher.hexdigest() + salt

        self.pwhash = pwhash

    def check_password(self, pwtext):
        'Return True if the hash of the given text matches the hashed password.'

        if not self.pwhash.startswith('{pw_v1}'):
            return self.check_password_v0(pwtext)

        hasher = hashlib.md5()
        hasher.update(pwtext)
        salt = self.pwhash[-8:]
        hasher.update(salt)
        pwhash = hasher.hexdigest()

        if pwhash == self.pwhash[7:-8]:
            return True
        else:
            return False

    def check_password_v0(self, pwtext):
        '''Old password verification, from before salted password storage.

        This method will be used for passwords in the old format.

        Passwords will be updated to the new format if the check
            is successful.

        returns True if the hash of the given text matches the hashed
            password.


        This method will go away in version 0.9

        '''

        hasher = hashlib.md5()
        hasher.update(pwtext)
        pwhash = hasher.digest()

        if pwhash == self.pwhash:
            self.set_password(pwtext)
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

        name = Character.__str__(self)
        return blue(name)

    #def __repr__(self):
        #return '''\
#Player (%s): %s  [%s]
    #%s
    #%s

    #Inventory:
        #%s

    #Home: %s

#''' % (self.tzid, self.name, 'room %s' % self._rid or 'Not logged in',
            #self.short,
            #self.long,
            #[item for item in self.items()],
            #self.home)

    def __repr__(self):
        return '[Player] %s (%s)' % (self.name, self.tzid)

    # Near actions
    def near_look(self, info):
        'Someone has "look"ed near this player.'

        looker = info['actor']
        lookee = info['actee']
        if looker is not self and self.can_see(looker):
            if lookee is self:
                self.message(looker, 'looks at you.')
            elif self.can_see(lookee):
                self.message(looker, 'looks at', lookee, '.')
            else:
                self.message(looker, 'looks at something.')

    def near_get(self, info):
        'Someone has "get"ted near this player.'

        getter = info['actor']
        item = info['item']
        if getter is not self:
            if self.can_see(getter) and self.can_see(item):
                self.message(getter, 'gets', item, '.')
            elif self.can_see(item):
                self.message(item, 'disappears.')
            elif self.can_see(getter):
                self.message(getter, 'gets something...')

    def near_drop(self, info):
        'Someone has "drop"ped near this player.'

        dropper = info['actor']
        item = info['item']
        if dropper is not self:
            if self.can_see(dropper) and self.can_see(item):
                self.message(dropper, 'drops', item, '.')
            elif self.can_see(item):
                self.message(item, 'appears.')

    def near_wear(self, info):
        'Someone has "wear"ed near this player.'

        wearer = info['actor']
        item = info['item']
        if wearer is not self and self.can_see(wearer):
            self.message(wearer, 'wears', item, '.')

    def near_unwear(self, info):
        'Someone has "remove"d near this player.'

        wearer = info['actor']
        item = info['item']
        if wearer is not self and self.can_see(wearer):
            self.message(wearer, 'removes', item, '.')

    def near_put(self, info):
        'Someone has "put" something in a container near this player.'

        putter = info['actor']
        item = info['item']
        container = info['container']
        if putter is not self and self.can_see(putter):
            if self.can_see(item) and self.can_see(container):
                self.message(putter, 'puts', item, 'in', container, '.')
            elif self.can_see(item):
                self.message(putter, 'did something with the', item, 'and it disappeared.')
            elif self.can_see(container):
                self.message(putter, 'puts something in the', container, '.')

    def near_take(self, info):
        'Someone has "take"n something from a container near this player.'

        taker = info['actor']
        item = info['item']
        container = info['container']
        if taker is not self and self.can_see(taker):
            if self.can_see(item) and self.can_see(container):
                self.message(taker, 'takes', item, 'from', container, '.')
            elif self.can_see(item):
                self.message(taker, 'did something and the', item, 'appeared.')
            elif self.can_see(container):
                self.message(taker, 'removed something from the', container, '.')

    def near_leave(self, info):
        'Someone has "leave"ed near this player.'

        leaver = info['actor']
        x = info['tox']
        if leaver is not self and self.can_see(leaver):
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
        if arriver is not self and self.can_see(arriver):
            if x is not None and self.can_see(x):
                self.message(arriver, 'arrives from', x, '.')
            else:
                self.message(arriver, 'arrives as if from nowhere.')

    def near_say(self, info):
        'Someone has "say"ed near this player.'

        speaker = info['actor']
        raw = info['raw']
        verb = info['verb'] + 's'
        quoted = '"' + raw + '"'
        if speaker is not self:
            if not self.can_see(speaker):
                speaker = 'Someone'
            self.message(speaker, verb+',', quoted)

    def near_shout(self, info):
        'Someone has "shout"ed near this player.'

        shouter = info['actor']
        raw = info['raw']
        x = info.get('fromx', None)
        if shouter is not self:
            if x is None:
                if not self.can_see(shouter):
                    shouter = 'Someone'
                msg = str(shouter) + ' shouts, "' + raw + '"'
            else:
                msg = 'You hear a shout from ' + str(x) + '.'
            self.message(msg)

    def near_emote(self, info):
        'Someone has "emote"d near this player.'

        emoter = info['actor']
        raw = info['raw']
        if emoter is not self and self.can_see(emoter):
            self.message(emoter, raw)

    def near_quit(self, info):
        'Someone has "quit" near this player.'

        quitter = info['actor']
        if quitter is not self and self.can_see(quitter):
            self.message(quitter, 'quits.')

    def near_appear(self, info):
        '''Something has appeared near this player.

        This is talking about becoming not invisible anymore,
            not about materializing from nowhere.

        If you are looking for some kind of materialization, it
            might be near_teleport_in, near_clone, near_dig
            or some new near action that you design.

        '''

        appearer = info['actor']
        container = appearer.container
        room = appearer.room

        if appearer is not self and self.can_see(appearer):
            if container is None:
                # The room disappeared... not sure what this means
                pass
            elif container.container is None:
                # So, it is in the room, and not in any container
                self.message(appearer, 'appears.')
            elif container is self:
                # it is in this player's inventory
                self.message('The', appearer, 'in your inventory becomes visible.')
            elif self in appearer.containers():
                container = appearer.container
                self.message('The', appearer, 'in the', container, 'becomes visible.')

    def near_disappear(self, info):
        '''Something has disappeared near this player.

        This is talking about becoming invisible, not dematerializing.

        If you are looking for some kind of dematerialization, you
            might be looking for near_teleport_away, near_destroy,
            or some new near action that you design.

        '''

        disappearer = info['actor']
        container = disappearer.container
        room = disappearer.room

        if disappearer is not self:
            if container is None:
                # The room disappeared... not sure what this means
                pass
            elif container.container is None:
                # So, it is in the room, and not in a container
                self.message(disappearer, 'disappears.')
            elif container is self:
                # it is in this player's inventory
                self.message('The', disappearer, 'in your inventory becomes invisible.')
            elif self in disappearer.containers():
                container = disappearer.container
                self.message('The', disappearer, 'in the', container, 'becomes invisible.')

    def near_teleport(self, info):
        wizard = info['actor']
        #wizard.room.action(dict(act='emote', actor=wizard, raw=msg))
        if wizard is not self and self.can_see(wizard):
            self.message(wizard, 'waves his hands around mysteriously.')

    def near_teleport_character_away(self, info):
        'Someone has "teleport"ed away from near this player.'

        teleporter = info['character']
        if teleporter is not self and self.can_see(teleporter):
            self.message(teleporter, 'disappears.')
        elif teleporter is self:
            self.message('You feel yourself being ripped away from where you are...')

    def near_teleport_character_in(self, info):
        'Someone has "teleport"ed in near this player.'

        teleporter = info['character']
        if teleporter is not self and self.can_see(teleporter):
            self.message(teleporter, 'appears.')
        elif teleporter is self:
            self.message('You have been teleported.')
            self.message(self.room)

    def near_teleport_item_away(self, info):
        'Something has been "teleport"ed away from near this player.'

        item = info['item']
        if self.can_see(item):
            self.message(item, 'disappears.')

    def near_teleport_item_in(self, info):
        'Something has been "teleport"ed in near this player.'

        item = info['item']
        if self.can_see(item):
            self.message(item, 'appears.')

    def near_sleep(self, info):
        'Someone has gone to sleep near this player.'

        sleeper = info['actor']
        if sleeper is not self and self.can_see(sleeper):
            self.message(sleeper, 'goes to sleep.')

    def near_awake(self, info):
        'Someone has woken up near this player.'

        sleeper = info['actor']
        if sleeper is not self and self.can_see(sleeper):
            self.message(sleeper, 'wakes up.')

    def near_clone_item(self, info):
        'Someone has "clone"d some item near this player.'

        cloner = info['actor']
        item = info['item']
        if cloner is not self and self.can_see(cloner):
            self.message(cloner, "mumbles something you can't quite make out and ... ")
            if self.can_see(item):
                self.message(cloner, 'now has', item, '.')
            else:
                self.message('Hmm... it looks like nothing happened.')

    def near_clone_mob(self, info):
        'Someone has "clone"d some mob near this player.'

        cloner = info['actor']
        mob = info['mob']
        if cloner is not self:
            if self.can_see(cloner):
                self.message(cloner, "mumbles something you can't quite make out and ... ")
            if self.can_see(mob):
                self.message(mob, 'has appeared.')

    def near_clone_exit(self, info):
        'Someone has "clone"d an exit near this player.'

        cloner = info['actor']
        x = info['x']
        if cloner is not self:
            if self.can_see(cloner):
                self.message(cloner, "mumbles something you can't quite make out and ... ")
            if self.can_see(x):
                self.message('An exit', x, 'has appeared.')

    def near_destroy_item(self, info):
        'Someone has "destroy"ed some item near this player.'

        destroyer = info['actor']
        item = info['item']
        if destroyer is not self:
            if self.can_see(destroyer):
                self.message(destroyer, "mumbles something you can't quite make out and ... ")
            if self.can_see(item):
                self.message(item, 'disappears.')

    def near_destroy_mob(self, info):
        'Someone has "destroy"ed some mob near this player.'

        destroyer = info['actor']
        mob = info['mob']
        if destroyer is not self:
            if self.can_see(destroyer):
                self.message(destroyer, "mumbles something you can't quite make out and ... ")
            if self.can_see(mob):
                self.message(mob, 'disappears.')

    def _near_lock(self, info):
        '''Someone has "lock"ed  or "unlock"ed a door near this player.

        This code is shared and called from near_lock and near_unlock

        '''

        locker = info['actor']
        action = info['action']
        door = info['door']
        key = info['key']

        if locker is not self:
            if self.can_see(locker) and self.can_see(door):
                if self.can_see(key):
                    keyphrase = 'with %s.' % key
                else:
                    keyphrase = '.'

                if action=='lock':
                    self.message(locker, 'locks the door', door, keyphrase)
                elif action=='unlock':
                    self.message(locker, 'unlocks the door', door, keyphrase)
                else:
                    if self.can_see(key):
                        self.message(locker, 'tries', key, 'in door', door, '.')
                    else:
                        self.message(locker, 'seems to be locking', door, 'but you do not see any key.')
            elif self.can_see(locker):
                self.message(locker, 'is trying a key... but you do not see any door there.')
            elif self.can_see(door):
                self.message('You hear the lock turning in door', door, '.')
            else:
                self.message('You hear what sounds like a key in a lock.')

    def near_lock(self, info):
        'Someone has "lock"ed a door near this player.'

        info['action'] = 'lock'
        self._near_lock(info)

    def near_unlock(self, info):
        'Someone has "unlock"ed a door near this player.'

        info['action'] = 'unlock'
        self._near_lock(info)

    def near_lockfail(self, info):
        'Someone has tried the wrong key in a door near this player.'

        info['action'] = 'fail'
        self._near_lock(info)

    def near_dig(self, info):
        'Someone has "dig"ged a new area near this player.'

        digger = info['actor']
        x = info['exit']
        if digger is not self:
            if self.can_see(digger):
                self.message(digger, 'digs a new exit', x, '.')
            elif self.can_see(x):
                self.message('A new exit', x, 'appears.')

    def near_use(self, info):
        'Someone has used something near this player.'

        user = info['actor']

        if user is not self:
            #check for a customized message first
            custom = info.get('custom', None)
            if custom is not None:
                self.message(custom % info)
            else:
                item = info['item']
                target = info.get('target', None)
                if target is None:
                    self.message(user, 'uses the', item, '.')
                else:
                    self.message(user, 'uses the', item, 'on', target, '.')


if __name__ == '__main__':
    update()
