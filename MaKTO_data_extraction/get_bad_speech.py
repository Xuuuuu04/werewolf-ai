import os
import json
import argparse
import re
from collections import defaultdict
from utils import judge_models, get_role_assignment

# SPEECH_WORDS_THRESHOLD = 0

def extract_bad_speech_villager(log, role_mapping, game_type):
    """
    Return: [(player_id, phase)]
    The rules for bad speech for the villager side:
    1. 被投出去的村民发言
    2. 预言家发言 获得>=所有村民投票一半及以上的票数 的发言
    3. 女巫发言 获得狼人投票 且民投票>=2 的发言
    """
    add_to_data = []
    vote_dict = {} # {day-1: {vote_to -> [who_vote, who_vote]]}
    speech_dict = defaultdict(dict) # {day-1: {speaker -> (role, speak_content)}}
    pk_happens = [] # a list to record pk happens at day i
    total_effective_votes_by_villager = {} # {day-1: 5}
    for i in log:
        day = i["day"]
        event = i["event"]
        # first process speech
        if event == "speech":
            if f"{day}-1" not in speech_dict:
                speech_dict[f"{day}-1"] = {}
            speech_dict[f"{day}-1"][i["source"]] = (role_mapping[str(i["source"])],  i["content"]["speech_content"])
        elif event == "speech_pk" and day in pk_happens:
            if f"{day}-pk" not in speech_dict:
                speech_dict[f"{day}-pk"] = {}
            speech_dict[f"{day}-pk"][i["source"]] = ((role_mapping[str(i["source"])],  i["content"]["speech_content"]))
        
        # then process detail vote
        if event == "vote":
            assert f"{day}-1" in speech_dict
            if f"{day}-1" not in vote_dict:
                vote_dict[f"{day}-1"] = defaultdict(list)
                total_effective_votes_by_villager[f"{day}-1"] = 0
            vote_dict[f"{day}-1"][i["target"]].append(i["source"])
            if i["target"] != 0 or i["target"] is not None:
                total_effective_votes_by_villager[f"{day}-1"] += 1

        elif event == "vote_pk" and day in pk_happens:
            assert f"{day}-pk" in speech_dict
            if f"{day}-pk" not in vote_dict:
                vote_dict[f"{day}-pk"] = defaultdict(list)
                total_effective_votes_by_villager[f"{day}-pk"] = 0
            vote_dict[f"{day}-pk"][i["target"]].append(i["source"])
            if i["target"] != 0 or i["target"] is not None:
                total_effective_votes_by_villager[f"{day}-pk"] += 1
        
        if event == "end_vote":
            if "expelled" in i["content"]: # someone is expelled, 
                if day not in pk_happens: # and not in pk turn.
                    vote_out_player = i["content"]["expelled"]
                    if vote_out_player in speech_dict[f"{day}-1"]: # 凡被投出的村民发言，就是不好的发言
                        add_to_data.append((vote_out_player, f"{day}_day_speech"))
                    
                    for player_id in speech_dict[f"{day}-1"].keys():
                        role, speech_content = speech_dict[f"{day}-1"][player_id]
                        if role == "Seer":
                            who_vote = vote_dict[f"{day}-1"].get(player_id, [])
                            count_vote_villagers = 0
                            for vote_player in who_vote:
                                if role_mapping.get(str(vote_player), "") != "Werewolf":
                                    count_vote_villagers += 1
                            if count_vote_villagers >= total_effective_votes_by_villager[f"{day}-1"] / 2:
                                if (player_id, f"{day}_day_speech") not in add_to_data:
                                    add_to_data.append((player_id, f"{day}_day_speech"))

                        if role == "Witch":
                            who_vote = vote_dict[f"{day}-1"].get(player_id, [])
                            count_vote_villagers = 0
                            count_vote_werewolf = 0
                            for vote_player in who_vote:
                                if role_mapping.get(str(vote_player), "") == "Werewolf":
                                    count_vote_werewolf += 1
                                else:
                                    count_vote_villagers += 1
                            if (count_vote_werewolf >= 1) and (count_vote_villagers >= 2): # todo: what about ``or``?
                                if (player_id, f"{day}_day_speech") not in add_to_data:
                                    add_to_data.append((player_id, f"{day}_day_speech"))

                else: # in pk turn
                    vote_out_player = i["content"]["expelled"]
                    if vote_out_player in speech_dict[f"{day}-pk"]:
                        add_to_data.append((vote_out_player, f"{day}_day_speech_pk"))
                    
                    for player_id in speech_dict[f"{day}-pk"].keys():
                        role, speech_content = speech_dict[f"{day}-pk"][player_id]
                        if role == "Seer":
                            who_vote = vote_dict[f"{day}-pk"].get(player_id, [])
                            count_vote_villagers = 0
                            for vote_player in who_vote:
                                if role_mapping.get(str(vote_player), "") != "Werewolf":
                                    count_vote_villagers += 1
                            if count_vote_villagers >= total_effective_votes_by_villager[f"{day}-pk"] / 2:
                                if (player_id, f"{day}_day_speech_pk") not in add_to_data:
                                    add_to_data.append((player_id, f"{day}_day_speech_pk"))

                        if role == "Witch":
                            who_vote = vote_dict[f"{day}-pk"].get(player_id, [])
                            count_vote_villagers = 0
                            count_vote_werewolf = 0
                            for vote_player in who_vote:
                                if role_mapping.get(str(vote_player), "") == "Werewolf":
                                    count_vote_werewolf += 1
                                else:
                                    count_vote_villagers += 1
                            if (count_vote_werewolf >= 1) and (count_vote_villagers >= 2): # todo: what about ``or``?
                                if (player_id, f"{day}_day_speech_pk") not in add_to_data:
                                    add_to_data.append((player_id, f"{day}_day_speech_pk"))                          
            elif i["content"]["vote_outcome"] == "draw":
                pk_happens.append(day)
    return add_to_data
        

