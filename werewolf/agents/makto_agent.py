import random
import re
import json
from werewolf.agents.prompt_template_v0 import CON
from werewolf.helper.utils import Matcher
from . import agent_registry as AgentRegistry
from werewolf.agents.llm_agent import LLMAgent
from tenacity import retry, stop_after_attempt, RetryError, RetryCallState


def extract_json(text):
    pattern = r'```json\s*([\s\S]*?)\s*```'
    match = re.search(pattern, text)
    if match:
        json_str = match.group(1)
        try:
            json_data = json.loads(json_str)
            return json_str
        except json.JSONDecodeError as e:
            print(f"JSON 解析错误: {e}")
            return None
    else:
        print("未找到 JSON 内容")
        return None


def before_attempts(retry_state: RetryCallState):
    global attempt_number
    attempt_number = retry_state.attempt_number



@AgentRegistry.register(
    ["sft_agent", "makto_agent"])
class MaktoAgent(LLMAgent):
    def __init__(self,
                 client=None,
                 tokenizer=None,
                 llm=None,
                 temperature=0.0,
                 log_file=None):
        super().__init__(client=client, tokenizer=tokenizer, llm=llm, temperature=temperature, log_file=log_file)
        self.matcher = Matcher()
        self.notes = {}  
        self.alive = [f"{i}号" for i in range(1, 10)]  
        self.client = client
        self.vote_reason = {} 

    def _parse_log_time(self, time_text):
        pattern = r"第(\d+)天(白天|夜晚)"
        match = re.search(pattern, time_text)
        matched_day = int(match.group(1))
        time_of_day = "day" if match.group(2) == "白天" else "night"
        return matched_day, time_of_day

    def parse_vote_info(self, game_log, vote_at_day):
        def sort_candidates(candidates):
            sorted_candidates = sorted(candidates, key=lambda candidate: int(candidate[:-1]))
            return sorted_candidates

        vote_info = ""
        pk_player = []
        vote_out_player = None
        for log in game_log:
            log_turn, log_time_of_day = self._parse_log_time(log.time)
            if log_turn != vote_at_day or "vote" not in log.event:
                continue

            if log.event == 'vote':
                if log.target > 0:
                    vote_info += "{}号玩家投给：{}号玩家；\n".format(log.source, log.target)
                else:
                    vote_info += "{}号玩家弃票；\n".format(log.source)
            elif log.event == 'vote_pk':
                if log.target > 0:
                    vote_info += "PK阶段，{}号玩家投给：{}号玩家；\n".format(log.source, log.target)
                else:
                    vote_info += "PK阶段，{}号玩家弃票；\n".format(log.source)
            elif log.event == 'end_vote':
                if log.content['vote_outcome'] == 'all abstention':
                    vote_info += "结果：所有玩家放弃投票，直接进入夜晚。\n"
                elif log.content['vote_outcome'] == 'all abstention in pk':
                    vote_info += "结果：所有玩家放弃投票，直接进入夜晚。\n"
                elif log.content['vote_outcome'] == 'draw':
                    pk_speech_list = ''
                    for idx in log.content['speech_queue']:
                        pk_speech_list += '{}号、'.format(idx)
                    pk_speech_list = pk_speech_list[:-1]
                    pk_vote_list = ''
                    for idx in log.content['vote_queue']:
                        pk_vote_list += '{}号、'.format(idx)
                    pk_vote_list = pk_vote_list[:-1]
                    vote_info += f"结果：平票，由{pk_speech_list}再次PK发言，{pk_vote_list}进行投票。\n"
                    pk_player = sort_candidates(pk_speech_list.split("、"))
                elif log.content['vote_outcome'] == 'draw in pk':
                    vote_info += "结果：再次平票，直接进入夜晚。\n"
                elif type(log.content['vote_outcome']) == int:
                    vote_info += "结果：{}号玩家被投票出局。\n".format(log.content['expelled'])
                    vote_out_player = log.content['expelled']
        return vote_info, vote_out_player, pk_player

    def format_log_with_notes(self, current_phase, game_log):
        note_logs = ""
        night_log_tmp = ""
        night_action_log_tmp = ""
        speech_log_tmp = ""
        current_turn = int(current_phase.split("_")[0])

        for day, content in self.notes.items():
            note_logs += f"第{day}天总结: {content}\n第{day}天投票记录：<VOTE_AT_DAY{day}>\n\n"

        for log in game_log:
            log_turn, log_time_of_day = self._parse_log_time(log.time)
            if "night" in current_phase:  
                if log_turn == current_turn:
                    if log.event == 'skill_wolf':
                        night_log_tmp += "今晚{}号狼人准备猎杀{}号。\n".format(log.source, log.target)
                    elif log.event == "kill_decision":
                        night_log_tmp += "今晚{}号玩家死亡，\n".format(log.target)

            elif "day" in current_phase: 
                if log.event == 'werewolf_team_info' and "狼人为" not in night_action_log_tmp:
                    wolf_team = ''
                    for idx in log.content['wolf_team']:
                        wolf_team += '{},'.format(idx)
                    wolf_team = wolf_team[:-1]
                    night_action_log_tmp += "狼人为：{}号玩家。\n".format(wolf_team)

                if log_turn == current_turn - 1:
                    if log.event == 'end_night':
                        dead_list = ""
                        for idx in log.content['dead_list']:
                            dead_list += '{}号、'.format(idx)
                        if len(dead_list) > 0:
                            dead_list = dead_list[:-1]
                            night_log_tmp = "昨晚{}玩家死亡。;".format(dead_list)
                        else:
                            night_log_tmp = "昨晚是个平安夜，没有人死亡。;"
                    if log.event == 'skill_wolf':
                        if "狼人投票杀害目标（得票多者被杀害，若平票，编号大的狼人选择的目标被杀害）：" not in night_action_log_tmp:
                            night_action_log_tmp += "狼人投票杀害目标（得票多者被杀害，若平票，编号大的狼人选择的目标被杀害）："
                        night_action_log_tmp += f"{log.source}选择杀害{log.target}号;\n"
                    elif log.event == 'kill_decision':
                        night_action_log_tmp += "狼人队伍杀了{}号。\n".format(log.target)
                    elif log.event == 'skill_seer':
                        night_action_log_tmp += "预言家查验{}号玩家，{}号玩家{}。\n".format(log.target, log.target,
                                                                                          '狼人' if log.content[
                                                                                                        'cheked_identity'] == 'bad' else '好人')
                    elif log.event == 'skill_guard':
                        if log.target != 0:
                            night_action_log_tmp += "守卫今晚选择守护{}号玩家。\n".format(log.target)
                        else:
                            night_action_log_tmp += "守卫今晚选择空守。\n"
                    elif log.event == 'skill_witch':
                        if 'heal' in log.content:
                            if log.target != 0:
                                night_action_log_tmp += "女巫用解药治疗了{}号。\n".format(log.target)
                            else:
                                night_action_log_tmp += "女巫没有用解药治疗{}号。\n".format(log.target)
                        elif 'poison' in log.content:
                            if log.target != 0:
                                night_action_log_tmp += "女巫用毒药毒害了{}号。\n".format(log.target)
                            else:
                                night_action_log_tmp += "女巫没有使用毒药。\n"
                    elif log.event == 'skill_hunter':
                        night_action_log_tmp += "{}号是猎人，他在{}射杀了{}号。\n".format(log.source, log.time,
                                                                                        log.target)
                elif log_turn == current_turn:
                    if log.event == 'speech' or log.event == 'speech_pk':
                        if len(log.content['speech_content']) > 0:
                            speech_log_tmp += "**{}号玩家**：{};\n".format(log.source,
                                                                          log.content['speech_content'])
                        else:
                            speech_log_tmp += "**{}号玩家**: 空;\n".format(log.source)

        return note_logs, night_log_tmp, night_action_log_tmp, speech_log_tmp


    def parse_vote_reponse(self, phase, response_text):
        day = int(phase.split("_")[0])
        night_or_action = phase.split("_")[1]
        note_str = self.matcher.match_note(response_text, output_str=True)
        self.notes[day] = note_str.strip()
        vote_reason = self.matcher.match_vote_reason(response_text)

        if "综上" in response_text:
            conclusion = response_text.split("综上")[-1]
            match = re.findall(r'\d+', conclusion)
            if len(match) > 0:
                output_vote = int(match[0])
            else:
                output_vote = -1
        else:
            if "弃票" in response_text:
                output_vote = -1
            else:
                match = re.findall(r'\d+', response_text)
                if len(match) > 0:
                    output_vote = int(match[-1])
                else:
                    output_vote = -1
        return note_str, vote_reason, output_vote



    def _process_speaker_order(self, first_speaker, all_speaker):
        first_index = all_speaker.index(f'{first_speaker}号')
        speak_order = all_speaker[first_index:] + all_speaker[:first_index]
        speak_order = [s + '玩家' for s in speak_order]
        return speak_order

    def _format_log_with_notes(self, current_phase, game_log):
        note_logs = ""
        wolf_team_info = ""
        night_log_tmp = ""
        wolf_killed_at_night = ""
        night_action_log_tmp = ""
        speech_log_tmp = ""
        previous_speaker = []
        pk_speech_log_tmp = ""
        previous_speaker_pk = []
        current_turn = int(current_phase.split("_")[0])

        for day, content in self.notes.items():
            note_logs += f"第{day}天总结: {content}\n\n"
        for log in game_log:
            log_turn, log_time_of_day = self._parse_log_time(log.time)
            if log.event == 'werewolf_team_info' and "狼人为" not in wolf_team_info:
                wolf_team = ''
                for idx in log.content['wolf_team']:
                    wolf_team += '{},'.format(idx)
                wolf_team = wolf_team[:-1]
                wolf_team_info += "- 狼人为：{}号玩家。\n".format(wolf_team)
            if log.event == 'end_night':
                dead_list = ""
                for idx in log.content['dead_list']:
                    dead_list += '{}号、'.format(idx)
                    if f"{idx}号" in self.alive:
                        self.alive.remove(f"{idx}号")
                if len(dead_list) > 0:
                    dead_list = dead_list[:-1]
                    night_log_tmp += f"第{log_turn + 1}轮{dead_list}玩家死亡；"
                else:
                    night_log_tmp += f"第{log_turn + 1}轮是个平安夜，没有人死亡；"
            elif log.event == 'kill_decision':
                night_action_log_tmp += f"第{log_turn + 1}轮狼人阵营选择击杀{log.target}号玩家。"
            elif log.event == 'skill_seer':
                if log.content["cheked_identity"] == "bad":
                    night_action_log_tmp += f"第{log_turn + 1}轮预言家查验{log.target}号玩家，{log.target}号玩家是狼人。"
                else:
                    night_action_log_tmp += f"第{log_turn + 1}轮预言家查验{log.target}号玩家，{log.target}号玩家不是狼人。"
            elif log.event == 'skill_guard':
                if log.target != 0:
                    night_action_log_tmp += f"第{log_turn + 1}轮守卫选择守护{log.target}号玩家。"
                else:
                    night_action_log_tmp += f"第{log_turn + 1}轮守卫没选择保护任何人。"
            elif log.event == 'skill_witch':
                if 'heal' in log.content:
                    if log.target != 0:
                        night_action_log_tmp += f"第{log_turn + 1}轮女巫对{log.target}号玩家使用了解药。"
                    else:
                        night_action_log_tmp += f"第{log_turn + 1}轮女巫没使用解药。"
                elif 'poison' in log.content:
                    if log.target != 0:
                        night_action_log_tmp += f"第{log_turn + 1}轮女巫对{log.target}号玩家使用了毒药。"
                    else:
                        night_action_log_tmp += f"第{log_turn + 1}轮女巫没有使用毒药。"
                elif 'pass' in log.content:
                    night_action_log_tmp += f"第{log_turn + 1}轮女巫没有使用解药；女巫没有使用毒药。"
            elif log.event == 'skill_hunter':
                if log.target != 0:
                    if log_turn == current_turn:
                        night_action_log_tmp += f"{log.source}号是猎人，他在第{current_turn}晚被狼人刀出局后选择射杀{log.target}号。"
                    else: 
                        night_action_log_tmp += f"{log.source}号是猎人，他在第{log_turn}天被投后选择射杀{log.target}号。"

            if "night" in current_phase: 
                if log_turn == current_turn:
                    if log.event == 'skill_wolf':
                        if "狼人投票杀害目标（得票多者被杀害，若平票，编号大的狼人选择的目标被杀害）：" not in night_log_tmp:
                            night_log_tmp += "狼人投票杀害目标（得票多者被杀害，若平票，编号大的狼人选择的目标被杀害）："
                        night_log_tmp += "{}号选择杀害{}号;".format(log.source, log.target)
                    elif log.event == "kill_decision":  
                        wolf_killed_at_night = "今晚{}号玩家死亡，".format(log.target)
            if log_turn == current_turn:
                if log.event == 'speech':
                    previous_speaker.append(log.source)
                    if len(log.content['speech_content']) > 0:
                        speech_log_tmp += "**{}号玩家**：{}\n".format(log.source, log.content['speech_content'].strip())
                    else:
                        speech_log_tmp += "**{}号玩家**： 空。\n".format(log.source)
                elif log.event == 'speech_pk':
                    previous_speaker_pk.append(log.source)
                    if len(log.content['speech_content']) > 0:
                        pk_speech_log_tmp += f"**{log.source}号玩家**：{log.content['speech_content'].strip()}\n"
                    else:
                        pk_speech_log_tmp += f"**{log.source}号玩家**：空。\n"

        return note_logs, night_log_tmp, night_action_log_tmp, wolf_team_info, wolf_killed_at_night, \
            speech_log_tmp, previous_speaker, pk_speech_log_tmp, previous_speaker_pk

    def _format_objective_info(self, phase, observation, note_logs, night_obs, night_action_log,
                               wolf_team_info, prev_speaker, prev_speaker_pk, vote_info, pk_players):
        day = int(phase.split("_")[0])
        objective_info = ""
        if "skill" in phase: 
            objective_info = f"- 游戏进程：目前游戏进行到第{day + 1}轮。\n"
            objective_info += f"- 当前存活的玩家有：{', '.join(self.alive)}，"

            if observation["identity"] == "Werewolf":
                objective_info += "只能在以上玩家中选择进行杀害\n"
                if len(wolf_team_info) > 0:
                    objective_info += wolf_team_info
                if len(night_obs.strip()) > 0:
                    objective_info += night_obs.strip() + "\n"
                else:
                    objective_info += "你是第一个行动的狼人，请选择你的杀害目标。\n"
            elif observation["identity"] == "Guard":
                objective_info += "只能在以上玩家中选择进行守护\n"
                if len(night_action_log.strip()) > 0:
                    objective_info += f"- 行动记录：{night_action_log}\n"
            elif observation["identity"] == "Seer":
                objective_info += "只能在以上玩家中选择进行查验\n"
                if len(night_action_log.strip()) > 0:
                    objective_info += f"- 行动记录：{night_action_log}\n"
            elif observation["identity"] == "Witch":
                if len(night_action_log.strip()) > 0:
                    objective_info += f"\n- 行动记录：{night_action_log}\n"
        elif "speech_pk" in phase:
            objective_info = f"- 游戏进程：目前游戏进行到第{day}轮的平票PK阶段" 
            if len(pk_players) > 0:
                objective_info += f"，PK台上是{'，'.join(pk_players)}玩家"
            objective_info += "\n"
            if observation["identity"] == "Werewolf" and len(wolf_team_info) > 0:
                objective_info += wolf_team_info
            objective_info += f"- 当前存活的玩家有：{', '.join(self.alive)}，\n"
            if len(night_action_log.strip()) > 0:
                objective_info += f"- 行动记录：{night_action_log}\n"
            if len(pk_players) > 0:
                if len(prev_speaker_pk) == 0:
                    speaker_order_pk = self._process_speaker_order(observation["current_act_idx"], pk_players)
                else:
                    first_speaker_pk = prev_speaker_pk[0]
                    speaker_order_pk = self._process_speaker_order(first_speaker_pk, pk_players)
                objective_info += f"- PK阶段的发言顺序为：{'；'.join(speaker_order_pk)}\n"
            objective_info += f"- 夜晚信息：{night_obs}\n"

        elif "speech" in phase:
            objective_info = f"- 游戏进程：目前游戏进行到第{day}轮。\n"
            if observation["identity"] == "Werewolf" and len(wolf_team_info) > 0:
                objective_info += wolf_team_info
            objective_info += f"- 当前存活的玩家有：{', '.join(self.alive)}，\n"
            if len(night_action_log.strip()) > 0:
                objective_info += f"- 行动记录：{night_action_log}\n"
            if len(prev_speaker) == 0:
                speaker_order = self._process_speaker_order(observation["current_act_idx"], self.alive)
            else:
                first_speaker = prev_speaker[0]
                speaker_order = self._process_speaker_order(first_speaker, self.alive)
            objective_info += f"- 本轮的发言顺序为：{'；'.join(speaker_order)}\n"
            objective_info += f"- 夜晚信息：{night_obs}\n"

        elif "vote" in phase:
            objective_info = f"- 游戏进程：目前游戏进行到第{day}轮。\n"
            if observation["identity"] == "Werewolf" and len(wolf_team_info) > 0:
                objective_info += wolf_team_info + "\n"
            objective_info += f"- 当前存活的玩家有：{', '.join(self.alive)}，\n"
            if len(night_action_log.strip()) > 0:
                objective_info += f"- 行动记录：{night_action_log}\n"
            objective_info += f"- 夜晚信息：{night_obs}\n"

        if len(vote_info) == 0:
            objective_info += "- 投票情况：暂无"
        else:
            objective_info += f"- 投票情况：{vote_info}"
        return objective_info

    def _format_subjective_info(self, phase, observation, note_logs, speech_log, pk_speech_log):
        day = int(phase.split("_")[0])
        subjective_info = ""
        if "skill" in phase:
            if day == 0:
                return "暂无"
            else:
                subjective_info = f"- 第{day}轮所有玩家发言：\n"
                subjective_info += speech_log + "\n"
        elif "speech_pk" in phase:
            subjective_info += f"- 本轮（第{day}轮）所有玩家发言：\n{speech_log}\n"
            if len(pk_speech_log.strip()) > 0:
                subjective_info += f"- 当前PK阶段玩家发言：\n{pk_speech_log}\n"
            else:
                subjective_info += f"- 目前PK阶段，你是第一个发言。\n"
        elif "speech" in phase: 
            if len(note_logs.strip()) > 0:
                subjective_info += note_logs + "\n"
            subjective_info += f"- 目前是第{day}轮，本轮在你之前的玩家发言：\n{speech_log}\n"
        elif "vote_pk" in phase:
            if len(note_logs.strip()) > 0:
                subjective_info += note_logs + "\n"
            subjective_info += f"- 本轮（第{day}轮）所有玩家发言：\n{speech_log}\n"
            if len(pk_speech_log.strip()) > 0:
                subjective_info += f"- 第{day}轮PK阶段所有玩家发言：\n{pk_speech_log}\n"
            if day in self.vote_reason:
                vote_reason_in_normal_vote = self.vote_reason[day]
                subjective_info += f"- 第{day}轮你的投票理由为：\n{vote_reason_in_normal_vote}\n"
        elif "vote" in phase:
            if len(note_logs.strip()) > 0:
                subjective_info += note_logs + "\n"
            subjective_info += f"- 本轮所有玩家发言：\n{speech_log}\n"
        return subjective_info

    def format_observation(self, observation):
        phase = observation["phase"]
        day = int(observation["phase"].split("_")[0]) + 1
        identity = observation["identity"]
        identity_info = CON.player_identity_info.format(player_idx=observation['current_act_idx'],
                                                        identity=CON.identity_chinese[identity],
                                                        identity_ability=CON.identity_abilities[identity])
        brief_identity_description = f"你目前是{observation['current_act_idx']}号{CON.identity_chinese[identity]}。"
        note_logs, night_obs, night_action_log, wolf_team_info, wolf_killed_at_night, \
            speech_log, prev_speaker, \
            pk_speech_log, prev_speaker_pk = self._format_log_with_notes(phase, observation["game_log"])

        vote_info = ""
        pk_players_at_day_i = []
        for day_i in range(1, day - 1):
            vote_info += f"第{day_i}轮投票记录："
            vote_info_at_day_i, vote_out_at_day_i, pk_players_at_day_i = self.parse_vote_info(observation['game_log'],
                                                                                              day_i)
            vote_info += vote_info_at_day_i

            if vote_out_at_day_i is not None and f"{vote_out_at_day_i}号" in self.alive:
                self.alive.remove(f"{vote_out_at_day_i}号")
        if "pk" in phase or "skill" in phase:
            vote_info_last_day, vote_out_last_day, pk_players_at_day_i = self.parse_vote_info(observation['game_log'],
                                                                                              day - 1)
            if vote_info_last_day != "":
                vote_info += f"第{day - 1}轮投票记录："
            vote_info += vote_info_last_day
            if vote_out_last_day is not None and f"{vote_out_last_day}号" in self.alive:
                self.alive.remove(f"{vote_out_last_day}号")

        objective_info = self._format_objective_info(phase, observation, note_logs, night_obs,
                                                     night_action_log, wolf_team_info, prev_speaker,
                                                     prev_speaker_pk,
                                                     vote_info, pk_players_at_day_i)
        subjective_info = self._format_subjective_info(phase, observation, note_logs, speech_log, pk_speech_log)

        if "skill" in phase:
            instruction = ""
            if identity == "Werewolf":
                instruction = CON.werewolf_skill_prompt_v3
            elif identity == "Seer":
                instruction = CON.seer_skill_prompt_v3
            elif identity == "Witch":
                instruction = CON.witch_skill_prompt_v3.format(wolf_killed_info=wolf_killed_at_night)
            elif identity == "Guard":
                instruction = CON.guard_skill_prompt_v3
            elif identity == "Hunter":
                instruction = CON.hunter_skill_prompt_v3
            prompt = CON.skill_prompt_v3.format(player_identity_info=identity_info,
                                                objective_info=objective_info,
                                                subjective_info=subjective_info,
                                                your_role=brief_identity_description,
                                                instruction_prompt=instruction)
        elif "speech" in phase:
            prompt = CON.speech_prompt_v3.format(player_identity_info=identity_info,
                                                 objective_info=objective_info,
                                                 subjective_info=subjective_info,
                                                 your_role=brief_identity_description)
        elif "vote" in phase:
            prompt = CON.vote_prompt_v3.format(player_identity_info=identity_info,
                                               objective_info=objective_info,
                                               subjective_info=subjective_info,
                                               your_role=brief_identity_description)
        else:
            raise ValueError("Invalid phase: {}".format(phase))
        return prompt

    def get_sys_prompt(self, observation):
        for i, log in enumerate(observation["game_log"]):
            if log.event == 'game_setting':
                total_players = sum([cnt for _, cnt in log.content.items()])
                if total_players == 9:
                    if "Guard" in log.content:
                        return CON.game_description_9p.format(god_description=CON.guard_description)
                    elif "Hunter" in log.content:
                        return CON.game_description_9p.format(god_description=CON.hunter_description)
                elif total_players == 7:
                    if "Guard" in log.content:
                        return CON.game_description_7p.format(god_description=CON.guard_description)
                    elif "Witch" in log.content:
                        return CON.game_description_7p.format(god_description=CON.witch_description)
            if i > 3:
                break
        return CON.game_description

    def __vllm_generate(self, messages):
        def process_messages(messages):
            processed_messages = []
            for message in messages:
                role = message["role"]
                content = message["content"].strip()
                processed_messages.append({"role": role, "content": content})
            return processed_messages

        messages = process_messages(messages)
        response = self.client.chat.completions.create(
            model=self.llm, messages=messages, temperature=self.temperature,
        )
        response_text = response.choices[0].message.content.strip()
        return response_text



    @retry(stop=stop_after_attempt(3), before=before_attempts)
    def _generate_speech(self, observation, messages):
        global attempt_number
        raw_action = self.__vllm_generate(messages)
        if "```json" in raw_action:
            raw_action = extract_json(raw_action)
        action, _, _, _, speech_template = self.parse_speech(raw_action)
        env_action = ('speech', action)
        print("*******************************")
        print("我是{}号，我的身份是{}, 当前阶段：{}".format(observation['current_act_idx'], observation['identity'],
                                                          observation['phase']))
        print("speech env_action: {}".format(env_action))
        return (env_action,
                {"response": raw_action,
                 "action": action,
                 "speech_template": speech_template,
                 "gen_times": attempt_number})

    @retry(stop=stop_after_attempt(3), before=before_attempts)
    def _generate_vote(self, observation, messages, valid_action):
        phase = observation['phase']
        global attempt_number
        response_text = self.__vllm_generate(messages)
        if "```json" in response_text:
            response_text = extract_json(response_text)
        print(response_text)
        note_str, vote_reason, output_vote = self.parse_note_vote_reason(phase, response_text)
        if output_vote == -1:
            action = "{'投票': '否'}"
        else:
            action = "{" + f"'投票': '{output_vote}'" + "}"
        assert action in valid_action
        assert response_text is not None and vote_reason is not None

        print("我是{}号，我的身份是{}, 当前阶段：{}".format(observation['current_act_idx'],
                                                          observation['identity'], observation['phase']))
        print("retry {}, action: {} valid_action: {} response: {}".format(attempt_number, action, valid_action,
                                                                          response_text))
        print("vote reason: \n{}".format(vote_reason))

        return (action,
                {"response": response_text,
                 "action": action,
                 "phase": phase,
                 "note": note_str,
                 "vote_reason": vote_reason,
                 "gen_times": attempt_number})

    @retry(stop=stop_after_attempt(3), before=before_attempts)
    def _generate_action(self, observation, messages, valid_action):
        global attempt_number
        raw_action = self.__vllm_generate(messages)
        if 'None' in raw_action:
            raw_action = raw_action.replace('None', '否')
        if observation["identity"] == "Witch":
            if "是" in raw_action: 
                for action_tuple in observation['valid_action']:
                    if action_tuple[0] == 'witch_heal':
                        raw_action = raw_action.replace("是", f"{action_tuple[1]}")
                        break
        if "```" in raw_action:
            raw_action = extract_json(raw_action)
        action, action_reason = self.parse_night_action(observation["identity"], raw_action)
        assert action in valid_action
        print("*******************************")
        print("我是{}号，我的身份是{}, 当前阶段：{}".format(observation['current_act_idx'],
                                                          observation['identity'], observation['phase']))
        print("retry {}, action: {} valid_action: {} raw_action: {}".format(attempt_number, action, valid_action,
                                                                            raw_action))
        return (action,
                {"response": raw_action,
                 "action": action,
                 "action_reason": action_reason,
                 "gen_times": attempt_number})

    def act(self, observation):
        system_prompt = self.get_sys_prompt(observation)
        input_prompt = self.format_observation(observation)
        print("\n------ PROMPT (w/o game desc.) ------")
        print(input_prompt)
        phase = observation['phase']
        day = int(phase.split("_")[0])

        if "speech" in phase:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": input_prompt.strip()}
            ]
            env_action, generation_info = self._generate_speech(observation, messages)
            if self.has_log:
                self.logger.info(phase,
                                 extra={"prompt": input_prompt,
                                        "response": generation_info.get("response", ""),
                                        "action": generation_info.get("action", "空"),
                                        "speech_template": generation_info.get("speech_template", ""),
                                        "player_id": observation['current_act_idx'],
                                        "role": observation['identity'],
                                        "phase": phase,
                                        "gen_times": generation_info.get("gen_times", 0)})
        elif "vote" in phase:
            valid_actions_str = self.get_valid_actions_str(observation['valid_action'])
            valid_action = list(self.nlp_action_to_env_action.keys())
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": input_prompt.strip()}
            ]
            try:
                action, generation_info = self._generate_vote(observation, messages, valid_action)
            except RetryError:
                action = random.choice(valid_action)
                generation_info = {"response": action,
                                   "vote_reason": f"超过3次生成投票错误。随机选择一个可行的投票或弃票。",
                                   "gen_times": 4}
            env_action = self.nlp_action_to_env_action[action]
            self.vote_reason[day] = generation_info.get("vote_reason", "")
            if self.has_log:
                self.logger.info(phase,
                                 extra={"prompt": input_prompt,
                                        "response": generation_info.get("response", ""),
                                        "action": action,
                                        "player_id": observation['current_act_idx'],
                                        "role": observation['identity'],
                                        "phase": phase,
                                        "note": generation_info.get("note", ""),
                                        "vote_reason": generation_info.get("vote_reason", ""),
                                        "gen_times": generation_info.get("gen_times", 4)})
        else: 
            valid_actions_str = self.get_valid_actions_str(observation['valid_action'])
            valid_action = list(self.nlp_action_to_env_action.keys())
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": input_prompt.strip()}
            ]
            try:
                action, generation_info = self._generate_action(observation, messages, valid_action)
            except RetryError:
                action = random.choice(valid_action)
                generation_info = {"response": action,
                                   "action_reason": f"超过3次生成错误。随机选择一个可行的动作",
                                   "gen_times": 4}
            env_action = self.nlp_action_to_env_action[action]
            if self.has_log:
                self.logger.info(phase,
                                 extra={"prompt": input_prompt,
                                        "response": generation_info.get("response", ""),
                                        "action": action,
                                        "action_reason": generation_info.get("action_reason"),
                                        "player_id": observation['current_act_idx'],
                                        "role": observation['identity'],
                                        "phase": phase,
                                        "gen_times": generation_info.get("gen_times", 4)})

        return env_action

    def parse_night_action(self, identity, raw_action):
        content = json.loads(raw_action)
        action_str = ""
        action_reason = ""
        if identity == "Witch":
            assert "解药" in content and "毒药" in content
            action_str = str({"解药": content.get("解药", "否"), "毒药": content.get("毒药", "否")})
            action_reason = content.get("原因", "")
        elif identity == "Werewolf":
            assert "杀害" in content
            action_str = str({"杀害": content["杀害"]})
            action_str = action_str.replace(": ", ":")
            action_reason = content.get("原因", "")
        elif identity == "Seer":
            assert "查验" in content
            action_str = str({"查验": content.get("查验", "否")})
            action_str = action_str.replace(": ", ":")
            action_reason = content.get("原因", "")
        elif identity == "Guard":
            assert "守卫" in content
            action_str = str({"守卫": content.get("守卫", "否")})
            action_str = action_str.replace(": ", ":")
            action_reason = content.get("原因", "")
        elif identity == "Hunter":
            shoot = content.get("击杀", "否")
            if shoot == "否" or shoot is None:
                action_str = "不进行射杀"
            else:
                action_str = f"射杀{shoot}号玩家"
            action_reason = content.get("原因", "")
        return action_str, action_reason

    def parse_speech(self, raw_action):
        content = json.loads(raw_action.strip())
        role_labels_str = ""
        speech = content.get("发言", "")
        role_display = content.get("想要展示的身份", "")
        role_labels = content.get("身份标签", {})
        call_for_vote = content.get("归票", "")
        if len(speech) == 0:
            speech = raw_action 
        for player, role in role_labels.items():
            role_labels_str += f"把{player}贴上身份标签：{role}。"
        speech_template = f"展现自己身份为{role_display}。{role_labels_str}。归票：{call_for_vote}。"
        return speech, role_display, role_labels, call_for_vote, speech_template

    def parse_note_vote_reason(self, phase, raw_action):
        day = int(phase.split("_")[0])
        content = json.loads(raw_action)
        note_str = ""
        if "笔记" in content:
            note_str = content["笔记"]
            self.notes[day] = note_str.strip()
        vote_reason = content.get("投票原因", "").strip()
        vote_to = content.get("投票玩家", "")
        if vote_to == "" or vote_to == "None" or vote_to == "弃票" or vote_to == "否":
            output_vote = -1
        else:
            match = re.findall(r'\d+', vote_to)
            if len(match) > 0:
                output_vote = int(match[0])
            else:
                output_vote = -1
        return note_str, vote_reason, output_vote

