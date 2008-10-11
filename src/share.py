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


'''Base classes and utility functions used by various different
    modules.

Notice that to avoid circular imports, this module imports
    several other modules at the bottom of the file instead
    of at the top. This allows those other modules to import
    this one.

'''


from twisted.internet import reactor

from persistent import Persistent
from persistent.list import PersistentList

import conf
from db import TZODB, TZIndex, tzid
zodb = TZODB()
dbroot = zodb.root
abort = zodb.abort
commit = zodb.commit

tzindex = TZIndex()




class TZObj(Persistent):
    'Base class for all MUD objects.'

    name = 'proto'
    short = ''
    long = ''

    gettable = True
    wearable = False

    def __init__(self, name='', short='', long='', owner=None):
        self.tzid = tzid()

        self.name = name if name else self.name
        self.short = short if short else self.short
        self.long = long if long else self.long

        self.owner = owner
        tzindex.add(self)

    def destroy(self):
        'Get rid of this object and remove it from the main index.'

        tzindex.remove(self)

    def __str__(self):
        return self.name

    def __copy__(self):
        new_item = self.__class__(self.name, self.short, self.long)
        return new_item

    def act_near(self, info):
        '''Something has happened near this object. Handle it if necessary.

        An object which wants to react to a nearby action should define
            a method called near_<action> which accepts the info dict.

        '''

        act = info['act']
        method_name = 'near_%s' % act
        #print 'looking for %s on %s' % (method_name, self.name)
        method = getattr(self, method_name, None)
        if method is not None:
            method(info)

    def look(self, looker):
        '''Return a multiline message (list of strings) for a player looking
            at this object.

        '''

        msgs = []

        if self.short:
            msgs.append('')
            msgs.append(self.short)

        if self.long:
            msgs.append('')
            msgs.append(self.long)

        return msgs

    def info(self):
        '''Return a multiline message (list of strings) with more details
            about this object.

        '''

        return ['%s (%s) %s' % (self.name, self.tzid, self.__class__)]


class TZContainer(TZObj):
    'Base class for all item-containing objects (including characters).'

    def __init__(self, name='', short='', long='', owner=None, items=None):
        TZObj.__init__(self, name, short, long, owner)

        self._item_ids = PersistentList()
        if items is not None:
            for item in items:
                self.add(item)

    def destroy(self):
        'Get rid of this container and every item in it.'

        for item in self.items():
            item.destroy()
        TZObj.destroy(self)

    def __contains__(self, obj):
        'Return True if the given object is in this container.'

        return obj.tzid in self._item_ids

    def items(self):
        'Return a list of the items in this container.'

        return [tzindex.get(iid) for iid in self._item_ids]

    def item(self, iid):
        'Return the item with the give id number if it is in this container.'

        if iid in self._item_ids:
            return tzindex.get(iid)
        else:
            return None

    def itemnames(self):
        'Return a list of the names of the items in this container.'

        return [item.name for item in self.items()]

    def itemname(self, name, all=False):
        '''Return the item with the given name if it is in this container,
            or None if no such item is in this container.

        Since item names are not unique, itemname returns the first item found
            with the given name. Pass in the parameter all=True to get a list
            of all items in this container with the given name instead.

        '''

        result = []
        for item in self.items():
            if item.name == name:
                if not all:
                    return item
                else:
                    result.append(item)

        for item in self.items():
            if hasattr(item, 'name_aka'):
                for aka in item.name_aka:
                    if aka == name:
                        if not all:
                            return item
                        else:
                            result.append(item)

        if result:
            return result
        else:
            return None

    def add(self, item):
        'Put the given item in this container.'

        if item not in self:
            self._item_ids.append(item.tzid)

    def remove(self, item):
        '''Remove the given item from this container, if it is there.

        Does not raise any error if the item is not in this container.

        '''

        if item in self:
            self._item_ids.remove(item.tzid)


