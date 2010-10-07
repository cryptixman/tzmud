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


'''Basic database elements.

Run this file to create the default database elements. This should
probably only be done after deleting any current database first.

'''

DB_VERSION = 3

from ZODB import FileStorage, DB, serialize
import transaction
from persistent.dict import PersistentDict
from persistent.list import PersistentList

from twisted.internet import reactor

if __name__ == '__main__':
    import os
    import sys

    etc = os.path.abspath('etc')
    sys.path.append(etc)

    import conf
    conf.load_plugins = False

from conf import datafs, backupdir, datafsname

class TZODB(object):
    'Database object. A Borg object with state which all share.'

    _state = {}
    def __new__(cls, *p, **k):
        self = object.__new__(cls)
        self.__dict__ = cls._state
        return self

    def __init__(self, fname=None, read_only=False):
        if fname is None:
            fname = datafs
        else:
            fname = '%s/%s' % (backupdir, fname)

        if not hasattr(self, 'read_only'):
            self.read_only = read_only

        if not hasattr(self, 'storage'):
            self.open(fname)
            reactor.callLater(30, self.pack_regularly)

    def open(self, fname):
        'Open connection to the database.'

        self.storage = FileStorage.FileStorage(fname, read_only=self.read_only)
        self.db = DB(self.storage)
        self.conn = self.db.open()
        self.root = self.conn.root()

    def close(self):
        'Close database connection.'

        self.commit()
        self.conn.close()
        self.db.close()
        self.storage.close()
        del self.storage

    def version(self):
        'return the version number stored in the database.'

        return self.root.get('DB_VERSION', 0)

    def check_version(self):
        return self.version() == DB_VERSION

    def begin(self):
        'Start a new database transaction.'

        transaction.begin()

    def commit(self):
        'Commit current changes to the database.'

        self.root._p_changed = 1
        transaction.commit()
        #print 'db COMMIT'

    def abort(self):
        'Abort the current database transaction, discarding all changes.'

        transaction.abort()

    def pack(self):
        'Pack the DB to remove old versions, like vacuum.'

        import time
        self.storage.pack(time.time(), serialize.referencesf)
        print 'DB Packed'

    def pack_regularly(self):
        'Pack the DB every pack_interval seconds.'

        self.pack()
        pack_interval = 600 #seconds (10 minutes)
        reactor.callLater(pack_interval, self.pack_regularly)

    def __str__(self):
        items = {}
        for k, v in self.root.items():
            try:
                uk = unicode(k)
                items[uk] = unicode(v)
            except:
                raise
        return unicode(items)


class TZDict(PersistentDict):
    'Customized persistent dictionary.'

    def __repr__(self):
        items = []
        for k, v in self.items():
            try:
                items.append(u'%s: %s' % (k, v.name))
            except AttributeError:
                items.append(unicode(k))
        return '{' + ', '.join(items) + '}'


class TZIndex(object):
    'Index of all MUD objects. A Borg object with shared state.'

    _state = {}
    def __new__(cls, *p, **k):
        self = object.__new__(cls, *p, **k)
        self.__dict__ = cls._state
        return self

    def __init__(self):
        if not hasattr(self, 'dbroot'):
            import db
            zodb = db.TZODB()
            self.dbroot = zodb.root

    def idx(self):
        '''Return the root of this index.
        Should reference a TZDict or a PersistentDict.

        '''

        return self.dbroot['_index']

    def add(self, tzobj):
        'Insert an entry in to the index.'

        self.idx()[tzobj.tzid] = tzobj

    def remove(self, tzobj):
        'Delete the given entry from the index.'

        del self.idx()[tzobj.tzid]

    def get(self, tzid):
        'Return the entry with the given id number.'

        i = self.idx()
        return i.get(tzid, None)

    def ls(self):
        'Return a list of the objects referenced by the index.'

        idx = self.idx()
        return idx.values()


