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


'''Mobile objects (creatures, non-player characters, etc) for the MUD.

Mobs are generally not gettable, and subclass the Character class.

'''

import random
import time

from twisted.internet import reactor

from persistent.list import PersistentList

from db import TZODB, TZIndex
zodb = TZODB()
dbroot = zodb.root
abort = zodb.abort
commit = zodb.commit

import tzprotocol

import rooms

from share import TZContainer, Character
from colors import magenta


def get(mid):
    'Return the mob with the given id number.'

    return dbroot['mobs'].get(mid, None)

def add(mob):
    'Add the given mob to the database.'

    dbroot['mobs'][mob.tzid] = mob

def remove(mob):
    'Remove the given mob from the database.'

    del dbroot['mobs'][mob.tzid]

def getname(name, all=False):
    '''Return the mob with the given name.

    Since object names are not necessarily unique, getname will by
        default return the first mob with the given name. To instead
        get a list of all the mobs with the given name, pass the
        parameter all=True.

    '''

    result = []
    for mob in ls():
        if mob.name == name:
            result.append(mob)

    if all:
        return result
    elif len(result) == 1:
        return result[0]
    else:
        return None

def ls():
    'Return a list of all the mobs in the database.'

    return dbroot['mobs'].values()

def names():
    '''Return a list of the names of all the mobs in the database.

    Since object names are not necessarily unique, names may return
        a particular name more than once.

    '''


    return [mob.name for mob in dbroot['mobs'].values()]


def nudge_all():
    'Nudge all the mobs in the database.'

    for mob in ls():
        print 'nudging', mob.name
        mob.nudge(0)




def weight(value):
    '''Decorator function to set the relative weighting of a function.

    Use this to make some mob actions more frequent or less frequent.

    For instance, in the base Mob class, these method defintions ...

    @weight(5)
    def action_sleep(self):
        [...]

    @weight(25)
    def action_awake(self):
        [...]

    Will cause awake to be called about 5 times more often than sleep.

    '''

    def set_weight(method):
        method.weight = value
        return method
    return set_weight


class Mob(Character):
    'Base class for all mob (mobile) objects in the MUD.'

    actionperiod = 10 # seconds

    def __init__(self, name='', short='', long=''):
        Character.__init__(self, name, short, long)

        self._last_act = 0
        self.nudge()

        add(self)

    def destroy(self):
        'Get rid of this mob and remove it from the mob index.'

        room = self.room
        if room is not None:
            room.rmmob(self)
        remove(self)
        Character.destroy(self)

    def exists(self):
        '''Return True if this mob is still an existing object

        This is used by the action framework to make sure that a mob
        has not been destroyed since the last time the action method
        was called since the twisted reactor will continue to hold
        a reference to the mob object.

        '''

        if get(self.tzid):
            return True
        else:
            return False

    def __str__(self):
        'Return the colorized name of this mob.'

        return magenta(self.name)

    def __repr__(self):
        return '''\
Mob: %s (%s) [in room %s]: %s
''' % (self.name, self.tzid, self._rid, self.short)

    def move(self, destination):
        'Remove the mob from its current room, and put it in the destination.'

        origin = rooms.get(self._rid)
        if origin is not None:
            origin.rmmob(self)

        destination.addmob(self)
        self._rid = destination.tzid

    def message(self, *args):
        '''Dummy method, to make it easier to share methods
        between characters and players.

        '''

        pass

    def mlmessage(self, msgs):
        '''Dummy method, to make it easier to share methods
        between characters and players.

        '''

        pass

    def actions(self):
        "return a list of this mob's possible actions"

        return [getattr(self, method) for method in dir(self) if method.startswith('action_')]

    def action(self):
        'Select a possible action using weighted choice'

        actions = self.actions()
        weights = [method.weight for method in actions]
        total = sum(weights)

        choice = random.randrange(total)

        while choice > weights[0]:
            choice -= weights[0]
            weights.pop(0)
            actions.pop(0)

        return actions[0]

    def act(self):
        'Choose an action and call it.'

        # mob may have been recently destroyed...
        if not self.exists():
            return

        action = self.action()
        try:
            if self.awake or action == self.action_awake:
                action()

            self._last_act = time.time()

        except:
            #print 'mob.act ABORT'
            abort()
            #raise

        else:
            #print 'mob.act COMMIT'
            commit()

        reactor.callLater(self.actionperiod, self.act)

    def nudge(self, delayfactor=10):
        'Make sure the mob is calling act() regularly.'

        now = time.time()

        if now > self._last_act + self.actionperiod * delayfactor:
            reactor.callLater(self.actionperiod, self.act)
        else:
            print 'Mob acted too recently to nudge.'


    @weight(5)
    def action_sleep(self):
        'Go to sleep.'

        if self.awake:
            self.awake = False
            self.room.action(dict(act='sleep', actor=self))


    @weight(25)
    def action_awake(self):
        'Wake up.'

        if not self.awake:
            self.awake = True
            self.room.action(dict(act='awake', actor=self))

    @weight(0)
    def action_move(self):
        'Select an exit at random and go there.'

        fol = self.following
        if fol is not None and (fol in self.room.players() or
                                fol in self.room.mobs()):
            return

        origin = self.room
        exits = origin.exits()
        if exits:
            x = random.choice(exits)
            if x.locked:
                return

            destination = x.destination
            if destination is not None:
                origin.action(dict(act='leave', actor=self, tox=x))

                self.move(destination)

                backx = None
                for backx in destination.exits():
                    if backx.destination == origin:
                        break

                destination.action(dict(act='arrive', actor=self, fromx=backx))

                #print self, 'moved from', room, 'to', destination


