"""环境 reset / step 基础流程测试。"""
import pytest

from werewolf.envs.werewolf_text_env_v0 import WerewolfTextEnvV0


@pytest.fixture
def env_9p():
    env = WerewolfTextEnvV0(
        n_player=9, n_role=5,
        n_werewolf=3, n_seer=1, n_guard=1, n_witch=1, n_villager=3, n_hunter=0,
    )
    roles = ['Werewolf'] * 3 + ['Seer', 'Witch', 'Guard'] + ['Villager'] * 3
    env.reset(roles=roles)
    return env


def test_reset_returns_initial_observation(env_9p):
    roles = ['Werewolf'] * 3 + ['Seer', 'Witch', 'Guard'] + ['Villager'] * 3
    obs = env_9p.reset(roles=roles)
    assert 'current_act_idx' in obs
    assert 'phase' in obs
    assert 'identity' in obs
    assert 'valid_action' in obs
    assert 'game_log' in obs


def test_phase_starts_with_wolf_skill(env_9p):
    """reset 后应从第0天夜晚狼人技能阶段开始。"""
    obs = env_9p.get_observation()
    assert 'wolf' in obs['phase']


def test_phase_progression_to_seer(env_9p):
    """3 个狼人都刀完后应进入预言家阶段。"""
    target = next(i for i, r in enumerate(env_9p.roles) if r != 'Werewolf' and env_9p.alive[i])
    # env.step 期望 agent 视角的 1-based target，内部转 0-based
    for _ in env_9p.WOLF_IDX:
        if env_9p.alive[env_9p.current_act_idx]:
            env_9p.step(('kill', target + 1))
        else:
            break
        if 'seer' in env_9p.phase:
            break
    assert 'seer' in env_9p.phase


def test_player_idx_is_0based_in_internal_log(env_9p):
    """日志内部 source/target 用 0-based；agent 传入的 action_content 是 1-based。"""
    wolf_idx = next(i for i, r in enumerate(env_9p.roles) if r == 'Werewolf' and env_9p.alive[i])
    target = next(i for i, r in enumerate(env_9p.roles) if r != 'Werewolf' and env_9p.alive[i])
    env_9p.step(('kill', target + 1))   # 1-based 传入
    skill_logs = [l for l in env_9p.game_log if l.event == 'skill_wolf']
    assert skill_logs, "应有 skill_wolf 事件"
    log = skill_logs[-1]
    assert log.source == wolf_idx       # 0-based 内部
    assert log.target == target         # 0-based 内部
