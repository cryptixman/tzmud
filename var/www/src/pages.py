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

from nevow import loaders, rend
from nevow import static
from nevow import tags as T
from nevow.entities import nbsp

from twisted.python.rebuild import rebuild

import players
import rooms
import mobs

from rooms import Room, Exit
from items import Item
from mobs import Mob
from players import Player

from share import module_as_string, class_as_string

from db import TZIndex
tzindex = TZIndex()


class xmlf(loaders.xmlfile):
    templateDir = 'var/www/templates'

class TZPage(rend.Page):
    addSlash = True
    title = 'Not Set'

    def child_styles(self, request):
        return static.File('var/www/styles')

    def child_rooms(self, request):
        return Rooms()

    def child_edit(self, request):
        return Edit()

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

    def data_players(self, ctx, data):
        p = players.ls()
        #p.sort(key=attrgetter('name'))
        return p

    def data_rooms(self, ctx, data):
        r = rooms.ls()
        #r.sort(key=attrgetter('name'))
        return r

class Index(TZPage):
    docFactory = xmlf('index.html')
    title = 'TZMud Web Interace'

    def data_trial(self, ctx, data):
        print 'test', ctx, data
        return "TEST!"

    def render_process_index(self, ctx, data):
        roomname = ctx.arg('roomname')
        if roomname:
            newroom = rooms.Room(roomname)
        return 'Processing'

    def render_index_players(self, ctx, data):
        lines = []
        for player in data:
            name = player.name
            if player.logged_in:
                room = player.room.name
                name += ' [%s]' % room
            lines.append(T.li[name])
        return T.ul[lines]

    def render_index_rooms(self, ctx, data):
        lines = []
        data.sort(key=attrgetter('name'))
        for room in data:
            tzid = T.td(_class="roomtzid")[room.tzid, ':']
            name = T.td(_class="roomname")[room.name]
            if not room.exits():
                row = T.tr(_class='warn')
            else:
                row = T.tr
            lines.append(row[tzid, name])

        return T.table[lines]

    def render_idtable(self, ctx, data):
        lines = []
        for obj in data:
            tzid = T.td(_class="objtzid")[obj.tzid, ':']
            name = T.td(_class="objname")[obj.name]
            lines.append(T.tr[tzid, name])
        return T.table[lines]

    def render_idtable_sortalpha(self, ctx, data):
        data.sort(key=attrgetter('name'))
        return self.render_idtable(ctx, data)

    def render_idtable_sortid(self, ctx, data):
        data.sort(key=attrgetter('tzid'))
        return self.render_idtable(ctx, data)


class Rooms(TZPage):
    docFactory = xmlf('rooms.html')
    title = 'Rooms'

    def render_process_rooms(self, ctx, data):
        return 'No processing done.'

    def render_rooms(self, ctx, data):
        lines = []
        data.sort(key=attrgetter('tzid'))
        for room in data:
            empty = T.td()['']
            tzid = T.td(_class="tzid")[room.tzid, ':']
            editlink = T.td(_class="text")[T.a(href="/edit/%s" % room.tzid)[room.name]]
            name = T.td(_class="text")[room.name]
            shortline = T.td(_class="text")[room.short]
            longline = T.td(_class="text")[room.long]
            exits = room.exits()
            if not exits:
                row = T.tr(_class='warn')
            else:
                row = T.tr
            lines.append(row[tzid, editlink])
            if room.short:
                lines.append(row[empty, shortline])
            if room.long:
                lines.append(row[empty, longline])
            if exits:
                xlines = []
                for x in exits:
                    xinfo = '%s --> %s (%s)' % (x.name,
                                                     x.destination.name,
                                                     x.destination.tzid)
                    xline = (xinfo, T.br)
                    xlines.append(xline)
                xd = T.td(_class="text2")[xlines]
                lines.append(row[empty, xd])

        return T.table[lines]


class Edit(TZPage):
    docFactory = xmlf('edit.html')
    title = 'Edit Object'

    def locateChild(self, context, segments):
        #print 'seg', context, segments
        tzid = int(segments[0])
        obj = tzindex.get(tzid)
        self.obj = obj
        bases = [Room, Exit, Item, Mob, Player]
        for base in bases:
            if issubclass(obj.__class__, base):
                self.base = base
                break
        self.cls = class_as_string(obj)
        self.bse = class_as_string(base, instance=False)
        #print 'module:', module_as_string(obj)
        #print 'class:', class_as_string(obj)
        #print 'base:', self.base
        return self, ()

    def form_options(self, options, selected=None):
        r = []
        for option in options:
            if option == selected:
                r.append(T.option(value=str(option), selected="selected")[str(option)])
            else:
                r.append(T.option(value=str(option))[str(option)])

        return r

    def form_options2(self, options, selected=None):
        selected = str(selected)

        r = []
        for option_id, option_text in options:
            option_id = str(option_id)
            option_text = str(option_text)

            if option_id == selected:
                r.append(T.option(value=option_id, selected="selected")[option_text])
            else:
                r.append(T.option(value=option_id)[option_text])

        return r

    def render_form_select(self, data):
        """Use to automatically render a select widget.

        Pass in a dictionary with keys:

        name: name of the select widget
        choices: list of 2-tuples (value, text)
        selected: value of selected choice (if any)
        editmode: False if element should be disabled

        """

        #print 'start', data
        name = data['name']
        #print 'rendering select ', name, data
        _id = name
        choices = data['choices']
        selected = data.get('selected', '')
        editmode = data.get('editmode', '')

        if not choices:
            return 'No choices available.'

        import types
        if type(choices[0]) in types.StringTypes:
            options = self.form_options(choices, selected)
        else:
            options = self.form_options2(choices, selected)

        if editmode:
            select = T.select(name=name, _id=_id)[options]
        else:
            select = T.select(name=name, _id=_id, disabled="disabled")[options]

        return select


    def render_name(self, ctx, data):
        return ctx.tag[self.obj.name]

    def render_objclass(self, ctx, data):
        cls = self.cls
        base = self.bse
        if cls != base:
            return ctx.tag['%s(%s)' % (cls, base)]
        else:
            return ''

    def render_clsinfo(self, ctx, data):
        return ctx.tag(_class="clsinfo")[self.obj.__doc__]

    def get_input_widget(self, name, data):
        if name=='owner':
            if data is None:
                tzid=''
            else:
                tzid=data.tzid
            ps = players.ls()
            ms = mobs.ls()
            cs = ps + ms
            choices = [(c.tzid, '%s (%s)' % (c.name, c.tzid)) for c in cs]
            choices.sort(key=itemgetter(1))
            info = dict(name=name,
                        choices=choices,
                        selected=tzid,
                        editmode=True)
            return self.render_form_select(info)

        if isinstance(data, str):
            if len(data) < 50:
                return T.input(value=data, size="60")
            else:
                return T.textarea(rows="4", cols="60")[data]

        if isinstance(data, bool):
            info = dict(name=name,
                        choices=[(True, 'True'), (False, 'False')],
                        selected=data,
                        editmode=True)
            return self.render_form_select(info)

        if isinstance(data, int):
            return T.input(value=data, size="5")

        else:
            return T.input

    def render_settings(self, ctx, data):
        settings = self.obj.settings
        print settings
        lines = []
        for setting in settings:
            label = T.td(_class="textlabel")[setting]
            val = getattr(self.obj, setting)
            print setting, val
            inpt = T.td[self.get_input_widget(setting, val)(name=setting, value=val)]
            lines.append(T.tr[label, inpt])

        return T.table[lines]

