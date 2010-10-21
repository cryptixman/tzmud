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


debug = True
restart_delay = 2

python = '/usr/bin/python2.6'
python_version = '2.6'

twistd = '/usr/bin/twistd'
twistdlog = 'var/log/twistd.log'
twistdpid = 'var/run/twistd.pid'
tztac = 'tzmud.tac'

tzcontrol = 'tzcontrol.py'

src = 'src'
plugins = 'src/plugins'
load_plugins = True

dbmod = 'src/db.py'

dbdir = 'var/db'
datafsname = 'Data.fs'
datafs = '%s/%s' % (dbdir, datafsname)
backupdir = 'var/db/backup'

port = 4444
local_only = True

home_id = 1

svn = '/usr/bin/svn'

web = False
web_port = 8888
web_local_only = True

enable_cmd_py = False

allow_utf8 = False

speechmode_default = False
talkmode = False # True: all players can use talk command. False: wizards only.

ansi_color_default = False
