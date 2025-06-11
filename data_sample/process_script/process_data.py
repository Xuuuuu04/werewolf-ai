import argparse
import copy
from pickletools import read_stringnl_noescape
from tqdm import tqdm
from utils import *
import json
from glob import glob
import os
import re
from dis import Instruction
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import random
import tokenize
import pdb
import math
import csv


def build_data(item):
#     prompt = """以下是一个任务的指令。请根据指令对任务进行回复。

# ### 指令：
# {instruction}

# ### 回复：""".format(instruction=item["instruction"]+item['input'])
    instruction = item["instruction"]
    user_input = item['input']
    response = item["output"]
    return {
        "instruction": instruction,
        "input": user_input,
        "response": response
    }


def write_parquet(data, name, save_path):
    # schema = pa.schema([
    #     ('prompt', pa.string()),
    #     ('response', pa.string())
    # ])
    schema = pa.schema([
        ('instruction', pa.string()),
        ('input', pa.string()),
        ('response', pa.string())
    ])
    # prompt_array = []
    instruction_array = []
    input_array = []
    response_array = []
    random.shuffle(data)
    for d in data:
        # prompt_array.append(d["prompt"])
        instruction_array.append(d["instruction"])
        input_array.append(d["input"])
        response_array.append(d["response"])

    # 生成 Parquet 数据
    # prompts = pa.array(prompt_array, type = pa.string())
    instructions = pa.array(instruction_array, type = pa.string())
    inputs = pa.array(input_array, type = pa.string())
    responses = pa.array(response_array, type = pa.string())

    # 生成 Parquet 数据
    # batch = pa.RecordBatch.from_arrays(
    #     [prompts, responses],
    #     schema = schema
    # )
    batch = pa.RecordBatch.from_arrays(
        [instructions, inputs, responses],
        schema = schema
    )
    table = pa.Table.from_batches([batch])
    # 写 Parquet 文件 sft.parquet
    pq.write_table(table, f'{save_path}/{name}.parquet')


def get_parquet(speech, action, vote, save_path):
    # 定义 Schema
    data1 = []
    data2 = []
    data3 = []
###################################
    for item in speech:
        data1.append(build_data(item))
    write_parquet(data1,"speech",save_path)
###################################
    for item in action:
        data2.append(build_data(item))
    write_parquet(data2,"action",save_path)
###################################
    for item in vote:
        data3.append(build_data(item))
    write_parquet(data3,"vote",save_path)

    write_parquet(data1+data2+data3,"shuffled_data",save_path)


def flatten_dict(d, parent_key='', sep='.'):
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)

def save_to_csv(data, filename, keys):
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        for item in data:
            flat_item = flatten_dict(item)
            writer.writerow({k: flat_item.get(k, '') for k in keys})