def db_init():
    print 'initializing ZODB'

    import db
    zodb = db.TZODB()
    dbroot = zodb.root

    dbroot['DB_VERSION'] = DB_VERSION


    dbroot['_index'] = db.TZDict()


    dbroot['share'] = db.TZDict()
    dbroot['share']['tzid'] = 0
    zodb.commit()


    dbroot['rooms'] = db.TZDict()
    zodb.commit()

    dbroot['exits'] = db.TZDict()
    zodb.commit()


    import rooms
    import exits
    void = rooms.Room('void', 'A very dark darkness')
    house = rooms.Room('house', 'A nice little house.')

    north = exits.Exit('the light', room=void,
                        destination=house)


    dbroot['players'] = db.TZDict()
    dbroot['players']['_index'] = db.TZDict()
    zodb.commit()

    dbroot['items'] = db.TZDict()
    import items
    rose = items.Rose()
    house.add(rose)


    dbroot['admin'] = PersistentList()
    dbroot['wizard'] = PersistentList()

    dbroot['mobs'] = db.TZDict()

    zodb.commit()

def db_upgrade(from_version, to_version):
    print 'upgrading ZODB'

    if to_version > from_version + 1 or to_version <= from_version:
        print '  Must upgrade 1 version at a time.'
        return

    import db
    import zc
    try:
        zodb = db.TZODB()
    except zc.lockfile.LockError:
        print '  DB locked. Shut down server before upgrading'
        return

    version = zodb.version()
    if version != from_version:
        print '  Current version:', version
        print '  Must upgrade from current version.'
        return

    for mod in 'players', 'mobs', 'items', 'rooms', 'exits':
        module = __import__(mod)
        if hasattr(module, 'upgrade'):
            module.upgrade(from_version, to_version)
    dbroot = zodb.root

    dbroot['DB_VERSION'] = to_version
    zodb.commit()

    db_upgradeall()

def db_upgradeall():
    import share
    share.upgradeall()

def db_pack():
    if len(sys.argv) == 2:
        fname = None
    elif len(sys.argv) == 3:
        fname = sys.argv[2]
    else:
        print 'Usage: db.py pack [filename]'
        sys.exit(1)

    print 'Packing DB'
    zodb = TZODB(fname)
    dbroot = zodb.root

    zodb.pack()

    zodb.commit()

    import conf
    import glob
    pths = glob.glob('%s/*%s.*' % (conf.backupdir, conf.datafsname))
    for pth in pths:
        os.remove(pth)

def db_depopulate():
    if len(sys.argv) == 2:
        fname = None
    elif len(sys.argv) == 3:
        fname = sys.argv[2]
    else:
        print 'Usage: db.py depopulate [filename]'
        sys.exit(1)

    print 'removing players from DB'
    zodb = TZODB(fname)
    dbroot = zodb.root

    names = dbroot['players'].keys()
    for name in names:
        if name == '_index':
            continue
        player = dbroot['players'][name]
        room = player.room
        if room is not None:
            room.rmplayer(player)
        del dbroot['players'][name]
        del dbroot['players']['_index'][player.tzid]
        del dbroot['_index'][player.tzid]
        if name in dbroot['admin']:
            dbroot['admin'].remove(name)
        if name in dbroot['wizard']:
            dbroot['wizard'].remove(name)

    zodb.commit()

    import conf
    import glob
    pths = glob.glob('%s/*%s.*' % (conf.backupdir, conf.datafsname))
    for pth in pths:
        os.remove(pth)

def db_display(fname=None):
    import db
    zodb = db.TZODB(fname, read_only=True)
    print zodb


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'init':
        db_init()
    elif len(sys.argv) > 1 and sys.argv[1] == 'upgrade':
        from_version = int(sys.argv[2])
        to_version = int(sys.argv[3])
        db_upgrade(from_version, to_version)
    elif len(sys.argv) > 1 and sys.argv[1] == 'upgradeall':
        db_upgradeall()
    elif len(sys.argv) > 1 and sys.argv[1] == 'pack':
        db_pack()
    elif len(sys.argv) > 1 and sys.argv[1] == 'depopulate':
        db_depopulate()
    elif len(sys.argv) > 1:
        fname = sys.argv[1]
        print 'Reading backup ZODB', fname
        db_display(fname)
    else:
        print 'Reading main ZODB'
        db_display()
