import os
import json
import argparse
import re
from collections import defaultdict
from utils import judge_models, get_role_assignment

def find_marjority_vote(vote_dict, role_mapping):
    # vote_dict is {vote_to -> [who_vote, ...]}
    max_count = 0
    majority_werewolf = 0
    for vote_to in vote_dict:
        if role_mapping.get(str(vote_to), "") == "Werewolf":
            count = len(vote_dict[vote_to])
            if count > max_count:
                max_count = count
                majority_werewolf = vote_to
    return majority_werewolf, max_count


def extract_bad_vote(log, role_mapping, game_type, strict_mode=False):
    """
    return: [(player_id, phase)]
    strict_mode: True if we use strict mode, mode: strict or loose
    The rules for good vote for the villager side:
    1. 村民投给好人并且最后把好人投死了，或者弃票
    2. (for strict mode) 考虑分票，没有投给获得真预言家所投给的狼，如果预言家死了，那就是没有投给获得票数最多的狼。
    """
    add_to_data = []
    vote_dict = {} # {day-1: {vote_to -> [who_vote, who_vote]]}
    pk_happens = [] # a list to record pk happens at day i
    seer_vote_dict = {} # {day-1: {vote_to -> [who_vote, who_vote]]}
    for i in log:
        day = i["day"]
        event = i["event"]
        if event == "vote":
            if f"{day}-1" not in vote_dict:
                vote_dict[f"{day}-1"] = defaultdict(list)
            if role_mapping.get(str(i["source"]), "") != "Werewolf": # only count the vote from villager
                vote_dict[f"{day}-1"][i["target"]].append(i["source"])
                if i["target"]==0 or i["target"] is None or role_mapping.get(str(i["target"]), "") != "Werewolf": # if vote to good, add to data
                    add_to_data.append((i["source"], f"{day}_day_vote"))
            
            if strict_mode and role_mapping.get(str(i["source"]), "")  == "Seer":
                seer_vote_dict[f"{day}-1"] = i["target"]
            
        elif event == "vote_pk" and day in pk_happens:
            if f"{day}-pk" not in vote_dict:
                vote_dict[f"{day}-pk"] = defaultdict(list)
            if role_mapping.get(str(i["source"]), "") != "Werewolf":
                vote_dict[f"{day}-pk"][i["target"]].append(i["source"])
                if i["target"]==0 or i["target"] is None or role_mapping.get(str(i["target"]), "") != "Werewolf": # if vote to good, add to data
                    add_to_data.append((i["source"], f"{day}_day_vote_pk"))
            if strict_mode and role_mapping.get(str(i["source"]), "")  == "Seer":
                seer_vote_dict[f"{day}-pk"] = i["target"]
           
        if strict_mode and event == "end_vote":
            # stats the majority vote
            if "expelled" in i["content"]: # someone is expelled, 
                vote_out_player = i["content"]["expelled"]
                if day not in pk_happens: # and not in pk turn.
                    if f"{day}-1" in seer_vote_dict: # if seer is alive
                        seers_vote = seer_vote_dict[f"{day}-1"]
                        if f"{day}-1" in vote_dict:
                            for vote_to in vote_dict[f"{day}-1"].keys():
                                if vote_to != seers_vote: # 分预言家的票，不做好
                                    for player_id in vote_dict[f"{day}-1"][vote_to]:
                                        if (player_id, f"{day}_day_vote") not in add_to_data:
                                            add_to_data.append((player_id, f"{day}_day_vote"))
                    elif f"{day}-1" in vote_dict: # 考虑多数村民投的且是给狼的，最后分票
                        majority_werewolf, max_count = find_marjority_vote(vote_dict[f"{day}-1"], role_mapping)
                        if majority_werewolf != 0 and max_count > 2: # this wolf has at least have 3 votes
                            for vote_to in vote_dict[f"{day}-1"]:
                                if vote_to != majority_werewolf:
                                    for player_id in vote_dict[f"{day}-1"][vote_to]:
                                        if (player_id, f"{day}_day_vote") not in add_to_data:
                                            add_to_data.append((player_id, f"{day}_day_vote"))    
                else: # pk turn
                    if f"{day}-pk" in seer_vote_dict: # if seer is alive
                        seers_vote = seer_vote_dict[f"{day}-pk"]
                        if f"{day}-pk" in vote_dict:
                            for vote_to in vote_dict[f"{day}-pk"].keys():
                                if vote_to != seers_vote:
                                    for player_id in vote_dict[f"{day}-pk"][vote_to]:
                                        if (player_id, f"{day}_day_vote_pk") not in add_to_data:
                                            add_to_data.append((player_id, f"{day}_day_vote_pk"))
                    elif f"{day}-pk" in vote_dict:
                        majority_werewolf, max_count = find_marjority_vote(vote_dict[f"{day}-pk"], role_mapping)
                        if majority_werewolf != 0 and max_count > 2: # this wolf has at least have 3 votes
                            for vote_to in vote_dict[f"{day}-pk"]:
                                if vote_to != majority_werewolf:
                                    for player_id in vote_dict[f"{day}-pk"][vote_to]:
                                        if (player_id, f"{day}_day_vote_pk") not in add_to_data:
                                            add_to_data.append((player_id, f"{day}_day_vote_pk"))
            elif i["content"]["vote_outcome"] == "draw":
                pk_happens.append(day)

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
                           type=str, default="sft_agent", help="the behavior data of which model to be trained")
    argparser.add_argument("--strict", action="store_true", help="whether to use strict mode")
    argparser.add_argument('--out_to', type=str, default="")
    argparser.add_argument('--self_play', action="store_true", help="whether to use self play")
    args = argparser.parse_args()

    all_bad_votes_villager = {} # {game_id: [(player_id, phase)]}
    villager_cnt = 0
    wolf_cnt = 0
    for sub_dir in os.listdir(args.game_dir):
        sub_dir_full = os.path.join(args.game_dir, sub_dir)
        if not os.path.isdir(sub_dir_full):
            continue
        if args.self_play and ("self_play" not in sub_dir and f"w-{args.sft_model_regx}_vs_v-{args.sft_model_regx}" not in sub_dir):
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

            if good_is_sft:
                # get the good vote
                bad_vote = extract_bad_vote(content, role_mapping, args.game_type, strict_mode=args.strict)
                all_bad_votes_villager[game_id_full] = bad_vote
                villager_cnt += len(bad_vote)
    
    # post process
    all_bad_votes_out = {}
    cnt = 0
    for path, bad_votes in all_bad_votes_villager.items():
        bad_vote_by_player = defaultdict(list)
        for i, (player_id, phase) in enumerate(bad_votes):
            if phase not in bad_vote_by_player[player_id]:
                bad_vote_by_player[player_id].append(phase)
                cnt += 1
        all_bad_votes_out[path] = bad_vote_by_player
    print("total bad votes:", cnt, villager_cnt, wolf_cnt)

    # write to file
    if args.strict:
        output_file = os.path.join(args.out_to, f"villager_bad_vote_strict.json")
    else:
        output_file = os.path.join(args.out_to, f"villager_bad_vote_loose.json")
    with open(output_file, "w") as f:
        json.dump(all_bad_votes_out, f, indent=4)
