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


'''Wizard commands.

Wizards are able to create new objects, destroy objects, change existing
    objects, and move objects around in the MUD.

'''

import copy
import operator

from twisted.internet import reactor

from db import TZODB, TZIndex
dbroot = TZODB().root

import conf

import admin
import players
import rooms
import items
import mobs
import colors

from share import find, class_as_string

import tzprotocol

tzindex = TZIndex()



def verify(player):
    'return True if player is a wizard, False otherwise'

    if player.name in dbroot['wizard']:
        return True
    elif admin.verify(player):
        return True
    else:
        return False


def add(player):
    'Add player to the wizard list.'

    if not verify(player):
        dbroot['wizard'].append(player.name)


def remove(player):
    'Add player to the wizard list.'

    if player.name in dbroot['wizard']:
        dbroot['wizard'].remove(player.name)


def cmd_info(s, r):
    '''info [<item>|<player>|<mob>|<room>|<exit>]

    Get more info about given object or about own player if none given

    '''

    objs = find(r, s.room, s.player, s.player, all=True)

    if objs:
        for obj in objs:
            s.mlmessage(obj.wizinfo())
    else:
        s.message('You do not see that here.')


def cmd_set(s, r):
    '''set <setting> on <object> [to <value>]

    Change the setting on the object. Value defaults to True if
        not specified.

    For a list of available settings, use @info <object>

    '''

    obj = find(r, s.room, s.player, s.room)
    if obj is None:
        s.message('You do not see that here.')
        return

    setting = r['setting']
    value = r.get('value', "True")

    try:
        success = obj.setting(setting, value)
    except ValueError, e:
        s.message('Error:', e)
    else:
        if success:
            value = obj.setting(setting)
            s.message('Set', setting, 'to', value, '.')
        else:
            s.message('Cannot set', setting, 'on', obj, '.')

def cmd_unset(s, r):
    '''unset <setting> on <object>

    Change the setting on the object to False.

    For a list of available settings, use @info <object>

    '''

    obj = find(r, s.room, s.player, s.room)
    if obj is None:
        s.message('You do not see that here.')
        return

    setting = r['setting']

    val = obj.setting(setting)
    if val in (True, False):
        value = 'False'
    else:
        value = ''

    try:
        success = obj.setting(setting, value)
    except ValueError, e:
        s.message('Error:', e)
    else:
        if success:
            s.message('Unset', setting, '.')
        else:
            s.message('Cannot unset', setting, 'on', obj, '.')


def cmd_teleport(s, r=None):
    '''teleport [to [<room>|<player>]] OR teleport <object> to <room>

    Teleport self to the named room or player, or if no name is given
        teleport self to home, OR

    Teleport the object to the room.

    '''

    room = s.room
    player = s.player
    if room is not None:
        room.action(dict(act='teleport', actor=player))

    objname = r.get('objname', '')
    objtzid = r.get('objtzid', 0)

    destname = r.get('obj2name', '')
    desttzid = r.get('obj2tzid', 0)

    if (objname or objtzid) and (destname or desttzid):
        destination = rooms.getname(destname) or rooms.get(desttzid)
        if destination is None:
            s.message('No such place.')
            return

        obj = find(r, room, player, room) or \
                players.getname(objname) or players.get(objtzid) or \
                mobs.getname(objname) or mobs.get(objtzid) or \
                tzindex.get(objtzid)
        if obj is None:
            s.message('No such object.')
        elif obj._bse == 'Room':
            s.message('You cannot teleport a room.')
        else:
            obj.teleport(destination)
            s.message('You teleport', obj, '.')

    elif not (destname or desttzid):
        # send the player home
        player.teleport()

    else:
        destination = rooms.getname(destname) or \
                        rooms.get(desttzid)

        if destination is None:
            toplayer = players.getname(destname) or \
                        players.get(desttzid)

            if toplayer is not None:
                destination = toplayer.room
                if destination is None:
                    s.message('Player is not logged in.')
                    return
            else:
                s.message('No such room or player.')
                return

        player.teleport(destination)


