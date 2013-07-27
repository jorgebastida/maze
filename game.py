#!/usr/bin/python
import sys
import time
import base64
import random
import argparse
import curses
import pickle
import threading
from functools import partial
from cStringIO import StringIO

import zmq

KEY_DOWN = 258
KEY_UP = 259
KEY_LEFT = 260
KEY_RIGHT = 261
KEY_ESC = 27

CELL_WIDTH = 4
CELL_HEIGHT = 2


class MazeException(Exception):
    pass


class ConnectionError(MazeException):
    pass


class MazeExit(Exception):
    pass


class MazeWin(Exception):
    pass


class MazeLose(Exception):
    pass


class Cell(object):

    def __init__(self, x, y, north=True, west=True, south=True, east=True,
                 north_limit=False, west_limit=False, south_limit=False,
                 east_limit=False):
        self.x = x
        self.y = y
        self.north = north
        self.west = west
        self.south = south
        self.east = east
        self.north_limit = north_limit
        self.west_limit = west_limit
        self.south_limit = south_limit
        self.east_limit = east_limit

    def intact_walls(self):
        return all([self.north, self.west, self.south, self.east])

    def destroy_wall_to(self, cell):
        if cell.x < self.x:
            self.west = False
        elif cell.x > self.x:
            self.east = False
        elif cell.y > self.y:
            self.south = False
        else:
            self.north = False

    def __repr__(self):
        return "[{0},{1}]".format(self.x, self.y)


class Maze(object):

    def __init__(self, width=10, height=10, exit=None):
        self.width = width
        self.height = height
        self.cells = [[None] * width for i in xrange(height)]

        for y in xrange(height):
            for x in xrange(width):
                self.cells[y][x] = Cell(x=x,
                                        y=y,
                                        north_limit=y == 0,
                                        west_limit=x == 0,
                                        south_limit=y == height - 1,
                                        east_limit=x == width - 1)

        cell_x = random.randint(0, width - 1)
        cell_y = random.randint(0, height - 1)
        stack = [self.cells[cell_y][cell_x]]

        visited_cells = 1
        while visited_cells < (width * height):
            cell = self.cells[cell_y][cell_x]
            neighbors = []

            def check_neighbor(x, y):
                if 0 <= x < width and 0 <= y < height and self.cells[y][x].intact_walls():
                    neighbors.append(self.cells[y][x])

            check_neighbor(cell_x, cell_y - 1)
            check_neighbor(cell_x, cell_y + 1)
            check_neighbor(cell_x - 1, cell_y)
            check_neighbor(cell_x + 1, cell_y)

            if neighbors:
                selected = random.sample(neighbors, 1)[0]
                cell.destroy_wall_to(selected)
                selected.destroy_wall_to(cell)
                stack.append(selected)
                cell_x = selected.x
                cell_y = selected.y
                visited_cells += 1
            else:
                previous = stack.pop()
                cell_x = previous.x
                cell_y = previous.y

        # Set exit
        if exit:
            exit_cell = self.cells[exit[1]][exit[0]]
            if exit_cell.north_limit:
                exit_cell.north = False
            elif exit_cell.south_limit:
                exit_cell.south = False
            elif exit_cell.east_limit:
                exit_cell.east = False
            else:
                exit_cell.west = False


class Player(object):

    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.movements = 0
        self.win = False


