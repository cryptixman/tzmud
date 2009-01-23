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


'''Most objects that can be found inside the MUD.

Items are generally gettable, and are sometimes wearable. Some
    items are also containers, which means that they can hold other
    items inside them.

'''

import time

from twisted.internet import reactor

from persistent.list import PersistentList

from db import TZODB, TZIndex
dbroot = TZODB().root

from share import TZObj, TZContainer
from share import register_plugin

import wizard
import players
import mobs
from colors import green


def get(iid):
    'Return the item with the given id number.'

    return dbroot['items'].get(iid, None)

def add(item):
    'Add the given item to the database.'

    dbroot['items'][item.tzid] = item

def remove(item):
    'Remove the given item from the database.'

    del dbroot['items'][item.tzid]

def getname(name, all=False):
    '''Return the item with the given name.

    Since object names are not necessarily unique, getname will by
        default return the first item with the given name. To instead
        get a list of all the items with the given name, pass the
        parameter all=True.

    '''

    result = []
    for item in ls():
        if item.name == name:
            if not all:
                return item
            else:
                result.append(item)

    if all:
        return result
    else:
        return None

def ls():
    'Return a list of all the items in the database.'

    return dbroot['items'].values()

def names():
    '''Return a list of the names of all the items in the database.

    Since object names are not necessarily unique, names may return
        a particular name more than once.

    '''

    return [item.name for item in dbroot['items'].values()]

def isitem(obj):
    return obj in ls()



class Item(TZObj):
    'Base class for all items in the MUD.'

    name = 'proto item'
    _bse = 'Item'

    def __init__(self, name='', short='', long='', owner=None):
        'Initialize this item, and add it to the item index.'

        TZObj.__init__(self, name, short, long, owner)
        add(self)

    def destroy(self):
        'Get rid of this item and remove it from the index.'

        container = self.container
        room = self.room

        if container is not None:
            container.remove(self)

        remove(self)
        TZObj.destroy(self)

        if room is not None:
            room.action(dict(act='destroy_item', actor=None, item=self))

    def get(self, character):
        'Character has picked up this item. return True if successful, else False'
        return True

    def drop(self, character):
        'Character has dropped this item. return True if successful, else False'
        return True

    def put(self, character, container):
        'Character has put this item in container.'
        pass

    def take(self, character, container):
        'Character has taken this item from container.'
        pass

    def wear(self, character):
        'Character has put on this item.'
        return True

    def unwear(self, character):
        'Character has taken off this item.'
        return True

    def wearer(self):
        'return the character wearing this item, or None if no one is.'

        if not self.wearable:
            return None

        for container in self.containers():
            try:
                wearing = container.is_wearing(self)
            except AttributeError:
                pass

            if wearing:
                return container

        return None

    def teleport(self, destination):
        'Teleport this item to room.'

        room = self.room
        container = self.container

        room.action(dict(act='teleport_item_away',
                            actor=None,
                            item=self,
                            container=container))
        container.remove(self)
        destination.add(self)
        destination.action(dict(act='teleport_item_in',
                                    delay=0.4,
                                    actor=None,
                                    item=self))


    def __str__(self):
        'Returns the colorized name of this item.'

        name = TZObj.__str__(self)
        return green(name)

    def __repr__(self):
        return '''\
Item (%s): %s
    %s
    %s
''' % (self.tzid, self.name, self.short, self.long)


class ContainerItem(Item, TZContainer):
    'Base class for all items that can contain other items.'

    name = 'container'

    def __init__(self, name='', short='', long='', owner=None):
        TZContainer.__init__(self, name, short, long, owner)
        add(self)

        self._bse = 'Item'

    def destroy(self):
        'Get rid of this item and remove it from the index.'

        container = self.container
        room = self.room

        if container is not None:
            container.remove(self)

        remove(self)
        TZContainer.destroy(self)

        if room is not None:
            room.action(dict(act='destroy_item', actor=None, item=self))

    def look(self, looker):
        '''Return a multiline message (list of strings) for a player looking
            at this character.

        '''

        msgs = TZContainer.look(self, looker)
        items = self.items()
        if items:
            msgs.append('')
            msgs.append('Holding:')
            for item in items:
                msgs.append('    ' + str(item))

        return msgs

    def __repr__(self):
        return '''\
Item (%s): %s
    %s
    %s
    Holding:
        %s
''' % (self.tzid, self.name, self.short, self.long,
            [item for item in self.items()])




