import time
from werewolf.agents.llm_agent import LLMAgent
from werewolf.agents.prompt_template_v0 import CON
from . import agent_registry as AgentRegistry

@AgentRegistry.register(["Human", "human"])
class HumanAgent(LLMAgent):
    def __init__(self,
                 client,
                 tokenizer=None,
                 llm=None,
                 temperature=1.0,
                 log_file=None):
        super().__init__(client=client, tokenizer=tokenizer, llm=llm, temperature=temperature, log_file=log_file)
        self.client = client
        self.llm = llm
        self.rate_limit = 6
        self.temperature = temperature

    def act(self, observation):
        prompt=self.format_observation(observation)
        phase = observation['phase'] 
        valid_action = list(self.nlp_action_to_env_action.keys()) 
        time.sleep(self.rate_limit)
        if 'speech' in phase:
            print('\n' + '='*60)
            print('💬 发言阶段')
            print(f'🎭 你的身份: {observation["identity"]}')
            print(f'👤 你是 {observation["current_act_idx"]} 号玩家')
            print('='*60)
            print(prompt)
            print('='*60)
            print('💡 提示：你可以分享信息、表明身份、分析局势或为其他玩家投票')
            raw_action = input("\n请输入你的发言内容：")
            env_action = ('speech', raw_action)
            print(f'\n✅ 你的发言已记录："{raw_action}"')
        
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
            # 显示游戏信息
            print('\n' + '='*60)
            print(f'🎮 当前阶段: {phase}')
            print(f'🎭 你的身份: {observation["identity"]}')
            print(f'👤 你是 {observation["current_act_idx"]} 号玩家')
            print('='*60)
            print(prompt)
            print('\n' + '='*60)
            print('📋 可选动作列表：')
            print('='*60)
            for idx, action_str in enumerate(valid_action):
                print(f"  [{idx}] {action_str}")
            print('='*60)
            
            user_input = input('\n请输入动作编号 (0-{}) 或完整动作字符串：'.format(len(valid_action)-1))
            
            # 支持输入索引或完整字符串
            try:
                action_idx = int(user_input)
                if 0 <= action_idx < len(valid_action):
                    raw_action = valid_action[action_idx]
                    action = raw_action
                else:
                    print(f'❌ 索引超出范围，请输入 0-{len(valid_action)-1}')
                    raw_action = valid_action[0]
                    action = raw_action
            except ValueError:
                # 用户输入的是完整字符串
                if user_input in valid_action:
                    raw_action = user_input
                    action = raw_action
                else:
                    print(f'❌ 输入无效，自动选择第一个动作')
                    raw_action = valid_action[0]
                    action = raw_action
            
            env_action = self.nlp_action_to_env_action[action]
            print(f'\n✅ 你选择的动作是: {action}')
            if self.has_log:
                self.logger.info(phase,
                                 extra={"prompt": prompt,
                                        "response": raw_action,
                                        "action": action,
                                        "player_id": observation['current_act_idx'],
                                        "role": observation['identity'],
                                        "phase": phase,
                                        "gen_times": 0})
        print("我是{}号，我的身份是{}, 当前阶段：{} raw_action {}".format(observation['current_act_idx'],
                                                                        observation['identity'],
                                                                        observation['phase'],
                                                                        env_action))
        return env_action
