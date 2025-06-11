import os
import json
import argparse
import re
from collections import defaultdict
from utils import judge_models, get_role_assignment


def get_wolf_acceptable_action(log, role_mapping):
    """
    return: [(player_id, phase)]
    The rule the judge the acceptable action for wolf: 
        1. wolf kill any of the gods at >=2 night
    """
    add_to_data = [] # (player_id, phase)
    kill_at_day = {} # 0->{3->[1,4]} who killed 
    for i in log:
        day = i["day"]
        if day < 1: # we don't count the first night
            continue
        if i["event"] == "skill_wolf":
            if role_mapping.get(str(i["target"]), "") in ["Seer", "Witch", "Guard", "Hunter"]:
                if day not in kill_at_day:
                    kill_at_day[day] = defaultdict(list)
                    kill_at_day[day][str(i["target"])].append(i["source"])
                else:
                    kill_at_day[day][str(i["target"])].append(i["source"])

        if i["event"] == "kill_decision":
            target = str(i["target"])
            phase = f"{day}_night_skill_wolf"
            if day in kill_at_day:
                if target in list(kill_at_day[day].keys()):
                    for wolf_id in kill_at_day[day][target]:
                        add_to_data.append((wolf_id, phase))
    return add_to_data


def get_good_acceptable_action(log, role_mapping, game_type):
    """
    return: [(player_id, phase)]
    The rules for acceptable action for good:
    1. seer: check the identity of the Werewolf player
    2. witch: heal anyone at day 0, poison the werewolf at day >= 1
    3. guard: for 9-p game: protect nobody at day 0, protect the good at day >= 1; for 7-p game: protect self.
    4. hunter: kill the werewolf
    """
    add_to_data = []
    for i in log:
        day = i["day"]
        event = i["event"]
        if event == "skill_seer":
            if i["content"]["cheked_identity"] == "bad":
                add_to_data.append((i["source"], f"{day}_night_skill_seer"))

        if event == "skill_witch": 
            if day == 0 and "heal" in i["content"]:
                add_to_data.append((i["source"], f"{day}_night_skill_witch"))
            if day >= 1 and "poison" in i["content"]:
                if role_mapping.get(str(i["target"]), "") == "Werewolf":
                    add_to_data.append((i["source"], f"{day}_night_skill_witch"))
        
        if event == "skill_guard":
            if game_type == "9p_seer_witch_guard" and day == 0 and i["target"] == 0:
                add_to_data.append((i["source"], f"{day}_night_skill_guard"))
            if game_type == "7p_seer_guard" and day == 0 and i["target"] == i["source"]:
                add_to_data.append((i["source"], f"{day}_night_skill_guard"))
            if day >= 1:
                if role_mapping.get(str(i["target"]), "") in ["Seer", "Witch", "Guard"]:
                    add_to_data.append((i["source"], f"{day}_night_skill_guard"))
        
        if event == "skill_hunter":
            if role_mapping.get(str(i["target"]), "") == "Werewolf":
                add_to_data.append((i["source"], f"{day}_night_skill_hunter"))

    return add_to_data

if __name__ == '__main__':
    argparser = argparse.ArgumentParser()
    argparser.add_argument('--game_dir',
                           type=str, default="./trial_logs",
                           help="path to the experiments")
    argparser.add_argument('--game_type',
                           type=str, default="9p_seer_witch_guard",
                           help="choose from: 9p_seer_witch_guard, 9p_seer_witch_hunter, 7p_seer_guard")
    argparser.add_argument('--sft_model_regx',
                           type=str, default="sft_agent")
    argparser.add_argument('--out_to', type=str, default="")
    argparser.add_argument('--self_play', action="store_true", help="whether to use self play")
    args = argparser.parse_args()

    assert args.game_type in args.game_dir

    all_acceptable_actions = {} # {game_id: [(player_id, phase)]}
    villager_cnt = 0
    wolf_cnt = 0
    for sub_dir in os.listdir(args.game_dir):
        sub_dir_full = os.path.join(args.game_dir, sub_dir)
        if not os.path.isdir(sub_dir_full):
            continue
        if args.self_play and "self_play" not in sub_dir:
            continue
        else:
            werewolf_is_sft = True
            good_is_sft = True
            werewolf_model_name = args.sft_model_regx
            good_model_name = args.sft_model_regx
        if (not args.self_play) and (not sub_dir.startswith("w-")):
            continue
        elif not args.self_play:
            (werewolf_model_name, werewolf_is_sft), (good_model_name, good_is_sft) = judge_models(sub_dir, args.sft_model_regx)
            if (not werewolf_is_sft) and (not good_is_sft):
                continue
        
        print(f"Extract data from ``{sub_dir}``, werewolf_model=``{werewolf_model_name}``, good_model=``{good_model_name}``...")
        for game_id in os.listdir(sub_dir_full):
            acceptable_actions_in_game_i = []
            game_id_full = os.path.join(sub_dir_full, game_id)
            if not os.path.isdir(game_id_full):
                continue
            game_log_file = os.path.join(game_id_full, "game_log.json")
            if not os.path.exists(game_log_file):
                print(game_log_file, "not exist")
                continue
            with open(game_log_file, "r") as f:
                content = json.loads(f.read())
            role_mapping = get_role_assignment(content)

            # acceptable actions for wolf:
            if werewolf_is_sft:
                wolf_acceptable_actions = get_wolf_acceptable_action(content, role_mapping) # [(wolf_id, phase)]
                acceptable_actions_in_game_i.extend(wolf_acceptable_actions)
                wolf_cnt += len(wolf_acceptable_actions)
            # acceptable actions for good:
            if good_is_sft:
                good_acceptable_acions = get_good_acceptable_action(content, role_mapping, args.game_type) # [(good_id, phase)]
                acceptable_actions_in_game_i.extend(good_acceptable_acions)
                villager_cnt += len(good_acceptable_acions)

            if len(acceptable_actions_in_game_i) > 0:
                all_acceptable_actions[game_id_full] = acceptable_actions_in_game_i
    
    # post process
    all_acceptable_actions_out = {}
    cnt = 0
    for path, acc_action in all_acceptable_actions.items():
        acceptable_action_by_player = defaultdict(list)
        for i, (player_id, phase) in enumerate(acc_action):
            if phase not in acceptable_action_by_player[player_id]:
                acceptable_action_by_player[player_id].append(phase)
                cnt += 1
        all_acceptable_actions_out[path] = acceptable_action_by_player
    print("total number of acceptable actions:", cnt, "villager_cnt:", villager_cnt, "wolf_cnt:", wolf_cnt)

    # write to file
    output_file = os.path.join(args.out_to, f"good_actions.json")
    with open(output_file, "w") as f:
        json.dump(all_acceptable_actions_out, f, indent=4)

            
            

            
            

