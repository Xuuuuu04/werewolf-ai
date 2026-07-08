import time
import re
import random
from werewolf.agents.llm_agent import LLMAgent
from . import agent_registry as AgentRegistry


@AgentRegistry.register(["gpt", "gpt-4", "GPT-4", "gpt4", "o1", "gpt4o", "gpt4o-mini", "qwen", "qwen3", "Qwen3-Next-80B-A3B-Instruct", "qwen3-coder-plus"])
class GPTAgent(LLMAgent):
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
        prompt = self.format_observation(observation)
        phase = observation['phase']
        # 仅在 skill/vote 阶段才需要枚举可选动作；speech 阶段不使用
        valid_action = list(self.nlp_action_to_env_action.keys()) if 'speech' not in phase else []
        time.sleep(self.rate_limit)
        if 'speech' in phase:
            if self.llm is not None:
                messages = [{'role': 'user', 'content': prompt}]
                if "o1" in self.llm:
                    response = self.client.chat.completions.create(model=self.llm, messages=messages, max_tokens=32000)
                else:
                    response = self.client.chat.completions.create(
                        model=self.llm, messages=messages, temperature=self.temperature
                    )
                raw_action = response.choices[0].message.content.strip()
                checked_action = self.extract_answer(raw_action)
                gen_times = 0
            else:
                raw_action = "aaa"
                gen_times = -1
                checked_action = 'bbb'
            env_action = ('speech', checked_action)

            if self.has_log:
                self.logger.info(phase,
                                 extra={"prompt": prompt,
                                        "response": checked_action,
                                        "action": raw_action,
                                        "player_id": observation['current_act_idx'],
                                        "role": observation['identity'],
                                        "phase": phase,
                                        "gen_times": gen_times})
        else:
            retry_count = 0
            raw_action = None
            if self.llm is not None:
                action = ''
                while action not in valid_action:
                    retry_count += 1
                    if retry_count > 3:
                        raw_action = valid_action[random.randint(0, len(valid_action) - 1)]
                        break
                    messages = [{'role': 'user', 'content': prompt}]
                    if "o1" in self.llm:
                        response = self.client.chat.completions.create(model=self.llm, messages=messages,
                                                                       max_tokens=32000)
                    else:
                        response = self.client.chat.completions.create(
                            model=self.llm, messages=messages, temperature=self.temperature
                        )
                    if self.debug:
                        print(f"🔍 API响应类型: {type(response)}")
                        print(f"🔍 API响应内容: {response}")
                    if hasattr(response, 'choices'):
                        raw_action = response.choices[0].message.content.strip().strip("- ")
                    else:
                        raw_action = str(response).strip().strip("- ")
                    # 严格校验：无效则随机选一个合法动作，避免 LLM 输出异常导致卡死
                    if raw_action in valid_action:
                        action = raw_action
                    else:
                        action = valid_action[random.randint(0, len(valid_action) - 1)]
            else:
                action = valid_action[random.randint(0, len(valid_action) - 1)]
                if self.debug:
                    print("🎲 随机选择有效动作: {} | 可选动作: {}".format(action, valid_action))
            env_action = self.nlp_action_to_env_action[action]
            if raw_action is None:
                raw_action = action
            if self.has_log:
                self.logger.info(phase,
                                 extra={"prompt": prompt,
                                        "response": raw_action,
                                        "action": action,
                                        "player_id": observation['current_act_idx'],
                                        "role": observation['identity'],
                                        "phase": phase,
                                        "gen_times": max(retry_count - 1, 0)})
        return env_action

    def extract_answer(self, response):
        pattern = r'\n\n\"(.*?)\"'
        matches = re.findall(pattern, response, re.DOTALL)
        if matches:
            response = matches[0]
        return response