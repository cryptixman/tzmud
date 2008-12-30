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


'''Room objects.

Rooms are containers of many different types of objects, so they
support the regular get() and getname() methods for items, but
also player() and playername() for players and mob() and mobname()
for mobs. It works out best to keep these object types separated.

'''

import time
import random

from twisted.internet import reactor

from persistent.list import PersistentList

from db import TZODB, TZIndex
zodb = TZODB()
dbroot = zodb.root
commit = zodb.commit
abort = zodb.abort

import conf
import mobs
import items
from share import TZContainer, TZObj, class_as_string, int_attr
from share import register_plugin
from colors import green, yellow, red

tzindex = TZIndex()


def get(rid):
    'Return the room with the given id number.'

    return dbroot['rooms'].get(rid, None)

def add(room):
    'Add the given room to the database.'

    dbroot['rooms'][room.tzid] = room

def remove(room):
    'Remove the given room from the database.'

    del dbroot['rooms'][room.tzid]

def getname(name, all=False):
    '''Return the room with the given name.

    Since object names are not necessarily unique, getname will by
        default return the first room with the given name. To instead
        get a list of all the rooms with the given name, pass the
        parameter all=True.

    '''

    result = []
    for room in ls():
        if room.name == name:
            if not all:
                return room
            else:
                result.append(room)

    if all:
        return result
    else:
        return None

def ls():
    'Return a list of all the rooms in the database.'

    return dbroot['rooms'].values()

def names():
    '''Return a list of the names of all the rooms in the database.

    Since object names are not necessarily unique, names may return
        a particular name more than once.

    '''


    return [room.name for room in dbroot['rooms'].values()]


def nudge_all():
    'Nudge all of the rooms.'

    for room in ls():
        print 'nudging', room.name
        room.nudge(0)


def register_room(cls):
    import rooms
    register_plugin(rooms, cls)




