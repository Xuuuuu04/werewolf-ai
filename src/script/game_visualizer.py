"""Gradio 游戏日志可视化工具。

读取 `--game_dir` 下的 `game_log.json`，
按事件流渲染人类可读的对局回放。

事件内容字段与 `werewolf.envs.werewolf_text_env_v0` 保持一致
（中文 key，1-based 玩家编号已存储于日志）。
"""
import argparse
import json
import os
import os.path

try:
    import gradio as gr
    from app_modules.presets import small_and_beautiful_theme
except ImportError as exc:  # pragma: no cover - 可视化是可选功能
    raise SystemExit(
        "缺少 gradio 依赖。请运行 `pip install gradio>=4.0.0` 后重试。"
    ) from exc

current_file_path = os.path.abspath(__file__)
current_dir = os.path.dirname(current_file_path)
with open(f"{current_dir}/app_modules/custom.css", "r", encoding="utf-8") as f:
    customCSS = f.read()

'''
usage:
python3 game_visualizer.py --game_dir {path to the games} --model_setting {game_setting}
'''

ROLE_EMOJI = {
    "Werewolf": "🐺",
    "Seer": "🔮",
    "Witch": "🧪",
    "Guard": "🛡️",
    "Hunter": "🔫",
    "Villager": "👤",
    "Hunter ": "🔫",
}


def emojing_roles(role, mode="full"):
    emoji = ROLE_EMOJI.get(role, "👤")
    if mode == "full":
        return f"{role} {emoji}"
    return emoji


def get_vote_results(vote_detail, id2role_emoji=None):
    s = ""
    for vp, players in vote_detail.items():
        if id2role_emoji is not None:
            all_p = ",".join([f"Player {i}{id2role_emoji.get(int(i), '')} " for i in players])
        else:
            all_p = ",".join([f"Player {i}" for i in players])
        if vp not in (-1, 0):
            emoji = id2role_emoji.get(int(vp), "") if id2role_emoji else ""
            s += f"* Vote for **Player {vp}**{emoji} (共{len(players)}票): {all_p}\n"
        else:
            s += f"* Not to vote: {all_p}\n"
    s += "\n"
    return s


def model_jugde(text):
    return text.split("-")[-1] if "-" in text else text


def get_role_assignment(log_path, model_setting):
    if "_vs_" in (model_setting or ""):
        werewolf_model = model_jugde(model_setting.split("_vs_")[0])
        human_model = model_jugde(model_setting.split("_vs_")[1])
    else:
        werewolf_model = human_model = model_setting or "AI"
    with open(log_path, "r", encoding="utf-8") as f:
        log = json.load(f)
    roles = {}
    id2role_emoji = {}
    text = "# **Role assignments:**\n"
    for i in log:
        if i.get("event") == "god_view":
            for number in i["content"]:
                role_name = i["content"][number]
                name = werewolf_model if role_name == "Werewolf" else human_model
                roles[int(number)] = emojing_roles(role_name) + ", " + name
                id2role_emoji[int(number)] = emojing_roles(role_name, mode="brief")
                text += f'* Player {number} ({name}): {emojing_roles(role_name)} \n'
        if i.get("event") == "werewolf_team_info":
            break
    text += "\n"
    return roles, id2role_emoji, text