def extract_bad_speech_werewolf(log, role_mapping, game_type):
    """
    Return: [(player_id, phase)]
    The rules for bad speech for the werewolf side:
    1. 被投出的狼人发言
    2. 发言获得了所有村民投票>=1/2的村民投票的狼人发言
    """
    add_to_data = []
    vote_dict = {} # {day-1: {vote_to -> [who_vote, who_vote]]}
    speech_dict = defaultdict(dict) # {day-1: {speaker -> (role, speak_content)}}
    pk_happens = [] # a list to record pk happens at day i
    total_effective_votes_by_villager = {} # {day-1: 5}
    for i in log:
        day = i["day"]
        event = i["event"]
        # first process speech
        if event == "speech":
            if f"{day}-1" not in speech_dict:
                speech_dict[f"{day}-1"] = defaultdict(tuple)
            speech_dict[f"{day}-1"][i["source"]] = (role_mapping[str(i["source"])],  i["content"]["speech_content"])
        elif event == "speech_pk" and day in pk_happens:
            if f"{day}-pk" not in speech_dict:
                speech_dict[f"{day}-pk"] = {}
            speech_dict[f"{day}-pk"][i["source"]] = ((role_mapping[str(i["source"])],  i["content"]["speech_content"]))
        
        # then process detail vote
        if event == "vote":
            assert f"{day}-1" in speech_dict
            if f"{day}-1" not in vote_dict:
                vote_dict[f"{day}-1"] = defaultdict(list)
                total_effective_votes_by_villager[f"{day}-1"] = 0
            vote_dict[f"{day}-1"][i["target"]].append(i["source"])
            if i["target"] != 0 or i["target"] is not None:
                total_effective_votes_by_villager[f"{day}-1"] += 1
        elif event == "vote_pk" and day in pk_happens:
            assert f"{day}-pk" in speech_dict
            if f"{day}-pk" not in vote_dict:
                vote_dict[f"{day}-pk"] = defaultdict(list)
                total_effective_votes_by_villager[f"{day}-pk"] = 0
            vote_dict[f"{day}-pk"][i["target"]].append(i["source"])
            if i["target"] != 0 or i["target"] is not None:
                total_effective_votes_by_villager[f"{day}-pk"] += 1
        
        if event == "end_vote":
            if "expelled" in i["content"]: # someone is expelled, 
                if day not in pk_happens: # and not in pk turn.
                    vote_out_player = i["content"]["expelled"]
                    if role_mapping.get(str(vote_out_player), "") == "Werewolf": # 凡是被投出，都不好
                        if (vote_out_player, f"{day}_day_speech") not in add_to_data:
                            add_to_data.append((vote_out_player, f"{day}_day_speech"))
                        # 获得了所有村民投票>=1/2的狼人发言
                        who_vote = vote_dict[f"{day}-1"].get(vote_out_player, [])
                        count_vote_villagers = 0
                        for vote_player in who_vote:
                            if role_mapping.get(str(vote_player), "") != "Werewolf":
                                count_vote_villagers += 1
                        if count_vote_villagers >= total_effective_votes_by_villager[f"{day}-1"] / 2:
                            if (vote_out_player, f"{day}_day_speech") not in add_to_data:
                                add_to_data.append((vote_out_player, f"{day}_day_speech"))
                else: # in pk turn
                    vote_out_player = i["content"]["expelled"]
                    if role_mapping.get(str(vote_out_player), "") == "Werewolf":
                        if (vote_out_player, f"{day}_day_speech_pk") not in add_to_data:
                            add_to_data.append((vote_out_player, f"{day}_day_speech_pk"))
                        # 获得了所有村民投票>=1/2的狼人发言
                        who_vote = vote_dict[f"{day}-pk"].get(vote_out_player, [])
                        count_vote_villagers = 0
                        for vote_player in who_vote:
                            if role_mapping.get(str(vote_player), "") != "Werewolf":
                                count_vote_villagers += 1
                        if count_vote_villagers >= total_effective_votes_by_villager[f"{day}-pk"] / 2:
                            if (vote_out_player, f"{day}_day_speech_pk") not in add_to_data:
                                add_to_data.append((vote_out_player, f"{day}_day_speech_pk"))

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
                           type=str, default="sft_agent", help="the behavior data of which model")
    argparser.add_argument('--out_to', type=str, default="KTO_selected/")
    argparser.add_argument("--self_play", action="store_true", help="whether to use self-play")
    args = argparser.parse_args()

    all_bad_speech = {} # {game_id: [(player_id, phase)]}
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
            bad_speech_in_game_i = []
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
            
            if werewolf_is_sft:
                wolf_bad_speech = extract_bad_speech_werewolf(content, role_mapping, args.game_type)
                bad_speech_in_game_i.extend(wolf_bad_speech)
                wolf_cnt += len(wolf_bad_speech)

            if good_is_sft:
                villager_bad_speech = extract_bad_speech_villager(content, role_mapping, args.game_type)
                bad_speech_in_game_i.extend(villager_bad_speech)
                villager_cnt += len(villager_bad_speech)
            
            if len(bad_speech_in_game_i) > 0:
                all_bad_speech[game_id_full] = bad_speech_in_game_i
            
    # post process
    all_bad_speech_out = {}
    cnt = 0
    for path, good_speech in all_bad_speech.items():
        bad_speech_by_player = defaultdict(list)
        for i, (player_id, phase) in enumerate(good_speech):
            if phase not in bad_speech_by_player[player_id]:
                bad_speech_by_player[player_id].append(phase)
                cnt += 1
        all_bad_speech_out[path] = bad_speech_by_player
    print("total bad speech:", cnt, villager_cnt, wolf_cnt)

    # write to file
    output_file = os.path.join(args.out_to, f"bad_speech.json")
    with open(output_file, "w") as f:
        json.dump(all_bad_speech_out, f, indent=4)