class Character(TZContainer):
    'Base class for Player and Mob classes.'

    gettable = False

    def __init__(self, name='', short='', long=''):
        TZContainer.__init__(self, name, short, long)

        self._rid = None
        self._hid = None
        self._follow_id = None

        self._wearing_ids = PersistentList()

        self.awake = True
        self.standing = True

        self.following = None

    def __repr__(self):
        return '''
Character (%s): %s
''' % (self.tzid, self.short)

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
                if self.is_wearing(item):
                    msgs.append('    ' + str(item) + '*')
                else:
                    msgs.append('    ' + str(item))

        return msgs

    def _get_room(self):
        ''''Getter for the room property.

        Character.room is a read-only property to ensure that Characters
            are only moved around using the .move() method. There are only
            a few places that should change a character's room.

        '''
        return rooms.get(self._rid)
    room = property(_get_room)

    def _set_home(self, room):
        'Setter for the home property.'
        if room is not None:
            self._hid = room.tzid
        else:
            self._hid = None
    def _get_home(self):
        'Getter for the home property.'
        return rooms.get(self._hid) or rooms.get(conf.home_id)
    home = property(_get_home, _set_home)

    def _get_following(self):
        '''Getter for the following property.

        The following property indicates which mob or player this character
            is following. If possible, when that character leaves the room,
            this character will follow along.

        '''


        if self._follow_id is None:
            return None
        else:
            player = players.get(self._follow_id)
            mob = mobs.get(self._follow_id)

            if player is not None:
                return player
            elif mob is not None:
                return mob
            else:
                return None
    def _set_following(self, c):
        'Setter for the following property.'
        if c is not None:
            if c == self:
                self._follow_id = None
            else:
                self._follow_id = c.tzid
        else:
            self._follow_id = None
    following = property(_get_following, _set_following)

    def get_item(self, item, room):
        'Get item from room.'

        self.add(item)
        room.remove(item)
        item.get(self)
        room.action(dict(act='get', actor=self, item=item))

    def drop_item(self, item):
        'Drop item from inventory.'

        if self.is_wearing(item):
            self.unwear(item)
            item.unwear(self)
        self.remove(item)
        room = self.room
        room.add(item)
        item.drop(self)
        room.action(dict(act='drop', actor=self, item=item))

    def wear(self, item):
        "Add the given item to this character's list of worn items."

        if not item in self or not item.wearable:
            return
        elif item.tzid in self._wearing_ids:
            return
        else:
            self._wearing_ids.append(item.tzid)
            item.wear(self)
            self.room.action(dict(act='wear', actor=self, item=item))

    def wearing(self):
        'Return a list of the items this character is wearing.'

        return [tzindex.get(tzid) for tzid in self._wearing_ids]

    def is_wearing(self, item):
        'Return True if this character is wearing the given item.'

        if item.tzid in self._wearing_ids:
            return True
        else:
            return False

    def unwear(self, item):
        "Remove the given item from this character's list of worn items."

        if self.is_wearing(item):
            self._wearing_ids.remove(item.tzid)
            item.unwear(self)
            self.room.action(dict(act='unwear', actor=self, item=item))

    # near actions
    def near_leave(self, info):
        'Someone left the room this character is in.'

        leaver = info['actor']
        x = info['tox']
        if self.following==leaver and self.awake:
            reactor.callLater(0, self._follow, leaver, x)

    def _follow(self, leaver, x):
        'Follow along if this character is following someone who left.'

        self.room.action(dict(act='leave', actor=self, tox=x))
        origin = self.room
        try:
            self.move(x.destination)
        except:
            #print 'Character._follow ABORT'
            abort()
        else:
            #print 'Character._follow COMMIT'
            commit()
        backx = None
        for backx in x.destination.exits():
            if backx.destination == origin:
                break
        self.room.action(dict(act='arrive', actor=self, fromx=backx))