class Rose(Item):
    'A simple flower item.'

    name = 'rose'
    short = 'A red rose.'
    name_aka = ['flower']

class Cup(ContainerItem):
    'A cup which should be able to hold some other small items.'

    name = 'cup'
    short = 'A small red plastic cup.'


class Bag(ContainerItem):
    'A possibly magical bag which can hold other items.'

    name = 'bag'
    short = 'A surprisingly spacious sack.'


class Mirror(Item):
    'An object for looking at yourself and maybe other things too.'

    name = 'mirror'
    short = 'A round silver mirror.'

    def near_look(self, info):
        looker = info['actor']
        lookee = info['actee']
        if lookee == self:
            looker.message('In the mirror you see ...')
            looker.mlmessage(looker.look(looker))

class WizRing(Item):
    'A ring which makes the wearer a wizard.'

    name = 'gold ring'
    short = 'A plain band of gold.'
    wearable = True
    name_aka = ['ring', 'precious']

    def wear(self, character):
        wizard.add(character)
        return True

    def unwear(self, character):
        wizard.remove(character)
        return True

class InvRing(Item):
    'A ring which makes the wearer invisible.'

    name = 'silver ring'
    short = 'A thin band of silver.'
    wearable = True
    name_aka = ['ring',]

    def _set_visible(self, character, vis):
        '''Set the visibility of the character.

        Need to do this later on, so that others in the room will see
            this player put the ring on and disappear, or see this
            player appear but not see him remove the ring.

        '''

        character.setting('visible', vis)

    def wear(self, character):
        reactor.callLater(0.4, self._set_visible, character, False)
        return True

    def unwear(self, character):
        reactor.callLater(0.4, self._set_visible, character, True)
        return True

class CursedItem(Item):
    'A wearable item which cannot be removed once worn'

    name = 'accursed'
    short = "You just can't seem to remove it."
    wearable = True

    def unwear(self, character):
        return False

class DetectInvisRing(Item):
    'A ring which allows the wearer to detect invisible objects.'


    name = 'pearl ring'
    short = 'A ring set with a large pearl.'
    wearable = True
    name_aka = ['ring',]
    _wearerid = None

    def near_look(self, info):
        wearer = self.wearer()
        looker = info['actor']
        obj = info['actee']
        if looker is wearer:
            room = wearer.room

            if obj is room:
                found = False
                for item in room.items():
                    if not item.visible:
                        found = True
                        break
                if found:
                    wearer.message('There is something invisible here.')

                found = False
                for c in room.players() + room.mobs():
                    if c is not wearer and not c.visible:
                        found = True
                        break
                if found:
                    wearer.message('There is someone invisible here.')

    def near_arrive(self, info):
        wearer = players.get(self._wearerid) or mobs.get(self._wearerid)
        if wearer is not None:
            arriver = info['actor']
            if arriver is wearer:
                self.near_look(info)

            else:
                if not arriver.visible:
                    wearer.message('Someone invisible just arrived.')

class Key(Item):
    'An item for locking/ unlocking doors, and maybe other lockable things.'

    name = 'key'
    short = 'A large steel key.'
    name_aka = ['key']

    def __init__(self, name='', short='', long=''):
        Item.__init__(self, name, short, long)
        self._key = hash(self.tzid)

    def locks(self, door):
        return self._key in door._keys

    def __copy__(self):
        new_key = Key(self.name, self.short, self.long)
        new_key._key = self._key
        return new_key


class SkeletonKey(Key):
    'A key which opens any door.'

    name = 'skeleton key'
    short = 'Looks like it may unlock just about anything.'
    name_aka = ['key']

    def locks(self, door):
        return True


class Coin(Item):
    'One or more coins.'

    name = 'coins'
    short = 'Some coins.'
    _n_coins = 1
    name_aka = ['coin', 'coins']

    def _get_name(self):
        n = self._n_coins
        if n>1 or n==0:
            return '%s coins' % self._n_coins
        else:
            return '1 coin'
    def _set_name(self, unused):
        pass
    name = property(_get_name, _set_name)

    def _set_n_coins(self, n):
        self._n_coins = n

    def add_coins(self, n):
        self._n_coins += n

    def remove_coins(self, n):
        if n <= self._n_coins:
            self._n_coins -= n
        else:
            raise ValueError

    def split(self, n):
        'Remove n from self, and return new object like self with n.'

        if n > self._n_coins:
            raise ValueError
        elif n == self._n_coins:
            return self
        else:
            self.remove_coins(n)
            coins = Coins()
            coins._set_n_coins(n)
            return coins

    def get(self, character):
        other_coins = character.itemname('coins')
        if other_coins is not None and other_coins is not self:
            self.add_coins(other_coins._n_coins)
            character.remove(other_coins)
            other_coins.destroy()

        return True

    def put(self, character, container):
        other_coins = container.itemname('coins')
        if other_coins is not None and other_coins is not self:
            self.add_coins(other_coins._n_coins)
            container.remove(other_coins)
            other_coins.destroy()