class Room(TZContainer):
    'Base class for all rooms in the MUD.'

    period = int_attr('period') # seconds

    def __init__(self, name='', short='', long='', owner=None,
                    exits=None, items=None):
        TZContainer.__init__(self, name, short, long, owner, items)

        self.settings.append('period')

        self._exit_ids = PersistentList()
        if exits is not None:
            for x in exits:
                self.addexit(x)
        self._player_ids = PersistentList()
        self._mob_ids = PersistentList()

        self._last_periodic = 0

        add(self)

        self.periodically()

    def destroy(self):
        '''Get rid of this room and remove it from the index.

        All outgoing exits will also be destroyed.
        Any mob in the room will be moved to its home.
        Any player in the room will be moved to its home.

        As with a TZContainer, any item in the room will be destroyed.

        '''

        print 'must destroy', self
        for x in self.exits():
            x.destroy()
        for mob in self.mobs():
            mob.move(mob.home)
        for player in self.players():
            player.move(player.home)
        remove(self)
        TZContainer.destroy(self)

    def periodically(self):
        '''Call self.periodic() every self.period seconds.

        if period == 0, disable the periodic calls. If you need a
            room to call periodic very quickly, just use a very small
            but non-zero number.

        '''

        if self.period:
            self._last_periodic = time.time()
            self.periodic()
            reactor.callLater(self.period, self.periodically)

    def nudge(self, delayfactor=10):
        'Nudge this room to make sure the periodic calls are happening.'

        now = time.time()

        if now > self._last_periodic + self.period * delayfactor:
            self.periodically()
        else:
            print 'Too recent to nudge.'

    def action(self, info):
        '''An action has occurred in this room which must be passed on to all
            players, mobs and items in the room.

        The action should also be passed on to all items that are carried
            by characters in this room (and to items inside of containers).

        Uses a callLater to make sure that reactions to the action occur
            after the action has been reported.

        Any player, mob, item or room which wants to react to an action
            should define a near_<action> method which accepts the info dict.

            The info dict should have at least act='action name' and
            actor=<character>. Different actions can pass whatever other
            information deemed necessary through the info dict.

        '''

        delay = info.get('delay', 0.1)
        reactor.callLater(delay, self._action, info)
        #raise SyntaxError

    def _action(self, info):
        'Actual action work is done here.'

        try:
            act = info['act']
            actor = info['actor']

            for player in self.players():
                player.act_near(info)

            for mob in self.mobs():
                if mob != actor:
                    mob.act_near(info)

            for item in self.items():
                item.act_near(info)

            for x in self.exits():
                x.act_near(info)

            self.act_near(info)

            # Some actions can affect nearby rooms. If that is the case for
            # this action, find the rooms from the exits and pass it on.
            spread = info.get('spread', None)
            if spread is not None and spread > 0:
                fromroom = info.get('fromroom', None)
                info['fromroom'] = self
                info['spread'] -= 1
                for x in self.exits():
                    room = x.destination
                    if room == fromroom:
                        continue
                    for bx in room.exits():
                        if bx.destination == self:
                            info['fromx'] = bx
                            break
                    # EEE -- Could calling this here be a transaction problem?
                    room.action(info)

        except Exception, e:
            print 'room._action ABORT'
            for line in e:
                print line
            abort()
            #raise

        else:
            #print 'room._action COMMIT'
            commit()

    def players(self):
        'Return a list of all the players in this room'

        return [tzindex.get(pid) for pid in self._player_ids]

    def player(self, pid):
        '''Return the player in this room with the given id number, or None if
            a player with that id number is not in this room.

        '''

        if pid in self._player_ids:
            return tzindex.get(pid)
        else:
            return None

    def playernames(self):
        'Return a list of the names of all the players in this room.'

        return [player.name for player in self.players()]

    def playername(self, name, all=False):
        '''Return the player in this room with the given name or None
            if a player by that name is not in this room.

        Although player names are unique, must follow the all= protocol
            to match other object types. If all=True, and the player is
            found, return the player in a one-item list instead of bare.

        '''

        for player in self.players():
            if player.name == name:
                if not all:
                    return player
                else:
                    return [player]
        return None

    def addplayer(self, player):
        'Put the given player in this room.'

        self._player_ids.append(player.tzid)
        player.container = self

    def rmplayer(self, player):
        'Remove the given player from this room.'

        self._player_ids.remove(player.tzid)
        player.container = None


    def mobs(self):
        'Return a list of the mobs in this room.'

        return [tzindex.get(pid) for pid in self._mob_ids]

    def mob(self, mid):
        '''Return the mob with the given id number if it is in this room, or None
            if no mob with that number is in this room.

        '''

        if mid in self._mob_ids:
            return tzindex.get(mid)
        else:
            return None

    def mobnames(self):
        'Return a list of the names of the mobs in this room.'

        return [mob.name for mob in self.mobs()]

    def mobname(self, name, all=False):
        '''Return the mob with the given name if it is in this room, or None
            if no mob by that name is in this room.

        Since mob names are not necessarily unique, mobnames will return the
            first mob found with the given name. If you want a list of all of
            the mobs by that name in this room, pass all=True.

        '''

        result = []
        for mob in self.mobs():
            if mob.name == name:
                if not all:
                    return mob
                else:
                    result.append(mob)

        for mob in self.mobs():
            if hasattr(mob, 'name_aka'):
                for aka in mob.name_aka:
                    if aka == name:
                        if not all:
                            return mob
                        else:
                            result.append(mob)

        if result:
            return result
        else:
            return None

    def addmob(self, mob):
        'Move the given mob to this room.'

        self._mob_ids.append(mob.tzid)
        mob.container = self

    def rmmob(self, mob):
        'Remove the given mob from this room.'

        self._mob_ids.remove(mob.tzid)
        mob.container = None


    def exits(self):
        'Return a list of all the exits from this room.'

        return [tzindex.get(xid) for xid in self._exit_ids]

    def exitnames(self):
        'Return a list of the names of all the exits from this room.'

        return [x.name for x in self.exits()]

    def exit(self, xid):
        '''Return the exit from this room with the given id number.

        Note that although "exit" is not a python keyword, it can be
            confusing sometimes be confusing to use exit as a variable
            name, and so "x" is usually used to mean an exit.

        '''

        if xid in self._exit_ids:
            return tzindex.get(xid)
        else:
            return None

    def exitname(self, name, all=False):
        '''Return the exit from this room with the given name, or None if no
            such exit from this room exists.

        Since exit names are not necessarily unique (yes, it is possible to
            have 2 north exits in a room), exitname will return the first exit
            found with the given name. To instead get a list of all the exits
            with a given name, pass the parameter all=True.

        '''

        result = []
        for x in self.exits():
            if x.name == name:
                if not all:
                    return x
                else:
                    result.append(x)
        if result:
            return result
        else:
            return None

    def addexit(self, x):
        'Put an exit in this room.'

        self._exit_ids.append(x.tzid)
        x.room = self

    def rmexit(self, x):
        'Remove an exit from this room.'

        self._exit_ids.remove(x.tzid)


    def look(self, looker):
        '''Return a multiline message (list of strings) to a player looking at
            this room.

        '''

        msgs = TZContainer.look(self, looker)

        xs = filter(looker.can_see, self.exits())
        if xs:
            msgs.append('')
            msgs.append('Exits: ')
            msgs.append('    ' + ', '.join(map(str, xs)))
            #print msgs

        iis = filter(looker.can_see, self.items())
        if iis:
            msgs.append('')
            if len(iis) > 1:
                msgs.append('You see some items here:')
            else:
                msgs.append('You see something here:')

            for item in iis:
                msgs.append('    ' + str(item))

        ps = filter(looker.can_see, self.players())
        if len(ps) > 1:
            msgs.append('')
            for player in ps:
                if player != looker:
                    msgs.append(str(player) + ' is here.')

        ms = filter(looker.can_see, self.mobs())
        if ms:
            msgs.append('')
            for mob in ms:
                msgs.append(str(mob) + ' is here.')

        return msgs

    def __str__(self):
        'Return the colorized name of this room.'

        name = TZContainer.__str__(self)
        return red(name)

    def __repr__(self):
        return '''\
Room (%s): %s
    %s
    %s
    Owner: %s

    Exits:
        %s

    Contents:
        %s

    Players:
        %s

    Mobs:
        %s

''' % (self.tzid, self.name, self.short, self.long, self.owner,
            [x for x in self.exits()],
                [item for item in self.items()],
                ['%s (%s)' % (player.name, player.tzid)
                    for player in self.players()],
                ['%s (%s)' % (mob.name, mob.tzid)
                    for mob in self.mobs()])

    def __copy__(self):
        '''A copy of a room will have everything the same except...
        The exits from the room will lead where the original exits
            lead, but there will be no connections in to the room.
        There will be nothing (no contents) in the room.

        '''

        c = Room(self.name, self.short, self.long, self.owner)

        for x in self.exits():
            new_x = Exit(x.name, x.short, x.long,
                            room=c, destination=x.destination)
            c.addexit(new_x)

        return c