def find(r, room, player=None, default=None, all=False):
    '''Utility function for finding an object in various places it
        might be located.

    This function searches for the object given in the parsed result r
        which could have an object name, or an object id number.

    It will return the current room if it matches, or
        an item in the room if it is there, or
        an item the player has if it is there, or
        a player in the room if it is there, or
        a mob in the room it it is there, or
        an exit from the room if it is there,
        in the given order.

    If the object is not found in any of these places, the function
        will return the default object (default defaults to None).

    This function normally returns the first object found which matches,
        but can return all possible matches if the parameter all=True
        is passed in.

    '''

    objname = r.get('objname', '')
    objtzid = r.get('objtzid', '')

    obj = None
    if objname:
        if objname == room.name:
            if not all:
                obj = room
            else:
                obj = [room]
        elif player is not None:
            obj = findname(objname, (room.itemname,
                                        player.itemname,
                                        room.playername,
                                        room.mobname,
                                        room.exitname,), all=all)
        else:
            obj = findname(objname, (room.itemname,
                                        room.playername,
                                        room.mobname,
                                        room.exitname,), all=all)

    elif objtzid:
        if objtzid == room.tzid:
            obj = room
        elif player is not None:
            obj = findtzid(objtzid, (room.item,
                                        player.item,
                                        room.player,
                                        room.mob,
                                        room.exit,))
        else:
            obj = findtzid(objtzid, (room.item,
                                        room.player,
                                        room.mob,
                                        room.exit,))
        if all:
            if obj:
                obj = [obj]
            else:
                obj = []

    else:
        obj = default
        if all:
            if obj:
                obj = [obj]
            else:
                obj = []

    return obj


def findtzid(tzid, searcher):
    '''Return the object with the given id number in the given container, or
        None if the object is not found.

    '''

    for search in searcher:
        found = search(tzid)
        if found is not None:
            return found
    return None

def findname(objname, searchers, all=False):
    '''Return the object with the given name in the given container, or None
        if the object is not found.

    Since names are not necessarily unique, findname will return the first
        object which matches. Pass in the parameter all=True to return a
        list of all possible matches.

    '''

    objs = []
    for search in searchers:
        found = search(objname, all=all)
        if found is not None:
            if not all:
                return found
            else:
                objs.extend(found)
    if objs:
        return objs
    else:
        return None


def class_as_string(obj):
    'Return the class of the given object as a string.'

    cls = obj.__class__
    tostr = str(cls)
    q1 = tostr.find("'")
    q2 = tostr.find("'", q1+1)
    clsstr = tostr[q1+1:q2]
    dot = clsstr.find('.')
    if dot > 0:
        mod, clsstr = clsstr.split('.')
    return clsstr


def upgrade(obj):
    '''Use this function to upgrade objects any time they need
        to change (ie. if it needs to grow a new property.)

    '''

    print 'upgrading', obj.name

    class NonexistentAttr(object):
        pass
    na = NonexistentAttr()

    import types

    updatedname = obj.name+'____updated____'
    updated = obj.__class__(updatedname)
    module = __import__(updated.__module__)

    try:
        module.remove(updated)
    except KeyError:
        pass
    tzindex.remove(updated)

    for attr in dir(updated):
        if attr.startswith('__'):
            pass
            #print '    ignoring'
        elif attr.startswith('_p_'):
            pass
            #print '    ignoring'
        elif attr == 'tzid':
            print '        tzid'
        elif attr == 'name':
            print '        name'
        else:
            oldattr = getattr(obj, attr, na)
            oldattrtype = type(oldattr)
            newattr = getattr(updated, attr, na)
            newattrtype = type(newattr)

            if newattrtype == types.MethodType:
                pass
                #print '    method', attr
            elif oldattr is not na:
                if newattr is None or newattrtype==oldattrtype:
                    print '        copying', attr
                    setattr(updated, attr, oldattr)
                else:
                    print '        ', attr, 'changed type'
            else:
                print '        new attribute', attr

    if module.get(obj.tzid):
        print 'replacing in module index'
        addtomodindex = True
        module.remove(obj)
    else:
        print 'NOT replacing in module index'
        addtomodindex = False
    tzindex.remove(obj)

    updated.tzid = obj.tzid
    updated.name = obj.name

    if addtomodindex:
        module.add(updated)
    tzindex.add(updated)

    commit()


def upgradeall():
    'Upgrade every object in the database.'

    for obj in tzindex.ls():
        upgrade(obj)


# Delay these imports due to circular dependencies
import players
import rooms
import mobs
