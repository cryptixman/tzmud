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
from persistent.dict import PersistentDict

import conf
from db import TZODB, TZIndex, tzid
zodb = TZODB()
dbroot = zodb.root
abort = zodb.abort
commit = zodb.commit

tzindex = TZIndex()




def int_attr(name, default=0):
    'An attribute that will always hold an integer'

    varname = '_%s' % name
    def getter(self, var=varname):
        return getattr(self, var, default)
    def setter(self, val, var=varname):
        val = int(val)
        setattr(self, var, val)
    return property(getter, setter)

def bool_attr(name, default=False):
    'An attribute that will always hold a boolean.'

    varname = '_%s' % name
    def getter(self, var=varname):
        return getattr(self, var, default)
    def setter(self, val, var=varname):
        if val not in (False, True):
            raise ValueError, 'Value must be a boolean.'
        val = bool(val)
        setattr(self, var, val)
    return property(getter, setter)

def str_attr(name, default='', blank_ok=True, setonce=False):
    'An attribute that will always hold a string.'

    varname = '_%s' % name
    def getter(self, var=varname):
        return getattr(self, var, default)
    if not setonce:
        def setter(self, val, var=varname):
            if val=='' and not blank_ok:
                raise ValueError, 'Blank string not allowed.'
            val = str(val)
            setattr(self, var, val)
    else:
        def setter(self, val, var=varname):
            if val=='' and not blank_ok:
                raise ValueError, 'Blank string not allowed.'
            ival = getattr(self, varname, default)
            if not ival:
                val = str(val)
                setattr(self, var, val)
            else:
                raise ValueError, 'Cannot be changed once set.'

    return property(getter, setter)


class TZObj(Persistent):
    'Base class for all MUD objects.'

    name = str_attr('name', default='proto', blank_ok=False)
    short = str_attr('short')
    long = str_attr('long')

    gettable = True
    wearable = False
    visible = bool_attr('visible', default=True)

    def __init__(self, name='', short='', long='', owner=None, container=None):
        self.tzid = tzid()

        self.name = name if name else self.name
        self.short = short if short else self.short
        self.long = long if long else self.long

        self.settings = PersistentList()
        self.settings += ['name', 'short', 'long', 'owner', 'visible']

        self.owner = owner
        self.container = container

        tzindex.add(self)

    def destroy(self):
        'Get rid of this object and remove it from the main index.'

        tzindex.remove(self)

    def __str__(self):
        if self.visible:
            return self.name
        else:
            return '(%s)' % self.name

    def __copy__(self):
        new_item = self.__class__(self.name, self.short, self.long)
        return new_item

    def _set_owner(self, owner):
        'Setter for the owner property.'
        if owner is not None:
            tzid = owner.tzid
            if players.get(tzid) is None and mobs.get(tzid) is None:
                raise ValueError, 'Owner must be a character (player or mob).'
            self._ownerid = owner.tzid
        else:
            self._ownerid = None
    def _get_owner(self):
        'Getter for the owner property.'
        return tzindex.get(self._ownerid)
    owner = property(_get_owner, _set_owner)

    def set_owner(self, iden):
        'iden is the name or the id # for the owner'

        if iden.startswith('#'):
            tzid = iden[1:]
            c = players.get(tzid) or mobs.get(tzid)
        else:
            name = iden
            c = players.getname(name) or mobs.getname(name)

        if c is None:
            return False
        else:
            self.owner = c
            return True

    def _set_container(self, container):
        '''Setter for the container property.

        Should only be None for rooms.

        '''
        if container is not None:
            self._containerid = container.tzid
        else:
            print self.name, 'has no container'
            self._containerid = None
    def _get_container(self):
        'Getter for the container property.'
        return tzindex.get(self._containerid)
    container = property(_get_container, _set_container)

    def setting(self, var, val=None):
        '''return the value of the given setting if val is None.
                returns None if this object does not have that setting.

            If a value is specified, changes the value of the setting.
                returns True if successful, or False otherwise.


            Looks for a variable called var in self.settings and
                only acts if the name is given there.


            Acts on either the value of self.var or the value
                of self._var in that order.

        '''

        uvar = '_%s' % var

        currval = getattr(self, var, None)
        if currval is None:
            currval = getattr(self, uvar, None)

        if val is None:
            # return the value of the setting.

            if var not in self.settings:
                return None

            return currval

        else:
            # change the value of the setting

            if var not in self.settings:
                return False

            if var == 'name' and not val:
                return False

            if val.lower() == 'true':
                val = True
            elif val.lower() == 'false':
                val = False
            else:
                try:
                    val = int(val)
                except ValueError:
                    try:
                        val = float(val)
                    except ValueError:
                        pass

            setter_name = 'set_%s' % var
            setter = getattr(self, setter_name, None)

            if setter is not None:
                if setter(val):
                    return True
                else:
                    return False
            elif hasattr(self, var):
                setattr(self, var, val)
                return True
            elif hasattr(self, uvar):
                setattr(self, uvar, val)
                return True
            else:
                return False


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

        For regular characters (not wizards) just returns the name
            and id of the object, so that it can be selected by id
            if there is more than one object by that name that is
            selectable.

        '''

        return ['%s (%s)' % (self.name, self.tzid)]

    def wizinfo(self):
        '''Return a multiline message (list of strings) with more details
            about this object.

        For wizards, gives the name, id and class of the object.

        '''

        lines = ['%s (%s) %s' % (self.name, self.tzid, class_as_string(self))]
        lines.append('Settings:')
        for var in self.settings:
            lines.append('    %s: %s' % (var, self.setting(var)))
        return lines

    def near_listen(self, info):
        obj = info['obj']
        if obj==self:
            listener = info['actor']
            listener.message("You don't hear anything.")


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

    def act_near(self, info):
        '''Something has happened near this object. Handle it if necessary,
            and pass the action on to any contained items.

        '''

        act = info['act']
        method_name = 'near_%s' % act
        method = getattr(self, method_name, None)
        if method is not None:
            method(info)

        for item in self.items():
            item.act_near(info)

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
                    if item not in result:
                        result.append(item)

        for item in self.items():
            if hasattr(item, 'name_aka'):
                for aka in item.name_aka:
                    if aka == name:
                        if not all:
                            return item
                        else:
                            if item not in result:
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

    def has_inside(self, item):
        '''Check for item in this container, including inside of
            containers in this container.

        '''

        for i in self.items():
            if i is item:
                return True
            if hasattr(i, 'has_inside'):
                return i.has_inside(item)


class Character(TZContainer):
    'Base class for Player and Mob classes.'

    gettable = False

    stats_list = ['health', 'strength', ]
    health = int_attr('health')
    strength = int_attr('strength')

    def __init__(self, name='', short='', long=''):
        TZContainer.__init__(self, name, short, long)

        self._rid = None
        self._hid = None
        self._follow_id = None

        self._set_default_stats()

        self._wearing_ids = PersistentList()

        self.awake = True
        self.standing = True

        self.following = None

    def __repr__(self):
        return '''
