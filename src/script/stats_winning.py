"""统计实验目录下各局游戏的胜负分布。

读取 `--game_dir` 下每个子目录的 `game_log.json`，
末尾事件为 `end_game`，内容形如 `{'游戏结果': '狼人获胜' | '村民获胜'}`。
"""
import argparse
import json
import os


def _read_winner(game_log_path: str) -> str:
    with open(game_log_path, "r", encoding="utf-8") as f:
        content = json.load(f)
    if not content:
        raise ValueError(f"空日志: {game_log_path}")
    end_entry = content[-1]
    if end_entry.get("event") != "end_game":
        raise ValueError(f"末尾事件不是 end_game: {game_log_path} -> {end_entry}")
    result = end_entry.get("content", {}).get("游戏结果")
    if result is None:
        raise ValueError(f"缺少 '游戏结果' 字段: {game_log_path}")
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--game_dir", type=str, default="./experiments",
                        help="path to the experiments")
    args = parser.parse_args()

    winning_stats = {"werewolf_win": 0, "villager_win": 0}

    for root, dirs, _ in os.walk(args.game_dir):
        for dir_name in dirs:
            game_log_file = os.path.join(root, dir_name, "game_log.json")
            if not os.path.exists(game_log_file):
                print(game_log_file, "not exist")
                continue
            try:
                winner = _read_winner(game_log_file)
            except (ValueError, KeyError, json.JSONDecodeError) as e:
                print(f"skip {game_log_file}: {e}")
                continue
            if winner == "狼人获胜":
                winning_stats["werewolf_win"] += 1
            elif winner == "村民获胜":
                winning_stats["villager_win"] += 1
            else:
                print(f"unknown winner '{winner}' in {game_log_file}")

    total = winning_stats["werewolf_win"] + winning_stats["villager_win"]
    print(winning_stats)
    if total > 0:
        print(f"狼人胜率: {winning_stats['werewolf_win'] / total:.2%}")
        print(f"村民胜率: {winning_stats['villager_win'] / total:.2%}")


if __name__ == '__main__':
    main()