def main(read_path, save_path, language, debug_path, add_rolepred, add_persona):
    config = {}
    data_speech= []
    data_action = []
    data_vote = []
    config['data_source'] = read_path
    config['save_path'] = save_path

    role_info = {}
    read_path_tqdm = tqdm(read_path, desc= "Process SFT Data", leave=True)
    for path in read_path_tqdm:
        # print(path)
        tqdm.write(path)
        if "9_player" in path:
            players = 9
            if "guard_witch_seer" in path:
                type = "guard_witch_seer"
            elif "hunter_witch_seer" in path:
                type = "hunter_witch_seer"
        elif "7_player" in path:
            players = 7
            if "seer_witch" in path:
                type = "seer_witch"
            elif "seer_guard" in path:
                type = "seer_guard"
        file_name = os.path.basename(path)
        event_path = os.path.join(path, f"event_{language}.json")
        with open(event_path,'r') as f:
            event = json.load(f)
        note_path = os.path.join(path, f"note_{language}.json")
        with open(note_path,'r') as f:
            note = json.load(f)

        werewolf = werewolf_ins(players, type, language=language)
        all_info = werewolf.visable_data(event,note)
        current_role = werewolf.global_id
        if language == "zh":
            current_role_dict = {str(i+1):ROLE_CN_MAPPING[current_role[i]] for i in range(len(current_role))}
        else:
            current_role_dict = {str(i+1):ROLE_EN_MAPPING[current_role[i]] for i in range(len(current_role))}
        role_info[path.split("/")[-1][:6]] = current_role_dict
        
        if debug_path != None:
            with open('all_info.json','w') as f:
                json.dump(all_info,f,ensure_ascii=False,indent=4)

        # speech 数据对
        for id, player in enumerate(all_info):
            current_round = None 
            next_round = 0
            for index, round in enumerate(player[1:]):
                if "speech" not in round['content'].keys():
                    continue
                next_round = round['round']
                if next_round == current_round and (player[0]["role_number"] not in player[1:][index-1]['content']['vote_result']['vote_equal_list']):
                    current_round = round['round']
                    continue
                speech = {}
                speech["instruction"] = player[0]["info"]
                persona = round['content']['speech']['persona']
                if persona is not None and add_persona:
                    charater = generate_persona(persona)
                    speech["instruction"] = player[0]["info"] + "\n" + charater

                if next_round == current_round and (player[0]["role_number"] in player[1:][index-1]['content']['vote_result']['vote_equal_list']):
                    if language == "zh":
                        speech["input"] = f"""在本场游戏中，你目前已知以下信息：
1. 角色设定：{player[0]['role_setting']}
2. 客观信息：
- 游戏进程：目前游戏进行到第{round["round"]}轮的平票PK阶段，PK台上是{get_pk_info(player[1:][index-1]['content']['vote_result']['vote_equal_list'])}
- {get_live_player_vote(round['content']['speech']['alive'], round['content']['night']['action'], round['content']['night']['role_visable'], player[1:][:index+1], round["round"], "speech")}
{get_pk_speech_order(round['content']['speech']['all_speech'][-len(player[1:][index-1]['content']['vote_result']['vote_equal_list']):])}
- 夜晚信息：{get_night_info(player[1:][:index+1])}
- 投票情况：{get_past_vote(player[1:][:index], language=language) if get_past_vote(player[1:][:index], language=language) != "" else "暂无"}
3. 主观信息：
{get_past_note(player[1:][:index-1])}
{get_pk_speech(current_round, player[1:][index-1]['content']['speech']['all_speech'], round['content']['speech']['past_speech'])}
{player[0]['role_simple_des']}请综合角色设定、客观信息以及主观信息分析场上目前的局势（注意客观信息一定为真实的，主观信息可能包含欺骗性的发言），总结接下来的发言意图（包括发言中希望向大家呈现的身份、发言中为每位玩家贴上的身份标签以及最终的归票）并组织你本轮的发言。请用关键字为“想要展示的身份”、“身份标签”、“归票”和“发言”的json格式输出。
"""
                    else:
                        speech["input"] = f"""In this game, you currently have the following information:
1. Role Setting: {player[0]['role_setting']}
2. Objective Information:
- Game Progress: The game is currently in Round {round["round"]}'s tie-break PK phase, with {get_pk_info(player[1:][index-1]['content']['vote_result']['vote_equal_list'])} on the PK platform
- {get_live_player_vote(round['content']['speech']['alive'], round['content']['night']['action'], round['content']['night']['role_visable'], player[1:][:index+1], round["round"], "speech", language='en')}
{get_pk_speech_order(round['content']['speech']['all_speech'][-len(player[1:][index-1]['content']['vote_result']['vote_equal_list']):], language=language)}
- Night Information: {get_night_info(player[1:][:index+1], language="en")}
- Voting Situation: {get_past_vote(player[1:][:index], language=language) if get_past_vote(player[1:][:index], language=language) != "" else "None yet"}
3. Subjective Information:
{get_past_note(player[1:][:index-1], language=language)}
{get_pk_speech(current_round, player[1:][index-1]['content']['speech']['all_speech'], round['content']['speech']['past_speech'], language=language)}
{player[0]['role_simple_des']} Please analyze the current situation based on role settings, objective information, and subjective information (note that objective information is always true, while subjective information may contain deceptive statements), summarize your speaking intentions for the next speech (including the identity you wish to present to everyone, identity labels for each player, and final vote direction) and organize your speech for this round. Please output in JSON format using the keywords "Identity to Display", "Identity Labels", "Vote Direction" and "Speech".
"""
                    speech_type = 'pk'
                else:
                    if language == "zh":
                        speech["input"] = f"""在本场游戏中，你目前已知以下信息：
1. 角色设定：{player[0]['role_setting']}
2. 客观信息：
- 游戏进程：目前游戏进行到第{round["round"]}轮。
- {get_live_player_vote(round['content']['speech']['alive'], round['content']['night']['action'], round['content']['night']['role_visable'], player[1:][:index+1], round["round"], "speech")}
{get_speech_order(round['content']['speech']['all_speech'])}
- 夜晚信息：{get_night_info(player[1:][:index+1])}
- 投票情况：{get_past_vote(player[1:][:index], language=language) if get_past_vote(player[1:][:index], language=language) != "" else "暂无"}
3. 主观信息：
{get_past_note(player[1:][:index])}
{get_past_speech_speech(round['round'], round['content']['speech']['past_speech'])}
{player[0]['role_simple_des']}请综合角色设定、客观信息以及主观信息分析场上目前的局势（注意客观信息一定为真实的，主观信息可能包含欺骗性的发言），总结接下来的发言意图（包括发言中希望向大家呈现的身份、发言中为每位玩家贴上的身份标签以及最终的归票）并组织你本轮的发言。请用关键字为“想要展示的身份”、“身份标签”、“归票”和“发言”的json格式输出。
"""
                    else:
                        speech["input"] = f"""In this game, you currently have the following information:
1. Role Setting: {player[0]['role_setting']}
2. Objective Information:
- Game Progress: The game is currently in Round {round["round"]}.
- {get_live_player_vote(round['content']['speech']['alive'], round['content']['night']['action'], round['content']['night']['role_visable'], player[1:][:index+1], round["round"], "speech", language="en")}
{get_speech_order(round['content']['speech']['all_speech'], language="en")}
- Night Information: {get_night_info(player[1:][:index+1],language="en")}
- Voting Situation: {get_past_vote(player[1:][:index], language=language) if get_past_vote(player[1:][:index], language=language) != "" else "None yet"}
3. Subjective Information:
{get_past_note(player[1:][:index], language=language)}
{get_past_speech_speech(round['round'], round['content']['speech']['past_speech'], language="en")}
{player[0]['role_simple_des']} Please analyze the current situation based on role settings, objective information, and subjective information (note that objective information is always true, while subjective information may contain deceptive statements), summarize your speaking intentions for the next speech (including the identity you wish to present to everyone, identity labels for each player, and final vote direction) and organize your speech for this round. Please output in JSON format using the keywords "Identity to Display", "Identity Labels", "Vote Direction" and "Speech".
"""
                    speech_type = 'normal'
                # speech["output"] = round['content']['speech']['info']
                speech["output"] = integrate_speech(get_self_present_label(round['content']['speech']['self_present_label'], language=language), 
                                                    get_speech_person_label(round['content']['speech']['speech_person_label'], language=language), 
                                                    get_call_for_vote(round['content']['speech']['call_for_vote'], language=language), 
                                                    round['content']['speech']['info'], language=language)
                speech['meta'] = {"game_id":file_name,"extra":{"turn":f"day-{round['round']}", "type":speech_type},"player_id":id+1, "role":player[0]['role'], "type":"speech", "game_setting":type}
                current_round = round['round']
                # pdb.set_trace()
                data_speech.append(speech)


        # action format
        shoot_yesornot = True
        for id, player in enumerate(all_info):
            player_visable = ""
            current_round = None
            next_round = 0
            for index, round in enumerate(player[1:]):
                next_round = round['round']
                if next_round == current_round:
                    current_round = round['round']
                    continue
                # day action
                if 'day' in round['content'] and shoot_yesornot:
                    action = {}
                    action["instruction"] = player[0]["info"]
                    action_god = round['content']['day']['shoot_info']['god']
                    shoot_type = round['content']['day']['shoot_or_not']
                    if shoot_type == 2 or shoot_type == -2: # 公投出局的情况
                        if language == "zh":
                            action["input"] = f"""在本场游戏中，你目前已知以下信息：
1. 角色设定：
你是{str(round['content']['day']['shoot_info']['hunter_player'])}号玩家。\n你的身份是：猎人。\n你可以在被狼人杀害或者在白天被放逐出局后，选择翻开自己的身份牌，带走场上一位存活的玩家，你可以选择不翻牌，但是翻了牌后必须带人。你的目标是合理利用这个技能为村民消灭狼人。
2. 客观信息：
- 游戏进程：目前游戏进行到第{round["round"]}轮。
- {get_live_player_vote(round['content']['day']['alive'], round['content']['night']['action'], round['content']['night']['role_visable'], player[1:][:index+1], round["round"], "shoot")}
- 夜晚信息：{get_night_info(player[1:][:index+1])}
- 投票情况：{get_past_vote(player[1:][:index], language=language) if get_past_vote(player[1:][:index], language=language) != "" else "暂无"}
3. 主观信息：
{get_past_note(player[1:][:index])}
{get_past_speech_speech(round['round'], round['content']['speech']['past_speech'])}
你目前是{str(round['content']['day']['shoot_info']['hunter_player'])}号猎人。{action_god}
"""
                        else:
                            action["input"] = f"""In this game, you currently have the following information:
1. Role Setting:
You are Player No. {str(round['content']['day']['shoot_info']['hunter_player'])}.\nYour identity is: Hunter.\nAfter being killed by werewolves or being exiled during the day, you can choose to reveal your identity card and take one surviving player with you. You can choose not to reveal your card, but once revealed, you must take someone with you. Your goal is to reasonably use this ability to help the villagers eliminate the werewolves.
2. Objective Information:
- Game Progress: The game is currently in Round {round["round"]}.
- {get_live_player_vote(round['content']['day']['alive'], round['content']['night']['action'], round['content']['night']['role_visable'], player[1:][:index+1], round["round"], "shoot", language="en")}
- Night Information: {get_night_info(player[1:][:index+1], language="en")}
- Voting Situation: {get_past_vote(player[1:][:index], language=language) if get_past_vote(player[1:][:index], language=language) != "" else "None yet"}
3. Subjective Information:
{get_past_note(player[1:][:index], language=language)}
{get_past_speech_speech(round['round'], round['content']['speech']['past_speech'], language="en")}
You are currently Hunter No. {str(round['content']['day']['shoot_info']['hunter_player'])}. {action_god}
"""
                    elif shoot_type == 1 or shoot_type == -1: # 夜晚被杀的情况
                        if language == "zh":
                            action["input"] = f"""在本场游戏中，你目前已知以下信息：
1. 角色设定：
你是{str(round['content']['day']['shoot_info']['hunter_player'])}号玩家。\n你的身份是：猎人。\n你可以在被狼人杀害或者在白天被放逐出局后，选择翻开自己的身份牌，带走场上一位存活的玩家，你可以选择不翻牌，但是翻了牌后必须带人。你的目标是合理利用这个技能为村民消灭狼人。
2. 客观信息：
- 游戏进程：目前游戏进行到第{round["round"]}轮。
- {get_live_player_vote(round['content']['day']['alive'], round['content']['night']['action'], round['content']['night']['role_visable'], player[1:][:index+1], round["round"], "shoot")}
- 夜晚信息：{get_night_info(player[1:][:index+1])}
- 投票情况：{get_past_vote(player[1:][:index], language=language) if get_past_vote(player[1:][:index], language=language) != "" else "暂无"}
3. 主观信息：
{get_past_note_ucround(player[1:][:index], round["round"])}
{get_all_speech(player[index]['round'], player[index]['content']['speech']['all_speech']) if "content" in player[index] else "暂无"}
你目前是{str(round['content']['day']['shoot_info']['hunter_player'])}号猎人。{action_god}
"""
                        else:
                            action["input"] = f"""In this game, you currently have the following information:
1. Role Setting:
You are Player No. {str(round['content']['day']['shoot_info']['hunter_player'])}.\nYour identity is: Hunter.\nAfter being killed by werewolves or being exiled during the day, you can choose to reveal your identity card and take one surviving player with you. You can choose not to reveal your card, but once revealed, you must take someone with you. Your goal is to reasonably use this ability to help the villagers eliminate the werewolves.
2. Objective Information:
- Game Progress: The game is currently in Round {round["round"]}.
- {get_live_player_vote(round['content']['day']['alive'], round['content']['night']['action'], round['content']['night']['role_visable'], player[1:][:index+1], round["round"], "shoot", language="en")}
- Night Information: {get_night_info(player[1:][:index+1], language="en")}
- Voting Situation: {get_past_vote(player[1:][:index], language=language) if get_past_vote(player[1:][:index], language=language) != "" else "None yet"}
3. Subjective Information:
{get_past_note_ucround(player[1:][:index], round["round"])}
{get_all_speech(player[index]['round'], player[index]['content']['speech']['all_speech'], language=language) if "content" in player[index] else "None yet"}
You are currently Hunter No. {str(round['content']['day']['shoot_info']['hunter_player'])}. {action_god}
"""
                    action["output"] = integrate_shoot(round['content']['day']['shoot_info']['target_player'], 
                                                       round["content"]["day"]["shoot_info"]["shoot_reason"], language=language)
                    action['meta'] = {"game_id":file_name,"extra":{"turn":f"day-{round['round']}", "type":"normal"},"player_id":id+1, "role":"hunter", "type":"action", "game_setting":type}
                    current_round = round['round']
                    data_action.append(action)
                    shoot_yesornot = False
                        
                # night action
                if round['content']['night']['action'] == None:
                    continue
                action = {}
                action["instruction"] = player[0]["info"]
                if language == "zh":
                    action["input"] = f"""在本场游戏中，你目前已知以下信息：
1. 角色设定：
{player[0]['role_setting']}
2. 客观信息：
- 游戏进程：目前游戏进行到第{round["round"]}轮。
- {get_live_player_action(round['content']['night']['alive'], round['content']['night']['action']['action'], round['content']['night']['action'], round['content']['night']['role_visable'], player[1:][:index], round["round"])}
- 投票情况：{get_past_vote(player[1:][:index], language=language) if get_past_vote(player[1:][:index], language=language) != "" else "暂无"}
3. 主观信息：
{get_past_note_ucround(player[1:][:index], round["round"])}
{get_all_speech(player[index]['round'], player[index]['content']['speech']['all_speech']) if "content" in player[index] else "暂无"}
{player[0]['role_simple_des']}{round['content']['night']['action']['god']}
"""
                else:
                    action["input"] = f"""In this game, you currently have the following information:
1. Role Setting:
{player[0]['role_setting']}
2. Objective Information:
- Game Progress: The game is currently in Round {round["round"]}.
- {get_live_player_action(round['content']['night']['alive'], round['content']['night']['action']['action'], round['content']['night']['action'], round['content']['night']['role_visable'], player[1:][:index], round["round"], language="en")}
- Voting Situation: {get_past_vote(player[1:][:index], language=language) if get_past_vote(player[1:][:index], language=language) != "" else "None yet"}
3. Subjective Information:
{get_past_note_ucround(player[1:][:index], round["round"], language=language)}
{get_all_speech(player[index]['round'], player[index]['content']['speech']['all_speech'], language=language) if "content" in player[index] else "None yet"}
{player[0]['role_simple_des']}{round['content']['night']['action']['god']}
"""
                # {get_past_note(player[1:][:index]) if get_past_note(player[1:][:index]) != "" else "暂无"}
                # action["output"] = str(round['content']['night']['action']['target'])
                player_visable = round["content"]["night"]["role_visable"]
                if round["round"] == 1:
                    if language == "zh":
                        first_action_reason = "第一晚" + generate_reason(round["content"]["night"]["action"]["action"], round["content"]["night"]["action"]["target"], round['content']['night']['role_visable'])
                    else:
                        first_action_reason = "First night " + generate_reason_en(round["content"]["night"]["action"]["action"], round["content"]["night"]["action"]["target"], round['content']['night']['role_visable'])
                    tmp_reason = first_action_reason
                    if "随机毒杀" in first_action_reason or "randomly" in first_action_reason:
                        p = random.random()
                        if p >= 0.5: 
                            if 'note' in round['content']:
                                next_reason = round["content"]["note"]["info"]["future_night_strategy"]
                            continue
                    action["output"] = integrate_action(round['content']['night']['action']['target'], first_action_reason, round["content"]["night"]["action"]["action"], language=language)
                    if 'note' in round['content']:
                        next_reason = round["content"]["note"]["info"]["future_night_strategy"]
                else:
                    # print(round)
                    action['output'] = integrate_action(round['content']['night']['action']['target'], copy.deepcopy(next_reason), round["content"]["night"]["action"]["action"], language=language)
                    tmp_reason = copy.deepcopy(next_reason)
                    if 'note' in round['content']:
                        next_reason = round["content"]["note"]["info"]["future_night_strategy"]
                # action["output"] = integrate_strings(round['content']['night']['action']['target'], player[index]["content"]["note"]["info"]["future_night_strategy"], round["content"]["night"]["action"]["action"])
                action['meta'] = {"game_id":file_name,"extra":{"turn":f"day-{round['round']}", "type":"normal"},"player_id":id+1, "role":player[0]['role'], "type":"action", "game_setting":type}
                current_round = round['round']
                if tmp_reason != None and tmp_reason != "":
                    data_action.append(action)


        # vote format
        for id, player in enumerate(all_info):
            if len(player) == 1:
                continue
            current_round = None 
            next_round = 0
            for index, round in enumerate(player[1:]):
                if 'vote' not in round['content']:
                    continue
                # if round['content']['night']['action'] == None:
                #     continue
                next_round = round['round']
                vote = {}
                vote["instruction"] = player[0]["info"]
                if next_round == current_round: # PK阶段特殊处理
                    if language == "zh":
                        vote["input"] = f"""在本场游戏中，你目前已知以下信息：
1. 角色设定：{player[0]['role_setting']}
2. 客观信息：
- 游戏进程：目前游戏进行到第{round["round"]}轮的平票PK阶段，PK台上是{get_pk_info(player[1:][index-1]['content']['vote_result']['vote_equal_list'])}
- {get_live_player_vote(round['content']['speech']['alive'], round['content']['night']['action'], round['content']['night']['role_visable'], player[1:][:index+1], round["round"], "vote")}
- 夜晚信息：{get_night_info(player[1:][:index+1])}
- 投票情况：{get_past_vote(player[1:][:index], language=language) if get_past_vote(player[1:][:index], language=language) != "" else "暂无"}
3. 主观信息：
{get_past_note(player[1:][:index-1])}
{get_pk_round_speech(current_round, player[1:][index-1]['content']['speech']['all_speech'], round['content']['speech']['all_speech'][-len(player[1:][index-1]['content']['vote_result']['vote_equal_list']):])}
{get_last_note(player[index]['round'], player[index])}
{player[0]['role_simple_des']}请综合角色设定、客观信息以及主观信息分析场上目前的局势（注意客观信息一定为真实的，主观信息可能包含欺骗性的发言）输出投票原因和要投票出局的玩家，直接输出玩家编号数字；如果弃票，请输出“弃票”。请用关键字为“笔记”、“投票原因”和“投票玩家”的json格式输出。
"""
                    else:
                        vote["input"] = f"""In this game, you currently have the following information:
1. Role Setting: {player[0]['role_setting']}
2. Objective Information:
- Game Progress: The game is currently in Round {round["round"]}'s tied vote PK stage, the players on the PK platform are {get_pk_info(player[1:][index-1]['content']['vote_result']['vote_equal_list'])}
- {get_live_player_vote(round['content']['speech']['alive'], round['content']['night']['action'], round['content']['night']['role_visable'], player[1:][:index+1], round["round"], "vote", language="en")}
- Night Information: {get_night_info(player[1:][:index+1], language="en")}
- Voting Situation: {get_past_vote(player[1:][:index], language=language) if get_past_vote(player[1:][:index], language=language) != "" else "None yet"}
3. Subjective Information:
{get_past_note(player[1:][:index-1], language=language)}
{get_pk_round_speech(current_round, player[1:][index-1]['content']['speech']['all_speech'], round['content']['speech']['all_speech'][-len(player[1:][index-1]['content']['vote_result']['vote_equal_list']):])}
{get_last_note(player[index]['round'], player[index])}
{player[0]['role_simple_des']}Please analyze the current situation based on role settings, objective information, and subjective information (note that objective information is always true, while subjective information may contain deceptive statements). Output the voting reason and the player to be voted out by directly outputting the player's number; if abstaining, please output "abstain". Please output in JSON format with keywords "notes", "voting_reason" and "voting_player".
"""
                    vote["output"] = integrate_vote_nonote(round['content']['vote']['info'], 
                                                           round['content']['vote']['action']['target'],
                                                           language=language)
                    vote_type = "pk"
                else:
                    if language == "zh":
                        vote["input"] = f"""在本场游戏中，你目前已知以下信息：
1. 角色设定：{player[0]['role_setting']}
2. 客观信息：
- 游戏进程：目前游戏进行到第{round["round"]}轮。
- {get_live_player_vote(round['content']['speech']['alive'], round['content']['night']['action'], round['content']['night']['role_visable'], player[1:][:index+1], round["round"], "vote")}
- 夜晚信息：{get_night_info(player[1:][:index+1])}
- 投票情况：{get_past_vote(player[1:][:index], language=language) if get_past_vote(player[1:][:index], language=language) != "" else "暂无"}
3. 主观信息：
{get_past_note(player[1:][:index])}
{get_round_speech(round['content']['speech']['all_speech'])}
{player[0]['role_simple_des']}请综合角色设定、客观信息以及主观信息分析场上目前的局势并形成你本轮的笔记（注意客观信息一定为真实的，主观信息可能包含欺骗性的发言），要求对夜晚信息和玩家发言进行总结和分析，并输出投票原因和要投票出局的玩家，直接输出玩家编号数字；如果弃票，请输出“弃票”。请用关键字为“笔记”、“投票原因”和“投票玩家”的json格式输出。
"""
                    else:
                        vote["input"] = f"""In this game, you currently have the following information:
1. Role Setting: {player[0]['role_setting']}
2. Objective Information:
- Game Progress: The game is currently in Round {round["round"]}.
- {get_live_player_vote(round['content']['speech']['alive'], round['content']['night']['action'], round['content']['night']['role_visable'], player[1:][:index+1], round["round"], "vote", language="en")}
- Night Information: {get_night_info(player[1:][:index+1], language="en")}
- Voting Situation: {get_past_vote(player[1:][:index], language=language) if get_past_vote(player[1:][:index], language=language) != "" else "None yet"}
3. Subjective Information:
{get_past_note(player[1:][:index], language=language)}
{get_round_speech(round['content']['speech']['all_speech'], language=language)}
{player[0]['role_simple_des']}Please analyze the current situation based on role settings, objective information, and subjective information to form your notes for this round (note that objective information is always true, while subjective information may contain deceptive statements). You need to summarize and analyze the night information and player statements, and output the voting reason and the player to be voted out by directly outputting the player's number; if abstaining, please output "abstain". Please output in JSON format with keywords "notes", "voting_reason" and "voting_player".
"""
                    vote_type = "normal"
                # {get_last_night_speech(round['content']['night'])}
                # try:
                # vote["output"] = f"总结：{round['content']['note']['info']['note']};\n投票原因：{round['content']['vote']['info']}。\n综上，我选择投票给：{round['content']['vote']['action']['target']}。"
                    vote["output"] = integrate_vote(round['content']['note']['info']['note'], 
                                                    round['content']['vote']['info'], 
                                                    round['content']['vote']['action']['target'],
                                                    language=language)
                # except:
                #     pdb.set_trace()
                vote['meta'] = {"game_id":file_name,"extra":{"turn":f"day-{round['round']}","type":vote_type},"player_id":id+1, "role":player[0]['role'], "type":"vote", "game_setting":type}
                current_round = round['round']
                data_vote.append(vote)
                
        if add_rolepred:
            for id, player in enumerate(all_info):
                if len(player) == 1: continue
                current_round = None 
                next_round = 0
                for index, round in enumerate(player[1:]):
                    if 'vote' not in round['content']:
                        continue
                    # if round['content']['night']['action'] == None:
                    #     continue
                    next_round = round['round']
                    vote = {}
                    vote["instruction"] = player[0]["info"]
                    if next_round == current_round: # PK阶段特殊处理
                        if language == "zh":
                            vote["input"] = f"""在本场游戏中，你目前已知以下信息：
1. 角色设定：{player[0]['role_setting']}
2. 客观信息：
- 游戏进程：目前游戏进行到第{round["round"]}轮的平票PK阶段，PK台上是{get_pk_info(player[1:][index-1]['content']['vote_result']['vote_equal_list'])}
- {get_live_player_vote(round['content']['speech']['alive'], round['content']['night']['action'], round['content']['night']['role_visable'], player[1:][:index+1], round["round"], "vote")}
- 夜晚信息：{get_night_info(player[1:][:index+1])}
- 投票情况：{get_past_vote(player[1:][:index], language=language) if get_past_vote(player[1:][:index], language=language) != "" else "暂无"}
3. 主观信息：
{get_rp_speech(player[1:][:index+1])}
{player[0]['role_simple_des']}请综合角色设定、客观信息以及主观信息（注意客观信息一定为真实的，主观信息可能包含欺骗性的发言）预测所有玩家的身份标签。请用关键字为“N号玩家”的json格式输出。
"""
                        else:
                            vote["input"] = f"""In this game, you currently have the following information:
1. Role Setting: {player[0]['role_setting']}
2. Objective Information:
- Game Progress: The game is currently in Round {round["round"]}'s tied vote PK stage, with {get_pk_info(player[1:][index-1]['content']['vote_result']['vote_equal_list'])} on the PK platform
- {get_live_player_vote(round['content']['speech']['alive'], round['content']['night']['action'], round['content']['night']['role_visable'], player[1:][:index+1], round["round"], "vote", language="en")}
- Night Information: {get_night_info(player[1:][:index+1], language=language)}
- Voting Situation: {get_past_vote(player[1:][:index], language=language) if get_past_vote(player[1:][:index], language=language) != "" else "None yet"}
3. Subjective Information:
{get_rp_speech(player[1:][:index+1], language=language)}
{player[0]['role_simple_des']}Please analyze the role settings, objective information, and subjective information (note that objective information is always true, while subjective information may contain deceptive statements) to predict the identity labels of all players. Please output in JSON format with the keyword "Player N".
"""
                        vote["output"] = integrate_rp(current_role_dict, language=language)
                        vote_type = "pk"
                    else:
                        if language == "zh":
                            vote["input"] = f"""在本场游戏中，你目前已知以下信息：
1. 角色设定：{player[0]['role_setting']}
2. 客观信息：
- 游戏进程：目前游戏进行到第{round["round"]}轮。
- {get_live_player_vote(round['content']['speech']['alive'], round['content']['night']['action'], round['content']['night']['role_visable'], player[1:][:index+1], round["round"], "vote")}
- 夜晚信息：{get_night_info(player[1:][:index+1])}
- 投票情况：{get_past_vote(player[1:][:index], language=language) if get_past_vote(player[1:][:index], language=language) != "" else "暂无"}
3. 主观信息：
{get_rp_speech(player[1:][:index+1])}
{player[0]['role_simple_des']}请综合角色设定、客观信息以及主观信息（注意客观信息一定为真实的，主观信息可能包含欺骗性的发言）预测所有玩家的身份标签。请用关键字为“N号玩家”的json格式输出。
"""
                        else:
                            vote["input"] = f"""In this game, you currently have the following information:
1. Role Setting: {player[0]['role_setting']}
2. Objective Information:
- Game Progress: The game is currently in Round {round["round"]}.
- {get_live_player_vote(round['content']['speech']['alive'], round['content']['night']['action'], round['content']['night']['role_visable'], player[1:][:index+1], round["round"], "vote", language="en")}
- Night Information: {get_night_info(player[1:][:index+1], language="en")}
- Voting Situation: {get_past_vote(player[1:][:index], language=language) if get_past_vote(player[1:][:index], language=language) != "" else "None yet"}
3. Subjective Information:
{get_rp_speech(player[1:][:index+1], language=language)}
{player[0]['role_simple_des']}Please analyze the role settings, objective information, and subjective information (note that objective information is always true, while subjective information may contain deceptive statements) to predict the identity labels of all players. Please output in JSON format with the keyword "Player N".
"""
                        vote_type = "normal"
                        vote["output"] = integrate_rp(current_role_dict,language=language)

                    vote['meta'] = {"game_id":file_name,"extra":{"turn":f"day-{round['round']}","type":vote_type},"player_id":id+1, "role":player[0]['role'], "type":"vote", "game_setting":type}
                    current_round = round['round']
                    data_vote.append(vote)
            
    config['number'] = {"speech":len(data_speech), "action": len(data_action), "note": len(data_vote)}
    config['length'] = {"speech":get_length(data_speech), "action": get_length(data_action), "note": get_length(data_vote)}
    with open(os.path.join(save_path,"roles_distribution.json"), "w") as f:
        json.dump(role_info, f, ensure_ascii= False, indent=4)

    return {"config":config,"speech":data_speech,"action":data_action,"vote":data_vote}


