import mobs
import items
import rooms
from share import register_plugin


class Bear(mobs.Mob):
    'Grr...'

    name = 'bear'
    short = 'A large brown bear.'

register_plugin(Bear)



class Boots(items.Item):
    'Comfy footwear.'

    name = 'boots'
    short = 'An old pair of hiking boots.'
    wearable = True

register_plugin(Boots)



class Library(rooms.Room):
    'Please, no talking in the library.'

    name = 'library'
    short = 'Shh... no talking'

    def action(self, info):
        act = info['act']
        if act in ('say', 'shout'):
            actor = info['actor']
            actor.message('Shh! No talking!')
        else:
            rooms.Room.action(self, info)

register_plugin(Library)



class VaultRoom(rooms.Room):
    'Room with a voice-activated door to another room.'

    name = 'vault room'

    def __init__(self, name=''):
        rooms.Room.__init__(self, name)
        self.make_vault()

    def make_vault(self):
        vault = rooms.Room('vault')
        x = rooms.Exit('the vault', room=self, destination=vault,
                                                    return_name='exit')
        x.locked = True
        self.the_vault_exit = x

    def near_say(self, info):
        raw = info['raw']
        x = self.the_vault_exit
        if raw == 'open sesame' and x.locked:
            x.locked = False
            self.action(dict(act='unlock', actor=None, door=x, key=None))
        elif raw == 'close sesame' and not x.locked:
            x.locked = True
            self.action(dict(act='lock', actor=None, door=x, key=None))

register_plugin(VaultRoom)


from share import str_attr
class PasswordDoor(rooms.Exit):
    'A door with a voice-activated lock.'

    name = 'pw door'
    locked = True
    password = str_attr('password', default='activate')
    settings = ['password']

    def near_say(self, info):
        raw = info['raw']
        if raw == self.password and self.locked:
            self.locked = False
            self.room.action(dict(act='unlock', actor=None, door=self, key=None))
        elif raw == self.password and not self.locked:
            self.locked = True
            self.room.action(dict(act='lock', actor=None, door=self, key=None))

register_plugin(PasswordDoor)
