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


from operator import attrgetter, itemgetter
from nevow import tags as T
from nevow import inevow

import players
import rooms
import mobs
import items

from rooms import Room, Exit
from items import Item
from mobs import Mob
from players import Player

from share import module_as_string, class_as_string

from db import TZIndex
tzindex = TZIndex()


from pages_base import TZPage, xmlf

class Rooms(TZPage):
    docFactory = xmlf('rooms.html')
    title = 'Rooms'

    def render_process_rooms(self, ctx, data):
        return 'No processing done.'

    def child_add(self, request):
        return AddRoom()

    def render_rooms(self, ctx, data):
        lines = []
        data.sort(key=attrgetter('tzid'))
        for room in data:
            empty = T.td(_class='empty')['']
            tzid = T.td(_class="tzid")[room.tzid, ':']
            editlink = T.td(_class="text")[T.a(href="/edit/%s" % room.tzid)[room.name]]
            name = T.td(_class="text")[room.name]
            shortline = T.td(_class="text")[room.short]
            longline = T.td(_class="text")[room.long]
            xs = room.exits()
            if not xs:
                rowcls = 'warn'
            else:
                rowcls = 'normal'
            lines.append(T.tr(_class=rowcls)[tzid, editlink])
            if room.short:
                lines.append(T.tr(_class=rowcls)[empty, shortline])
            if room.long:
                lines.append(T.tr(_class=rowcls)[empty, longline])
            if xs:
                for x in xs:
                    dest = x.destination
                    desttzid = getattr(dest, 'tzid', 'None')
                    destname = getattr(dest, 'name', None)
                    xlink = T.a(href="/edit/%s" % x.tzid)[x.name]

                    if dest is not None:
                        roomlink = T.a(href="/edit/%s" % desttzid)[destname]
                    else:
                        roomlink = 'Broken'
                    xd = T.td(_class="text2")[xlink, ' --> ', roomlink, ' (%s)' % desttzid]
                    lines.append(T.tr(_class=rowcls)[empty, xd])

            lines.append(T.tr(_class='normal')[empty, empty])

        return T.table[lines]


class AddRoom(TZPage):
    docFactory = xmlf('process_and_redirect.html')

    def render_process(self, ctx, data):
        request = ctx.locate(inevow.IRequest)

        roomname = ctx.arg('roomname')
        roomclass = ctx.arg('roomclass')

        if roomname and roomclass in rooms.classes():
            cls = getattr(rooms, roomclass)
            newroom = cls(roomname)
            tzid = newroom.tzid
            editpage = '/edit/%s' % tzid
            request.redirect(editpage)
        else:
            self.goback(request, 'Give a name for the room.')
