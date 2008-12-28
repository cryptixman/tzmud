import mobs
import items
import rooms


class Bear(mobs.Mob):
    'Grr...'

    name = 'bear'
    short = 'A large brown bear.'

mobs.register_mob(Bear)



class Boots(items.Item):
    'Comfy footwear.'

    name = 'boots'
    short = 'An old pair of hiking boots.'
    wearable = True

items.register_item(Boots)



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

rooms.register_room(Library)
