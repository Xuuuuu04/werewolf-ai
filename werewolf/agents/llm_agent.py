import logging
from werewolf.agents.prompt_template_v0 import CON
from werewolf.agents.base_agent import Agent
from werewolf.helper.log_utils import JsonFormatter, CustomLoggerAdapter

class LLMAgent(Agent):
    def __init__(self,
                 client=None,
                 tokenizer=None,
                 llm=None,
                 temperature=1.0,
                 log_file=None):
        self.client = client 
        self.tokenizer = tokenizer
        self.llm = llm
        self.nlp_action_to_env_action = {}
        self.temperature = temperature
        if log_file is not None:
            self.has_log = True
            self.handler = logging.FileHandler(log_file)
            self.handler.setLevel(logging.INFO)
            self.handler.setFormatter(JsonFormatter())
            logger = logging.getLogger(log_file.split("/")[-1].replace(".jsonl", ""))
            logger.setLevel(logging.INFO)
            logger.addHandler(self.handler)
            self.logger = CustomLoggerAdapter(logger, extra={})
        else:
            self.has_log = False


    def format_observation(self, observation):
        phase = observation['phase']
        if 'skill' in phase or 'vote' in phase:
            valid_actions = observation['valid_action']
            valid_actions_str = self.get_valid_actions_str(valid_actions)
            identity = observation['identity']
            identity_info = CON.player_identity_info.format(player_idx=observation['current_act_idx'],
                                                            identity=CON.identity_chinese[identity],
                                                            identity_ability=CON.identity_abilities[identity])
            logs = self.format_log(observation['game_log'])
            if 'skill' in phase:
                prompt = CON.skill_prompt.format(game_description=CON.game_description,
                                                 player_identity_info=identity_info, logs=logs,
                                                 valid_actions=valid_actions_str)
            else:
                prompt = CON.vote_prompt.format(game_description=CON.game_description,
                                                player_identity_info=identity_info, logs=logs,
                                                valid_actions=valid_actions_str)
        elif 'speech' in phase:
            identity = observation['identity']
            identity_info = CON.player_identity_info.format(player_idx=observation['current_act_idx'],
                                                            identity=CON.identity_chinese[identity],
                                                            identity_ability=CON.identity_abilities[identity])
            logs = self.format_log(observation['game_log'])

            prompt = CON.speech_prompt.format(game_description=CON.game_description,
                                              player_identity_info=identity_info, logs=logs, )
        else:
            raise ValueError
        return prompt

    def _print_log(self, log):
        print("===============")
        print(log.event)
        print(log.viewer)
        print(log.source)
        print(log.target)
        print(log.content)
        print(log.time)
        print("===============\n")


    def format_log(self, game_log):
        logs = ""
        for log in game_log:
            log_tmp=""
            if log.event == 'game_setting':
                log_tmp = '本局游戏各个身份和对应数量如下：\n'
                for key, value in log.content.items():
                    log_tmp += "- {}:{}\n".format(CON.identity_chinese[key], value)
            if log.event == 'skill_wolf':
                log_tmp = "{}号是狼人，他在{}准备猎杀{}号。\n".format(log.source, log.time, log.target)
            elif log.event == 'kill_decision':
                log_tmp = "狼人队伍在{}猎杀了{}号。\n".format(log.time, log.target)
            elif log.event == 'skill_seer':
                log_tmp = "{}号是预言家，你在{}查验了{}号的身份是{}。\n".format(log.source, log.time, log.target,
                                                                              '狼人' if log.content[
                                                                                            'cheked_identity'] == 'bad' else '好人')
            elif log.event == 'skill_guard':
                log_tmp = "{}号是守卫，你在{}守护了{}号。\n".format(log.source, log.time, log.target)
            elif log.event == 'skill_witch':
                if 'heal' in log.content:
                    log_tmp = "{}号是女巫，你在{}使用解药治疗了{}号。\n".format(log.source, log.time, log.target)
                elif 'poison' in log.content:
                    log_tmp = "{}号是女巫，你在{}使用毒药毒害了{}号。\n".format(log.source, log.time, log.target)
            elif log.event == 'skill_hunter':
                log_tmp = "{}号是猎人，他在{}射杀了{}号。\n".format(log.source, log.time, log.target)
            elif log.event == 'speech' or log.event == 'speech_pk':
                if len(log.content['speech_content']) > 0:
                    log_tmp = "{}号在{}发言内容：{}。\n".format(log.source, log.time, log.content['speech_content'])
                else:
                    log_tmp = "{}号在{}发言内容为空。\n".format(log.source, log.time)
            elif log.event == 'vote':
                if log.target > 0:
                    log_tmp = "{}号在{}投票给{}号。\n".format(log.source, log.time, log.target)
                else:
                    log_tmp = "{}号在{}放弃投票。\n".format(log.source, log.time, log.target)
            elif log.event == 'vote_pk':
                if log.target > 0:
                    log_tmp = "{}号在{}pk环节投票给{}号。\n".format(log.source, log.time, log.target)
                else:
                    log_tmp = "{}号在{}pk环节放弃投票。\n".format(log.source, log.time, log.target)
            elif log.event == 'end_game':
                log_tmp = "游戏结束！\n"
            elif log.event == 'end_night':
                dead_list = ""
                for idx in log.content['dead_list']:
                    dead_list += '{}号、'.format(idx)
                if len(dead_list) > 0:
                    dead_list = dead_list[:-1]
                    log_tmp = "{}死亡的玩家是{}。\n".format(log.time, dead_list)
                else:
                    log_tmp = "{}无人死亡。\n".format(log.time)
            elif log.event == 'end_vote':
                if log.content['vote_outcome'] == 'all abstention':
                    log_tmp = "{}所有玩家放弃投票，直接进入夜晚。\n".format(log.time)
                elif log.content['vote_outcome'] == 'all abstention in pk':
                    log_tmp = "{}再次发言，所有玩家放弃投票，直接进入夜晚。\n".format(log.time)
                elif log.content['vote_outcome'] == 'draw':
                    pk_speech_list = ''
                    for idx in log.content['speech_queue']:
                        pk_speech_list += '{}号、'.format(idx)
                    pk_speech_list = pk_speech_list[:-1]

                    pk_vote_list = ''
                    for idx in log.content['vote_queue']:
                        pk_vote_list += '{}号、'.format(idx)
                    pk_vote_list = pk_vote_list[:-1]
                    log_tmp = "{}平票，由{}再次发言，{}进行投票。\n".format(log.time, pk_speech_list, pk_vote_list)
                elif log.content['vote_outcome'] == 'draw in pk':
                    log_tmp = "{}再次平票，直接进入夜晚。\n".format(log.time)
                elif type(log.content['vote_outcome']) == int:
                    log_tmp = "{}通过投票驱逐了{}号。\n".format(log.time, log.content['expelled'])
                else:
                    raise ValueError
            elif log.event == 'werewolf_team_info':
                wolf_team = ''
                for idx in log.content['wolf_team']:
                    wolf_team += '{}号、'.format(idx)
                wolf_team = wolf_team[:-1]
                log_tmp = "狼人队伍的成员是{}。\n".format(wolf_team)
            elif log.event == 'self_identity':
                pass
            logs += log_tmp

        return logs

    def get_valid_actions_str(self, valid_actions):
        valid_actions_str = ""
        for action in valid_actions:
            if action[0] == 'kill':
                if action[1] == 0:
                    valid_actions_str += "- {'杀害':'否'}\n"
                else:
                    valid_actions_str += "- {{'杀害':'{0}'}}\n".format(action[1])
            elif action[0] == 'check':
                if action[1] == 0:
                    valid_actions_str += "- {'查验':'否'}\n"
                else:
                    valid_actions_str += "- {{'查验':'{0}'}}\n".format(action[1])
            elif action[0] == 'guard':
                if action[1] == 0:
                    valid_actions_str += "- {'守卫':'否'}\n"
                else:
                    valid_actions_str += "- {{'守卫':'{0}'}}\n".format(action[1])
            elif 'witch' in action[0]:
                if action[0] == 'witch_pass':
                    valid_actions_str += "- {'解药': '否', '毒药': '否'}\n"
                elif action[0] == 'witch_poison':
                    valid_actions_str += "- {{'解药': '否', '毒药': '{0}'}}\n".format(action[1])
                elif action[0] == 'witch_heal':
                    valid_actions_str += "- {{'解药': '{0}', '毒药': '否'}}\n".format(action[1])
            elif action[0] == 'shoot':
                if action[1] == 0:
                    valid_actions_str += "- 不进行射杀\n"
                else:
                    valid_actions_str += "- 射杀{}号玩家\n".format(action[1])
            elif action[0] == 'vote' or action[0] == 'vote_pk':
                if action[1] == 0:
                    valid_actions_str += "- {'投票': '否'}\n"
                else:
                    valid_actions_str += "- {{'投票': '{0}'}}\n".format(action[1])

        self.nlp_action_to_env_action = {}
        for (nlp_action, env_action) in zip(valid_actions_str.split('\n'), valid_actions):
            self.nlp_action_to_env_action[nlp_action[2:]] = env_action

        return valid_actions_str

    def reset(self):
        return

    def act(self, observation):
        raise NotImplementedError

