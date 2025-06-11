import os
import json
import argparse

if __name__ == '__main__':
    argparser = argparse.ArgumentParser()
    argparser.add_argument('--game_dir',
                           type=str, default="./experiments",
                           help="path to the experiments")
    args = argparser.parse_args()

    winning_stats = {
        "werewolf_win": 0,
        "villager_win": 0
    }

    for root, dirs, files in os.walk(args.game_dir):
        for dir in dirs:
            game_log_file = os.path.join(root, dir, "game_log.json")
            if not os.path.exists(game_log_file):
                print(game_log_file, "not exist")
                continue
            with open(game_log_file, "r") as f:
                content = json.loads(f.read())

            winning_info = content[-1]
            if winning_info["content"]["outcome"] == 1:
                winning_stats["werewolf_win"] += 1
            else:
                winning_stats["villager_win"] += 1

    print(winning_stats)