class Exit(TZObj):
    'A way to move from one room to another.'

    _link_exit_id = 0

    def __init__(self, name, short='', long='', room=None, destination=None, return_name=''):
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

        self.settings += ['locked', 'weight',]

    def destroy(self):
        'Get rid of this exit.'

        self.room.rmexit(self)
        TZObj.destroy(self)

    def go(self, character):
        '''character is trying to go through this exit.

        returns (True, None) if it works.
        returns (False, 'Some message explaining why not.') if not.

        '''

        if self.destination is None:
            return (False, 'Exit %s is broken....'%self)
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
                    msgs.append('Exit %s to %s.' % (str(self), self.destination))
                else:
                    msgs.append('The exit %s is locked.' % self)

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
        return '%s --> %s' % (self.name, self.destination)

    def _set_room(self, room):
        'Setter for the room property.'
        if room is not None:
            self._rid = room.tzid
        else:
            self._rid = None
    def _get_room(self):
        'Getter for the room property.'
        return get(self._rid)
    room = property(_get_room, _set_room)

    def _set_destination(self, destination):
        'Setter for the destination property.'
        if destination is not None:
            self._destid = destination.tzid
        else:
            self._destid = None
    def _get_destination(self):
        'Getter for the destination property.'
        return get(self._destid)
    destination = property(_get_destination, _set_destination)

    def _set_locked(self, tf):
        tf = bool(tf)
        self._locked = tf
        if self._link_exit_id:
            otherx = tzindex.get(self._link_exit_id)
            otherx._locked = tf
    def _get_locked(self):
        return self._locked
    locked = property(_get_locked, _set_locked)

    def _set_weight(self, w):
        self._weight = w
        if self._link_exit_id:
            otherx = tzindex.get(self._link_exit_id)
            otherx._weight = w
    def _get_weight(self):
        return self._weight
    weight = property(_get_weight, _set_weight)


class_names = ['Room', 'SmallRoom', 'Trap', 'TimedTrap', 'Zoo', 'TeleTrap']

def classes():
    'Return a list of the names of the clonable rooms.'

    return class_names


class SmallRoom(Room):
    '''A room that can only hold so many characters.

    max: Maximum number of characters in this room.

    '''

    name = 'small room'
    short = 'Seems kind of crowded in here.'
    max = int_attr('max', default=1)

    def __init__(self, name=''):
        Room.__init__(self, name)
        self.settings.append('max')

    def near_arrive(self, info):
        '''A character has just arrived here. If the room is full, send back!

        # EEE -- this causes a strange problem with someone is following.
        #       The messages are coming through in incorrect order, and
        #       seemingly from the wrong rooms. Not quite sure how to
        #       fix this.

        '''

        arriver = info['actor']
        characters = self.players() + self.mobs()
        if len(characters) > self.max:
            x = info['fromx']
            arriver.message('The room is too full to enter.')
            if x is None:
                xs = self.exits()
                if xs:
                    x = random.choice(xs)
            if x is not None:
                arriver.go(x)
                arriver.message(x.destination)


class Trap(Room):
    'A room that has no exits.'

    name = 'a trap'
    short = "There's no way out...."

    def addexit(self, x):
        pass


