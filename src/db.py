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

from ZODB import FileStorage, DB
import transaction
from persistent.dict import PersistentDict
from persistent.list import PersistentList

from twisted.internet import reactor

if __name__ == '__main__':
    import os
    import sys

    etc = os.path.abspath('etc')
    sys.path.append(etc)

from conf import datafs, backupdir, datafsname

class TZODB(object):
    'Database object. A Borg object with state which all share.'

    _state = {}
    def __new__(cls, *p, **k):
        self = object.__new__(cls, *p, **k)
        self.__dict__ = cls._state
        return self

    def __init__(self, fname=None):
        if fname is None:
            fname = datafs
        else:
            fname = '%s/%s' % (backupdir, fname)

        if not hasattr(self, 'storage'):
            self.open(fname)
            reactor.callLater(30, self.pack_regularly)

    def open(self, fname):
        'Open connection to the database.'

        self.storage = FileStorage.FileStorage(fname)
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
        self.storage.pack(time.time(), None)
        print 'DB Packed'

    def pack_regularly(self):
        'Pack the DB every pack_interval seconds.'

        self.pack()
        pack_interval = 600 #seconds (10 minutes)
        reactor.callLater(pack_interval, self.pack_regularly)


class TZDict(PersistentDict):
    'Customized persistent dictionary.'

    def __repr__(self):
        items = []
        for k, v in self.items():
            try:
                items.append('%s: %s' % (k, v.name))
            except AttributeError:
                items.append(str(k))
        return '{' + ', '.join(items) + '}'


def tzid():
    'Increment the id counter and return the next available id number.'

    previd = dbroot['share']['tzid']
    nextid = previd + 1
    dbroot['share']['tzid'] = nextid
    return nextid


class TZIndex(object):
    'Index of all MUD objects. A Borg object with shared state.'

    _state = {}
    def __new__(cls, *p, **k):
        self = object.__new__(cls, *p, **k)
        self.__dict__ = cls._state
        return self

    def index(self):
        '''Return the root of this index.
        Should reference a TZDict or a PersistentDict.

        '''

        return dbroot['_index']

    def add(self, tzobj):
        'Insert an entry in to the index.'

        self.index()[tzobj.tzid] = tzobj

    def remove(self, tzobj):
        'Delete the given entry from the index.'

        del self.index()[tzobj.tzid]

    def get(self, tzid):
        'Return the entry with the given id number.'

        i = self.index()
        return i.get(tzid, None)

    def ls(self):
        'Return a list of the objects referenced by the index.'

        return self.index().values()


def db_init():
    print 'initializing ZODB'

    zodb = TZODB()
    dbroot = zodb.root


    dbroot['_index'] = TZDict()


    dbroot['share'] = TZDict()
    dbroot['share']['tzid'] = 0
    zodb.commit()


    dbroot['rooms'] = TZDict()
    zodb.commit()


    import rooms
    void = rooms.Room('void', 'A very dark darkness')
    house = rooms.Room('house', 'A nice little house.')

    north = rooms.Exit('the light', room=void,
                        destination=house)


    dbroot['players'] = TZDict()
    dbroot['players']['_index'] = TZDict()


    dbroot['items'] = TZDict()
    import items
    rose = items.Rose()
    house.add(rose)


    dbroot['admin'] = PersistentList()
    dbroot['wizard'] = PersistentList()

    dbroot['mobs'] = TZDict()

    zodb.commit()

def db_upgrade():
    print 'upgrading ZODB'

    for mod in 'players', 'mobs', 'items', 'rooms':
        module = __import__(mod)
        if hasattr(module, 'upgrade'):
            module.upgrade()

    zodb = TZODB()
    dbroot = zodb.root

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
    os.system('rm %s/*%s.*' % (conf.backupdir, conf.datafsname))

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
    os.system('rm %s/*%s.*' % (conf.backupdir, conf.datafsname))

def db_display(fname=None):
    zodb = TZODB(fname)
    dbroot = zodb.root
    print dbroot


if __name__ != '__main__':
    try:
        zodb = TZODB()
        dbroot = zodb.root
        commit = zodb.commit
    except:
        # If the main database is in use, this will fail,
        # In that case, reinitializing with a different name
        # should allow access to the other database.
        pass

else:
    from db import TZODB
    from db import TZDict

    if len(sys.argv) > 1 and sys.argv[1] == 'init':
        db_init()
    elif len(sys.argv) > 1 and sys.argv[1] == 'upgrade':
        db_upgrade()
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