def cmd_summon(s, r):
    '''summon <character>|<mob class>

    If the name or id# given is an existing player or mob, this
        will act like: teleport <character> to <here>.

    If the name does not exist already, but is a mob class, this
        will be like: clone <mobclass>.

    '''

    room = s.room
    objname = r.get('objname', '')
    objtzid = r.get('objtzid', 0)

    char = players.getname(objname) or players.get(objtzid) or \
                mobs.getname(objname) or mobs.get(objtzid)

    if char is not None:
        char.teleport(room)
        s.message('You summon', char, '.')

    elif objname in mobs.classes():
        mob = _clone_mob(s, objname, objtzid)
        s.message('You summon', mob, '.')

    else:
        iden = objname if objname else '#%s' % objtzid
        s.message('Unable to summon', iden, '.')

def cmd_dig(s, r):
    '''dig <exit> to <destination> [return by <exit>]

    Connect exit to room and optionally from the new room back to here.

    Destination or exits can be existing objects, or if they do not
        yet exist, they will be created.

    If the exit out name is one of the compass directions (ie north,
        south, east, northeast, etc) and no return by exit name is
        given, the return by exit will be created automatically with
        the opposite direction name. (eg. if an exit out is dug to
        the west, an exit in will also be added to the east from
        the destination.)

    '''

    room = s.room

    destname = r.get('destname', '')
    desttzid = r.get('desttzid', 0)
    if not destname and not desttzid:
        raise SyntaxError, 'Command used improperly.'
    destination = rooms.getname(destname) or rooms.get(desttzid)

    if destination is None and destname:
        destination = rooms.Room(destname)
        s.message(destination, 'created.')
    elif destination is None:
        s.message('#', desttzid, 'is not a room.')
        return

    exitoutname = r.get('exitoutname', '')
    exitouttzid = r.get('exitouttzid', 0)
    xo = room.exitname(exitoutname) or room.exit(exitouttzid)

    exitinname = r.get('exitinname', '')
    exitintzid = r.get('exitintzid', 0)
    if not exitinname and not exitintzid:
        autoreturnby = {'north': 'south',
                        'south': 'north',
                        'east': 'west',
                        'west': 'east',
                        'northeast': 'southwest',
                        'northwest': 'southeast',
                        'southeast': 'northwest',
                        'southwest': 'northeast',}
        if exitoutname in autoreturnby:
            exitinname = autoreturnby[exitoutname]
        else:
            exitinname = 'door'

    xi = destination.exitname(exitinname) or destination.exit(exitintzid)
    if xi is not None:
        exitinname = xi.name

    if xo is not None:
        xo.destination = destination
        if xi is not None:
            xi.destination = room
        else:
            xi = rooms.Exit(exitinname, room=destination, destination=room)
            xo.link(xi)
            destination.action(dict(act='dig', actor=None, exit=xi))
        s.message('You reconnect', xo, 'to', destination, '.')

    elif exitoutname:
        if exitinname or xi is None:
            xo = rooms.Exit(exitoutname, room=room, destination=destination, return_name=exitinname)
            room.action(dict(act='dig', actor=s.player, exit=xo))
            xi = xo.get_linked_exit()
            destination.action(dict(act='dig', actor=None, exit=xi))
            s.message('You dig', xo, 'to', destination, '.')
        else:
            s.message('#', exitintzid, 'is not an exit in', destination, '.')
            raise TypeError

    else:
        s.message('#', exitouttzid, 'is not an exit in this room.')


def cmd_lock(s, r):
    '''lock <door> with <key>

    Add the given key to the list of keys that will lock
        the door, and lock the door.

    '''

    objname = r.get('objname', '')
    objtzid = r.get('objtzid', 0)
    if not objname and not objtzid:
        raise SyntaxError, 'Command used improperly.'
    x = s.room.exitname(objname) or s.room.exit(objtzid)
    if x is None:
        s.message('No such exit.')
        return

    keyname = r.get('obj2name', '')
    keytzid = r.get('obj2tzid', 0)

    key = s.player.itemname(keyname) or s.player.item(keytzid)
    if key is None:
        s.message('You do not have such a key.')
        return

    x.add_key(key)
    x.lock(key)
    s.message('You make the door', x, 'lockable with key', key, '.')
    s.room.action(dict(act='lock', actor=s.player, door=x, key=key))


