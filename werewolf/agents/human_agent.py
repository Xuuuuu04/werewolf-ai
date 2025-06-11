import time
from werewolf.agents.llm_agent import LLMAgent
from werewolf.agents.prompt_template_v0 import CON
from . import agent_registry as AgentRegistry

@AgentRegistry.register(["Human"])
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
            raw_action = input("{}\n请输入你的发言内容：".format(prompt))
            env_action = ('speech', raw_action)
        
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
            raw_action = input('{}\n{}\n请输入你要采取的动作：'.format(prompt, valid_action))
            assert raw_action in valid_action
            action = raw_action
            env_action = self.nlp_action_to_env_action[action]
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