def classes():
    'Return a list of the names of the clonable mobs'

    return 'Cat', 'Sloth', 'Snake', 'PackRat'


class Cat(Mob):
    'Miaw!'

    name = 'cat'
    short = 'A frisky little kitty cat.'

    def look(self, looker):
        'Return a string to send to the player looking at this cat.'

        msgs = Mob.look(self, looker)
        if not self.awake:
            msgs.append('    ' + str(self) + ' is sleeping... shhhh.')
        return msgs

    @weight(50)
    def action_move(self):
        Mob.action_move(self)

    def near_say(self, info):
        '''Players can cause the cat to follow by saying "here kitty" or
            stop the cat from following by saying "go away".

        '''

        speaker = info['actor']
        msg = info['raw']
        m = msg.lower()
        if m.startswith('here kitty'):
            self.following = speaker
            speaker.message(self, 'starts following you.')
        elif m.startswith('go away'):
            self.following = self
            speaker.message(self, 'stops following you.')


class Sloth(Mob):
    'A lazy mob which does not move around.'

    name = 'sloth'
    short = 'A furry gray sloth.'


class Snake(Mob):
    'A legless reptile.'

    name = 'snake'
    short = 'A green garter snake.'
    actionperiod = 1 # seconds

    @weight(100)
    def action_move(self):
        Mob.action_move(self)


class PackRat(Mob):
    'Collects things and brings them back to its nest.'

    actionperiod = 5 # seconds
    name_aka = ['rat']

    name = 'packrat'
    short = 'A large scruffy rat. Is it carrying something?'

    def __init__(self, name='', short='', long=''):
        Mob.__init__(self, name, short, long)
        self._path_home = PersistentList()
        self._searching = True
        self._has_dug_home = False

    def near_drop(self, info):
        if self._searching and self.room!=self.home and not self.items():
            item = info['item']
            if item in self.room:
                self.get_item(item, self.room)
                self._searching = False

                if not self._has_dug_home:
                    self._dig_home()

    @weight(100)
    def action_move(self):
        x = self._choose_exit()
        if x is not None:
            self._move(x)
            if self._searching and x.destination!=self.home and not self.items():
                item = self._search()
                if item and not self._has_dug_home:
                    self._dig_home()
            if not self._searching and x.destination==self.home:
                self._store_item()

    def _choose_exit(self):
        origin = self.room
        exits = origin.exits()
        x = None
        if exits:
            if self._searching:
                x = random.choice(exits)
                if x.locked:
                    x = None
            else:
                for x in exits:
                    try:
                        if x.destination == self._path_home[-2]:
                            break
                    except KeyError:
                        print 'No -2'
        return x

    def _move(self, x):
        origin = self.room
        destination = x.destination
        if destination is not None:
            origin.action(dict(act='leave', actor=self, tox=x))

            self.move(destination)

            if destination not in self._path_home:
                self._path_home.append(destination)
            else:
                i = self._path_home.index(destination)
                l = len(self._path_home)
                if i+1 < l:
                    for d in range(i+1, l):
                        del self._path_home[d]

            backx = None
            for backx in destination.exits():
                if backx.destination == origin:
                    break

            destination.action(dict(act='arrive', actor=self, fromx=backx))

    def _search(self):
        items = self.room.items()
        if items:
            item = items[0]
            self.get_item(item, self.room)
            self._searching = False
            return item
        else:
            return None

    def _dig_home(self):
        home = rooms.Room('rat nest', "The rat's nest.")
        x = rooms.Exit('hole', 'A roughly dug hole.',
                        room=self.room,
                        destination=home, return_name='exit')
        self.home = home
        for i in range(len(self._path_home)):
            self._path_home.pop()
        self._path_home.append(home)
        self._path_home.append(self.room)
        self.room.action(dict(act='dig', actor=self, exit=x))
        self._has_dug_home = True

    def _store_item(self):
        item = self.items()[0]
        self.drop_item(item, self.room)
        self._searching = True
