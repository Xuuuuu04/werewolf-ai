import logging
from werewolf.agents.prompt_template_v0 import CON
from werewolf.agents.base_agent import Agent
from werewolf.helper.log_utils import JsonFormatter, CustomLoggerAdapter, format_game_log

class LLMAgent(Agent):
    def __init__(self,
                 client=None,
                 tokenizer=None,
                 llm=None,
                 temperature=1.0,
                 log_file=None,
                 debug=False):
        self.client = client
        self.tokenizer = tokenizer
        self.llm = llm
        self.nlp_action_to_env_action = {}
        self.temperature = temperature
        self.debug = debug  # 控制是否显示调试信息
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
        """委托给共享实现 `werewolf.helper.log_utils.format_game_log`。

        历史上此方法与 run_battle.format_game_log 各维护一份中文文案，
        容易分叉。现统一从 log_utils.format_log_entry 取值。
        """
        return format_game_log(game_log)

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