def cmd_list(s, r):
    '''list |players|items|rooms|mobs|exits|

    List all objects of the given type.

    '''

    listing = r['type']

    if listing == 'players':
        objs = players.ls()
        classes = []
    elif listing == 'items':
        objs = items.ls()
        classes = items.classes()
    elif listing == 'rooms':
        objs = rooms.ls()
        classes = rooms.classes()
    elif listing == 'mobs':
        objs = mobs.ls()
        classes = mobs.classes()
    elif listing == 'exits':
        objs = rooms.ls_exits()
        classes = rooms.exit_classes()
    print 'info objs', objs
    if objs:
        s.message('Existing objects:')
        objs.sort(key=operator.attrgetter('tzid'))
        msgs = []
        for obj in objs:
            tzid = '(%s)' % obj.tzid
            msgs.append('%s %s' % (tzid.rjust(4, ' '), obj))
        s.mlmessage(msgs, indent=4)
    else:
        s.message('No', listing, 'yet.')

    if classes:
        classes = list(classes)
        classes.sort()
        if objs:
            s.message()
        s.message('Cloneable:')
        s.columns_v(classes, color=colors.white)


def cmd_clone(s, r):
    '''clone <object> [as <name for new clone>]

    Create an instance of the given object, or create a new
        kind of object based on the given one.

    '''

    objname = r.get('objname', '')
    objtzid = r.get('objtzid', 0)

    if not objname and not objtzid:
        raise SyntaxError, 'Command used improperly.'

    newname = r.get('new', '')

    for cloner in (_clone_item, _clone_mob, _clone_room, _clone_exit):
        if cloner(s, objname, objtzid, newname):
            return

    name = objname or '#%s' % objtzid
    s.message('No', name, 'to clone.')

def _clone_item(s, objname, objtzid, newname=''):
    # first try to clone an item
    # look first in the room or on the player
    # then at existing item objects
    orig = s.player.itemname(objname) or \
                s.player.item(objtzid) or \
                s.room.itemname(objname) or \
                s.room.item(objtzid) or \
                items.getname(objname) or \
                items.get(objtzid)

    # if it is not there, it might be an item class
    if orig is None:
        if objname in items.classes():
            cls = getattr(items, objname)
            obj = cls()
        else:
            obj = None
    else:
        obj = copy.copy(orig)

    if obj:
        if newname:
            obj.name = newname
        s.message(obj, 'created.')
        s.player.add(obj)
        s.room.action(dict(act='clone_item', actor=s.player, item=obj))
        return obj

def _clone_mob(s, objname, objtzid, newname=''):
    # next, try to clone a mob
    # look first in the room
    # then at existing mobs
    orig = s.room.mobname(objname) or \
            s.room.mob(objtzid) or \
            mobs.getname(objname) or \
            mobs.get(objtzid)

    # if it is not there, it might be a mob class
    if orig is None:
        if objname in mobs.classes():
            cls = getattr(mobs, objname)
            obj = cls()
        else:
            obj = None
    else:
        obj = copy.copy(orig)

    if obj:
        if newname:
            obj.name = newname
        s.message(obj, 'created.')
        obj.move(s.room)
        obj.home = s.room
        s.room.action(dict(act='clone_mob', actor=s.player, mob=obj))
        return obj

def _clone_room(s, objname, objtzid, newname=''):
    # next, try to clone a room
    # first look at existing rooms
    orig = rooms.getname(objname) or \
            rooms.get(objtzid)

    # if it is not there, it might be a Room class
    if orig is None:
        if objname in rooms.classes():
            cls = getattr(rooms, objname)
            obj = cls()
        else:
            obj = None
    else:
        obj = copy.copy(orig)

    if obj:
        if newname:
            obj.name = newname
        s.message(obj, 'created.')
        return obj

