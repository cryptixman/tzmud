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


'''Control program for starting, stopping, and controlling the server.

'''

#/usr/bin/env python

import os
import sys
import time
import shutil

etc = os.path.abspath('etc')
sys.path.append(etc)

def create_conf():
    'If the conf file does not exist, create it.'

    f = file('etc/conf.py', 'w')
    f.write('from defaults import *\n')
    f.write('\n')
    f.write('# Make configuration changes here.\n')
    f.write('# See etc/defaults.py for available parameters.\n')
    f.write('\n')
    f.write('\n')
    f.close()

try:
    import conf
except ImportError:
    create_conf()
    print 'etc/conf.py created'
    print
    print 'Please check configuration before starting server.'
    sys.exit(0)


def pid():
    'Return the pid of the running server.'

    twistdpid = None
    for f in conf.twistdpid, conf.twistdpid2:
        try:
            twistdpid = int(file(f).read())
        except:
            pass

    return twistdpid

def rmpid():
    'Remove any pid files. Used to clean up after a server crash.'

    for f in conf.twistdpid, conf.twistdpid2:
        try:
            os.remove(f)
        except OSError:
            pass

def delay():
    'Wait for a few seconds before proceeding.'

    time.sleep(5)

def start():
    'Try to start the server if it is not already running.'

    p = pid()
    if p is None:
        cmd = '%s --pidfile %s -y %s -l %s' % (conf.twistd,
                                    conf.twistdpid,
                                    conf.tztac,
                                    conf.twistdlog)
        os.system(cmd)
    else:
        print 'Server is already running.'

def shutdown():
    'Try to shut down the server if it is running.'

    p = pid()
    os.chmod(conf.tztac, 0)
    if p is not None:
        try:
            os.kill(p, 15)
        except OSError:
            print 'Server already shut down.'
            rmpid()
        time.sleep(2)
    os.chmod(conf.tztac, 0644)

def restart():
    'Shut down, wait a few seconds, then start up again.'

    shutdown()
    delay()
    start()

def dbclean():
    '''Remove all database related files.

    WARNING: Back up the database first if you may ever need
                the files again.

    '''

    cmd = 'rm %s*' % conf.datafs
    os.system(cmd)

def dbinit():
    'Remove old database and start from a complete fresh start.'

    dbclean()
    cmd = '%s %s init' % (conf.python, conf.dbmod)
    os.system(cmd)

def fresh():
    'Shut down the server, completely reinitialize that database, and restart.'

    shutdown()
    delay()
    dbinit()
    start()

def rollbackfile(rbf):
    '''Check for existence of given rollback file.

    Defaults to most recent backup file if None given.

    '''

    if rbf is None:
        backups = os.listdir(conf.backupdir)
        f = backups[-1]
        rbf = '%s/%s' % (conf.backupdir, f)
    elif not os.path.exists(rbf):
        print 'ERROR'
        print 'File not found: %s' % rbf
        return False

    return rbf

def rollback(rbf):
    '''Remove current database and copy over given backup as the database.

    Defaults to most recent backup if None given.

    '''

    rbf = rollbackfile(rbf)
    if rbf:
        shutdown()
        delay()
        dbclean()
        shutil.copyfile(rbf, conf.datafs)
        start()
        return True
    else:
        return False

def upgradedb():
    '''Go through the database and upgrade all objects to use the latest
    class definitions.'''

    shutdown()
    delay()

    import conf

    src = os.path.abspath(conf.src)
    sys.path.append(src)

    import share
    share.upgradeall()



def check_python_version():
    '''Verify that the version of python running this script is the one
    specified in the configuration file.

    '''

    import sys

    running_major, running_minor = sys.version_info[0:2]

    major_txt, minor_txt = conf.python_version.split('.')
    needed_major, needed_minor = int(major_txt), int(minor_txt)

    return needed_major==running_major and needed_minor==running_minor




def main():
    'Check given cmd line options and run the selected functions.'

    if check_python_version():

        from optparse import OptionParser

        usage = "usage: %prog <option>"
        parser = OptionParser(usage)

        parser.add_option('-q', '--quit', dest='quit',
            action="store_true",
            help='Shut down the server.')
        parser.add_option('-s', '--start', dest='start',
            action="store_true",
            help='Start the server.')
        parser.add_option('-r', '--restart', dest='restart',
            action="store_true",
            help='Restart the server.')
        parser.add_option('-f', '--fresh', dest='fresh',
            action="store_true",
            help='Re-initialize the database.')
        parser.add_option('-d', '--delay', dest='delay',
            action="store_true",
            help='Delay 5 seconds before acting.')
        parser.add_option('-z', '--rollback', dest='rollback',
            action="store_true",
            help='Restore a previous Data.fs. Default is most recent backup. Use -Z (--rollbackfile) to specify a different file.')
        parser.add_option('-Z', '--rollbackfile', dest='rollbackfile',
            help='Specify a different file for database rollback. Must also give -z (--rollback) or it is an error.')
        parser.add_option('-U', '--upgradedb', dest='upgradedb',
            action="store_true",
            help='Upgrade the database. Use after adding or removing attributes from persistent objects.')

        (options, args) = parser.parse_args()


        if options.rollbackfile and not options.rollback:
            print 'ERROR'
            print 'Must give -z (--rollback) when specifying rollback file.'
            print
            parser.print_help()
            return

        if options.delay:
            delay()

        if options.quit:
            shutdown()
        elif options.start:
            start()
        elif options.restart:
            restart()
        elif options.fresh:
            fresh()
        elif options.rollback:
            if not rollback(options.rollbackfile):
                parser.print_help()
        elif options.upgradedb:
            upgradedb()
        else:
            parser.print_help()

    else:
        cmd = '%s %s %s' % (conf.python, conf.tzcontrol, ' '.join(sys.argv[1:]))
        os.system(cmd)


if __name__ == '__main__':
    main()
