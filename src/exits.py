# Copyright 2010 Lee Harr
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


'''Exit objects.

Exits are portals between rooms.
'''

from persistent.list import PersistentList

from share import TZObj

from db import TZODB, TZIndex
zodb = TZODB()
dbroot = zodb.root
commit = zodb.commit
abort = zodb.abort

import rooms
import players
from colors import green, yellow, red

tzindex = TZIndex()


def get(xid):
    'Return the exit with the given id number.'

    return dbroot['exits'].get(xid, None)

def add(x):
    'Add the given exit to the database.'

    dbroot['exits'][x.tzid] = x

def remove(x):
    'Remove the given exit from the database.'

    del dbroot['exits'][x.tzid]

def getname(name, all=False):
    '''Return the exit with the given name.

    Since object names are not necessarily unique, getname will by
        default return the first exit with the given name. To instead
        get a list of all the exits with the given name, pass the
        parameter all=True.

    '''

    result = []
    for x in ls():
        if x.name == name:
            if not all:
                return x
            else:
                result.append(x)

    if all:
        return result
    else:
        return None

def ls():
    'Return a list of all the exits in the database.'

    return dbroot['exits'].values()

def names():
    '''Return a list of the names of all the exits in the database.

    Since object names are not necessarily unique, names may return
        a particular name more than once.

    '''

    return [x.name for x in dbroot['exits'].values()]

def isexit(obj):
    return obj in ls()


class Exit(TZObj):
    'A way to move from one room to another.'

    name = 'proto exit'
    _link_exit_id = 0
    settings = ['locked', 'weight',]
    _bse = 'Exit'


    def __init__(self, name='', short='', long='', room=None, destination=None, return_name=''):
        TZObj.__init__(self, name, short, long)
        self._rid = None
        self.room = room

        self.weight = 0
        self.locked = False

        if room is not None:
            room.addexit(self)
        self.destination = destination

        if return_name and destination is not None:
            x = destination.exitname(return_name)
            if x is not None:
                x.destination = room
            else:
                x = Exit(return_name, room=destination, destination=room)
            self.link(x)

        self._keys = PersistentList()

        add(self)

    def destroy(self):
        'Get rid of this exit.'

        if self.room is not None:
            self.room.rmexit(self)
        remove(self)
        TZObj.destroy(self)

    def go(self, character):
        '''character is trying to go through this exit.

        returns (True, None) if it works.
        returns (False, 'Some message explaining why not.') if not.

        '''

        if self.destination is None:
            return (False, u'Exit %s is broken....'%self)
        if self.locked:
            return (False, 'The door is locked.')
        elif self.weight:
            if character.setting('strength') < self.weight:
                return (False, 'The door is too heavy.')

        return (True, None)

    def add_key(self, key):
        'Make this door lockable with the given key.'

        _key = key._key
        if _key not in self._keys:
            self._keys.append(_key)
        if self._link_exit_id:
            otherx = tzindex.get(self._link_exit_id)
            if _key not in otherx._keys:
                otherx._keys.append(_key)

    def lock(self, key):
        'Lock this door if the key is correct.'

        if key.locks(self):
            self.locked = True

    def unlock(self, key):
        'Unlock this door if the key is correct.'

        if key.locks(self):
            self.locked = False

    def link(self, otherx):
        '''Connect this door to another one, so that locking/ unlocking this
            door will also lock/ unlock the connected door.

        '''

        self._link_exit_id = otherx.tzid
        otherx._link_exit_id = self.tzid

        if self.weight:
            otherx.weight = self.weight

    def get_linked_exit(self):
        if self._link_exit_id:
            return tzindex.get(self._link_exit_id)
        else:
            return None

    def look(self, s):
        '''Return a multiline message (list of strings) to a player looking
            at this exit.

        '''

        if self.short or self.long:
            msgs = TZObj.look(self, s)
        else:
            msgs = []
            if self._destid is None or self.destination is None:
                msgs.append('Broken exit.')
            else:
                if not self.locked:
                    msgs.append(u'Exit %s to %s.' % (unicode(self), self.destination))
                else:
                    msgs.append(u'The exit %s is locked.' % self)

        return msgs

    def near_listen(self, info):
        obj = info['obj']
        if obj is self:
            listener = info['actor']
            d = self.destination
            if d.mobs() or d.players():
                listener.message('You hear someone there.')
            else:
                listener.message('It sounds quiet there.')


    def __str__(self):
        'Return the colorized name of this exit.'

        name = TZObj.__str__(self)
        return yellow(name)

    def __repr__(self):
        return u'%s --> %s' % (self.name, self.destination)

    def _set_room(self, room):
        'Setter for the room property.'
        if room is not None:
            self._rid = room.tzid
        else:
            self._rid = None
    def _get_room(self):
        'Getter for the room property.'
        return rooms.get(self._rid)
    room = property(_get_room, _set_room)

    def _set_destination(self, destination):
        'Setter for the destination property.'
        if destination is not None:
            self._destid = destination.tzid
        else:
            self._destid = None
    def _get_destination(self):
        'Getter for the destination property.'
        return rooms.get(self._destid)
    destination = property(_get_destination, _set_destination)

    def _set_locked(self, tf):
        tf = bool(tf)
        self._locked = tf
        if self._link_exit_id:
            otherx = tzindex.get(self._link_exit_id)
            if otherx is not None:
                otherx._locked = tf
    def _get_locked(self):
        return self._locked
    locked = property(_get_locked, _set_locked)

    def _set_weight(self, w):
        self._weight = w
        if self._link_exit_id:
            otherx = tzindex.get(self._link_exit_id)
            if otherx is not None:
                otherx._weight = w
    def _get_weight(self):
        return self._weight
    weight = property(_get_weight, _set_weight)
    def set_weight(self, w):
        try:
            w = int(w)
        except ValueError:
            return False

        self.weight = w
        return True

    def teleport(self, destination):
        'Unhook this exit from its room and connect it to destination.'

        self.room.rmexit(self)
        destination.addexit(self)



class PlayersOnly(Exit):
    'An Exit that only players can pass through. No mobs allowed!'

    def go(self, character):
        '''character is trying to go through this exit.'''

        if players.isplayer(character):
            return Exit.go(self, character)
        else:
            return (False, 'Exit is for players only.')


class_names = ['Exit', 'PlayersOnly', ]

def classes():
    'Return a list of the names of the clonable rooms.'

    return class_names



def upgrade(from_version, to_version):
    from share import upgrade
    if from_version==0 and to_version==1:
        from db import TZDict
        dbroot['exits'] = TZDict()
        commit()

        all_exits = []
        import rooms
        for room in rooms.ls():
            all_exits.extend(room.exits())

        for x in all_exits:
            print 'upgrading', x
            updated = upgrade(x, Exit)
            updated.destination = rooms.get(updated._destid)
            add(updated)

        commit()
