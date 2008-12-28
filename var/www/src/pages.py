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
import items

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

    def data_mobs(self, ctx, data):
        r = mobs.ls()
        #r.sort(key=attrgetter('name'))
        return r

    def data_items(self, ctx, data):
        r = items.ls()
        #r.sort(key=attrgetter('name'))
        return r

class Index(TZPage):
    docFactory = xmlf('index.html')
    title = 'TZMud Web Interace'

    def render_process_index(self, ctx, data):
        roomname = ctx.arg('roomname')
        if roomname:
            newroom = rooms.Room(roomname)
            return 'Processing'
        else:
            return ''

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
            editlink = T.a(href="/edit/%s" % room.tzid)[room.name]
            tzid = T.td(_class="roomtzid")[room.tzid, ':']
            #name = T.td(_class="roomname")[room.name]
            name = T.td(_class="roomname")[editlink]
            if not room.exits():
                row = T.tr(_class='warn')
            else:
                row = T.tr
            lines.append(row[tzid, name])

        return T.table[lines]

    def render_idtable(self, ctx, data):
        lines = []
        for obj in data:
            editlink = T.a(href="/edit/%s" % obj.tzid)[obj.name]
            tzid = T.td(_class="objtzid")[obj.tzid, ':']
            #name = T.td(_class="objname")[obj.name]
            name = T.td(_class="objname")[editlink]
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


class Edit(TZPage):
    docFactory = xmlf('edit.html')
    title = 'Edit Object'

    def locateChild(self, context, segments):
        #print 'seg', context, segments
        tzid = int(segments[0])
        obj = tzindex.get(tzid)
        self.obj = obj

        bases = [Room, Exit, Item, Mob, Player]
        found = False
        for base in bases:
            if issubclass(obj.__class__, base):
                found = True
                self.base = base
                break
        if not found:
            # Module was probably rebuilt elsewhere (from the MUD).
            # Try rebuilding then finding the base class again.
            self.child_rebuild(None)
            return self.locateChild(context, segments)
        else:
            self.bse = class_as_string(base, instance=False)

        self.cls = class_as_string(obj)
        #print 'module:', module_as_string(obj)
        #print 'class:', class_as_string(obj)
        #print 'base:', self.bse
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
        name = self.obj.name
        cls = self.cls
        base = self.bse
        if cls != base:
            return ctx.tag['%s : %s(%s)' % (name, cls, base)]
        else:
            return ctx.tag['%s : %s' % (name, cls)]

    def render_clsinfo(self, ctx, data):
        doc = self.obj.__doc__
        return ctx.tag(_class="clsinfo")[doc]

    def get_input_widget(self, name, data):
        if name=='owner':
            return self.owner_widget(name, data)
        elif isinstance(data, str):
            return self.str_widget(name, data)
        elif isinstance(data, bool):
            return self.bool_widget(name, data)
        elif isinstance(data, int):
            return self.int_widget(name, data)
        else:
            return self.input_widget(name, data)

    def owner_widget(self, name, data):
        if data is None:
            tzid=None
        else:
            tzid=data.tzid
        ps = players.ls()
        ms = mobs.ls()
        cs = ps + ms
        choices = [(c.tzid, '%s (%s)' % (c.name, c.tzid)) for c in cs]
        choices.insert(0, (None, 'None'))
        choices.sort(key=itemgetter(1))
        info = dict(name=name,
                    choices=choices,
                    selected=tzid,
                    editmode=True)

        return self.render_form_select(info)

    def str_widget(self, name, data):
        disabled = ''
        if name=='name':
            if self.bse=='Player':
                disabled = 'disabled'

        if len(data) < 50:
            if disabled:
                return T.input(name=name, value=data, size="60", disabled=disabled)
            else:
                return T.input(name=name, value=data, size="60")
        else:
            return T.textarea(name=name, rows="4", cols="60")[data]

    def bool_widget(self, name, data):
        info = dict(name=name,
                    choices=[(True, 'True'), (False, 'False')],
                    selected=data,
                    editmode=True)
        return self.render_form_select(info)

    def int_widget(self, name, data):
        return T.input(name=name, value=data, size="5")

    def input_widget(self, name, data):
        return T.input(name=name, value=data)


    def render_settings(self, ctx, data):
        settings = self.obj.settings
        print settings
        lines = []
        for setting in settings:
            label = T.td(_class="textlabel")[setting]
            val = self.obj.setting(setting)
            print setting, val
            inpt = T.td[self.get_input_widget(setting, val)]
            lines.append(T.tr[label, inpt])

        return T.table[lines]

    def render_exits(self, ctx, data):
        if self.bse != 'Room':
            return ''

        xs = self.obj.exits()
        xs.sort(key=attrgetter('name'))
        if xs:
            lines = [T.tr[T.td['Exits'], T.td, T.td, T.td, T.td]]
            rs = rooms.ls()
            for x in xs:
                dest = x.destination
                choices = [(r.tzid, '%s (%s)' % (r.name, r.tzid)) for r in rs]
                choices.insert(0, (None, 'None'))
                desttzid = getattr(dest, 'tzid', None)
                destname = getattr(dest, 'name', None)
                destinfo = dict(name=x.name,
                            choices=choices,
                            selected=desttzid,
                            editmode=True)

                xlink = T.a(href="/edit/%s" % x.tzid)[x.name]
                if dest is not None:
                    roomlink = T.a(href="/edit/%s" % desttzid)[destname]
                else:
                    roomlink = 'Broken'
                lines.append(T.tr[T.td[xlink],
                                T.td[T.input(name='', value=x.name)],
                                T.td['-->'],
                                T.td[self.render_form_select(destinfo)],
                                T.td[roomlink]])

        else:
            lines = T.tr(_class="warn")[T.td['No exits']]

        return T.table[lines]