def get_gamelog_md(roles, id2role_emoji, log_path, model_setting):
    with open(log_path, "r", encoding="utf-8") as f:
        log = json.load(f)
    round_num = 0
    text = ""
    vote_out_players = []
    all_votes_reasonings = {i + 1: {} for i in range(len(roles))}
    end_flag = False
    vote_detail_this_round = {}
    day_processed = []

    for i in log:
        event = i.get("event")
        content = i.get("content", {})
        if event == "game_setting":
            round_num = int(i["day"]) + 1
            text += "------\n"
            vote_detail_this_round = {}
        elif event == "skill_seer":
            checked = content.get("查验结果")
            verdict = "werewolf" if checked == "bad" else "好人"
            text += f"* 预言家 🔮 ({i['source']}号): 查看玩家{i['target']}, 结果：**{verdict}**\n"
        elif event == "skill_guard":
            target = content.get("保护目标", -1)
            if target and target > 0:
                text += f"* 守卫 🛡️ ({i['source']}号): 守护 {target}号玩家\n"
            else:
                text += f"* 守卫 🛡️ ({i['source']}号): 空守\n"
        elif event == "skill_wolf":
            text += f"* 狼人 🐺 ({i['source']}号): 选择刀 {content.get('猎杀目标', '?')}号\n"
        elif event == "kill_decision":
            text += f"# **Night {round_num}**\n"
            text += f"* 狼人队伍: 杀害 {content.get('猎杀决定', '?')}号玩家\n\n"
        elif event == "skill_witch":
            if "毒药目标" in content:
                text += f"* 女巫 🧪 ({i['source']}号): 毒 {content['毒药目标']}号玩家 (未使用解药)\n"
            elif "解药目标" in content:
                text += f"* 女巫 🧪 ({i['source']}号): 救起 {content['解药目标']}号玩家 (未使用毒药)\n"
            elif "放弃行动" in content:
                text += f"* 女巫 🧪 ({i['source']}号): 不救不毒\n"
        elif event == "skill_hunter":
            target = content.get("射杀目标", -1)
            if target and target > 0:
                text += f"* 猎人 🔫 ({i['source']}号): 开枪带走 {target}号玩家\n"
            else:
                text += f"* 猎人 🔫 ({i['source']}号): 未开枪\n"
        elif event == "end_night":
            dead_list = content.get("死亡名单", [])
            if dead_list:
                text += f"🌙 本夜死亡: {dead_list}\n"
            else:
                text += "🌙 本夜平安夜\n"
        elif event == "speech" or event == "speech_pk":
            if i['day'] not in day_processed:
                text += f"\n----\n# 第{i['day']}天发言. \n"
                day_processed.append(i['day'])
            speech = content.get("发言内容", "")
            role = roles.get(i['source'], "?")
            text += f"- **Player {i['source']}** ({role}):\n"
            text += f"\n**{speech}**\n"
        elif event == "vote":
            vote_to = i.get("target", -1)
            p = i["source"]
            if vote_to and vote_to > 0:
                vote_text = f"投给 **{vote_to}号玩家** ({roles.get(vote_to, '?')})。\n"
            else:
                vote_to = -1
                vote_text = "弃票。\n"
            all_votes_reasonings[p][f"Day {i['day']}"] = vote_text
            vote_detail_this_round.setdefault(vote_to, []).append(p)
        elif event == "vote_pk":
            vote_to = i.get("target", -1)
            p = i["source"]
            if vote_to and vote_to > 0:
                vote_text = f"PK投给 **{vote_to}号玩家** ({roles.get(vote_to, '?')})。\n"
            else:
                vote_to = -1
                vote_text = "PK弃票。\n"
            all_votes_reasonings[p][f"Day {i['day']}_pk"] = vote_text
            vote_detail_this_round.setdefault(vote_to, []).append(p)
        elif event == "end_vote":
            vote_stage = i["day"]
            text += f"## Voting @ Day {vote_stage}\n"
            text += f"{get_vote_results(vote_detail_this_round, id2role_emoji=id2role_emoji)}\n"
            result = content.get("投票结果")
            if isinstance(result, int):
                text += f"### **{result}号玩家 ({roles.get(result, '?')})出局！**\n\n"
                vote_out_players.append(result)
            elif result == "平票":
                text += "### 平票，进入PK\n\n"
            elif result == "PK阶段平票":
                text += "### PK再次平票，无人出局\n\n"
            elif result in ("全员弃票", "PK阶段全员弃票"):
                text += "### 全员弃票，无人出局\n\n"
            text += "------\n"
            vote_detail_this_round = {}
        elif event == "end_game" and not end_flag:
            outcome = content.get("游戏结果", "")
            if "狼人" in outcome:
                symbol = "🐺"
                winner = "Werewolf"
            else:
                symbol = "👤"
                winner = "Villager"
            text += f"## Game end at Round {i['day']}. {symbol}***{winner}*** wins!"
            end_flag = True

    text += "\n"
    return text, all_votes_reasonings, vote_out_players, {}


def find_matching_pk(game_dir, model_setting, choice):
    if not game_dir or not os.path.isdir(game_dir):
        return []
    game_record = os.listdir(game_dir)
    if len(choice) == 0:
        choice = [f"game_{i}" for i in range(1, 31)]
    matching_paths = [os.path.join(game_dir, path) for path in game_record
                      if path in choice
                      and os.path.isdir(os.path.join(game_dir, path))
                      and "game_log.json" in os.listdir(os.path.join(game_dir, path))]
    return matching_paths


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--game_dir", type=str, default=None, help="game path")
    parser.add_argument("--model_setting", type=str, default=None,
                        help="game setting: example: w-makto_vs_v-gpt4")
    args = parser.parse_args()

    choice = []  # if choice is empty, all the games will be checked

    game_ready_list = find_matching_pk(args.game_dir, args.model_setting, choice)
    if args.game_dir is not None:
        args.model_setting = os.path.basename(args.game_dir.rstrip("/"))
    with gr.Blocks(css=customCSS, theme=small_and_beautiful_theme) as demo:
        demo.title = "WereWolf demo"
        gr.Markdown(f"{args.model_setting}\n")
        for game_choice in game_ready_list:
            game_id = game_choice.split("/")[-1]
            with gr.Tab(f"{game_id}"):
                event_log = os.path.join(game_choice, "game_log.json")
                roles, id2role_emoji, role_assignment_md = get_role_assignment(event_log, args.model_setting)
                game_log_main_str, all_votes, vote_out_players, _ = get_gamelog_md(
                    roles, id2role_emoji, event_log, args.model_setting)
                with gr.Row():
                    gr.Markdown(role_assignment_md)
                with gr.Row():
                    with gr.Column(scale=6):
                        gr.Markdown("# Main Game\n" + game_log_main_str)
                    with gr.Column(scale=4):
                        gr.Markdown("# Votings & NoteTakings")
                        for player_id in all_votes.keys():
                            note_day_processed = []
                            with gr.Tab(f"Player {player_id} ({roles.get(player_id, '?')})"):
                                if len(all_votes[player_id]) == 0:
                                    gr.Markdown("## 首夜被刀🔪")
                                for day in all_votes[player_id]:
                                    with gr.Row():
                                        gr.Markdown(f"# 📅{day}")
                                    with gr.Row():
                                        gr.Markdown(f"**VOTE**: " + all_votes[player_id][day] + "\n")
                                    note_day = day.split(" ")[1].split("_")[0]
                                    if note_day in note_day_processed:
                                        continue
                                    note_day_processed.append(note_day)

    demo.queue(max_size=20).launch(server_name="0.0.0.0", server_port=6006)
