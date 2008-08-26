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


'''Twistd TAC file.'''


import sys
import os

etc = os.path.abspath('etc')
sys.path.append(etc)

from twisted.internet import reactor
import transaction

import conf

src = os.path.abspath(conf.src)
sys.path.append(src)


from db import TZODB
from tzprotocol import TZ


from twisted.internet import protocol

factory = protocol.ServerFactory()
TZ.factory = factory
factory.protocol = TZ
factory.clients = []
TZ.clients = factory.clients
factory._player_protocols = {}
TZ._player_protocols = factory._player_protocols
factory._restart = True
TZ.purge_all()


from twisted.application import service, internet


class TZMUD(internet.TCPServer):
    'Main MUD Server class.'

    def close_db(self):
        'Close the database connection before shutting down the server.'

        print 'closing ZODB'
        zodb = TZODB()
        zodb.pack()
        zodb.close()

    def maybe_restart(self):
        'Try to restart the server if _restart has been set.'

        print 'maybe restarting...'
        if factory._restart:
            print '_restart is True'

            if not os.path.exists(conf.twistdpid):
                pidfile = conf.twistdpid
            else:
                pidfile = conf.twistdpid2

            cmd = 'twistd --pidfile %s --logfile %s -y %s' % (pidfile,
                                                                conf.twistdlog,
                                                                conf.tztac,)
            os.system(cmd)
        else:
            print '_restart is False'

application = service.Application('tzmud_server')
server = TZMUD(conf.port, factory)
reactor.addSystemEventTrigger("after", "shutdown", server.close_db)
reactor.addSystemEventTrigger("after", "shutdown", server.maybe_restart)
import mobs
reactor.callLater(10, mobs.nudge_all)
import rooms
reactor.callLater(10, rooms.nudge_all)
server.setServiceParent(application)







if conf.web:
    from twisted.application import internet
    from twisted.application import service
    from nevow import appserver

    etc = os.path.abspath('var/www/src')
    sys.path.append(etc)

    import pages

    app2 = service.Application('tzmudweb')
    site = appserver.NevowSite(pages.Index())
    webserver = internet.TCPServer(8080, site)
    webserver.setServiceParent(application)
