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
from bisect import bisect

from twisted.internet import reactor

from persistent.list import PersistentList
from persistent.dict import PersistentDict

from db import TZODB, TZIndex
zodb = TZODB()
dbroot = zodb.root
abort = zodb.abort
commit = zodb.commit

import tzprotocol

import rooms
import items

from share import TZContainer, Character, class_as_string, int_attr, str_attr
from share import register_plugin
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
            if not all:
                return mob
            else:
                result.append(mob)

    if all:
        return result
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

def ismob(obj):
    return obj in ls()


def nudge_all():
    'Nudge all the mobs in the database.'

    for mob in ls():
        print 'nudging', mob.name
        mob.nudge(0)


class Mob(Character):
    'Base class for all mob (mobile) objects in the MUD.'

    name = 'proto mob'
    period = int_attr('period', default=10) # seconds
    settings = ['period']
    _bse = 'Mob'

    def __init__(self, name='', short='', long=''):
        Character.__init__(self, name, short, long)

        self._last_act = 0
        self.nudge()

        add(self)

        self._action_weights = PersistentDict()
        self.set_default_action_weights()
        self.set_action_weights(action_awake=500,
                                action_move=0)

    def destroy(self):
        'Get rid of this mob and remove it from the mob index.'

        room = self.room
        if room is not None:
            room.rmmob(self)
            room.action(dict(act='destroy_mob', actor=None, mob=self))

        remove(self)
        Character.destroy(self)

    def __str__(self):
        'Return the colorized name of this mob.'

        name = Character.__str__(self)
        return magenta(name)

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

    def set_action_weights(self, **kw):
        '''set the weight of the given methods by name.

        >>> mob.set_action_weights(action_sleep=50,
                                    action_move=200)

        '''

        for meth_name, weight in kw.items():
            self._action_weights[meth_name] = weight

    def set_default_action_weights(self):
        '''set all action_* methods to weight 100.'''

        for meth_name in self.actions():
            self._action_weights[meth_name] = 100

    def actions(self):
        """return a list of this mob's possible actions.

        Names of actions should begin with action_

        """

        acts = [meth_name for meth_name in dir(self)
                    if meth_name.startswith('action_')]
        return acts

    def action(self):
        'Select a possible action using weighted choice'

        action_names = self.actions()
        weights = [self._action_weights[meth_name] for meth_name in action_names]
        total = float(sum(weights))
        cum_norm_weights = [0.0]*len(weights)
        for i in xrange(len(weights)):
            cum_norm_weights[i] = cum_norm_weights[i-1] + weights[i]/total
        meth_name = action_names[bisect(cum_norm_weights, random.random())]
        return getattr(self, meth_name)

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

        reactor.callLater(self.period, self.act)

    def nudge(self, delayfactor=10):
        'Make sure the mob is calling act() regularly.'

        now = time.time()

        if now > self._last_act + self.period * delayfactor:
            reactor.callLater(self.period, self.act)
        else:
            print 'Mob acted too recently to nudge.'


    def action_sleep(self):
        'Go to sleep.'

        if self.awake:
            self.awake = False
            self.room.action(dict(act='sleep', actor=self))

    def action_awake(self):
        'Wake up.'

        if not self.awake:
            self.awake = True
            self.room.action(dict(act='awake', actor=self))

    def action_move(self):
        'Select an exit at random and go there.'

        room = self.room
        fol = self.following
        if fol is not None and (fol in room.players() or
                                fol in room.mobs()):
            return

        exits = filter(self.can_see, room.exits())
        if exits:
            x = random.choice(exits)
            success, msg = self.go(x)


class_names = ['Cat', 'Sloth', 'Snake', 'PackRat', 'Photographer', 'Spawner']

def classes():
    'Return a list of the names of the clonable mobs'

    return class_names



class Cat(Mob):
    'Miaw!'

    name = 'cat'
    short = 'A frisky little kitty cat.'

    def __init__(self, name='', short='', long=''):
        Mob.__init__(self, name, short, long)
        self.set_action_weights(action_move=1000)

    def look(self, looker):
        'Return a string to send to the player looking at this cat.'

        msgs = Mob.look(self, looker)
        if not self.awake:
            msgs.append('    ' + str(self) + ' is sleeping.... Aww. So cute.')
        return msgs

    def near_say(self, info):
        '''Players can cause the cat to follow by saying "here kitty" or
            stop the cat from following by saying "go away".

        '''

        speaker = info['actor']
        if speaker is not self: # not quite sure how this could be false
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


    def __init__(self, name='', short='', long=''):
        Mob.__init__(self, name, short, long)
        self.set_action_weights(action_move=2000)
        self.period = 1 # second

    def action_reweight(self):
        pass