def write_file(results):
    config = results['config']
    speech = results['speech']
    action = results['action']
    vote = results['vote']
    save_path = config['save_path']

    if not os.path.exists(save_path):
        os.mkdir(save_path)
    # get_parquet(speech, action, vote, save_path)

    with open(save_path+"/config.json","w") as f:
        json.dump(config,f,ensure_ascii=False,indent=4)
    
    # 定义所有可能的键
    all_keys = ["instruction", "input", "output", "meta.game_id", "meta.extra.turn", "meta.extra.type", "meta.player_id", "meta.role", "meta.type", "meta.game_setting"]
    
    # 保存speech数据
    save_to_csv(speech, save_path + "/speech.csv", all_keys)

    # 保存action数据
    save_to_csv(action, save_path + "/action.csv", all_keys)

    # 保存vote数据
    save_to_csv(vote, save_path + "/vote.csv", all_keys)

    # 合并所有数据并保存
    final = speech + action + vote
    save_to_csv(final, save_path + "/mixed_data.csv", all_keys)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--read_path",
        type=str,
    )
    parser.add_argument("--save_path",type=str)
    parser.add_argument("--language", type=str,default="zh", choices=["zh", "en"])
    parser.add_argument("--debug_path",type=str,default=None)
    parser.add_argument("--add_persona",type=bool,default=False)
    parser.add_argument("--add_rolepred",type=bool,default=False)
    args = parser.parse_args()
    # skip_dataset = ["0407-1-376952876","0407-4-756447788","0409-1-515447852","0409-2-265936896","0416-1-859140137","0508-2-481680933"]
    #0407-1是预守，0407-4和0416-1是预女，
    ###################Generate Dataset###################################
    # skip_dataset.append("0422-3-425165843") # 有问题的数据
    
    read_path = []
    for file_path in args.read_path.split(','):
        for path in glob(f"{file_path}/*"):
            read_path.append(path)
    ###################For Debug###################################
    if args.debug_path != None:
        read_path = [args.debug_path]
    os.makedirs(args.save_path, exist_ok=True)

    # pdb.set_trace()
    results = main(read_path,args.save_path, args.language, args.debug_path,args.add_rolepred, args.add_persona)
    write_file(results)