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
import urlparse

from nevow import loaders, rend
from nevow import static
from nevow import tags as T
from nevow.entities import nbsp
from nevow import inevow

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

import pages_base
from pages_base import xmlf, normalize_args

class Edit(pages_base.TZPage):
    docFactory = xmlf('edit.html')
    title = 'Edit Object'

    def render_process(self, ctx, data):
        request = inevow.IRequest(ctx)
        args = normalize_args(request.args)

        print 'args:', args

        if args:
            for s in self.obj.settings:
                val = args.get(s, None)
                if val is None:
                    continue

                if s == 'owner' and val != 'None':
                    val = '#%s' % val

                self.obj.setting(s, val)


            toroomid = args.get('room', None)
            if toroomid is not None:
                toroomid = int(toroomid)
                toroom = tzindex.get(toroomid)
                room = self.obj.room
                if toroom is not room:
                    roomid = room.tzid
                    print 'teleport from', room.name, 'to', toroom.name



        return ''


    def locateChild(self, ctx, segments):
        '''for pages that need to find which object they should operate on
                from the URL. For instance /edit/102 should act on the
                object with tzid = 102.

        This method will set some convenience variables so that they will
            be available later:

            self.obj    --> the actual object
            self.tzid   --> the tzid of the object
            self.cls    --> name of the object's class (a string)
            self.base   --> the most important base class of the object
                                one of ...  rooms.Room
                                            rooms.Exit
                                            items.Item
                                            mobs.Mob
                                            players.Player
            self.bse    --> name of the object's base class (a string)

        '''

        tzid = int(segments[0])
        self.tzid = tzid
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
            self.child_rebuild(ctx)
            return self.locateChild(ctx, segments)
        else:
            self.bse = class_as_string(base, instance=False)

        self.cls = class_as_string(obj)

        return self, ()


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

    def get_setting_widget(self, name, data):
        if name == 'owner':
            return self.owner_widget(name, data), self.editlink_widget(data)
        elif name == 'room':
            return self.rooms_widget(name, data), self.editlink_widget(data)
        elif name == 'container':
            return self.rooms_widget(name, data), self.containerlink_widget(data)
        elif name == 'destination':
            return self.rooms_widget(name, data), self.editlink_widget(data)
        elif name == 'mobtype':
            return self.mobtypes_widget(name, data)
        elif isinstance(data, str):
            return self.str_widget(name, data)
        elif isinstance(data, bool):
            return self.bool_widget(name, data)
        elif isinstance(data, int):
            return self.int_widget(name, data)
        else:
            return self.input_widget(name, data)

    def editlink_widget(self, obj):
        if obj is None:
            tzid=None
        else:
            tzid=obj.tzid

        if tzid is not None:
            editlink = "/edit/%s" % tzid
            link = T.a(href=editlink)[T.span(_class="editlink")[obj.name]]
        else:
            link = ''

        return link

    def container_widget(self, obj):
        links = []
        for o in obj.containers():
            links.append(self.editlink_widget(o))
        return T.span[links]

    def deletelink_widget(self, obj):
        if obj is None:
            tzid=None
        else:
            tzid=obj.tzid

        if tzid is not None:
            editlink = "/destroy/%s" % tzid
            link = T.a(href=editlink)[T.span(_class="deletelink")['X']]
        else:
            link = ''

        return link

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
                    selected=tzid)

        return self.render_form_select(info)

    def rooms_widget(self, name, x):
        if x is None:
            tzid=None
        else:
            tzid=x.tzid

        rs = rooms.ls()
        rs.sort(key=attrgetter('name'))
        choices = [(r.tzid, '%s (%s)' % (r.name, r.tzid)) for r in rs]
        choices.insert(0, (None, 'None'))
        info = dict(name=name,
                    choices=choices,
                    selected=tzid)

        return self.render_form_select(info)

    def str_widget(self, name, data, size=60):
        disabled = ''
        if name=='name':
            if self.bse=='Player':
                disabled = 'disabled'

        if len(data) < 50:
            size = str(size)
            if disabled:
                return T.input(name=name, value=data, size=size, disabled=disabled)
            else:
                return T.input(name=name, value=data, size=size)
        else:
            return T.textarea(name=name, rows="4", cols="60")[data]

    def bool_widget(self, name, data):
        info = dict(name=name,
                    choices=[(True, 'True'), (False, 'False')],
                    selected=data)
        return self.render_form_select(info)

    def int_widget(self, name, data):
        return T.input(name=name, value=data, size="5")

    def input_widget(self, name, data):
        return T.input(name=name, value=data)

    def mobtypes_widget(self, name, data):
        choices = mobs.classes()
        choices.sort()
        info = dict(name=name,
                    choices=choices,
                    selected=data)
        return self.render_form_select(info)


    def render_settings(self, ctx, data):
        settings = self.obj.settings[:]
        if self.bse != 'Room':
            settings.append('room')
        if self.bse == 'Exit':
            settings.append('destination')

        lines = []
        for setting in settings:
            label = T.td(_class="textlabel")[setting]
            val = self.obj.setting(setting)
            if val is None:
                val = getattr(self.obj, setting, None)
            inpt = T.td[self.get_setting_widget(setting, val)]
            lines.append(T.tr[label, inpt])

        if self.bse != 'Room' and self.obj.container != self.obj.room:
            label = T.td(_class="textlabel")['container']
            inpt = T.td[self.container_widget(self.obj)]
            lines.append(T.tr[label, inpt])

        empty = T.td(_class='empty')['']
        lines.append(T.tr[empty, empty])
        submit = T.input(_type="submit", value=" Change ")
        lines.append(T.tr[empty, T.td[submit]])

        tbl = T.table(_class="center")[lines]

        return T.form(action=".", method="POST")[tbl]

    def render_exits(self, ctx, data):
        if self.bse != 'Room':
            return ''

        xs = self.obj.exits()
        xs.sort(key=attrgetter('name'))
        if xs:
            lines = [T.h2(_class="section")['Exits:']]

            rows = []
            for x in xs:
                tzid = x.tzid
                destf = 'dest_%s' % tzid
                namef = 'name_%s' % tzid
                dest = x.destination
                rows.append(T.tr[
                                T.td[self.deletelink_widget(x)],
                                T.td[self.editlink_widget(x)],
                                T.td[self.str_widget(namef, x.name, 20)],
                                T.td['-->'],
                                T.td[self.rooms_widget(destf, dest)],
                                T.td[self.editlink_widget(dest)],
                                T.td[T.input(_type="submit", value="update")]])
            tbl = T.table(_class="center")[rows]
            lines.append(tbl)
            return T.form(action="/exits/update/", method="POST")[lines]

        else:
            return T.h2(_class="warn")['No exits']

    def render_addexitform(self, ctx, data):
        if self.bse != 'Room':
            return ''

        tzid = self.tzid # to know which room to add the exit to
        action = '/exits/add/'
        lines = [T.h2['Add Exit']]
        exitclasses = rooms.exit_classes()
        exitclasses.sort()
        choices = [(cls, cls) for cls in exitclasses]
        xinfo = dict(name='xclass',
                            choices=choices,
                            selected='Exit')
        bxinfo = dict(name='bxclass',
                            choices=choices,
                            selected='Exit')
        row = T.tr[T.td[self.render_form_select(xinfo)],
                    T.td[T.input(name='xname')],
                    T.td['-->'],
                    T.td[self.rooms_widget('dest', None)],
                    T.td['<--'],
                    T.td[T.input(name='bxname')],
                    T.td[self.render_form_select(bxinfo)],
                    T.td[T.input(type='submit', value=' Add ')]]
        tbl = T.table(_class="center")[row]
        lines.append(tbl)
        lines.append(T.input(_type="hidden", name="roomid", value=tzid))
        form = T.form(action=action, method='POST')[lines]

        return T.div(_class='addexit')[form]


class Destroy(Edit):
    docFactory = xmlf('process_and_redirect.html')

    def render_process(self, ctx, data):
        self.obj.destroy()
        self.goback(ctx)
