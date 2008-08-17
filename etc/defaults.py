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


python_location = '/usr/bin/python'
python_version = '2.5'
python = python_location + python_version

twistd = '/usr/bin/twistd'
twistdlog = 'var/log/twistd.log'
twistdpid = 'var/run/twistd.pid'
twistdpid2 = 'var/run/twistd2.pid'
tztac = 'tzmud.tac'

tzcontrol = 'tzcontrol.py'

src = 'src'

dbmod = 'src/db.py'

dbdir = 'var/db'
datafsname = 'Data.fs'
datafs = '%s/%s' % (dbdir, datafsname)
backupdir = 'var/backup'

port = 4444

home_id = 1
