import os
import json
import argparse
import re
from collections import defaultdict
from utils import judge_models, get_role_assignment

def extract_good_vote(log, role_mapping, game_type, loose_mode=False):
    """
    return: [(player_id, phase)]
    loose_mode: True if we use loose mode, mode: strict or loose
    The rules for good vote for the villager side:
    1. vote to the werewolf and successfully vote out the werewolf.
    2. (for loose mode) for gods, vote to the werewolf
    """
    add_to_data = []
    vote_dict = {} # {day-1: {vote_to -> [who_vote, who_vote]]}
    pk_happens = [] # a list to record pk happens at day i
    for i in log:
        day = i["day"]
        event = i["event"]
        if event == "vote":
            if f"{day}-1" not in vote_dict:
                vote_dict[f"{day}-1"] = defaultdict(list)
            if role_mapping.get(str(i["source"]), "") != "Werewolf": # only count the vote from villager
                vote_dict[f"{day}-1"][i["target"]].append(i["source"])
            # for loose mode, we also consider the vote from gods
            if loose_mode:
                if role_mapping.get(str(i["source"]), "") in ["Seer", "Witch", "Guard", "Hunter"]:
                    add_to_data.append((i["source"], f"{day}_day_vote"))

        elif event == "vote_pk" and day in pk_happens:
            if f"{day}-pk" not in vote_dict:
                vote_dict[f"{day}-pk"] = defaultdict(list)
            if role_mapping.get(str(i["source"]), "") != "Werewolf":
                vote_dict[f"{day}-pk"][i["target"]].append(i["source"])
            # for loose mode, we also consider the vote from gods in the pk phase
            if loose_mode:
                if role_mapping.get(str(i["source"]), "") in ["Seer", "Witch", "Guard", "Hunter"]:
                    add_to_data.append((i["source"], f"{day}_day_vote_pk"))
        
        if event == "end_vote":
            if "expelled" in i["content"]: # someone is expelled, 
                if day not in pk_happens: # and not in pk turn.
                    vote_out_player = i["content"]["expelled"]
                    if role_mapping.get(str(vote_out_player), "") == "Werewolf":
                        if f"{day}-1" in vote_dict:
                            for player_id in vote_dict[f"{day}-1"][vote_out_player]:
                                if (player_id, f"{day}_day_vote") not in add_to_data:
                                    add_to_data.append((player_id, f"{day}_day_vote"))
                else:
                    vote_out_player = i["content"]["expelled"]
                    if role_mapping.get(str(vote_out_player), "") == "Werewolf":
                        if f"{day}-pk" in vote_dict:
                            for player_id in vote_dict[f"{day}-pk"][vote_out_player]:
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
                           type=str, default="sft_agent")
    argparser.add_argument("--loose", action="store_true", help="whether to use loose mode")
    argparser.add_argument('--out_to', type=str, default="")
    argparser.add_argument("--self_play", action="store_true", help="whether to use self-play")
    args = argparser.parse_args()

    all_good_votes_villager = {} # {game_id: [(player_id, phase)]}
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
                good_vote = extract_good_vote(content, role_mapping, args.game_type, loose_mode=args.loose)
                all_good_votes_villager[game_id_full] = good_vote
    
    # post process
    all_good_votes_out = {}
    cnt = 0
    for path, good_votes in all_good_votes_villager.items():
        good_vote_by_player = defaultdict(list)
        for i, (player_id, phase) in enumerate(good_votes):
            if phase not in good_vote_by_player[player_id]:
                good_vote_by_player[player_id].append(phase)
                cnt += 1
        all_good_votes_out[path] = good_vote_by_player
    print("total good votes:", cnt)

    # write to file
    if args.loose:
        output_file = os.path.join(args.out_to, f"villager_good_vote_loose.json")
    else:
        output_file = os.path.join(args.out_to, f"villager_good_vote_strict.json")
    with open(output_file, "w") as f:
        json.dump(all_good_votes_out, f, indent=4)
