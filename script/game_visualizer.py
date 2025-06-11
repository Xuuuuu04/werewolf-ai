import json
import argparse
import os.path
import gradio as gr
from app_modules.presets import small_and_beautiful_theme

current_file_path = os.path.abspath(__file__)
current_dir = os.path.dirname(current_file_path)
with open(f"{current_dir}/app_modules/custom.css", "r", encoding="utf-8") as f:
    customCSS = f.read()

'''
usage:
python3 game_visualizer.py --game_dir {path to the games} --model_setting {game_setting}
'''


def emojing_roles(role, mode="full"):
    roles = ["Witch", "Guard", "Seer", "Villager", "Werewolf", "Hunter"]
    roles_emoji = ["🧙🏻", "💂", "👁️", "👤", "🐺", "🔫"]
    if mode == "full":
        return role + " " + roles_emoji[roles.index(role)]
    else:
        return roles_emoji[roles.index(role)]


def get_vote_results(vote_detail, id2role_emoji=None):
    s = ""
    for vp, players in vote_detail.items():
        if id2role_emoji is not None:
            all_p = ",".join([f"Player {i}{id2role_emoji[int(i)]} " for i in players])
        else:
            all_p = ",".join([f"Player {i}" for i in players])
        if vp != -1:
            if id2role_emoji is not None:
                s += f"* Vote for **Player {vp}**{id2role_emoji[int(vp)]} (共{len(players)}票): {all_p}\n"
            else:
                s += f"* Vote for **Player {vp}** (共{len(players)}票): {all_p}\n"
        else:
            s += f"* Not to vote: {all_p}\n"
    s += "\n"
    return s


def model_jugde(text):
    model_name = text.split("-")[1]
    return model_name


def get_role_assignment(log_path, model_setting):
    werewolf_model, human_model = model_jugde(model_setting.split("_vs_")[0]), model_jugde \
        (model_setting.split("_vs_")[1])
    with open(log_path, "r") as f:
        log = json.load(f)
    roles = {}
    id2role_emoji = {}
    text = "# **Role assignments:**\n"
    for i in log:
        event = i["event"]
        if event == "god_view":
            for number in i["content"]:
                if i["content"][number] == "Werewolf":
                    name = werewolf_model
                else:
                    name = human_model
                roles[int(number)] = emojing_roles(i["content"][number]) + ", " + name
                id2role_emoji[int(number)] = emojing_roles(i["content"][number], mode="brief")
                text += f'* Player {number} ({name}): {emojing_roles(i["content"][number])} \n'
        if event == "werewolf_team_info":
            break
    text += "\n"
    return roles, id2role_emoji, text


def process_shoot_summary(content):
    reason = content['context']
    hunter_player = content["player"]
    target_player = content["shoot_player"]
    text = f"**{reason}**\n\n"
    text += "> **身份标签**："
    for player_id, label in content["role_prediction"].items():
        text += f"{player_id}号: {','.join(label)}; "
    text += "\n\n"
    return hunter_player, target_player, text


def get_note_md(note_log_path):
    note_path = os.listdir(note_log_path)
    note_dict = dict()
    player_note_path = [os.path.join(note_log_path, path) for path in note_path if "game" not in path]
    for player_note in player_note_path:
        current_info = []
        with open(player_note, encoding="utf-8") as f:
            for line in f:
                single_info = json.loads(line)
                current_info.append(single_info)
                player_id = single_info["player_id"]
                if player_id not in note_dict:
                    note_dict[player_id] = {}
        vote_info = [info for info in current_info if "vote" in info["message"]]
        for message in vote_info:
            note_day = message["message"].split("_")[0]
            if "vote_reason" in message:
                vote_reason = message["vote_reason"] + "\n\n"
            else:
                vote_reason = "无投票理由" + "\n\n"
            note_dict[player_id][note_day] = vote_reason
    return note_dict


def find_action_reason(log_path, player, role, day, event):
    action_reason_ret = ""
    phase = f"{day}_night_{event}"
    file = log_path.replace("game_log.json", f"Player_{player}.jsonl")
    with open(file, "r") as f:
        for line in f:
            content = json.loads(line.strip())
            if content["phase"] == phase:
                res = content.get("action_reason", "")
                if len(res) > 0:
                    action_reason_ret = res.replace("\n", "").strip()
                    break
    return action_reason_ret


def find_speech_template(log_path, player, day, event):
    speech_template_ret = ""
    phase = f"{day}_day_{event}"
    file = log_path.replace("game_log.json", f"Player_{player}.jsonl")
    with open(file, "r") as f:
        for line in f:
            content = json.loads(line.strip())
            if content["phase"] == phase:
                temp = content.get("speech_template", "")
                if len(temp) > 0:
                    speech_template_ret = temp.replace("贴上身份标签", "").replace("把", "")
                    break
    return speech_template_ret


