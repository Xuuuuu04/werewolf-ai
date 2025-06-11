import os
import json
import argparse
import re
from collections import defaultdict
from utils import judge_models, get_role_assignment

SPEECH_WORDS_THRESHOLD = 0
def extract_good_speech_villager(log, role_mapping, game_type):
    """
    Return: [(player_id, phase)]
    The rules for good speech for the villager side:
    1. 没有获得一票、且发言字数超过 SPEECH_WORDS_THRESHOLD 字 的好人发言。
    2. 预言家或者女巫发言，最后没有被投出 且 获取村民票数<=1，可以视为好发言。
    """
    add_to_data = []
    vote_dict = {} # {day-1: {vote_to -> [who_vote, who_vote]]}
    speech_dict = defaultdict(dict) # {day-1: {speaker -> (role, speak_content)}}
    pk_happens = [] # a list to record pk happens at day i
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
            if role_mapping.get(str(i["source"]), "") != "Werewolf": # only count the vote from villager
                vote_dict[f"{day}-1"][i["target"]].append(i["source"])
        elif event == "vote_pk" and day in pk_happens:
            assert f"{day}-pk" in speech_dict
            if f"{day}-pk" not in vote_dict:
                vote_dict[f"{day}-pk"] = defaultdict(list)
            if role_mapping.get(str(i["source"]), "") != "Werewolf":
                vote_dict[f"{day}-pk"][i["target"]].append(i["source"])
        
        if event == "end_vote":
            if "expelled" in i["content"]: # someone is expelled, 
                if day not in pk_happens: # and not in pk turn.
                    vote_out_player = i["content"]["expelled"]
                    for player_id in speech_dict[f"{day}-1"].keys():
                        role, speech_content = speech_dict[f"{day}-1"][player_id]
                        # if no one vote to this player(as villager side), and the speech is long enough
                        if (role != "Werewolf") and (len(speech_content) >= SPEECH_WORDS_THRESHOLD) and (player_id not in vote_dict[f"{day}-1"]): 
                            if (player_id, f"{day}_day_speech") not in add_to_data:
                                add_to_data.append((player_id, f"{day}_day_speech"))
                        elif (role in ["Seer", "Witch"]) and (len(speech_content) >= SPEECH_WORDS_THRESHOLD) and (vote_out_player != player_id): # 如果是神职且没有被投出
                            who_vote = vote_dict[f"{day}-1"].get(player_id, [])
                            if len(who_vote) <= 1 and ((player_id, f"{day}_day_speech") not in add_to_data):
                                add_to_data.append((player_id, f"{day}_day_speech"))
                        
                else: # in pk turn
                    vote_out_player = i["content"]["expelled"]
                    for player_id in speech_dict[f"{day}-pk"].keys():
                        role, speech_content = speech_dict[f"{day}-pk"][player_id]
                        # if no one vote to this player(as villager side), and the speech is long enough
                        if (role != "Werewolf") and (len(speech_content) >= SPEECH_WORDS_THRESHOLD) and player_id not in vote_dict[f"{day}-pk"]:
                            if (player_id, f"{day}_day_speech_pk") not in add_to_data:
                                add_to_data.append((player_id, f"{day}_day_speech_pk"))
                        elif (role in ["Seer", "Witch"]) and (len(speech_content) >= SPEECH_WORDS_THRESHOLD) and (vote_out_player != player_id): # 如果是神职且没有被投出
                            who_vote = vote_dict[f"{day}-pk"].get(player_id, [])
                            if len(who_vote) and ((player_id, f"{day}_day_speech_pk") not in add_to_data):
                                    add_to_data.append((player_id, f"{day}_day_speech_pk"))                            

            elif i["content"]["vote_outcome"] == "draw":
                pk_happens.append(day)
    return add_to_data
        

def extract_good_speech_werewolf(log, role_mapping, game_type):
    """
    Return: [(player_id, phase)]
    The rules for good speech for the werewolf side:
    1. 没有被投出的狼人发言就视为好。
    """
    add_to_data = []
    vote_dict = {} # {day-1: {vote_to -> [who_vote, who_vote]]}
    speech_dict = defaultdict(dict) # {day-1: {speaker -> (role, speak_content)}}
    pk_happens = [] # a list to record pk happens at day i
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
            if role_mapping.get(str(i["source"]), "") != "Werewolf": # only count the vote from villager
                vote_dict[f"{day}-1"][i["target"]].append(i["source"])
        elif event == "vote_pk" and day in pk_happens:
            assert f"{day}-pk" in speech_dict
            if f"{day}-pk" not in vote_dict:
                vote_dict[f"{day}-pk"] = defaultdict(list)
            if role_mapping.get(str(i["source"]), "") != "Werewolf":
                vote_dict[f"{day}-pk"][i["target"]].append(i["source"])
        
        if event == "end_vote":
            if "expelled" in i["content"]: # someone is expelled, 
                if day not in pk_happens: # and not in pk turn.
                    vote_out_player = i["content"]["expelled"]
                    for player_id in speech_dict[f"{day}-1"].keys():
                        role, speech_content = speech_dict[f"{day}-1"][player_id]
                        # if no one vote to this player(as wolf side), and the speech is long enough
                        if (role == "Werewolf") and (len(speech_content) >= SPEECH_WORDS_THRESHOLD) and (player_id != vote_out_player):
                            if (player_id, f"{day}_day_speech") not in add_to_data:
                                add_to_data.append((player_id, f"{day}_day_speech"))
                else: # in pk turn
                    vote_out_player = i["content"]["expelled"]
                    for player_id in speech_dict[f"{day}-pk"].keys():
                        role, speech_content = speech_dict[f"{day}-pk"][player_id]
                        # if no one vote to this player(as villager side), and the speech is long enough
                        if (role == "Werewolf") and (len(speech_content) >= SPEECH_WORDS_THRESHOLD) and (player_id != vote_out_player):
                            if (player_id, f"{day}_day_speech_pk") not in add_to_data:
                                add_to_data.append((player_id, f"{day}_day_speech_pk"))

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
    argparser.add_argument('--out_to', type=str, default="")
    argparser.add_argument('--self_play', action="store_true", help="whether to extract data from self-play")
    args = argparser.parse_args()

    all_good_speech = {} # {game_id: [(player_id, phase)]}
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
            good_speech_in_game_i = []
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
                wolf_good_speech = extract_good_speech_werewolf(content, role_mapping, args.game_type)
                good_speech_in_game_i.extend(wolf_good_speech)
                wolf_cnt += len(wolf_good_speech)

            if good_is_sft:
                villager_good_speech = extract_good_speech_villager(content, role_mapping, args.game_type)
                good_speech_in_game_i.extend(villager_good_speech)
                villager_cnt += len(villager_good_speech)
            
            if len(good_speech_in_game_i) > 0:
                all_good_speech[game_id_full] = good_speech_in_game_i
            
    # post process
    all_good_speech_out = {}
    cnt = 0
    for path, good_speech in all_good_speech.items():
        good_speech_by_player = defaultdict(list)
        for i, (player_id, phase) in enumerate(good_speech):
            if phase not in good_speech_by_player[player_id]:
                good_speech_by_player[player_id].append(phase)
                cnt += 1
        all_good_speech_out[path] = good_speech_by_player
    print("total good speech:", cnt, villager_cnt, wolf_cnt)

    # write to file
    output_file = os.path.join(args.out_to, f"good_speech.json")
    with open(output_file, "w") as f:
        json.dump(all_good_speech_out, f, indent=4)
