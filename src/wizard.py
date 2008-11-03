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


def cmd_teleport(s, r=None):
    '''teleport [<room>|<player>] OR teleport <object> to <room>

    Teleport self to the named room or player, or if no name is given
        teleport self to home, OR

    Teleport the object to the room.

    '''

    if s.room is not None:
        s.room.action(dict(act='teleport', actor=s.player))

    destname = r.get('obj2name', '')
    desttzid = r.get('obj2tzid', 0)

    if destname or desttzid:
        destination = rooms.getname(destname) or rooms.get(desttzid)
        if destination is None:
            s.message('No such place.')
            return

        objname = r.get('objname', '')
        objtzid = r.get('objtzid', 0)
        obj = find(r, s.room, s.player, s.room)
        if obj is None:
            s.message('No such object.')
            return
        elif s.room.itemname(objname) or s.room.item(objtzid):
            item = s.room.itemname(objname) or s.room.item(objtzid)
            s.room.remove(item)
            destination.add(item)
            s.room.action(dict(act='teleport_item_away', actor=s.player,
                                item=item))
        elif s.player.itemname(objname) or s.player.item(objtzid):
            item = s.player.itemname(objname) or s.player.item(objtzid)
            s.player.remove(item)
            destination.add(item)
            destination.action(dict(act='teleport_item_in', actor=s.player,
                                item=item))
        elif s.room.playername(objname) or s.room.player(objtzid):
            player = s.room.playername(objname) or s.room.player(objtzid)
            def notify_later():
                s.room.action(dict(act='teleport_character_away', actor=s.player,
                                        character=player))
            def teleport_later(player, destination):
                player.move(destination)
                destination.action(dict(act='teleport_character_in',
                                        actor=s.player,
                                        character=player))
            reactor.callLater(0.2, notify_later)
            reactor.callLater(0.4, teleport_later, player, destination)
        elif s.room.mobname(objname) or s.room.mob(objtzid):
            mob = s.room.mobname(objname) or s.room.mob(objtzid)
            mob.move(destination)
            s.room.action(dict(act='teleport_character_away', actor=s.player,
                                character=mob))
            destination.action(dict(act='teleport_character_in', actor=s.player,
                                character=mob))
        elif s.room.exit(objtzid) or s.room.exitname(objname):
            x = s.room.exit(objtzid) or s.room.exitname(objname)
            s.room.rmexit(x)
            destination.addexit(x)
            s.message('Exit', x, 'moved.')
        else:
            s.message('Cannot teleport the', obj, '.')

    else:
        obj = s.player
        origin = s.player.room
        destname = r.get('objname', '')
        desttzid = r.get('objtzid', 0)

        if not destname and not desttzid:
            destination = s.player.home
        else:
            destination = rooms.getname(destname) or \
                            rooms.get(desttzid)

            if destination is None:
                player = players.getname(destname) or \
                            players.get(desttzid)

                if player is not None:
                    destination = player.room
                    if destination is None:
                        s.message('Player is not logged in.')
                        return
                else:
                    s.message('No such room or player.')
                    return

        if origin is not None:
            origin.action(dict(act='teleport_character_away', actor=s.player,
                                    character=s.player))

        s.player.move(destination)

        s.message(s.room.name)
        destination.action(dict(act='teleport_character_in', actor=s.player,
                                    character=s.player))


def cmd_dig(s, r):
    '''dig <exit> to <destination> [return by <exit>]

    Connect exit to room and optionally from the new room back to here.

    Destination or exits can be existing objects, or if they do not yet
        exist, they will be created.

    '''

    destname = r.get('destname', '')
    desttzid = r.get('desttzid', 0)

    destination = rooms.getname(destname) or rooms.get(desttzid)
    if destination is None and destname:
        destination = rooms.Room(destname)
    elif destination is None:
        s.message('#', desttzid, 'is not a room.')
        return


    exitoutname = r.get('exitoutname', '')
    exitouttzid = r.get('exitouttzid', 0)

    x = s.room.exitname(exitoutname) or s.room.exit(exitouttzid)
    if x is not None:
        x.destination = destination
    elif exitoutname:
        x = rooms.Exit(exitoutname, destination=destination)
        s.room.addexit(x)
    else:
        s.message('#', exitouttzid, 'is not an exit in this room.')


    exitinname = r.get('exitinname', '')
    exitintzid = r.get('exitintzid', 0)

    if exitinname or exitintzid:
        bx = destination.exitname(exitinname) or destination.exit(exitintzid)
        if bx is not None:
            bx.destination = s.room
        elif exitinname:
            bx = rooms.Exit(exitinname, destination=s.room)
            destination.addexit(bx)
        else:
            s.message('#', exitintzid, 'is not an exit.')
            raise TypeError

        # If digging both directions, link the exits
        if bx is not None:
            x.link(bx)


def cmd_lock(s, r):
    '''lock <door> with <key>

    Add the given key to the list of keys that will lock
        the door, and lock the door.

    '''

    objname = r.get('objname', '')
    objtzid = r.get('objtzid', 0)
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
    s.room.action(dict(act='lock', actor=s.player, action='lock', door=x))


def cmd_list(s, r):
    '''list |players|items|rooms|mobs|

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
    newname = r.get('new', '')

    # try to clone an item in the room or on the player
    orig = s.player.itemname(objname) or \
                s.player.item(objtzid) or \
                s.room.itemname(objname) or \
                s.room.item(objtzid) or \
                items.getname(objname) or \
                items.get(objtzid)

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
        return

    # next, try to clone a mob
    orig = s.room.mobname(objname) or \
            s.room.mob(objtzid) or \
            mobs.getname(objname) or \
            mobs.get(objtzid)

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
        return

    # finally, try to clone a room
    orig = rooms.getname(objname) or \
            rooms.get(objtzid)

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
        return

    else:
        name = objname or '#%s' % objtzid
        s.message('No', name, 'to clone.')
        return


def cmd_study(s, r):
    '''study <object>|<object type>

    Learn more information about an object, or one of
        the different types of clonable objects that
        are available.

    See the lists of cloneables using the @list command.

    '''

    objname = r.get('objname', '')
    objtzid = r.get('objtzid', 0)

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

    player = s.player
    room = s.room
    obj = find(r, room, player, room)
    if obj is None:
        objname = r.get('objname', '')
        objtzid = r.get('objtzid', 0)
        obj = rooms.getname(objname) or \
                rooms.get(objtzid) or \
                tzindex.get(objtzid)

    if obj is not None:
        if obj in player:
            player.remove(obj)
        elif obj in room:
            room.remove(obj)
            s.room.action(dict(act='destroy_item', actor=s.player, item=obj))
        elif obj in room.mobs():
            s.room.action(dict(act='destroy_mob', actor=s.player, mob=obj))

        obj.destroy()
        try:
            s.message(class_as_string(obj), obj, 'destroyed.')
        except TypeError:
            s.message('Destroyed.')
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
