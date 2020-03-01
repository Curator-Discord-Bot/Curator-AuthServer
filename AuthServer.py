"""
Example "auth" server

This server authenticates players with the mojang session server, then kicks
them. Useful for server websites that ask users for a valid Minecraft account.
"""

from twisted.internet import reactor
from quarry.net.server import ServerFactory, ServerProtocol
import psycopg2
from random import randint
from config import database, password, port, host, user

con = None


class AuthProtocol(ServerProtocol):
    def player_joined(self):
        global con
        # This method gets called when a player successfully joins the server.
        #   If we're in online mode (the default), this means auth with the
        #   session server was successful and the user definitely owns the
        #   display name they claim to.

        # Call super. This switches us to "play" mode, marks the player as
        #   in-game, and does some logging.
        ServerProtocol.player_joined(self)
        id = self.uuid.to_hex(with_dashes=False)

        cur = con.cursor()

        try:
            cur.execute('SELECT pin FROM auths where minecraft_uuid=%s;', [id])
            pin = cur.fetchone()
            print(pin)
            if not pin:
                pin = randint(1000, 9999)
                cur.execute('SELECT pin FROM auths where pin=%s;', [pin])
                res = cur.fetchone()
                while res:
                    pin = randint(1000, 9999)
                    cur.execute('SELECT pin FROM auths where pin=%s;', [pin])
                    res = cur.fetchone()

                cur.execute('INSERT INTO auths (minecraft_uuid, pin) VALUES (%s, %s);', (str(id), str(pin)))
                con.commit()
            else:
                pin = pin[0]

            # Kick the player.
            self.close(f"Send command to Curator bot: ,auth {pin}")
        except Exception as e:
            print(e)
            self.close('No')


class AuthFactory(ServerFactory):
    protocol = AuthProtocol
    motd = "Curator - Auth Server"


def main(argv):
    global con
    # Parse options
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("-a", "--host", default="", help="address to listen on")
    parser.add_argument("-p", "--port", default=25565, type=int, help="port to listen on")
    parser.add_argument("-db", "--database", default=False, type=bool, help="initializes the database")
    args = parser.parse_args(argv)

    con = con or psycopg2.connect(database=database, user=user, password=password,
                                  host=host, port=port)

    if args.database:
        con.cursor().execute(
            'CREATE TABLE auths(minecraft_uuid UUID, pin INTEGER UNIQUE, PRIMARY KEY (minecraft_uuid));')
        con.commit()

    # Create factory
    factory = AuthFactory()

    # Listen
    factory.listen(args.host, args.port)
    reactor.run()


if __name__ == "__main__":
    import sys

    print(f'Running {__file__}')
    main(sys.argv[1:])
