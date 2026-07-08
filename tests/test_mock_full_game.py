"""端到端：用 mock LLM 跑一局完整 AI vs AI 对战，验证整个 pipeline 不崩溃。

mock 策略：
- skill 阶段：从 valid_action 中随机选一个合法动作
- speech 阶段：返回固定模板文本
- vote 阶段：从 valid_action 中随机选
"""
import random

import pytest

from werewolf.envs.werewolf_text_env_v0 import WerewolfTextEnvV0


class _MockResp:
    """模拟 OpenAI ChatCompletion 返回结构。"""
    class _Choice:
        class _Message:
            def __init__(self, content):
                self.content = content
        def __init__(self, content):
            self.message = _MockResp._Choice._Message(content)
    def __init__(self, content):
        self.choices = [_MockResp._Choice(content)]


class _MockClient:
    """不实际调用 OpenAI，按 phase 返回合法随机动作 / 模板发言。"""
    def __init__(self):
        self._rng = random.Random(42)

    @property
    def chat(self):
        outer = self

        class _Completions:
            @property
            def completions(self):
                class _Create:
                    def create(self_inner, model=None, messages=None, temperature=None, max_tokens=None):
                        # 不解析 prompt，由 _MockAgent 自己决定动作；
                        # 这里只在 GPTAgent.act 内部被调用，返回固定占位
                        text = outer._rng.choice([
                            "我认为应当重点关注。", "我注意到有可疑行为。",
                            "请大家理性分析。", "建议谨慎投票。",
                        ])
                        return _MockResp(text)
                return _Create()
        return _Completions()


class _MockAgent:
    """绕过 LLM，直接从 env 的 valid_action 随机选合法动作。

    等价于一个 RandomAgent，但能产出可读的 speech 文本。
    """
    def __init__(self, player_idx):
        self.player_idx = player_idx
        self._rng = random.Random(player_idx + 1)
        self.has_log = False
        self.debug = False

    def reset(self):
        pass

    def act(self, observation):
        phase = observation['phase']
        valid = observation.get('valid_action', [])
        if 'speech' in phase:
            return ('speech', f"玩家{self.player_idx + 1}在此发言。")
        if not valid:
            return ('pass', -1)
        # 优先选非弃票/非空动作
        meaningful = [a for a in valid if a[1] != -1]
        pool = meaningful if meaningful else valid
        return self._rng.choice(pool)


def _drive_full_game(env, agent_list, max_steps=200):
    """驱动整局游戏直到 done 或达到 step 上限。"""
    obs = env.get_observation()
    steps = 0
    while steps < max_steps:
        idx = obs['current_act_idx']
        agent = agent_list[idx - 1]   # current_act_idx 是 1-based
        action = agent.act(obs)
        obs, reward, done, info = env.step(action)
        steps += 1
        if done:
            return reward, done, info, steps
    return None, False, {}, max_steps


def test_full_game_completes_without_crash():
    """完整对局应在 200 步内结束，不抛异常，且 info['Werewolf'] 为 ±1。"""
    random.seed(0)
    env = WerewolfTextEnvV0(
        n_player=9, n_role=5,
        n_werewolf=3, n_seer=1, n_guard=1, n_witch=1, n_villager=3, n_hunter=0,
    )
    roles = ['Werewolf'] * 3 + ['Seer', 'Witch', 'Guard'] + ['Villager'] * 3
    env.reset(roles=roles)

    agent_list = [_MockAgent(i) for i in range(9)]
    reward, done, info, steps = _drive_full_game(env, agent_list, max_steps=200)

    assert done is True, f"游戏未在 {steps} 步内结束"
    assert 'Werewolf' in info, f"info 缺 Werewolf 字段: {info}"
    assert info['Werewolf'] in (1, -1), f"胜负判定异常: {info}"
    assert steps < 200, "可能在死循环"


def test_full_game_with_hunter_role():
    """带猎人的 9 人局也应能完整跑完。"""
    random.seed(7)
    env = WerewolfTextEnvV0(
        n_player=9, n_role=6,
        n_werewolf=3, n_seer=1, n_guard=1, n_witch=1, n_hunter=1, n_villager=2,
    )
    roles = ['Werewolf'] * 3 + ['Seer', 'Witch', 'Guard', 'Hunter'] + ['Villager'] * 2
    env.reset(roles=roles)

    agent_list = [_MockAgent(i) for i in range(9)]
    reward, done, info, steps = _drive_full_game(env, agent_list, max_steps=300)

    assert done is True, f"带猎人局未在 {steps} 步内结束"
    assert info['Werewolf'] in (1, -1)


def test_multiple_games_stability():
    """连续跑 5 局都应稳定结束，不抛异常。"""
    random.seed(123)
    for game_i in range(5):
        env = WerewolfTextEnvV0(
            n_player=9, n_role=5,
            n_werewolf=3, n_seer=1, n_guard=1, n_witch=1, n_villager=3, n_hunter=0,
        )
        roles = ['Werewolf'] * 3 + ['Seer', 'Witch', 'Guard'] + ['Villager'] * 3
        env.reset(roles=roles)

        agent_list = [_MockAgent(i) for i in range(9)]
        _, done, info, steps = _drive_full_game(env, agent_list, max_steps=200)
        assert done, f"第 {game_i} 局未结束 (steps={steps})"
        assert info['Werewolf'] in (1, -1), f"第 {game_i} 局胜负判定异常"
