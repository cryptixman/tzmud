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


from operator import attrgetter

from nevow import loaders, rend
from nevow import static
from nevow import tags as T
from nevow.entities import nbsp

from twisted.python.rebuild import rebuild

import players
import rooms


class xmlf(loaders.xmlfile):
    templateDir = 'var/www/templates'

class TZPage(rend.Page):
    addSlash = True
    title = 'Not Set'

    def child_styles(self, request):
        return static.File('var/www/styles')

    def render_head(self, context, data):
        return xmlf('head.html')

    def render_title(self, context, data):
        context.fillSlots('title', self.title)
        return context.tag

    def render_scripts(self, context, data):
        return context.tag

    def render_header(self, context, data):
        return xmlf('header.html')

    def render_footer(self, context, data):
        return xmlf('footer.html')

    def child_rebuild(self, request):
        import pages
        rebuild(pages)
        return self

class Index(TZPage):
    docFactory = xmlf('index.html')
    title = 'TZMud Web Interace'

    def data_trial(self, ctx, data):
        print 'test', ctx, data
        return "TEST!"

    def data_players(self, ctx, data):
        p = players.ls()
        p.sort(key=attrgetter('name'))
        return p

    def render_players(self, ctx, data):
        lines = []
        for player in data:
            name = player.name
            if player.logged_in:
                room = player.room.name
                name += ' [%s]' % room
            lines.append(T.li[name])
        return T.ul[lines]

    def data_rooms(self, ctx, data):
        r = rooms.ls()
        r.sort(key=attrgetter('name'))
        return r

    def render_rooms(self, ctx, data):
        lines = []
        for room in data:
            tzid = T.td(_class="roomtzid")[room.tzid, ':']
            name = T.td(_class="roomname")[room.name]
            lines.append(T.tr[tzid, name])

        return T.table[lines]