Character (%s): %s
''' % (self.tzid, self.short)

    def _set_default_stats(self):
        self._stats0 = PersistentDict()

        self.settings += self.stats_list

        for name in self.stats_list:
            val = 0
            self._stats0[name] = val

    def go(self, x):
        '''Character is trying to go through exit x.

        Passes through the return value from the exit.

        '''

        r = x.go(self)
        success, msg = r
        if success:
            room = x.room
            dest = x.destination
            room.action(dict(act='leave', actor=self, tox=x))
            self.move(dest)

            backx = None
            for backx in dest.exits():
                if backx.destination == room:
                    break
            dest.action(dict(act='arrive', actor=self, fromx=backx))

        return r

    def look_at(self, obj):
        '''This character is looking at the given object.

        returns a list of strings.

        Takes in to account whether the object is visible
            to this character.

        '''

        if self.can_see(obj):
            return obj.look(self)

    def can_see(self, obj):
        '''return True if character can see the given object.
        '''

        if obj is None:
            return False

        if obj.visible or obj is self or wizard.verify(self):
            return True
        else:
            return False

    def look(self, looker):
        '''Return a multiline message (list of strings) for a player looking
            at this character.

        '''

        msgs = TZContainer.look(self, looker)
        iis = filter(looker.can_see, self.items())
        if iis:
            msgs.append('')
            msgs.append('Holding:')
            for item in iis:
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
        'Get item from room. return True if successful, else False.'

        if item.get(self):
            self.add(item)
            room.remove(item)
            room.action(dict(act='get', actor=self, item=item))
            return True
        else:
            return False

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
        if leaver is not self and self.can_see(leaver):
            if self.following==leaver and self.awake:
                reactor.callLater(0, self._follow, leaver, x)

    def _follow(self, leaver, x):
        'Follow along if this character is following someone who left.'

        try:
            self.go(x)
        except:
            #print 'Character._follow ABORT'
            abort()
        else:
            #print 'Character._follow COMMIT'
            commit()



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

    # Some objects create other objects during their
    #   creation. In order to make sure that we get rid
    #   of the unwanted duplicates, set the _upgraded
    #   flag on the updated version. Anything that does
    #   not have this flag will later be deleted.
    #
    # This means that if a new update to an object (the
    #   reason for running the upgrade on the database)
    #   involves the creation of an object that was not
    #   created before, that new addition should be
    #   marked with "_upgraded = True" manually before
    #   running the upgrade, or else it will be deleted.
    updated._upgraded = True


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
            if attr in ['_exit_ids', '_mob_ids', '_item_ids']:
                newattr = None
            newattrtype = type(newattr)

            listtypes = [type([]), type(PersistentList())]
            dicttypes = [type({}), type(PersistentDict())]

            if newattrtype == types.MethodType:
                pass
                #print '    method', attr
            elif newattrtype in listtypes and newattrtype==oldattrtype:
                print '        extending list', attr
                print '        oldattr', oldattr
                print '        newattr', newattr
                for val in oldattr:
                    print '         checking', val
                    if val not in newattr:
                        print '             adding', val
                        newattr.append(val)
            elif newattrtype in dicttypes and newattrtype==oldattrtype:
                print '        extending dict', attr
                for var in oldattr:
                    if var not in newattr:
                        newattr[var] = oldattr[var]
            elif oldattr is not na:
                if newattr is None or newattrtype==oldattrtype:
                    print '        copying', attr
                    try:
                        setattr(updated, attr, oldattr)
                    except AttributeError:
                        print '        ...must be a property.'
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

    for obj in tzindex.ls():
        print 'checking for duplicate', obj.name,
        upgraded = getattr(obj, '_upgraded', False)
        if not upgraded:
            print 'dup'
            tzindex.remove(obj)
            module = __import__(obj.__module__)
            if module.get(obj.tzid):
                module.remove(obj)
        else:
            print 'unique'
            del(obj._upgraded)

    commit()


# Delay these imports due to circular dependencies
import players
import rooms
import mobs
import wizard
