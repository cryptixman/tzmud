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

if __name__ == '__main__':
    import os, sys
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

    def __init__(self, fdt=None):
        if fdt is None:
            fname = datafs
        else:
            fname = '%s/%s.%s' % (backupdir, fdt, datafsname)

        if not hasattr(self, 'storage'):
            self.open(fname)

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




if __name__ != '__main__':
    zodb = TZODB()
    dbroot = zodb.root
    commit = zodb.commit


else:
    import os
    import sys

    etc = os.path.abspath('etc')
    sys.path.append(etc)

    from db import TZODB
    from db import TZDict

    if len(sys.argv) > 1 and sys.argv[1] == 'init':
        print 'initializing ZODB'

        zodb = TZODB()
        dbroot = zodb.root


        dbroot['_index'] = TZDict()


        dbroot['share'] = PersistentDict()
        dbroot['share']['tzid'] = 0
        zodb.commit()



        dbroot['rooms'] = TZDict()
        zodb.commit()

        import rooms
        void = rooms.Room('void', 'A very dark darkness')
        rooms.add(void)
        house = rooms.Room('house', 'A nice little house.')
        rooms.add(house)

        #void = rooms.getname('void')
        #while len(void.players):
            #void.players.pop()

        house = rooms.getname('house')
        north = rooms.Exit('north', destination=house)
        void.addexit(north)
        south = rooms.Exit('south', destination=void)
        house.addexit(south)


        dbroot['players'] = TZDict()
        dbroot['players']['_index'] = TZDict()

        import players
        player = players.Player('Admin', 'Initial Admin User.')
        player.set_password('pw')

        player = players.Player('Awiz', 'Initial Wizard User.')
        player.set_password('pw')
        player.home = rooms.getname('house')
        rooms.getname('house').owner = players.getname('Awiz').tzid

        player = players.Player('Aplayer', 'Initial player.')
        player.set_password('pw')


        dbroot['items'] = TZDict()
        import items
        rose = items.Rose()
        items.add(rose)
        house = rooms.getname('house')
        house.add(rose)
        cup = items.Cup()
        lee3 = players.getname('lee3')
        lee3.add(cup)


        dbroot['admin'] = PersistentList(['lee'])
        dbroot['wizard'] = PersistentList(['lee', 'lee2'])

        dbroot['mobs'] = TZDict()

        zodb.commit()

    elif len(sys.argv) > 1 and sys.argv[1] == 'upgrade':
        print 'upgrading ZODB'

        for mod in 'players', 'mobs', 'items', 'rooms':
            module = __import__(mod)
            if hasattr(module, 'upgrade'):
                module.upgrade()

        zodb = TZODB()
        dbroot = zodb.root

    elif len(sys.argv) > 1:
        fdt = sys.argv[1]
        print 'reading backup ZODB', fdt

        zodb = TZODB(fdt)
        dbroot = zodb.root

    else:
        zodb = TZODB()
        dbroot = zodb.root


    print dbroot
