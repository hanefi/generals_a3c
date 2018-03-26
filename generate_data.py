import argparse
from multiprocessing import Pool
import generalsim

from os import listdir
from os.path import isfile, join
import pickle
import numpy as np

REPORT_INTERVAL = 10000
# Currently only extracting games between 2 players
# with greater than 80 stars
NUM_PLAYERS = 2
STAR_TRESH = 80


def extract_game(f_name):
    game_x, game_y, game_z = [], [], []
    if f_name.endswith(".gioreplay"):
        game = generalsim.GeneralSim(f_name)
        status = game.add_log(STAR_TRESH, NUM_PLAYERS)

        if status:
            while not game.step():
                pass

            game_x, game_y, game_z = game.export_log()

    return game_x, game_y, game_z


def extract_data(l_f, threads):
    """Extracts data from a list of  gioreplay"""
    pool = Pool(threads)

    mapped_data = pool.map(extract_game, l_f)
    x, y, z = list(zip(*mapped_data))

    return x, y, z


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--processes", type=int, default=None)
    parser.add_argument("--data", type=str, default="replays_prod",
                        help="directory where the gioreplay files are stored")
    parser.add_argument("--stars", type=int, default=90,
                        help="threshold for stars to parse games from")
    parser.add_argument("--players", type=int, default=2,
                        help="number of players needed so that we parse games")
    args = parser.parse_args()
    NUM_PLAYERS = args.players
    STAR_TRESH = args.stars

    print("Finding all gioreplay files...")
    f_list = [join(args.data, f) for f in listdir(args.data) if isfile(join(args.data, f))]

    print("Extracting data from all gioreplay files...")
    x, y, z = extract_data(f_list, args.processes)

    x = list(map(bool,x))
    y = list(map(bool,y))
    z = list(map(bool,z))

    np.savez("data_x", x)
    np.savez("data_y", y)
    np.savez("data_z", z)
