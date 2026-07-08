import time
from colorama import Style
from werewolf.agents.llm_agent import LLMAgent
from werewolf.agents.prompt_template_v0 import CON
from werewolf.helper.console_ui import ConsoleUI
from . import agent_registry as AgentRegistry

@AgentRegistry.register(["Human", "human"])
class HumanAgent(LLMAgent):
    def __init__(self,
                 client,
                 tokenizer=None,
                 llm=None,
                 temperature=1.0,
                 log_file=None,
                 debug=False):
        super().__init__(client=client, tokenizer=tokenizer, llm=llm, temperature=temperature,
                         log_file=log_file, debug=debug)
        self.client = client
        self.llm = llm
        self.rate_limit = 6
        self.temperature = temperature
        self.debug = debug  # 控制是否显示调试信息

    def act(self, observation):
        prompt=self.format_observation(observation)
        phase = observation['phase'] 
        valid_action = list(self.nlp_action_to_env_action.keys()) 
        time.sleep(self.rate_limit)
        if 'speech' in phase:
            # 发言阶段 - 只显示操作界面，不重复显示游戏状态
            print(f"\n{ConsoleUI.COLORS['speech']}{'═' * 70}{Style.RESET_ALL}")
            print(f"{ConsoleUI.ICONS['speech']} {ConsoleUI.COLORS['speech']}你的发言回合{Style.RESET_ALL}")
            print(f"{ConsoleUI.COLORS['speech']}{'═' * 70}{Style.RESET_ALL}")

            # 提示信息
            ConsoleUI.print_tips([
                "你可以分享查验信息（金水/查杀）",
                "可以表明身份或质疑他人悍跳",
                "可以分析局势进行站边",
                "可以归票推出狼人"
            ])

            raw_action = ConsoleUI.print_input_prompt("请输入你的发言内容")
            env_action = ('speech', raw_action)
            ConsoleUI.print_success(f'你的发言已记录："{raw_action}"')
        
            if self.has_log:
                self.logger.info(phase,
                                 extra={"prompt": prompt,
                                        "response": raw_action,
                                        "action": raw_action,
                                        "player_id": observation['current_act_idx'],
                                        "role": observation['identity'],
                                        "phase": phase,
                                        "gen_times": 0})
        else:
            # 动作阶段 - 只显示操作界面，不重复显示游戏状态
            phase_icon = '🌙' if 'night' in phase else '☀️' if 'day' in phase else '🎮'
            phase_color = ConsoleUI.COLORS['night'] if 'night' in phase else ConsoleUI.COLORS['vote']

            print(f"\n{phase_color}{'═' * 70}{Style.RESET_ALL}")
            print(f"{phase_icon} {phase_color}你的行动回合{Style.RESET_ALL}")
            print(f"{phase_color}{'═' * 70}{Style.RESET_ALL}")

            # 打印可选动作
            ConsoleUI.print_action_list(valid_action, title="可选动作")

            # 根据阶段给出提示
            tips = []
            if 'wolf' in phase:
                tips = ["选择合适的猎杀目标", "注意躲避预言家查验", "可考虑自刀制造银水"]
            elif 'vote' in phase:
                tips = ["分析发言内容站边", "注意归票避免平票", "重点关注悍跳和查杀"]
            elif 'seer' in phase:
                tips = ["查验可疑玩家获取金水/查杀", "注意保护自己身份"]
            elif 'witch' in phase:
                tips = ["判断是否使用解药救人", "毒药用于确认的狼人", "注意狼人可能自刀"]
            elif 'guard' in phase:
                tips = ["守护重要神职", "注意不能连续守护同一人"]

            if tips:
                ConsoleUI.print_tips(tips)

            user_input = ConsoleUI.print_input_prompt(
                f'请输入动作编号 (0-{len(valid_action)-1}) 或完整动作字符串'
            )

            # 支持输入索引或完整字符串
            try:
                action_idx = int(user_input)
                if 0 <= action_idx < len(valid_action):
                    raw_action = valid_action[action_idx]
                    action = raw_action
                else:
                    ConsoleUI.print_error(f'索引超出范围，请输入 0-{len(valid_action)-1}')
                    raw_action = valid_action[0]
                    action = raw_action
            except ValueError:
                # 用户输入的是完整字符串
                if user_input in valid_action:
                    raw_action = user_input
                    action = raw_action
                else:
                    ConsoleUI.print_error('输入无效，自动选择第一个动作')
                    raw_action = valid_action[0]
                    action = raw_action

            env_action = self.nlp_action_to_env_action[action]
            ConsoleUI.print_success(f'你选择的动作是: {action}')
            if self.has_log:
                self.logger.info(phase,
                                 extra={"prompt": prompt,
                                        "response": raw_action,
                                        "action": action,
                                        "player_id": observation['current_act_idx'],
                                        "role": observation['identity'],
                                        "phase": phase,
                                        "gen_times": 0})
        return env_action
