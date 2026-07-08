"""环境胜负判定规则单元测试。

覆盖「屠边规则」：
- 狼全死 → 村胜
- 神职全死 → 狼胜（屠神）
- 平民全死 → 狼胜（屠民）
- 仍未结束
"""
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


def test_village_wins_when_all_wolves_dead(env_9p):
    # 狼全死，所有好人存活
    env_9p.alive = [0., 0., 0., 1., 1., 1., 1., 1., 1.]
    _, done, info = env_9p.is_done()
    assert done is True
    assert info['Werewolf'] == -1


def test_wolf_wins_when_all_gods_dead(env_9p):
    # 3狼 + 3村民存活，3神全死 → 屠神
    env_9p.alive = [1., 1., 1., 0., 0., 0., 1., 1., 1.]
    _, done, info = env_9p.is_done()
    assert done is True
    assert info['Werewolf'] == 1


def test_wolf_wins_when_all_villagers_dead(env_9p):
    # 3狼 + 3神存活，3村民全死 → 屠民
    env_9p.alive = [1., 1., 1., 1., 1., 1., 0., 0., 0.]
    _, done, info = env_9p.is_done()
    assert done is True
    assert info['Werewolf'] == 1


def test_game_continues_when_no_side_satisfied(env_9p):
    # 3狼 + 2神 + 2村民存活
    env_9p.alive = [1., 1., 1., 1., 1., 0., 1., 1., 0.]
    _, done, info = env_9p.is_done()
    assert done is False
    assert info == {}


def test_parity_rule_removed(env_9p):
    # 旧「屠城规则」在狼数=好人数时判狼胜；屠边规则下此时不应结束
    # 3狼 + 2村民 + 1神存活（狼数=3，好人数=3）
    env_9p.alive = [1., 1., 1., 1., 0., 0., 1., 0., 1.]
    _, done, info = env_9p.is_done()
    assert done is False, ('屠边规则不应在 parity 时结束', info)
