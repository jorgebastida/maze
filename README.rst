Maze
=====

Small ncurses maze game developed in 24h (~18h) during the Euskal Encounter XXI FOSS coding competition.

For the creation of the maze I've use a depth-First search algorithm which creates "perfect" mazes (without contiguous spaces or blocks).
After creating the maze, the game choose a random exit and a random start position for the player (trying to put him as far as
possible from the exit).

For the networking I've use ØMQ. The client polls the server every few milliseconds updating the position of the user, and as response it receives the position of the server's user.

You are always the player ``(1)`` and your opponent ``(2)``.

You can control the player using:

* ←  : Left arrow
* →   : Right arrow
* ↑   : Up arrow
* ↓   : Down arrow
* Esc : Exit


Requirements
------------

* Python 2.7
* pyzmq==13.1.0


Features
--------

* Random maze generator.
* Create mazes with arbitrary width and height.
* Random start and end positions.
* Single Player mode.

  * With progressive difficulty.
  * Number of moves.
  * Time spent.

* Multiplayer mode over the network.

  * Challenge your friends over the network!
  * Discover how log it took you.

* Sound!! ~ Kind of ;)
* Multi platform... *ish.
* In color!

Single Player
-------------

You can start a single player game running ``python game.py``.

If you want to start a game using a bigger maze, run: ``python game.py --width=14 --height=20``.


Multi Player
------------

You can start a multiplayer server running ``python game.py --server`` this will create a server on ``8123``.
Using another terminal or computer, you can connect to this server using: ``python game.py --connect localhost:8123``.

Enjoy!

Help
----

    usage: game.py [-h] [--width WIDTH] [--height HEIGHT] [--server]
                   [--server-port SERVER_PORT] [--connect SERVER_ADDRESS]

    Maze game for the Euskal Encounter XXI.

    optional arguments:
      -h, --help            show this help message and exit
      --width WIDTH         Maze width
      --height HEIGHT       Maze height
      --server              Start a maze server
      --server-port SERVER_PORT
                            Server port
      --connect SERVER_ADDRESS
                            Server host:port


ScreenShot
-----------

.. image:: https://github.com/jorgebastida/maze/raw/master/screenshot.png


Known bugs
-----------

* If you want to create big mazes, be sure that your terminal is big enough, or the program will raise an error.
* Sometimes the server exit abnormaly.
* Pulsation scores are not yet implemented on multiplayer.

