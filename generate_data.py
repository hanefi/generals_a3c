import argparse
from multiprocessing import Pool
from termcolor import cprint
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
    x, y, z = zip(*mapped_data)

    return x, y, z


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--threads", type=int, default=None)
    parser.add_argument("--data", type=str, default="/home/yilundu/fbcode/experimental/yilundu/generals/generals_a3c/replays_prod",
                        help="Directory where the gioreplay files are stored")
    parser.add_argument("--stars", type=int, default=90)
    parser.add_argument("--players", type=int, default=2)
    args = parser.parse_args()
    NUM_PLAYERS = args.players
    STAR_TRESH = args.stars

    cprint("Finding all gioreplay files...", "green")
    f_list = [join(args.data, f) for f in listdir(args.data) if isfile(join(args.data, f))]

    cprint("Extracting data from all gioreplay files...", "green")
    x, y, z = extract_data(f_list, args.threads)

    x = list(filter(lambda x: True if x else False, x))
    y = list(filter(lambda y: True if y else False, y))
    z = list(filter(lambda z: True if z else False, z))

    np.savez("/mnt/homedir/yilundu/data_x", x)
    np.savez("/mnt/homedir/yilundu/data_y", y)
    np.savez("/mnt/homedir/yilundu/data_z", z)



