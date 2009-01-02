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

from pages_base import TZPage, xmlf, normalize_args


class Exits(TZPage):
    docFactory = xmlf('exits.html')
    title = 'Exits'

    def child_update(self, request):
        return UpdateExit()


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
