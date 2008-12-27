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

from twisted.python.rebuild import rebuild

import conf

from db import TZODB
dbroot = TZODB().root

import players
import rooms
import mobs
import wizard


def verify(player):
    'Return True if player is a wizard, False otherwise.'

    if player.name in dbroot['admin']:
        return True
    else:
        return False


def add(player):
    'Add player to the admin list.'

    if not verify(player):
        dbroot['admin'].append(player.name)


def cmd_admin(s, r):
    '''admin <player>

    Create a new admin.

    '''

    player = players.getname(r)
    if player is not None:
        add(player)
        s.message(player, 'is now an admin.')
    else:
        s.message('No such player.')


def cmd_wizard(s, r):
    '''wizard <player>

    Create a new wizard.

    '''

    player = players.getname(r)
    if player is not None:
        wizard.add(player)
        s.message(player, 'is now a wizard.')
    else:
        s.message('No such player.')


def cmd_py(s, r):
    '''py <python statement to execute>

    Run a python statement.

    WARNING: This should probably be disabled in a production system.

    '''

    try:
        s.message(str(eval(r)))
    except Exception, e:
        s.message('ERROR')
        for line in e:
            s.message(line)


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


def cmd_pack(s):
    '''pack

    Pack the DB.

    '''

    s.message('Packing database.')
    TZODB().pack()
    s.message('Database Packed.')


def cmd_backup(s):
    '''backup

    Create a backup of the database. The name of the backup file is
        based on the date and time. The database can later be rolled
        back to this file using the rollback command.

    '''

    cmd = '%s %s -b' % (conf.python, conf.tzcontrol)
    os.system(cmd)

    s.message('Backup saved.')


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

    from twisted.internet import reactor
    reactor.callLater(delay, restart, s)


def restart(s):
    for client in s.factory.clients:
        client.transport.loseConnection()

    cmd = (conf.python, conf.tzcontrol, '-r')
    os.spawnl(os.P_NOWAIT, conf.python, *cmd)


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

    from twisted.internet import reactor
    reactor.callLater(delay, shutdown, s)


def shutdown(s):
    '''Disconnect all clients and shut down.

    If factory._restart is True, the server should restart itself.

    '''

    for client in s.factory.clients:
        client.transport.loseConnection()

    from twisted.internet import reactor
    reactor.stop()

def cmd_fresh(s):
    '''fresh

    Stop the server, re-initialize the database and restart.

    WARNING: This will disconnect everyone from the server!
    WARNING:
    WARNING: This will delete the database!

    '''

    cmd_shutdown(s)

    cmd = (conf.python, conf.tzcontrol, '-f')
    os.spawnl(os.P_NOWAIT, conf.python, *cmd)


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

    cmd = (conf.python, conf.tzcontrol, '-z', rbf)
    os.spawnl(os.P_NOWAIT, conf.python, *cmd)


def cmd_list(s, r):
    '''list backups

    Show a listing of available backup databases.

    '''

    if r=='backups':
        backups = os.listdir(conf.backupdir)
        backups = [f for f in backups if not f.startswith('.')]
        if backups:
            backups.sort()
            s.message('Available backups:')
            s.mlmessage(backups, indent=4)
        else:
            s.message('No backups yet.')
    else:
        s.message('Not implemented.')


def cmd_svnup(s):
    '''svnup

    Update the server to the latest source code,
    stop the server, and restart.

    WARNING: This will disconnect everyone from the server!

    '''


    import os
    import conf
    cmd = conf.svn
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
            try:
                rebuild(mod)
            except Exception, e:
                s.message('Error rebuilding')
                s.mlmessage(e)
                print 'Error rebuilding'
                for line in e:
                    print line



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
        commands.sort()
        s.columns_v(commands)

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
