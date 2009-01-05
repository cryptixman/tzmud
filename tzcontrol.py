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
import datetime
now = datetime.datetime.now
import shutil
import platform


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
    f.write('# After making changes, verify the config file with:\n')
    f.write('# python tzcontrol.py -c\n')
    f.write('\n')
    f.close()

def check_db():
    if not os.path.exists(conf.datafs):
        print
        print 'There is no database in the location given in'
        print 'in your configuration file [etc/conf.py].'
        print
        print 'If this is your first time running the server,'
        print 'you should initialize the database with:'
        print 'tzcontrol -f'
        print 'to create a "fresh" install.'
        print
        print 'Be sure to change the passwords before putting'
        print 'putting the server on the network.'
        print
        return False
    else:
        return True

try:
    import conf
except ImportError:
    create_conf()
    print 'etc/conf.py created'
    print
    print 'Please check configuration before starting server:'
    print '  python tzcontrol.py -c'
    print
    import conf
    check_db()
    sys.exit(0)


def verify_config():
    varstrings = ['python:-', 'python_version:ver', 'twistd:-', 'twistdlog:-', 'twistdpid:-', 'tztac:-', 'tzcontrol:-', 'src:d', 'plugins:d', 'dbmod:-', 'dbdir:d', 'datafs:-', 'backupdir:d', 'svn:-', 'port:int', 'local_only:bool', 'home_id:int', 'web:bool', 'web_local_only:bool', 'enable_cmd_py:bool']

    for varstring in varstrings:
        varname, vartype = varstring.split(':')
        print 'Checking var:',
        print '%-15s' % varname,

        try:
            val = getattr(conf, varname)
        except AttributeError:
            print '!! variable is missing'
            continue

        if vartype in ('-', 'd'):
            dirname, filename = os.path.split(val)

            exists = os.path.exists(val)
            isfile = os.path.isfile(val)
            dir_exists = os.path.exists(dirname)
            isdir = os.path.isdir(val)

        if vartype == '-':
            if exists and isfile:
                print 'ok'
            elif dir_exists and not exists:
                print '!! file', filename, 'not found in', dirname
            elif exists and isdir:
                print '!! must give the full path to the file'
            elif not dir_exists:
                print '!! directory', dirname, 'does not exist'
            else:
                print '!!'

        elif vartype == 'd':
            if exists and isdir:
                print 'ok'
            elif exists and not isdir:
                print '!! must give a directory path'
            else:
                print '!!'

        elif vartype == 'int':
            try:
                testval = int(val)
            except:
                testval = 'ERROR'

            if testval == val:
                print 'ok'
            else:
                print '!! must give an integer value'

        elif vartype == 'bool':
            try:
                testval = bool(val)
            except:
                testval = 'ERROR'

            if testval == val:
                print 'ok'
            else:
                print '!! must give a boolean value'

        elif vartype == 'ver':
            try:
                t1, t2 = val.split('.')
                i1, i2 = int(t1), int(t2)
            except:
                print "!! must be a string in the form 'X.Y'"
            else:
                print 'ok'

def pid():
    'Return the pid of the running server.'

    twistdpid = None
    for f in conf.twistdpid, 'twistd.pid':
        try:
            twistdpid = int(file(f).read())
        except:
            pass

    return twistdpid

def rmpid():
    'Remove any pid files. Used to clean up after a server crash.'

    for f in conf.twistdpid, 'twistd.pid':
        try:
            os.remove(f)
        except OSError:
            pass

def delay():
    'Wait for a few seconds before proceeding.'

    time.sleep(conf.restart_delay)

def start():
    'Try to start the server if it is not already running.'

    p = pid()
    if p is None:
        system = platform.system()

        if system != 'Linux':
            cmd = '%s -y %s -l %s' % (conf.twistd,
                                        conf.tztac,
                                        conf.twistdlog)
        else:
            cmd = '%s -y %s --pidfile %s -l %s' % (conf.twistd,
                                        conf.tztac,
                                        conf.twistdpid,
                                        conf.twistdlog)
        if check_db():
            from subprocess import Popen, PIPE, STDOUT
            p = Popen(cmd, shell=True, stdin=PIPE, stdout=PIPE,
                                                    stderr=STDOUT)
            output, unused = p.communicate()
            status = p.returncode

            if status:
                print 'Unable to start server'
                print 'Error code:', status
                print 'Command:', cmd
                print
                print output

            else:
                print 'MUD server started on port', conf.port
                if conf.web:
                    print '        Web server on port', conf.web_port
    else:
        print 'Server is already running.'

def shutdown():
    'Try to shut down the server if it is running.'

    p = pid()
    if p is not None:
        try:
            os.kill(p, 15)
        except OSError:
            print 'Server already shut down.'
            rmpid()

    dbunlock()

def restart():
    'Shut down, wait a few seconds, then start up again.'

    cmd = (conf.python, conf.tzcontrol, '-q')
    os.spawnl(os.P_NOWAIT, conf.python, *cmd)

    cmd = (conf.python, conf.tzcontrol, '-d', '-s')
    os.spawnl(os.P_NOWAIT, conf.python, *cmd)

