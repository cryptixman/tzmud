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


'''PyParsing parser for MUD commands.

There is a parser for general commands, and one for wizard commands.

Run the module for a simple interface to test what the output of the
parser will be for given inputs.

'''

from pyparsing import Word, alphas, nums, alphanums, printables, oneOf, OneOrMore, Optional, CaselessLiteral, ParseException, LineEnd, replaceWith, Suppress, Combine, Empty, restOfLine, SkipTo, FollowedBy, alphas8bit

import conf
if conf.allow_utf8:
    all_alphas = u''.join(unichr(c) for c in xrange(256)
                                        if unichr(c).isalpha())
    utf8_alphas_keep = all_alphas[55:]
    alphas = alphas + utf8_alphas_keep
    alphanums = alphas + nums
    printables = u''.join(unichr(c) for c in xrange(65536)
                                        if not unichr(c).isspace())


def toint(s, l, t):
    return int(t[0])

space = OneOrMore(' ')
objnameref = Combine(OneOrMore(Word(alphanums)),
                        joinString=' ', adjacent=False)('objname')
number = Word(nums)
number.setParseAction(toint)
objtzidref = Suppress('#') + number('objtzid')
objref = objnameref | objtzidref

obj2nameref = Combine(OneOrMore(Word(alphanums)),
                        joinString=' ', adjacent=False)('obj2name')
number2 = Word(nums)
number2.setParseAction(toint)
obj2tzidref = Suppress('#') + number2('obj2tzid')
obj2ref = obj2nameref | obj2tzidref


look_verb1 = oneOf('look l', caseless=True)('verb')
look_verb1.setParseAction(replaceWith('look'))
look_verb2a = CaselessLiteral('look ')
look_verb2b = CaselessLiteral('l ')
look_verb2 = (look_verb2a|look_verb2b)('verb')
look_verb2.setParseAction(replaceWith('look'))
look1 = look_verb1 + LineEnd()
look2 = look_verb2 + Optional(CaselessLiteral('at ')) + Optional(objref) + LineEnd()
look = look1 | look2


info_verb = CaselessLiteral('info')('verb')
info = info_verb + Optional(objref) + LineEnd()


time_verb = CaselessLiteral('time')('verb')
time = time_verb + LineEnd()


get_verb = oneOf('get take', caseless=True)('verb')
get_verb.setParseAction(replaceWith('get'))
get = get_verb + objref + LineEnd()


drop_verb = CaselessLiteral('drop')('verb')
drop = drop_verb + Optional(number)('number') + objref + LineEnd()


in_ = Suppress(CaselessLiteral('in '))
thingname = Combine(OneOrMore(~in_ + Word(alphanums)),
                             joinString=' ', adjacent=False)('objname')
put_verb = CaselessLiteral('put')('verb')
put = put_verb + (thingname|objtzidref) + in_ + obj2ref


from_ = Suppress(CaselessLiteral('from '))
thingname = Combine(OneOrMore(~from_ + Word(alphanums)),
                             joinString=' ', adjacent=False)('objname')
take_verb = oneOf('take remove', caseless=True)('verb')
take_verb.setParseAction(replaceWith('take'))
take = take_verb + Optional(Optional(number)('number')) + (thingname|objtzidref) + from_ + obj2ref


inventory_verb = oneOf('inventory inv i')('verb')
inventory_verb.setParseAction(replaceWith('inventory'))
inventory = inventory_verb + LineEnd()


wear_verb = CaselessLiteral('wear')('verb')
wear = wear_verb + objref


remove_verb = CaselessLiteral('remove')('verb')
remove = remove_verb + objref


go_verb = oneOf('go enter')('verb')
go_verb.setParseAction(replaceWith('go'))
go = go_verb + Optional('to') + objref + LineEnd()


on_ = Suppress(CaselessLiteral('on '))
use_verb = CaselessLiteral('use')('verb')
words_without_on = Combine(OneOrMore(~on_ + Word(alphanums)),
                             joinString=' ', adjacent=False)('objname')
use = use_verb + (words_without_on|objtzidref) + Optional(on_ + obj2ref)


with_ = Suppress(CaselessLiteral('with '))
lock_verb = CaselessLiteral('lock')('verb')
lock_obj_name = Combine(OneOrMore(~with_ + Word(alphanums)),
                             joinString=' ', adjacent=False)('objname')
lock1 = lock_verb + (lock_obj_name|objtzidref) + with_ + obj2ref
lock2 = lock_verb + objref + LineEnd()
lock = lock1 | lock2

unlock_verb = CaselessLiteral('unlock')('verb')
unlock1 = unlock_verb + (lock_obj_name|objtzidref) + with_ + obj2ref
unlock2 = unlock_verb + objref + LineEnd()
unlock = unlock1 | unlock2


follow_verb = CaselessLiteral('follow')('verb')
follow = follow_verb + Optional(objref) + LineEnd()


exits = CaselessLiteral('exits')('verb') + LineEnd()


say_verb = oneOf('say "', caseless=True)('verb')
say_verb.setParseAction(replaceWith('say'))
words = Combine(OneOrMore(Word(printables)),
                        joinString=' ', adjacent=False)('message')
say = say_verb + words


to_ = Suppress(CaselessLiteral('to '))
words_without_to = Combine(OneOrMore(~to_ + Word(alphanums)),
                             joinString=' ', adjacent=False)('objname')
listen_verb = CaselessLiteral('listen')('verb')
listen = listen_verb + Optional(to_) + objref


shout_verb = CaselessLiteral('shout')('verb')
shout = shout_verb + words


emote_verb = oneOf('emote :', caseless=True)('verb')
emote_verb.setParseAction(replaceWith('emote'))
emote = emote_verb + words


