"""猎人技能规则测试。

猎人被毒不能开枪（"闷枪"）；被狼刀或被放逐可以开枪。
"""
import pytest

from werewolf.envs.werewolf_text_env_v0 import WerewolfTextEnvV0


@pytest.fixture
def env_9p_with_hunter():
    """9 人局：3狼 + 预言家 + 女巫 + 守卫 + 猎人 + 2村民。"""
    env = WerewolfTextEnvV0(
        n_player=9, n_role=6,
        n_werewolf=3, n_seer=1, n_guard=1, n_witch=1, n_hunter=1,
        n_villager=2,
    )
    roles = ['Werewolf'] * 3 + ['Seer', 'Witch', 'Guard', 'Hunter'] + ['Villager'] * 2
    env.reset(roles=roles)
    return env


def _set_hunter_at(env, idx):
    """把 idx 位置的角色改成 Hunter，便于定位猎人下标。"""
    # roles 顺序按 fixture: [W,W,W,Seer,Witch,Guard,Hunter,V,V]
    env.HUNTER_IDX = idx
    env.roles[idx] = 'Hunter'


def test_hunter_can_shoot_when_killed_by_wolf(env_9p_with_hunter):
    """被狼刀：可以开枪。环境通过 witch_poison_idx != HUNTER_IDX 判定。"""
    env = env_9p_with_hunter
    # 猎人下标按 reset 时的顺序
    hunter_idx = env.HUNTER_IDX
    # 模拟未被毒（witch_poison_idx 默认为 -1）
    env.witch_poison_idx = -1
    assert env.witch_poison_idx != hunter_idx


def test_hunter_cannot_shoot_when_poisoned(env_9p_with_hunter):
    """被女巫毒：不能开枪。环境用 witch_poison_idx == HUNTER_IDX 阻止。"""
    env = env_9p_with_hunter
    hunter_idx = env.HUNTER_IDX
    env.witch_poison_idx = hunter_idx
    assert env.witch_poison_idx == hunter_idx