class PackRat(Mob):
    'Collects things and brings them back to its nest.'

    name_aka = ['rat']

    name = 'packrat'
    short = 'A large scruffy rat. Is it carrying something?'

    def __init__(self, name='', short='', long=''):
        Mob.__init__(self, name, short, long)
        self._path_home = PersistentList()
        self._searching = True
        self._has_dug_home = False
        self.set_action_weights(action_move=2000)
        self.period = 5 # seconds

    def near_drop(self, info):
        dropper = info['actor']
        if dropper is not self:
            if (self._searching and self.room!=self.home
                            and not self.items() and self.awake):
                item = info['item']
                if item in self.room:
                    self.get_item(item, self.room)
                    self._searching = False

                    if not self._has_dug_home:
                        self._dig_home()

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
        exits = filter(self.can_see, origin.exits())
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
        success, msg = self.go(x)
        if success:
            dest = x.destination
            if dest not in self._path_home:
                self._path_home.append(dest)
            else:
                i = self._path_home.index(dest)
                l = len(self._path_home)
                if i+1 < l:
                    for d in range(i+1, l):
                        del self._path_home[-1]

    def _search(self):
        items = filter(self.can_see, self.room.items())
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
        self.drop_item(item)
        self._searching = True


class Photographer(Mob):
    'Wanders around taking pictures'

    name_aka = ['photographer']

    name = 'photographer'
    short = 'A guy with a bag and a camera.'

    def __init__(self, name='', short='', long=''):
        Mob.__init__(self, name, short, long)
        camera = items.Camera()
        self.add(camera)
        bag = items.Bag()
        self.add(bag)
        self.set_action_weights(action_sleep=0,
                                action_awake=0,
                                action_move=400,
                                action_snap=1000)
        self.period = 25 # seconds

    def action_snap(self):
        'Take a picture.'

        camera = self.itemname('camera')
        bag = self.itemname('bag')
        r = self.room
        if r != self.home:
            i = r.items()
            m = r.mobs()
            m.remove(self)
            p = r.players()
            x = r.exits()
            choices = i or m or p or x or [r]
            obj = random.choice(choices)
            photoname = 'photo of %s' % obj.name
            have_one_already = bag.itemname(photoname)

            if have_one_already is None:
                camera.use(self, obj)
                photo = self.itemname(photoname)
                self.remove(photo)
                bag.add(photo)

    def action_drop(self):
        'Drop one of the pictures.'

        bag = self.itemname('bag')
        picnames = bag.itemnames()
        picnames = [n for n in picnames if n.startswith('photo of')]
        if picnames:
            picname = random.choice(picnames)
            pic = bag.itemname(picname)
            bag.remove(pic)
            self.add(pic)
            self.drop_item(pic)

    def near_say(self, info):
        speaker = info['actor']
        if speaker is not self:
            msg = info['raw']
            m = msg.lower()
            if m.startswith('hello'):
                self.room.action(dict(act='say',
                                        verb='respond',
                                        actor=self,
                                        raw='Hi there!'))


class Spawner(Mob):
    '''Periodically creates a mob. Only spawns when there is not a
            mob of that type in the room.

    '''

    name = 'spawner'
    visible = False
    mobtype = str_attr('mobtype', default='Cat')
    settings = ['mobtype']
    period = 600 # 10 minutes

    def __init__(self, name='', short='', long=''):
        Mob.__init__(self, name, short, long)
        self.set_action_weights(action_sleep=0,
                                action_awake=0,
                                action_move=0,)

    def set_mobtype(self, mobtype):
        'Make sure the mobtype exists.'

        if mobtype not in classes():
            raise ValueError, 'Given mob type does not exist.'
            #return False
        else:
            self.mobtype = mobtype
            return True

    def action_spawn(self):
        room = self.room
        mobtype = self.setting('mobtype')
        ms = room.mobs()
        for mob in ms:
            mobcls = class_as_string(mob)
            if mobcls == mobtype:
                return

        import mobs
        spawncls = getattr(mobs, mobtype)
        mob = spawncls()
        mob.home = room
        mob.move(room)
        self.room.action(dict(act='arrive', actor=mob, fromx=None))