quit_verb = oneOf('quit', caseless=True)('verb')
quit_verb.setParseAction(replaceWith('quit'))
quit_ = quit_verb + LineEnd()


who_verb = CaselessLiteral('who')('verb')
who = who_verb + LineEnd()


stats_verb = CaselessLiteral('stats')('verb')
stats = stats_verb + LineEnd()


set0_verb = CaselessLiteral('set')('verb')
set1_verb = CaselessLiteral('set ')('verb')
set1_verb.setParseAction(replaceWith('set'))
set_var = Word(alphas)('var')
set_val = Word(alphas)('val')
set0 = set0_verb + LineEnd()
set1 = set1_verb + set_var + Optional(Optional('=' + set_val)) + LineEnd()
set = set0 | set1

unset_verb = CaselessLiteral('unset')('verb')
unset = unset_verb + set_var + LineEnd()


password_verb = CaselessLiteral('password')('verb')
password_word = Word(printables)
password = password_verb + password_word('old') + password_word('new') + LineEnd()


help_verb = oneOf('help ?', caseless=True)('verb')
help_verb.setParseAction(replaceWith('help'))
help = help_verb + Optional(Word(alphas)('topic')) + LineEnd()


xyzzy = CaselessLiteral('xyzzy')('verb') + LineEnd()


catchall = objnameref('verb')


section = Empty()('section')
section.setParseAction(replaceWith('actions'))

actions_parser = section + (info | time | take | get | drop | put | inventory | wear | remove | use | lock | listen | look | unlock | follow | exits | say | shout | emote | quit_ | who | stats | set | unset | password | xyzzy | help | go | catchall)



wiz = CaselessLiteral('@')('section')
wiz.setParseAction(replaceWith('wizard'))


info_verb = CaselessLiteral('info')('verb')
info = info_verb + Optional(objref) + LineEnd()


teleport_verb = CaselessLiteral('teleport')('verb')
teleport_to = obj2ref
teleport1 = teleport_verb + Optional(teleport_to) + LineEnd()

thingname = Combine(OneOrMore(~to_ + Word(alphanums)),
                             joinString=' ', adjacent=False)('objname')
teleport2 = teleport_verb + Optional(thingname|objtzidref) + to_ + obj2ref
teleport = teleport2 | teleport1

summon_verb = CaselessLiteral('summon')('verb')
summon = summon_verb + objref + LineEnd()

dig_verb = CaselessLiteral('dig')('verb')

returnby_ = Suppress(CaselessLiteral('return by '))

dig_out_name = Combine(OneOrMore(~to_ + Word(alphanums)),
                        joinString=' ', adjacent=False)('exitoutname')
dig_out_id = Suppress('#') + number('exitouttzid')
dig_out = dig_out_name|dig_out_id

dig_dest_name = Combine(OneOrMore(~returnby_ + Word(alphanums)),
                            joinString=' ', adjacent=False)('destname')
dig_dest_id = Suppress('#') + number('desttzid')
dig_dest = dig_dest_name|dig_dest_id

dig_in_name = Combine(returnby_ + OneOrMore(Word(alphanums)),
                        joinString=' ', adjacent=False)('exitinname')
dig_in_id = returnby_ + Suppress('#') + number('exitintzid')
dig_in = Optional(dig_in_name|dig_in_id)

dig_ = dig_verb + dig_out + to_ + dig_dest + dig_in


list_verb = CaselessLiteral('list')('verb')
list_type = oneOf('players items rooms mobs')('type')
list_ = list_verb + list_type


as_ = Suppress(CaselessLiteral('as '))
clone_verb = CaselessLiteral('clone')('verb')
clone_name = Combine(OneOrMore(~as_ + Word(alphanums)),
                        joinString=' ', adjacent=False)('objname')
new_name = Combine(OneOrMore(Word(alphanums)),
                        joinString=' ', adjacent=False)('new')
clone_obj = clone_name|objtzidref
clone = clone_verb + clone_obj + Optional(as_ + new_name)


study_verb = CaselessLiteral('study')('verb')
study = study_verb + objnameref + LineEnd()


rename_verb = CaselessLiteral('rename')('verb')
rename_obj_name = Combine(OneOrMore(~to_ + Word(alphanums)),
                             joinString=' ', adjacent=False)('objname')
rename = rename_verb + Optional(rename_obj_name|objtzidref) + to_ + new_name


is_ = Suppress(CaselessLiteral('is '))
for_ = Optional(Suppress(CaselessLiteral('for ')))
short_verb = CaselessLiteral('short')('verb')
obj_name = Combine(OneOrMore(~is_ + Word(alphanums)),
                             joinString=' ', adjacent=False)('objname')
new_desc = Combine(OneOrMore(Word(printables)),
                        joinString=' ', adjacent=False)('new')
short = short_verb + for_ + Optional(obj_name|objtzidref) + is_ + new_desc


long_verb = CaselessLiteral('long')('verb')
long_ = long_verb + for_ + Optional(obj_name|objtzidref) + is_ + new_desc


wizset = set1_verb + words_without_on('setting') + on_ + (words_without_to|objtzidref) + Optional(to_ + words('value'))

wizunset = unset_verb + words_without_on('setting') + on_ + (words_without_to|objtzidref)


destroy_verb = CaselessLiteral('destroy')('verb')
destroy = destroy_verb + objref


wizard_parser = wiz + (info | teleport | summon | dig_ | lock1 | list_ | clone | study | rename | short | long_ | destroy | wizset | wizunset | help | catchall)


full_parser = actions_parser | wizard_parser



if __name__ == '__main__':
    cmd = ''
    while cmd != 'q':
        cmd = raw_input('::>')
        try:
            p = full_parser.parseString(cmd)
            print p
            print p.asDict()
        except ParseException:
            print 'no match'