class TimedTrap(Room):
    'Waits for a specified time, then springs the trap.'

    name = 'timed trap'
    short = 'Is that a ticking sound you hear?'
    timer = int_attr('timer', default=5) # seconds

    def __init__(self, name=''):
        Room.__init__(self, name)
        self._springing = False
        self.settings.append('timer')

    def near_arrive(self, info):
        if not self._springing:
            self._springing = True
            reactor.callLater(self.timer, self.spring_trap)

    def spring_trap(self):
        self._springing = False
        for c in self.mobs() + self.players():
            c.message('Gotcha!')


class TeleTrap(TimedTrap):
    '''A trap that teleports characters to different rooms.

    If _targets is empty, will select from all rooms randomly.

    '''

    name = 'room'

    def __init__(self, name=''):
        TimedTrap.__init__(self)
        self._targets = PersistentList()

    def addtarget(self, name):
        if name not in self._targets:
            self._targets.append(name)

    def spring_trap(self):
        try:
            TimedTrap.spring_trap(self)

            if not self._targets:
                rms = ls()
            else:
                rms = [getattr(rooms, name) for name in self._targets]

            p = self.players()
            m = self.mobs()
            characters = p + m
            for c in characters:
                c.message('Click.')
                room = random.choice(rms)
                c.move(room)

        except:
            abort()

        else:
            commit()


class Zoo(Room):
    '''This room will automatically build rooms for every available mob
        and popululate those rooms.

    Once an hour, it will check to see that the mobs are still in their
        cages, and if not it will repopulate the cages.

    Destroying the Zoo should destroy all of the associated objects that
        were built during its creation, except for any escaped mobs.

    '''

    name = 'zoo'
    short = 'All sorts of strange creatures.'

    def __init__(self, name=''):
        self.period = 3600 # 60 minutes
        Room.__init__(self, name)

    def destroy(self):
        '''Get rid of the Zoo.

        Be careful to get rid of everything associated with the zoo,
            but not anything that may have wandered in here.

        '''

        for x in self.exits():
            if x.name.startswith('see the'):
                outside = x.destination
                for ox in outside.exits():
                    if ox.destination != self:
                        cage = ox.destination
                        # Try to remove any mobs that may have wandered
                        # in here before destroying any mobs.
                        for mob in cage.mobs():
                            mob.move(mob.home)
                        for mob in cage.mobs():
                            mob.destroy()
                        cage.destroy()
                outside.destroy()

        Room.destroy(self)

    def periodic(self):
        'Check to see the zoo has all of its inhabitants.'

        self.populate()

    def populate(self):
        '''If the Zoo has an area for a mob, check that the mob is still
            there and if not, respawn it.

        If the Zoo does not have an area for the mob, it may be a new mob,
            so build a place for it.

        '''

        key = self.itemname('key')
        if key is None:
            # Check if the room has any keys. If not make one.
            # If it does have at least one key, only make a
            #   new one very rarely.
            _key = None
            if hasattr(self, '_key'):
                _key = getattr(self, '_key')
            if _key is None or random.choice(random.randrange(50)) == 0:
                key = items.Key()
                self.add(key)
                # make sure to always use the same key
                if hasattr(self, '_key'):
                    key._key = getattr(self, '_key')
        self._key = key._key

        for mobclass in mobs.classes():
            exists = False
            for x in self.exits():
                if x.name == 'see the %s' % mobclass.lower():
                    exists = True
                    self.respawn(x.destination, mobclass)

            if not exists:
                self.build(mobclass)

    def respawn(self, outside, mc):
        'Check to see if the mob is in its cage. If not then make a new one.'

        # lock the doors
        key = self.itemname('key')
        door = outside.exitname('door')
        door.lock(key)

        # check if the mob is still at home
        cage = door.destination
        found = False
        for mob in cage.mobs():
            mobclass = class_as_string(mob)
            if mobclass == mc:
                found = True

        if not found:
            cls = getattr(mobs, mc)
            mob = cls()
            mob.home = cage
            mob.move(cage)

    def build(self, mobclass):
        '''Construct an area for the given mob.

        If there is a key in the Zoo, use that key for the door to the
            new cage. If not, create a new key.

        '''

        mcl = mobclass.lower()

        key = self.itemname('key')

        outside = Room('outside the %s cage' % mcl)
        x = Exit('see the %s' % mcl)
        bx = Exit('zoo')
        self.addexit(x)
        x.destination = outside
        bx.destination = self
        outside.addexit(bx)

        cage = Room('%s cage' % mcl)
        x = Exit('door')
        bx = Exit('exit')
        x.link(bx)
        x.add_key(key)
        x.lock(key)
        outside.addexit(x)
        x.destination = cage
        bx.destination = outside
        cage.addexit(bx)

        self.respawn(outside, mobclass)