def get_gamelog_md(roles, id2role_emoji, log_path, model_setting):
    with open(log_path, "r") as f:
        log = json.load(f)
    round_num = 0
    text = ""
    vote_out_players = []
    all_note_takings = {i + 1: {} for i in range(len(roles))}
    all_votes_reasonings = {i + 1: {} for i in range(len(roles))}
    all_reviews = {}
    end_flag = False
    current_player_speech = None
    speech_summary_dict = {}
    day_processed = []
    werewolf_model, human_model = model_jugde(model_setting.split("_vs_")[0]), model_jugde \
        (model_setting.split("_vs_")[1])
    against = [werewolf_model, human_model]
    for i in log:
        event = i["event"]
        if "content" in i.keys():
            content = i["content"]

        if event == "game_setting":
            round_num = int(i["day"]) + 1
            text += "------\n"
            vote_detail_this_round = {}
            speech_summary_dict = {}
            werewolf_night_discussion_text = ""
            current_player_speech = None
            vote_stage = round_num

        elif event == "skill_seer":
            action_reason = find_action_reason(log_path, i['source'], role="Seer", day=i['day'], event=i['event'])
            text += f"* Seer👁 ({i['source']}号): 查看玩家{i['target']}. [*原因：{action_reason}*]"
            if i["content"]["cheked_identity"] == "bad":
                text += f"{i['target']}号玩家是 **werewolf**.\n"
            else:
                text += f"{i['target']}号玩家不是 **werewolf**.\n"

        elif event == "skill_guard":
            player = i["source"]
            action_reason = find_action_reason(log_path, i['source'], role="Guard", day=i['day'], event=i['event'])
            if i['target'] != 0:
                text += f"* 守卫 💂({i['source']}号): 守护 {i['target']}号玩家 [*原因：{action_reason}*]\n"
            else:
                text += f"* 守卫 💂({i['source']}号): 守护空守 [*原因：{action_reason}*]\n"
        elif event == "skill_wolf":
            action_reason = find_action_reason(log_path, i['source'], role="Guard", day=i['day'], event=i['event'])
            werewolf_night_discussion_text += f"{i['source']}选择刀{i['target']} *[{action_reason}]*; "
            werewolf_night_discussion_text += "\n"
        elif event == "kill_decision":
            text += f"# **Night {round_num}**\n"
            text += f"* 狼人🐺: 杀害{i['target']}号玩家\n"
            text += "\n> " + werewolf_night_discussion_text
        elif event == "skill_witch":
            action_reason = find_action_reason(log_path, i['source'], role="Guard", day=i['day'], event=i['event'])
            if "poison" in i["content"]:
                text += f"* 女巫🧙🏻({i['source']}号): 毒{i['target']}号玩家\n"
                text += f"* 女巫🧙🏻({i['source']}号): 没有救人\n"
            elif "heal" in i["content"]:
                text += f"* 女巫🧙🏻({i['source']}号): 没有毒人\n"
                text += f"* 女巫🧙🏻({i['source']}号): 救起{i['target']}号玩家\n"
            elif "pass" in i["content"]:
                text += f"* 女巫🧙🏻({i['source']}号): 没有救人，没有毒人\n"
            if len(action_reason):
                text += "\n> 女巫原因：" + action_reason
        elif event == "speech": 
            if i['day'] not in day_processed:
                text += f"\n----\n# 第{i['day']}天发言. \n"
                day_processed.append(i['day'])
            werewolf_night_discussion_text = ""
            current_player_speech = i['source']
            role = roles[current_player_speech]
            text += f"- **Player {i['source']}** ({role}):\n"
            text += f"\n**{i['content']['speech_content']}**\n"

            speech_temp = find_speech_template(log_path, i['source'], i['day'], i['event'])
            if len(speech_temp) > 0:
                text += f"> *{speech_temp}*\n"

            if current_player_speech in speech_summary_dict and len(speech_summary_dict[current_player_speech]) > 0:
                text += speech_summary_dict[current_player_speech]
                speech_summary_dict[current_player_speech] = ""
        elif event == "vote":
            vote_stage = i['day']
            p = i['source']
            vote_to = i['target']
            if vote_to != 0:
                vote_text = f"投给 **{vote_to}号玩家** ({roles[vote_to]})。\n"
            else:
                vote_to = -1
                vote_text = f"弃票。\n"
            all_votes_reasonings[p][f"Day {vote_stage}"] = vote_text

            if vote_to not in vote_detail_this_round:
                vote_detail_this_round[vote_to] = [i["source"]]
            else:
                vote_detail_this_round[vote_to].append(i["source"])

        elif event == "end_vote":
            text += f"## Voting @ Day {vote_stage}\n"
            text += f"{get_vote_results(vote_detail_this_round, id2role_emoji=id2role_emoji)}\n"
            round_num = int(i["day"]) + 1
            if i["target"] == 0:
                text += f"### 无人出局 **\n\n"
            else:
                text += f"### **{i['target']}号玩家 ({roles[i['target']]})出局！**\n\n"
                vote_out_players.append(i['target'])
            text += "------\n"
            vote_detail_this_round = {}
            speech_summary_dict = {}
            werewolf_night_discussion_text = ""
            current_player_speech = None
            vote_stage = round_num
            vote_detail_this_round = {}
        elif event == "speech_pk": 
            if "平票PK阶段" not in text:
                text += f"## Day {vote_stage - 1} 平票PK阶段 \n"
            current_player_speech = i['source']
            role = roles[current_player_speech]
            text += f"- **Player {i['source']}** ({role}):\n"
            text += f"\n**{i['content']['speech_content']}**\n"
            if current_player_speech in speech_summary_dict and len(speech_summary_dict[current_player_speech]) > 0:
                text += speech_summary_dict[current_player_speech]
                speech_summary_dict[current_player_speech] = ""
        elif event == "vote_pk":
            vote_stage = i['day']
            p = i['source']
            vote_to = i['target']
            if vote_to != 0:
                vote_text = f"投给 **{vote_to}号玩家** ({roles[vote_to]})。\n"
            else:
                vote_to = -1
                vote_text = f"弃票。\n"
            all_votes_reasonings[p][f"Day {vote_stage}_pk"] = vote_text

            if vote_to not in vote_detail_this_round:
                vote_detail_this_round[vote_to] = [i["source"]]
            else:
                vote_detail_this_round[vote_to].append(i["source"])

        elif event == "end_game" and not end_flag:
            if i["content"]['outcome'] == -1:
                winner, symbol = against[-1], "👤"
            else:
                winner, symbol = against[0], "🐺"
            text += f"## Game end at Round {i['day']}. {symbol}***{winner}*** wins!"
            end_flag = True

    text += "\n"
    return text, all_votes_reasonings, vote_out_players, all_reviews