class Hat(Item):
    'Headgear'

    name = 'hat'
    short = 'An old top hat.'
    wearable = True


class Camera(Item):
    'Take snapshots of items, rooms, characters.'

    name = 'camera'
    short = 'A small black box with a silver button on top.'

    def use(self, actor, obj):
        'actor uses the camera to take picture of obj.'

        if obj is None:
            obj = actor.room

        msgs = obj.look(actor)
        msgs = ['    '+line for line in msgs]
        msgs.insert(0, 'The picture is of ' + obj.name + '.')
        picture = '\n'.join(msgs)

        photo = Photograph()
        photo.name = 'photo of %s' % obj.name
        photo.long = picture

        actor.message('That looks like a good one...')
        actor.message('You have a photo of', obj.name, '.')
        actor.add(photo)

        actor.room.action(dict(act='use',
                                custom='%(actor)s snaps a picture of %(target)s.',
                                actor=actor, item=self, target=obj))


class Photograph(Item):
    'A snapshot of some object.'

    name = 'photo'
    name_aka = ['photo', 'photograph', 'picture']
    short = 'A glossy piece of paper with a realistic picture on it.'
    long = "It's blank."


class LeadBox(ContainerItem):
    'Container which prevents nearby actions from affecting its contents'

    name = 'lead box'
    name_aka = ['box']

    def act_near(self, info):
        TZObj.act_near(self, info)

class Trap(Item):
    '''A surprise for the character holding this item,
        or for nearby characters.

    '''

    def activate(self):
        self.spring()

    def spring(self):
        container = self.container
        room = self.room
        import share
        if container == room:
            for c in room.mobs():
                c.message('Gotcha!')
            for p in room.players():
                p.message('Gotcha!')
        elif isinstance(container, share.Character):
            container.message('Gotcha!')

class GetTrap(Trap):
    'getting this item springs the trap.'

    name = 'gettrap'
    short = 'Hey! That is an interesting looking thing....'

    def get(self, character):
        self.activate()
        return True

class TimeTrap(Trap):
    'Trap which springs a set time after it is activated.'

    name = 'timetrap'
    delay = 2 # seconds
    settings = ['delay']

    def activate(self):
        delay = self.setting('delay')
        reactor.callLater(delay, self.spring)

class GetTimeTrap(TimeTrap, GetTrap):
    'TimeTrap activated by getting it.'

    name = 'gettimetrap'

class VoiceTrap(Trap):
    'Trap activated by voice command.'

    name = 'voicetrap'
    command = 'activate'
    settings = ['command']

    def near_say(self, info):
        c = info['actor']
        msg = info['raw']
        m = msg.lower()
        if m == self.command:
            self.activate()

class VoiceTimeTrap(TimeTrap, VoiceTrap):
    'TimeTrap activated by voice command.'

    name = 'voice timetrap'


class TreasureChest(ContainerItem):
    'A chest with one of each Item inside'

    name = 'treasure chest'
    name_aka = ['chest',]

    def __init__(self, name=''):
        ContainerItem.__init__(self, name)

        for clsname in classes():
            if clsname == 'TreasureChest':
                continue

            import items
            cls = getattr(items, clsname)
            i = cls()
            self.add(i)




class_names = ['Item', 'ContainerItem', 'Rose', 'Cup', 'Bag', 'Mirror', 'WizRing', 'Key', 'SkeletonKey', 'Coin', 'Hat', 'Camera', 'Photograph', 'InvRing', 'GetTrap', 'GetTimeTrap', 'DetectInvisRing', 'LeadBox', 'VoiceTrap', 'VoiceTimeTrap', 'TreasureChest', 'CursedItem']

def classes():
    'Returns a list of the names of the clonable items.'

    return class_names