class Game(object):

    def __init__(self, screen, width, height, playing=False):
        self.screen = screen
        self.exit = random.sample([[0, i] for i in range(0, height)] + [[i, 0] for i in range(0, width)], 1)[0]
        self.maze = Maze(width=width, height=height, exit=self.exit)
        self.start_time = 0
        self.finished = False
        self.client = None
        self.playing = playing
        #
        # Calculate the start point. The Manhattan distance between
        # this point and the exit must be at least (width + height / 3)
        # This is a made-up number.
        #
        distance = 0
        min_distance = width + height / 3

        while distance < min_distance:
            player_coords = random.randint(0, width - 1), random.randint(0, height - 1)
            distance = abs(player_coords[0] - self.exit[0]) + abs(player_coords[1] - self.exit[1])

        self.players = [Player(*player_coords)]

    def set_client(self, client):
        self.client = client

    def add_player(self):
        self.players.append(Player(0, 0))

    def start(self, wait=True):

        self.screen.clear()

        if wait:
            self.screen.addstr(0, 0, "   Press any key to start a {0}x{1} maze!".format(self.maze.width, self.maze.height), curses.A_BOLD)
            self.screen.refresh()

            # Wait to any key
            while True:
                key = self.screen.getch()
                if key:
                    break

            if self.client:
                print self.client.send("go go")

            self.playing = True
        else:
            self.screen.addstr(0, 0, "   Be ready! The game will start soon!".format(self.maze.width, self.maze.height), curses.A_BOLD)
            self.screen.refresh()

            while not self.playing:
                time.sleep(0.1)

        self.start_time = time.time()

        # Clear the screen
        self.screen.clear()

        while True:
            self.draw()
            key = self.screen.getch()

            if self.finished:
                self.screen.clear()
                raise MazeLose()

            # Move player using the key pad
            if key in (KEY_UP, KEY_DOWN, KEY_RIGHT, KEY_LEFT, KEY_ESC):

                # Exit if the player press esc
                if key == KEY_ESC:
                    raise MazeExit("Bye!")

                self.move_player(0, key)
                self.draw()

                # Check if the player is in the exit cell

                if self.players[0].x == self.exit[0] and self.players[0].y == self.exit[1]:
                    self.finished = True
                    self.playing = False
                    self.players[0].win = True
                    self.total_time = int(time.time() - self.start_time)
                    curses.beep()
                    text = " You Win! ({0} sec.) ".format(self.total_time)
                    self.screen.addstr(max([0, self.maze.height / 2]) * CELL_HEIGHT, max([0, max([0, self.maze.width / 2]) * CELL_WIDTH - (len(text) / 2), 0]), text, curses.color_pair(1))
                    self.screen.refresh()
                    if self.client:
                        self.client.send("loser loser")
                        raise MazeWin(self.total_time)
                    else:
                        break

    def move_player(self, number, direction):
        player = self.players[number]
        cell = self.maze.cells[player.y][player.x]
        action = False
        if direction == KEY_UP:
            if not cell.north:
                player.y -= 1
                action = True
        elif direction == KEY_DOWN:
            if not cell.south:
                player.y += 1
                action = True
        elif direction == KEY_RIGHT:
            if not cell.east:
                player.x += 1
                action = True
        elif direction == KEY_LEFT:
            if not cell.west:
                player.x -= 1
                action = True

        if action:
            player.movements += 1
            if self.client:
                self.client.send_update()

    def draw(self):
        for row_index, row in enumerate(self.maze.cells):

            #
            # Draw top characters
            #

            for cell in row:
                self.screen.addstr(cell.y * CELL_HEIGHT, cell.x * CELL_WIDTH, "+")
                if cell.north:
                    self.screen.addstr(cell.y * CELL_HEIGHT, cell.x * CELL_WIDTH + 1, "---")
                else:
                    self.screen.addstr(cell.y * CELL_HEIGHT, cell.x * CELL_WIDTH + 1, "   ")

            self.screen.addstr(row_index * CELL_HEIGHT, self.maze.width * CELL_WIDTH, "+")

            #
            # Draw cell body
            #

            for cell in row:
                if cell.west:
                    self.screen.addstr(cell.y * CELL_HEIGHT + 1, cell.x * CELL_WIDTH, "|")
                else:
                    self.screen.addstr(cell.y * CELL_HEIGHT + 1 , cell.x * CELL_WIDTH, " ")

                self.screen.addstr(cell.y * CELL_HEIGHT + 1, cell.x * CELL_WIDTH + 1, "   ")

                if cell.x == self.maze.width - 1 and cell.east:
                    self.screen.addstr(cell.y * CELL_HEIGHT + 1, cell.x * CELL_WIDTH + CELL_WIDTH, "|")

            #
            # Draw cell bottom
            #

            if cell.y == self.maze.height - 1:
                for cell in row:
                    self.screen.addstr(cell.y * CELL_HEIGHT + 2, cell.x * CELL_WIDTH, "+")
                    if cell.south:
                        self.screen.addstr(cell.y * CELL_HEIGHT + 2, cell.x * 4 + 1, "---")
                    else:
                        self.screen.addstr(cell.y * CELL_HEIGHT + 2, cell.x * 4 + 1, "   ")
                self.screen.addstr(cell.y * CELL_HEIGHT + 2, self.maze.width * CELL_WIDTH, "+")

        #
        # Print player 1
        #

        for number, player in enumerate(self.players):
            self.screen.addstr(player.y * CELL_HEIGHT + 1, player.x * CELL_WIDTH + 1, " {0} ".format(number + 1), curses.color_pair(number + 2))

            # Print user's movements
            self.screen.addstr(self.maze.height * CELL_HEIGHT + 2 + number, 0, "(Player {0}) - {1} movements.".format(number + 1, player.movements))

        # As I don't know how to hide the cursors - this is quite a dirty way to remove it from the middle of the screen.
        self.screen.addstr(self.maze.height * CELL_HEIGHT, self.maze.width * CELL_WIDTH, "+")

        self.screen.refresh()