def _clone_exit(s, objname, objtzid, newname=''):
    # Finally, try to clone an Exit
    # fist look at existing exits in this room
    orig = s.room.exitname(objname) or \
            s.room.exit(objtzid)

    # if it is not there, it might be an Exit class
    if orig is None:
        if objname in rooms.exit_classes():
            cls = getattr(rooms, objname)
            obj = cls()
        else:
            obj = None
    else:
        obj = copy.copy(orig)

    if obj:
        if newname:
            obj.name = newname
        s.room.addexit(obj)
        s.message(obj, 'created.')
        s.room.action(dict(act='clone_exit', actor=s.player, x=obj))
        return obj


def cmd_study(s, r):
    '''study <object>|<object type>

    Learn more information about an object, or one of
        the different types of clonable objects that
        are available.

    See the lists of cloneables using the @list command.

    '''

    objname = r.get('objname', '')
    objtzid = r.get('objtzid', 0)
    if not objname and not objtzid:
        raise SyntaxError, 'Command used improperly.'

    obj = find(r, s.room, s.player, s.room)
    if obj is not None:
        doc = obj.__doc__
        name = class_as_string(obj)
        found = obj
    else:
        found = False
        for mod in items, mobs, rooms:
            for name in mod.classes():
                if objname == name:
                    found = name
                    cls = getattr(mod, name)
                    doc = cls.__doc__

        if not found:
            s.message('No such thing to study.')
            return

    if doc is None:
        doc = '... but it is still a mystery'

    name = colors.white(name)
    s.message('You study the', found)
    msgs = doc.split('\n')
    s.mlmessage(msgs, indent=4)


def cmd_rename(s, r):
    '''rename [<object>] to <new name>

    Set the name for the given object
        or for the current room if no object given.

    '''

    obj = find(r, s.room, s.player, s.room)
    newname = r['new']

    if obj is not None:
        oldname = obj.name
        obj.name = newname
        s.message(oldname, 'renamed to', newname, '.')

    else:
        s.message('No such object to rename.')


def cmd_short(s, r):
    '''short [for] [<object>] is <text>

    Set the short description for the given object
        or for the current room if no object given.

    '''

    obj = find(r, s.room, s.player, s.room)
    newshort = r['new']

    if obj is not None:
        obj.short = newshort
        s.message('Short description set on', obj, '.')

    else:
        s.message('No such object to rename.')


def cmd_long(s, r):
    '''long [for] [<object>] is <text>

    Set the long description for the given object
        or for the current room if no object given.

    '''

    obj = find(r, s.room, s.player, s.room)
    newlong = r['new']

    if obj is not None:
        obj.long = newlong
        s.message('Long description set on', obj, '.')

    else:
        s.message('No such object to rename.')


def cmd_destroy(s, r):
    '''destroy <object>

    Destroy the specified object.

    '''

    objname = r.get('objname', '')
    objtzid = r.get('objtzid', 0)
    if not objname and not objtzid:
        raise SyntaxError, 'Command used improperly.'

    player = s.player
    room = s.room
    obj = find(r, room, player)
    if obj is None:
        obj = rooms.getname(objname) or \
                rooms.get(objtzid) or \
                tzindex.get(objtzid)

    if obj is not None:
        s.message('You speak a word of power and ...')
        s.room.action(dict(act="destroy", actor=player))
        obj.destroy()

    else:
        s.message('Object not found.')


def cmd_help(s, r=None):
    '''help [<subject>]

    Get help on some <subject> or general help if no subject given.

    '''

    topic = r.get('topic', None)

    import wizard
    if topic is None:
        s.message('Available wizard commands:')
        commands = []
        for func in dir(wizard):
            if func.startswith('cmd_'):
                #s.message(func[4:], indent=4)
                commands.append(func[4:])
        commands.sort()
        s.columns_v(commands)
    else:
        func_name = 'cmd_%s' % topic
        func = getattr(wizard, func_name, None)
        if func is not None:
            doc = func.__doc__
            if doc is not None:
                msg = 'Help on %s:' % topic
                s.message(msg)
                s.message()
                msg = doc.split('\n')
                msg.insert(0, 'Syntax:')
                msg[1] = '        @' + msg[1]
                s.mlmessage(msg)
                return

        msg = 'Sorry. No wizard help available on that subject.'
        s.message(msg)
