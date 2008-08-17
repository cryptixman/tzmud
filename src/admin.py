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


'''Admin commands.

Admins are able to restart, or stop the server, and to back up and
    restore the database.

'''

import os
import copy
import datetime
now = datetime.datetime.now
import shutil
import time

from twisted.python.rebuild import rebuild

import conf

from db import TZODB
dbroot = TZODB().root

import rooms
import mobs


def verify(player):
    'Return True if player is a wizard, False otherwise.'

    if player.name in dbroot['admin']:
        return True
    else:
        return False


def cmd_py(s, r):
    '''py <python statement to execute>

    Run a python statement.

    WARNING: This should probably be disabled in a production system.

    '''

    s.message(str(eval(r)))


def cmd_db(s, r=None):
    '''db [<section name>]

    Show the contents of the database.

    If a section is given, show only that section, otherwise
    show the entire database.

    '''

    if r is None:
        root = s.dbroot
    else:
        try:
            root = s.dbroot[r]
        except KeyError:
            s.message('Section not found.')
            return

    for k in root:
        try:
            obj = root[k]
            s.message(k + ':')
        except TypeError:
            obj = k
        try:
            s.mlmessage(obj.__repr__().split('\n'), indent=4)
        except AttributeError:
            s.mlmessage(str(obj).split('\n'), indent=4)
        s.message('')


def cmd_backup(s):
    '''backup

    Create a backup of the database. The name of the backup file is
        based on the date and time. The database can later be rolled
        back to this file using the rollback command.

    '''

    dt = now()
    dtstr = '%04d.%02d.%02d_%02d:%02d' % (dt.year, dt.month, dt.day,
                                            dt.hour, dt.minute)
    backupfile = '%s.%s' % (dtstr, conf.datafsname)

    if not os.path.exists(conf.backupdir):
        os.mkdir(conf.backupdir)

    fname = '%s/%s' % (conf.backupdir, backupfile)

    shutil.copyfile(conf.datafs, fname)
    s.message('Backup ' + fname + ' created.')


def cmd_restart(s, r=None):
    '''restart [<delay>]

    Attempt to restart the server.

    Default delay is 2 seconds, or
        delay the specified number of seconds.

    WARNING: This will disconnect everyone from the server!

    '''

    if r is None:
        delay = 2 # seconds
    else:
        delay = int(r) # seconds

    s.broadcast('WARNING! WARNING! WARNING! WARNING! WARNING! WARNING!')
    s.broadcast('TZMud will restart in ' + str(delay) + ' seconds!')

    s.factory._restart = True
    from twisted.internet import reactor
    reactor.callLater(delay, shutdown, s)


def cmd_shutdown(s, r=None):
    '''shutdown [<delay>]

    Attempt to shut down the server.

    Default delay is 2 seconds, or
        delay the specified number of seconds.

    WARNING: This will disconnect everyone from the server!

    '''

    if r is None:
        delay = 2 # seconds
    else:
        delay = int(r) # seconds

    s.broadcast('WARNING! WARNING! WARNING! WARNING! WARNING! WARNING!')
    s.broadcast('TZMud will shut down in ' + str(delay) + ' seconds!')

    s.factory._restart = False
    from twisted.internet import reactor
    reactor.callLater(delay, shutdown, s)


def shutdown(s):
    '''Disconnect all clients and shut down.

    If factory._restart is True, the server should restart itself.

    '''

    for client in s.factory.clients:
        client.transport.loseConnection()

    import os
    for f in conf.twistdpid, conf.twistdpid2:
        try:
            pid = file(f).read()
            os.kill(int(pid), 15)
        except:
            print f, 'not found'


def cmd_fresh(s):
    '''fresh

    Stop the server, re-initialize the database and restart.

    WARNING: This will disconnect everyone from the server!
    WARNING:
    WARNING: This will delete the database!

    '''

    cmd_shutdown(s)

    import os
    import conf
    cmd = '%s %s -d -f &' % (conf.python, conf.tzcontrol)
    os.system(cmd)


def cmd_rollback(s, r=None):
    '''rollback [<file>]

    Stop the server, rollback the database and restart.
    Defaults to rolling back to most recent backup.

    WARNING: This will disconnect everyone from the server!
    WARNING:
    WARNING: This will delete the current database!

    '''

    cmd_shutdown(s)

    import os
    import conf

    if r is not None:
        rbf = '-Z %s' % r
    else:
        rbf = ''

    cmd = '%s %s -d -z %s &' % (conf.python, conf.tzcontrol, rbf)
    os.system(cmd)


def cmd_svnup(s):
    '''svnup

    Update the server to the latest source code,
    stop the server, and restart.

    WARNING: This will disconnect everyone from the server!

    '''


    import os
    import conf
    cmd = 'svn up'
    os.system(cmd)

    cmd_restart(s)


def cmd_nudge(s):
    '''nudge

    Give all of the mobs and rooms a nudge to get them started again.
    Useful after an error has caused some mobs to stop moving, or some
        rooms to stop running their periodic code.

    '''

    mobs.nudge_all()
    rooms.nudge_all()


def cmd_rebuild(s, r=None):
    '''rebuild [<module name>]

    Attempt to incorporate changes made to modules since server start.

    If module name is given, rebuild only that module, or if no module
        specified, try to rebuild all possible modules.

    Currently rebuilds ...
        admin
        wizard
        actions
        rooms
        items
        share
        conf

    Does NOT rebuild ...
        players
        db
        tzprotocol
        tzmud.tac

    If you make changes to one of those files, try using
        !restart to restart the server

    '''

    if r is None:
        import admin
        rebuild(admin)
        import wizard
        rebuild(wizard)
        import actions
        rebuild(actions)
        import rooms
        rebuild(rooms)
        import items
        rebuild(items)
        import mobs
        rebuild(mobs)
        import share
        rebuild(share)
        import conf
        rebuild(conf)
        import parse
        rebuild(parse)

        #import players
        #rebuild(players)
        #import db
        #rebuild(db)
        #import tzprotocol
        #rebuild(tzprotocol)

    else:
        try:
            mod = __import__(r)
        except ImportError:
            s.message('Module not found.')
        else:
            rebuild(mod)


def cmd_help(s, r=None):
    '''help [<subject>]

    Get help on some <subject> or general help if no subject given.

    '''

    import admin
    if r is None:
        s.message('Available admin commands:')
        commands = []
        for func in dir(admin):
            if func.startswith('cmd_'):
                #s.message(func[4:], indent=4)
                commands.append(func[4:])
        s.columns(commands)

    else:
        func_name = 'cmd_%s' % r
        func = getattr(admin, func_name, None)
        if func is not None:
            doc = func.__doc__
            if doc is not None:
                msg = 'Help on %s:' % r
                s.message(msg)
                s.message()
                msg = doc.split('\n')
                msg.insert(0, 'Syntax:')
                msg[1] = '        !' + msg[1]
                s.mlmessage(msg)
                return

        msg = 'Sorry. No admin help available on that subject.'
        s.message(msg)
