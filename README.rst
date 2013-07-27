Maze
=====

Small ncurses maze game developed in 24h during the Euskal Encounter XXI FOSS coding competition


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
