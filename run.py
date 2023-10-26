import argparse
import asyncio
import logging
import aiohttp
import sc2
from sc2.main import run_game
from sc2.data import Race, Difficulty
from sc2.client import Client
from sc2.player import Bot, Computer
from sc2.protocol import ConnectionAlreadyClosed
from bots import FourGate


class LadderGame:
    def __init__(self, args, bot):
        self.args = args
        self.bot = bot

    async def join_game(self):
        ws_url = f"ws://{self.args.LadderServer}:{self.args.GamePort}/sc2api"
        ws_connection = await aiohttp.ClientSession().ws_connect(ws_url, timeout=120)
        client = Client(ws_connection)
        try:
            result = await sc2.main._play_game(self.bot, client, self.args.Realtime, self._port_config())
            # Add any replay save or other operations here if needed
        except ConnectionAlreadyClosed:
            logging.error("Connection was closed before the game ended")
            return None
        finally:
            await ws_connection.close()

        return result

    def _port_config(self):
        lan_port = self.args.StartPort
        ports = [lan_port + p for p in range(1, 6)]
        portconfig = sc2.portconfig.Portconfig()
        portconfig.shared = ports[0]  # Not used
        portconfig.server = [ports[1], ports[2]]
        portconfig.players = [[ports[3], ports[4]]]
        return portconfig

    def run(self):
        print("Starting ladder game...")
        result = asyncio.get_event_loop().run_until_complete(self.join_game())
        print(result, " against opponent ", self.args.OpponentId)


class LocalGame:
    def __init__(self, args, bot):
        self.args = args
        self.bot = bot

    def run(self):
        print("Starting local game...")
        run_game(sc2.maps.get(self.args.Map),
                    [self.bot, Computer(Race[self.args.ComputerRace], Difficulty[self.args.ComputerDifficulty])],
                    realtime=self.args.Realtime, sc2_version=self.args.Sc2Version)


def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("--GamePort", type=int, help="Game port.")
    parser.add_argument("--StartPort", type=int, help="Start port.")
    parser.add_argument("--LadderServer", type=str, help="Ladder server.")
    parser.add_argument("--Sc2Version", type=str, help="The version of Starcraft 2 to load.")
    parser.add_argument("--ComputerRace", type=str, default="Terran", help="Computer race for local play.")
    parser.add_argument("--ComputerDifficulty", type=str, default="VeryHard", help="Computer difficulty for local play.")
    parser.add_argument("--Map", type=str, default="AutomatonLE", help="Map for local play.")
    parser.add_argument("--OpponentId", type=str, help="Unique opponent identifier.")
    parser.add_argument("--Realtime", action='store_true', help="Use realtime mode.")
    args, unknown_args = parser.parse_known_args()

    for unknown_arg in unknown_args:
        print(f"Unknown argument: {unknown_arg}")

    if args.OpponentId is None:
        args.OpponentId = args.LadderServer or f"{args.ComputerRace}_{args.ComputerDifficulty}"
    return args


def load_bot(opponent_id):
    competitive_bot = FourGate()
    competitive_bot.opponent_id = opponent_id
    return Bot(FourGate.RACE, competitive_bot)


def main():
    args = parse_arguments()
    bot = load_bot(args.OpponentId)

    if args.LadderServer:
        game = LadderGame(args, bot)
    else:
        game = LocalGame(args, bot)

    game.run()


if __name__ == "__main__":
    main()
