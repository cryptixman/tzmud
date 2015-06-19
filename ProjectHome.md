# TZMud #
## A Python MUD Server ##

TZMud is a server to host a multi-user domain (MUD) in the tradition of LPMud, but implemented in the Python programming language.

TZMud uses several high-quality Python libraries to handle basic functions so that it can concentrate on the actual MUD functions:

  * Twisted to handle networking and event loop,
  * ZODB to store the data, and
  * Pyparsing to parse player input.


TZMud is currently tested only on Ubuntu Linux. Any OS-specific code that causes the server to not run on your system can be considered a bug. Please file an issue (with a patch if possible :o) so we can correct the problem.