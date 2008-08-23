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


'''Functions and configuration for adding colors to server output.'''


yes = dict(
    reset = '\033[0m',
    red = '\033[31m',
    blue = '\033[36m',
    green = '\033[32m',
    yellow = '\033[33m',
    magenta = '\033[35m',
    white = '\033[37m',
    bold = '\033[1m'
)

no = dict(
    reset = '',
    red = '',
    blue = '',
    green = '',
    yellow = '',
    magenta = '',
    white = '',
    bold = ''
)



def blue(txt):
    return bold('%(blue)s' + txt + '%(reset)s')

def red(txt):
    return bold('%(red)s' + txt + '%(reset)s')

def green(txt):
    return bold('%(green)s' + txt + '%(reset)s')

def yellow(txt):
    return bold('%(yellow)s' + txt + '%(reset)s')

def magenta(txt):
    return bold('%(magenta)s' + txt + '%(reset)s')

def white(txt):
    return bold('%(white)s' + txt + '%(reset)s')

def bold(txt):
    return '%(bold)s' + txt + '%(reset)s'

