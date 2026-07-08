"""RandomAgent 完整对局集成测试。

RandomAgent 是 base_agent.py 中的内置 agent，不经 LLM 即可决策，
适合作为环境的最小可运行集成验证。
"""
import random

import pytest

from werewolf.agents.base_agent import RandomAgent, Agent
from werewolf.envs.werewolf_text_env_v0 import WerewolfTextEnvV0


def test_random_agent_is_agent_subclass():
    assert issubclass(RandomAgent, Agent)


def test_random_agent_speech_returns_tuple():
    agent = RandomAgent()
    obs = {'phase': 'speech', 'valid_action': []}
    action = agent.act(obs)
    assert isinstance(action, tuple)
    assert action[0] == 'speech'


def test_random_agent_skill_picks_from_valid():
    agent = RandomAgent()
    valid = [('kill', 1), ('kill', 2), ('kill', -1)]
    obs = {'phase': 'skill_wolf', 'valid_action': valid}
    random.seed(0)
    action = agent.act(obs)
    assert action in valid


def test_random_agent_full_game_completes():
    """用 9 个 RandomAgent 跑完整对局，应在有限步内结束。"""
    random.seed(42)
    env = WerewolfTextEnvV0(
        n_player=9, n_role=5,
        n_werewolf=3, n_seer=1, n_guard=1, n_witch=1, n_villager=3, n_hunter=0,
    )
    roles = ['Werewolf'] * 3 + ['Seer', 'Witch', 'Guard'] + ['Villager'] * 3
    env.reset(roles=roles)

    agents = [RandomAgent() for _ in range(9)]
    for a in agents:
        a.reset()

    obs = env.get_observation()
    for step in range(200):
        idx = obs['current_act_idx']
        action = agents[idx - 1].act(obs)
        obs, reward, done, info = env.step(action)
        if done:
            break
    else:
        pytest.fail("RandomAgent 对局未在 200 步内结束")

    assert done
    assert info['Werewolf'] in (1, -1)
    # reward 应是非零向量（胜负已分配）
    assert any(r != 0 for r in reward)


def test_random_agent_resets_cleanly():
    """RandomAgent.reset 应可重复调用不报错。"""
    agent = RandomAgent()
    agent.reset()
    agent.reset()
    assert True