class GameProtocol(threading.Thread):

    def __init__(self, game):
        self.game = game
        self.lock = threading.Lock()
        super(GameProtocol, self).__init__()

    def process_update(self, payload):
        player_coords = map(int, payload.split())
        self.game.players[1].x, self.game.players[1].y = player_coords
        self.game.draw()

    def send_update(self):
        self.socket.send("update %s %s" % (self.game.players[0].x, self.game.players[0].y))

    def log(self, text):
        with open('{0}.log'.format(self.__class__.__name__), 'a+') as f:
            f.write(text + '\n')


class ServerThread(GameProtocol):

    def __init__(self, port=8123, *args, **kwargs):
        self.port = port
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.socket.bind("tcp://*:{0}".format(self.port))
        super(ServerThread, self).__init__(*args, **kwargs)

    def run(self):

        while True:
            #  Wait for next move
            self.log("Acquire lock")
            self.lock.acquire()

            self.log("Wait for a request")
            message = self.socket.recv()
            self.log("New request with message: %s" % message)

            action, payload = message.split(' ', 1)

            self.log("Action: %s  Payload: %s" % (action, payload))

            if action == "update" and self.game.playing:
                self.process_update(payload)
                self.send_update()

            elif action == "hello":
                self.socket.send("hello client")

            elif action == "get":

                if payload == "map":
                    src = StringIO()
                    pickler = pickle.Pickler(src)
                    pickler.dump([self.game.exit, self.game.maze])
                    self.socket.send("map %s" % base64.b64encode(src.getvalue()))

            elif action == "go":
                self.game.playing = True
                self.socket.send("go go")

            elif action == "loser":
                #self.game.playing = False
                self.game.finished = True
                self.socket.send("winer winer")

            self.lock.release()
            self.log("Lock released")

    def join(self, *args, **kwargs):
        self.socket.unbind("tcp://*:{0}".format(self.port))
        return super(ServerThread, self).join(*args, **kwargs)


