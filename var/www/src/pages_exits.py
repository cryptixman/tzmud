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


from db import TZIndex
tzindex = TZIndex()

from nevow import inevow

import rooms
import exits

from pages_base import TZPage, xmlf, normalize_args


class Exits(TZPage):
    docFactory = xmlf('exits.html')
    title = 'Exits'

    def child_add(self, request):
        return AddExit()

    def child_update(self, request):
        return UpdateExit()


class AddExit(TZPage):
    docFactory = xmlf('process_and_redirect.html')

    def render_process(self, ctx, data):
        request = ctx.locate(inevow.IRequest)
        args = normalize_args(request.args)

        roomid = int(args['roomid'])
        room = tzindex.get(roomid)

        xname = args['xname']
        xclass = args['xclass']

        bxname = args['bxname']
        bxclass = args['bxclass']

        destid = args['dest']
        if destid != 'None':
            destid = int(destid)
            dest = tzindex.get(destid)
        else:
            dest = None

        newroomcls = args['newroom']
        if newroomcls == 'None':
            newroomcls = None

        if dest is None and newroomcls is None:
            self.goback(request, 'Choose existing room, or room type to clone.')
            return
        elif dest is not None and newroomcls is not None:
            self.goback(request, 'Choose only one target room: Existing room or New room.')
            return
        elif newroomcls and newroomcls in rooms.classes():
            cls = getattr(rooms, newroomcls)
            newroomname = args['newroomname']
            if newroomname:
                newroom = cls(newroomname)
            else:
                newroom = cls()
            dest = newroom
            print 'NR', dest, dest.name

        if xname and xclass in exits.classes():
            xcls = getattr(exits, xclass)
            if bxname and bxclass in exits.classes():
                bxcls = getattr(exits, xclass)
                bx = bxcls(bxname, room=dest)
                x = xcls(xname, room=room, destination=dest, return_name=bxname)
            else:
                x = xcls(xname, room=room, destination=dest)
            tzid = x.tzid
            editpage = '/edit/%s' % roomid
            request.redirect(editpage)
        else:
            self.goback(request, 'Give a name for the exit.')

class UpdateExit(TZPage):
    docFactory = xmlf('process_and_redirect.html')

    def render_process(self, ctx, data):
        request = ctx.locate(inevow.IRequest)
        args = normalize_args(request.args)
        for arg, val in args.items():
            if arg.startswith('name'):
                unused, tzid = arg.split('_')
                tzid = int(tzid)
                name = val
                destfield = 'dest_%s' % tzid
                desttzid = args[destfield]
                if desttzid == 'None':
                    desttzid = None
                    dest = None
                else:
                    desttzid = int(desttzid)
                    dest = tzindex.get(desttzid)

                x = tzindex.get(tzid)
                if x is None:
                    continue

                origname = x.name
                if x.destination is not None:
                    origdesttzid = x.destination.tzid
                else:
                    origdesttzid = None

                if name==origname and desttzid==origdesttzid:
                    continue

                if name != origname:
                    x.name = name

                if desttzid != origdesttzid:
                    x.destination = dest

        self.goback(ctx)
