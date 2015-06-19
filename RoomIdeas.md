What kinds of rooms would you like to create?



Right now I am thinking about ...

A room which can only hold so many characters. (done -- SmallRoom)


## Travel Ideas from j@ ##

"enter room" to enter a room with 1 entrance
```
A flower-laden hill You see the entrance to a dark cave.
>> enter cave
A dark cave You see an exit leading out.
```

**This is mostly done as of [r178](https://code.google.com/p/tzmud/source/detail?r=178)**



"out" to leave a room with 1 exit
```
>> out
A flower-laden hill You see the entrance to a dark cave.
```

**This is mostly done as of [r167](https://code.google.com/p/tzmud/source/detail?r=167)**

Player can say "out", "leave", "exit", "go out"


"enter" and "leave" are usually associated with Exits specifically marked
as "in" and "out" and they will not work with any other exits, say "south", "west", etc. That appears more reasonable and may prevent illogical messages.


I think it is pretty good as it is... "enter" is just a synonym for "go",
while "out", "leave", and "exit" are special-cased for rooms with only
one exit.

Give it a try as-is and see how it works.