class ClientThread(GameProtocol):

    timeout = 0.1

    def __init__(self, address="localhost:8123", *args, **kwargs):
        self.log("Creating client thread...")
        super(ClientThread, self).__init__(*args, **kwargs)
        self.address = address
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REQ)
        self.socket.connect("tcp://%s" % self.address)
        self.timer = None

        # Say HELLO to the server
        self.log("Saying Hello")
        response = self.send("hello server")
        if response != "hello client":
            raise ConnectionError("This server is not acceptiong new connections.")

        # Get the map
        response = self.send("get map")
        if not response.startswith('map '):
            raise ConnectionError("Error downloading map from the server.")

        # Load pickled maze
        _, m = response.split(" ", 1)
        src = StringIO(base64.b64decode(m))
        unpickler = pickle.Unpickler(src)
        exit, maze = unpickler.load()
        self.game.maze = maze
        self.game.exit = exit

    def create_timer(self):
        """Create a timer that sends user's position to the server every
        ``timeout`` seconds."""
        self.log("Creating timer")
        if self.timer:
            self.timer.cancel()
        self.timer = threading.Timer(self.timeout, partial(self.trigger_update, True))
        self.timer.start()

    def run(self):
        self.create_timer()

    def send(self, message):
        self.log("Trying to send: %s" % message)
        self.lock.acquire()
        self.log("Lock acquired to send: %s" % message)
        self.socket.send(message)
        self.log("Message sent: %s" % message)
        response = self.socket.recv()
        self.log("Response: %s received" % response)
        self.lock.release()
        self.log("Lock released")
        return response

    def send_update(self):
        self.log("Trying to send: update")
        self.lock.acquire()
        self.log("Lock acquired to send: update")
        super(ClientThread, self).send_update()
        response = self.socket.recv()
        self.lock.release()
        return response

    def trigger_update(self, from_timer=False):
        self.log("trigger_update called, playing is %s" % self.game.playing)

        # Don't pull the server until the game starts
        if self.game.playing:
            response = self.send_update()
            action, payload = response.split(" ", 1)
            self.log("Action received: %s payload: %s" % (action, payload))

            if action == "update":
                self.process_update(payload)

            elif action == "loser":
                self.game.playing = False
                self.game.finished = True
                self.socket.send("winer winer")

        if from_timer:
            self.create_timer()

    def join(self, *args, **kwargs):
        self.timer.cancel()
        return super(ClientThread, self).join(*args, **kwargs)


def run_game(screen, width=4, height=10, is_server=False, server_port=8123, server_address=None):

    curses.start_color()
    curses.use_default_colors()

    # Define color pairs
    curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_GREEN)
    curses.init_pair(2, curses.COLOR_BLACK, curses.COLOR_BLUE)
    curses.init_pair(3, curses.COLOR_BLACK, curses.COLOR_RED)

    curses.noecho()  # Suppress key output to screen
    screen.keypad(1)  # set mode when capturing keypresses

    # Continue?
    while True:
        client = server = None

        game = Game(screen=screen, width=width, height=height)

        if is_server:
            server = ServerThread(game=game, port=server_port)
            server.start()
            game.add_player()

        elif server_address:
            client = ClientThread(game=game, address=server_address)
            client.start()

            game.set_client(client)
            game.add_player()

        try:
            game.start(wait=not server)

        except (MazeLose, MazeWin):
            if server:
                server.join(0.1)

            if client:
                client.join(0.1)

            screen.clear()

            if server or client:
                raise

        # Continue?
        screen.addstr(game.maze.height * CELL_HEIGHT + 6, 0, "Continue? [Y/n]")
        key = screen.getch()

        while key not in map(ord, ['n', 'N', 'y', 'Y', '\n']):
            key = screen.getch()

        if key in map(ord, ['n', 'N']):
            raise MazeExit()

        # Make the next screen harder
        width += random.randint(0, 3)
        height += random.randint(0, 3)

        # But not too much...
        width = min([width, 40])
        height = min([height, 25])


def main():

    parser = argparse.ArgumentParser(description='Maze game for the Euskal Encounter XXI.')
    parser.add_argument('--width', dest='width', default=4, help="Maze width", type=int)
    parser.add_argument('--height', dest='height', default=4, help="Maze height", type=int)
    parser.add_argument('--server', dest='server', action="store_true", default=False, help="Start a maze server")
    parser.add_argument('--server-port', dest='server_port', default=8123, help="Server port", type=int)
    parser.add_argument('--connect', dest='server_address', help="Server host:port")
    args = parser.parse_args()

    if args.width < 2:
        parser.error("width can't be smaller than 2.")

    if args.height < 2:
        parser.error("height can't be smaller than 2.")

    try:
        curses.wrapper(partial(run_game, width=args.width,
                                         height=args.height,
                                         is_server=args.server,
                                         server_port=args.server_port,
                                         server_address=args.server_address))
    except curses.error:
        print "ERROR: It looks like your terminal is not big enough for this maze."
        sys.exit(-1)
    except MazeException, exc:
        print exc.args[0]
        sys.exit(-2)
    except MazeExit:
        print "Bye!"
    except MazeWin, exc:
        print "You won in %s sec!" % exc.args[0]
    except MazeLose:
        print "You lose!"
    sys.exit(0)

if __name__ == '__main__':
    main()
