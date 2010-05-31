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

from rooms import Room
from exits import Exit
from items import Item
from mobs import Mob
from players import Player

from share import module_as_string, class_as_string
import conf

from db import TZIndex
tzindex = TZIndex()


def normalize_args(args, preserve='', remove='errmsg'):
    '''Make args a 1:1 dict of key:value instead of key:[value, value, ]
    by selecting the first item in the list to be the value.

    If some values should be left as lists, pass in their keys
    in the preserve parameter.

    preserve can be a single key or list of keys to not change.

    >>> normalize_args({'name': ['one', 'two', 'three']})
    {'name': 'one'}
    >>> normalize_args({'name': ['one', 'two', 'three'], 'id': ['12345']})
    {'name': 'one', 'id': '12345'}
    >>> normalize_args({'name': ['one', 'two', 'three'], 'id': ['12345']}, preserve='name')
    {'name': ['one', 'two', 'three'], 'id': '12345'}
    >>> normalize_args({'name': ['one', 'two', 'three'], 'id': ['12345']}, preserve=['name', 'id'])
    {'name': ['one', 'two', 'three'], 'id': ['12345']}

    '''

    for k in args.keys():
        if not k == preserve and not k in preserve:
            args[k] = args[k][0]
        if k == remove or k in remove:
            del args[k]
    return args


class xmlf(loaders.xmlfile):
    templateDir = 'var/www/templates'

class TZPage(rend.Page):
    addSlash = True
    title = 'Not Set'

    def child_styles(self, request):
        return static.File('var/www/styles')

    def child_rooms(self, request):
        return pages_rooms.Rooms()

    def child_exits(self, request):
        return pages_exits.Exits()

    def child_edit(self, request):
        return pages_edit.Edit()

    def child_destroy(self, request):
        return pages_edit.Destroy()

    def render_head(self, ctx, data):
        request = ctx.locate(inevow.IRequest)
        if conf.allow_utf8:
            request.setHeader('Content-Type', 'text/html; charset=UTF-8')
        return xmlf('head.html')

    def render_title(self, ctx, data):
        ctx.fillSlots('title', self.title)
        return ctx.tag

    def render_scripts(self, ctx, data):
        return ctx.tag

    def render_header(self, ctx, data):
        return xmlf('header.html')

    def render_footer(self, ctx, data):
        return xmlf('footer.html')

    def render_errmsg(self, ctx, data):
        errmsg = ctx.arg('errmsg')

        if errmsg:
            lines = [T.h2['Error:']]
            lines.append(T.h4[errmsg])
            return T.div(_class="errmsg")[lines]
        else:
            return ''

    def goback(self, rc, msg=''):
        request = inevow.IRequest(rc)
        headers = request.getAllHeaders()
        backurl = headers.get('referer')
        if backurl:
            parsed = urlparse.urlsplit(backurl)
            backpath = parsed.path

        else:
            backpath = '/'

        request.redirect('%s?errmsg=%s' % (backpath, msg))


    def form_options(self, options, selected=None):
        r = []
        for option in options:
            if option == selected:
                r.append(T.option(value=unicode(option), selected="selected")[unicode(option)])
            else:
                r.append(T.option(value=unicode(option))[unicode(option)])

        return r

    def form_options2(self, options, selected=None):
        selected = unicode(selected)

        r = []
        for option_id, option_text in options:
            option_id = unicode(option_id)
            option_text = unicode(option_text)

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
        editmode = data.get('editmode', True)

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


    def child_rebuild(self, ctx):
        import pages_base
        rebuild(pages_base)
        import pages_index
        rebuild(pages_index)
        import pages_rooms
        rebuild(pages_rooms)
        import pages_edit
        rebuild(pages_edit)
        import pages_exits
        rebuild(pages_exits)
        self.goback(ctx)
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

    def render_addroomform(self, ctx, data):
        action = '/rooms/add/'
        lines = [T.h2['Add Room']]
        roomclasses = rooms.classes()
        roomclasses.sort()
        choices = [(cls, cls) for cls in roomclasses]
        roomsinfo = dict(name='roomclass',
                            choices=choices,
                            selected='Room')
        row = T.tr[T.td[self.render_form_select(roomsinfo)],
                    T.td[T.input(name='roomname')],
                    T.td[T.input(type='submit', value=' Add ')]]
        tbl = T.table(_class="center")[row]
        lines.append(tbl)
        form = T.form(action=action, method='POST')[lines]

        return T.div(_class='addroom')[form]


import pages_index
import pages_exits
import pages_edit
import pages_rooms