def find_matching_pk(game_dir, model_setting, choice):
    game_record = os.listdir(game_dir)
    if len(choice) == 0:
        choice = [f"game_{i}" for i in range(1, 31)]
    matching_paths = [os.path.join(game_dir, path) for path in game_record if
                      path in choice and "game_log.json" in os.listdir(os.path.join(game_dir, path))]
    return matching_paths


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--game_dir", type=str, default=None, help="game path")
    parser.add_argument("--model_setting", type=str, default=None,
                        help="game setting: example: w-makto_vs_v-gpt4")
    args = parser.parse_args()

    # choice = ["game_1", "game_2", "game_3", "game_4"]
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
                all_notes = get_note_md(game_choice)
                game_log_main_str, all_votes, vote_out_players, all_reviews = get_gamelog_md(roles, id2role_emoji,
                                                                                             event_log,
                                                                                             args.model_setting)
                with gr.Row():
                    gr.Markdown(role_assignment_md)
                with gr.Row():
                    with gr.Column(scale=6):
                        gr.Markdown("# Main Game\n" + game_log_main_str)
                    with gr.Column(scale=4):
                        gr.Markdown("# Votings & NoteTakings")
                        for player_id in all_votes.keys():
                            note_day_processed = []
                            with gr.Tab(f"Player {player_id} ({roles[player_id]})"):
                                if len(all_votes[player_id]) == 0:
                                    gr.Markdown(f"## 首夜被刀🔪")
                                for day in all_votes[player_id]:
                                    with gr.Row():
                                        gr.Markdown(f"# 📅{day}")
                                    with gr.Row():  
                                        gr.Markdown(f"**VOTE**: " + all_votes[player_id][day] + "\n")
                                    with gr.Row(): 
                                        note_day = day.split(" ")[1].split("_")[0]
                                        if note_day in note_day_processed:
                                            continue
                                        else:
                                            if note_day in all_notes[player_id]:
                                                gr.Markdown \
                                                    (f"# 📒笔记:\n" + "\n " + all_notes[player_id][note_day].replace("\n"
                                                                                                                    ,
                                                                                                                    "\n\n") + "\n------")
                                            elif player_id in vote_out_players: 
                                                gr.Markdown \
                                                    (f"# 📒笔记:\n" + "- **VOTE OUT! No note-takings this turn.**" + "\n------")
                                            note_day_processed.append(note_day)

    demo.queue(max_size=20).launch(server_name="0.0.0.0", server_port=6006)