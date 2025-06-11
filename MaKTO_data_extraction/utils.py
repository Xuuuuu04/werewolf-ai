import os
import re

game_description_9p = """你现在正在玩一种叫做“狼人杀”的游戏。
在这款游戏中，玩家通常被分为两个阵营：狼人和村民。
狼人杀游戏中不同角色的玩家有不同的目标：
- 村民的目的是识别出狼人，并通过投票使他们出局。
- 对于狼人来说，他们的主要目标是隐藏他们的真实身份，在讨论中误导他人，以免被投票出局并尽可能的猎杀村民。
以下是一些基本规则：
- 身份：玩家的身份是秘密分配的。狼人彼此知道对方的身份，而村民只知道自己的身份。
- 昼夜更替：游戏有交替的白天和黑夜阶段。夜里，狼人秘密选择一名村民猎杀。白天，所有玩家讨论并投票决定他们认为是狼人的玩家，票数最多的玩家被淘汰。
- 特殊角色：游戏中有存在一些有特殊能力的角色，比如能得知玩家身份的“预言家”、具有治疗和毒杀能力的“女巫”等。
- 获胜条件：当游戏中有一个群体实现它们的获胜条件时游戏结束。如果所有狼人被淘汰，村民就获胜。如果狼人杀死了所有普通村民或所有特殊角色，狼人就获胜。
在这个游戏中，我们有从1到9号共9名玩家 —— 6名村民和3名狼人。村民中有特殊角色，包括：
- 1位预言家：
    - 目标：预言家的目的是帮助村民识别狼人。
    - 能力：在夜晚阶段，预言家可以秘密选择一名玩家，每晚了解他的真实身份（是否为狼人）。
- 1位女巫：
    - 目标：女巫的目的是策略性地使用她的特殊能力来帮助村民。
    - 能力：女巫有一瓶解药和一瓶毒药。一旦使用，后续回合中不能再用。女巫不能在同一晚既使用解药又使用毒药。解药可以用来救一名在夜间被狼人猎杀的玩家。毒药可以淘汰一名很可能是狼人的玩家。
{god_description}其他的都是普通村民。
"""

game_description_7p = """你现在正在玩一种叫做“狼人杀”的游戏。
在这款游戏中，玩家通常被分为两个阵营：狼人和村民。
狼人杀游戏中不同角色的玩家有不同的目标：
- 村民的目的是识别出狼人，并通过投票使他们出局。
- 对于狼人来说，他们的主要目标是隐藏他们的真实身份，在讨论中误导他人，以免被投票出局并尽可能的猎杀村民。
以下是一些基本规则：
- 身份：玩家的身份是秘密分配的。狼人彼此知道对方的身份，而村民只知道自己的身份。
- 昼夜更替：游戏有交替的白天和黑夜阶段。夜里，狼人秘密选择一名村民猎杀。白天，所有玩家讨论并投票决定他们认为是狼人的玩家，票数最多的玩家被淘汰。
- 特殊角色：游戏中有存在一些有特殊能力的角色，比如能得知玩家身份的“预言家”等。
- 获胜条件：当游戏中有一个群体实现它们的获胜条件时游戏结束。如果所有狼人被淘汰，村民就获胜。如果狼人杀死了所有普通村民或所有特殊角色，狼人就获胜。

在这个游戏中，我们有从1到7号共7名玩家 —— 5名村民和2名狼人。村民中有特殊角色，包括：
- 1位预言家：
    - 目标：预言家的目的是帮助村民识别狼人。
    - 能力：在夜晚阶段，预言家可以秘密选择一名玩家，每晚了解他的真实身份（是否为狼人）。
{god_description}其他的都是普通村民。"""

guard_description="""- 1位守卫：
    - 目标：守卫的目的是策略性地使用他的特殊能力来帮助村民。
    - 能力：守卫每晚可以保护一名玩家，防止他们受到狼人的攻击。守卫可以选择保护自己，或者选择不保护任何人，但他不能在连续两个夜晚保护同一个玩家。
"""
hunter_description = """- 1位猎人：
    - 目标：猎人的目的是策略性地使用他的特殊能力帮助村民消灭狼人。
    - 能力：当猎人被狼人杀害或者在白天被放逐出局后，他可以翻开自己的身份牌并向场上任意一位活着的玩家射出一发复仇的子弹，带着这位玩家一起死亡。猎人可以选择不翻牌，但是只要翻了牌就必须带人（注意，当猎人被女巫毒杀后，不能翻牌带人）。
"""
witch_description = """- 1位女巫：
    - 目标：女巫的目的是策略性地使用她的特殊能力来帮助村民。
    - 能力：女巫有一瓶解药和一瓶毒药。一旦使用，后续回合中不能再用。女巫不能在同一晚既使用解药又使用毒药。解药可以用来救一名在夜间被狼人猎杀的玩家。毒药可以淘汰一名很可能是狼人的玩家。
"""

def get_system_prompt(game_type):
    if game_type == "9p_seer_witch_guard":
        return game_description_9p.format(god_description=guard_description)
    elif game_type == "9p_seer_witch_hunter":
        return game_description_9p.format(god_description=hunter_description)
    elif game_type == "7p_seer_witch":
        return game_description_7p.format(god_description=witch_description)
    elif game_type == "7p_seer_guard":
        return game_description_7p.format(god_description=guard_description)
    return game_description_9p.format(god_description=guard_description)

def get_game_description(game_type):
    game_desc = get_system_prompt(game_type)
    game_desc = game_desc.replace("你现在正在玩一种叫做“狼人杀”的游戏。\n在这款游戏中，", "狼人杀的游戏规则和须知如下：\n")
    return game_desc


def judge_models(model_setting, sft_model_regx):
    if "_tmp0.5" in model_setting:
        model_setting = model_setting.replace("_tmp0.5", "") # we only consider tmp=0.5,
    werewolf_model_name = model_setting.split("_vs_")[0].split("-")[1]
    good_model_name = model_setting.split("_vs_")[1].split("-")[1]

    werewolf_flag = False
    good_flag = False

    for sft_type in sft_model_regx.split("|"):
        if sft_type == werewolf_model_name:
        # if sft_type in werewolf_model_name:
            werewolf_flag = True
        if sft_type == good_model_name:
        # if sft_type in good_model_name:
            good_flag = True
    return (werewolf_model_name, werewolf_flag), (good_model_name, good_flag)


def get_role_assignment(log):
    for i in log:
        event = i["event"]
        if event == "god_view":
            role_assignment = i["content"] # "1"->"Villager"/"Werewolf"/"Seer"/"Witch"/"Guard"/"Hunter"
            return role_assignment
    return None


def create_message(role, content):
    return {
        "role": role,
        "content": content
    }