def dbclean():
    '''Remove all database related files.

    WARNING: Back up the database first if you may ever need
                the files again.

    '''

    import glob
    pths = glob.glob('%s*' % conf.datafs)
    for pth in pths:
        os.remove(pth)

def dbunlock():
    '''Remove the Data.fs.lock file -- which for some reason is
        not being removed when the database is closed, preventing
        the server from restarting in some cases.

    '''

    try:
        os.remove('%s.lock' % conf.datafs)
    except OSError:
        pass

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

def backup():
    'Take a backup of the database.'

    dt = now()
    dtstr = '%04d.%02d.%02d_%02d:%02d' % (dt.year, dt.month, dt.day,
                                            dt.hour, dt.minute)
    fname = '%s.%s' % (dtstr, conf.datafsname)

    if not os.path.exists(conf.backupdir):
        os.mkdir(conf.backupdir)

    fpath = '%s/%s' % (conf.backupdir, fname)

    shutil.copyfile(conf.datafs, fpath)
    pack(fname)

    print 'backup', fname, 'saved in', conf.backupdir

    return fname

def depopulate(fname):
    '''Remove all players from the given database file.

    This is used to make a copy of the world that can be easily
        distributed.

    '''

    cmd = '%s %s depopulate %s' % (conf.python, conf.dbmod, fname)
    os.system(cmd)

def world():
    'Save depopulated backup.'

    fname = backup()
    depopulate(fname)
    pack(fname)
    fpath = '%s/%s' % (conf.backupdir, fname)
    worldname = '%s/0.%s' % (conf.backupdir, conf.datafsname)
    shutil.copyfile(fpath, worldname)

def pack(fname):
    'Pack the given backup database.'

    cmd = '%s %s pack %s' % (conf.python, conf.dbmod, fname)
    os.system(cmd)

def rollbackfile(fname):
    '''Check for existence of given rollback file.

    Defaults to most recent backup file if None given.

    '''

    if fname is None:
        backups = os.listdir(conf.backupdir)
        backups = [f for f in backups if not f.startswith('.')]
        backups.sort()
        if backups:
            fname = backups[-1]
        else:
            print 'ERROR'
            print 'No backup files exist.'
            return False

    rbf = '%s/%s' % (conf.backupdir, fname)

    if not os.path.exists(rbf):
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
        print 'Restoring backup', rbf
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

    try:
        major_txt, minor_txt = conf.python_version.split('.')
        needed_major, needed_minor = int(major_txt), int(minor_txt)
    except:
        print 'Warning: unable to verify python version.'
        result = True
    else:
        result = (needed_major==running_major and
                    needed_minor==running_minor)

    return result




def main():
    'Check given cmd line options and run the selected functions.'

    if check_python_version():

        system = platform.system()
        if system != 'Linux':
            print 'Warning: System is only tested on Linux.'
            print 'Warning: Some options may not work properly.'
            print
            print 'If you can make this work properly on your system,'
            print '     please submit a patch to:'
            print '         http://tzmud.googlecode.com/'
            print

        from optparse import OptionParser, SUPPRESS_HELP

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
        parser.add_option('-b', '--backup', dest='backup',
            action="store_true",
            help='Back up the database.')
        parser.add_option('-W', '--world', dest='world',
            action="store_true",
            help='Save depopulated DB for world distribution.')
        parser.add_option('-z', '--rollback', dest='rollback',
            action="store_true",
            help='Restore a previous Data.fs. Default is most recent backup. Use -Z (--rollbackfile) to specify a different file.')
        parser.add_option('-Z', '--rollbackfile', dest='rollbackfile',
            help='Specify a different file for database rollback. Must also give -z (--rollback) or it is an error.')
        parser.add_option('-U', '--upgradedb', dest='upgradedb',
            action="store_true",
            help='Upgrade the database. Use after adding or removing attributes from persistent objects.')
        parser.add_option('-c', '--verify-config', dest='verify_config',
            action="store_true",
            help='Verify the config.py file.')
        # Option '-2' is used by tzcontrol.py to indicate that this
        #   is the 2nd pass at running the script (this time hopefully
        #   with the correct version). It should not be needed by the
        #   user, so help output is suppressed.
        parser.add_option('-2', dest='unused',
            action="store_true",
            help=SUPPRESS_HELP)
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
        elif options.backup:
            backup()
        elif options.world:
            world()
        elif options.rollback:
            if not rollback(options.rollbackfile):
                parser.print_help()
        elif options.upgradedb:
            upgradedb()
        elif options.verify_config:
            verify_config()
        else:
            parser.print_help()

    else:
        args = sys.argv[1:]
        last = args[-1]

        if last != '-2':
            argstr = ' '.join(args)
            cmd = '%s %s %s -2' % (conf.python, conf.tzcontrol, argstr)
            os.system(cmd)
        else:
            print 'ERROR: Unable to locate the correct python version.'
            print
            print 'Please verify your config file with:'
            print '   python tzcontrol.py -c'
            print
            print 'and ensure that the specified version is available.'


if __name__ == '__main__':
    main()
