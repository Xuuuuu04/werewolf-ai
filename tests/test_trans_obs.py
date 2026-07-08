"""trans_obs_env_to_agt 副作用回归测试。

历史 bug：旧实现直接 mutate 传入的 game_log，导致：
- env.get_observation() 多次调用后，self.game_log 中编号被多次 +1
- 写盘日志 self.game_log 被 mutate 后，后续读取得到 1-based 而非 0-based
"""
import json
import os

import pytest

from werewolf.envs.werewolf_text_env_v0 import WerewolfTextEnvV0
from werewolf.helper.log_utils import Log


@pytest.fixture
def env_9p():
    env = WerewolfTextEnvV0(
        n_player=9, n_role=5,
        n_werewolf=3, n_seer=1, n_guard=1, n_witch=1, n_villager=3, n_hunter=0,
    )
    roles = ['Werewolf'] * 3 + ['Seer', 'Witch', 'Guard'] + ['Villager'] * 3
    env.reset(roles=roles)
    return env


def test_trans_does_not_mutate_input(env_9p):
    """转换函数不应修改入参 log 对象的任何字段。"""
    original_log = Log(viewer=[0], source=1, target=2,
                       content={'查验结果': 'bad'}, day=1, time='第1天夜晚',
                       event='skill_seer')
    snapshot_src = original_log.source
    snapshot_tgt = original_log.target
    snapshot_viewer = list(original_log.viewer)

    _ = env_9p.trans_obs_env_to_agt([original_log])

    assert original_log.source == snapshot_src, "source 被 mutate"
    assert original_log.target == snapshot_tgt, "target 被 mutate"
    assert original_log.viewer == snapshot_viewer, "viewer 被 mutate"


def test_trans_returns_1based_values(env_9p):
    """转换后应是 1-based。"""
    log = Log(viewer=[0], source=1, target=2,
              content={'查验结果': 'bad'}, day=1, time='第1天夜晚',
              event='skill_seer')
    result = env_9p.trans_obs_env_to_agt([log])
    new_log = result[0]
    assert new_log.source == 2   # 0-based 1 -> 1-based 2
    assert new_log.target == 3   # 0-based 2 -> 1-based 3
    assert new_log.viewer == [1]


def test_trans_skips_game_setting_and_end_game(env_9p):
    """game_setting / end_game 的 content 不应被 +1。"""
    setting_log = Log(viewer=[0], source=-1, target=-1,
                      content={'Werewolf': 3, 'Seer': 1}, day=0, time='',
                      event='game_setting')
    end_log = Log(viewer=[0], source=-1, target=-1,
                  content={'游戏结果': '狼人获胜'}, day=3, time='',
                  event='end_game')
    result = env_9p.trans_obs_env_to_agt([setting_log, end_log])
    assert result[0].content == {'Werewolf': 3, 'Seer': 1}
    assert result[1].content == {'游戏结果': '狼人获胜'}


def test_trans_handles_list_content(env_9p):
    """content 中的 list 应逐项 +1。"""
    log = Log(viewer=[0], source=1, target=-1,
              content={'死亡名单': [0, 2, 4]}, day=1, time='第1天夜晚',
              event='end_night')
    result = env_9p.trans_obs_env_to_agt([log])
    assert result[0].content['死亡名单'] == [1, 3, 5]


def test_repeated_trans_idempotent_on_internal_state(env_9p):
    """多次调用 trans 不应使 self.game_log 中的编号累积偏移。"""
    wolf_idx = next(i for i, r in enumerate(env_9p.roles) if r == 'Werewolf' and env_9p.alive[i])
    target = next(i for i, r in enumerate(env_9p.roles) if r != 'Werewolf' and env_9p.alive[i])
    env_9p.step(('kill', target + 1))

    # 抓取转换前 self.game_log 最后一条 skill_wolf 的 source（0-based）
    internal_logs = [l for l in env_9p.game_log if l.event == 'skill_wolf']
    original_source = internal_logs[-1].source

    # 调用两次转换
    _ = env_9p.trans_obs_env_to_agt(env_9p.game_log)
    _ = env_9p.trans_obs_env_to_agt(env_9p.game_log)

    # 再次读取内部状态，应未被 mutate
    internal_logs2 = [l for l in env_9p.game_log if l.event == 'skill_wolf']
    assert internal_logs2[-1].source == original_source, \
        "内部 game_log 被转换函数 mutate，编号已累积偏移"


def test_written_game_log_is_1based(env_9p, tmp_path):
    """写盘的 game_log.json 应是 1-based。"""
    env_9p.log_save_path = str(tmp_path)
    # 跑到游戏结束：让所有狼人刀村民，加速结束
    # 简单做法：直接把存活状态设到「狼胜」边界再 step 触发 end_game
    # 但 end_game 需要 step 流程触发；这里用 mock agent 跑完
    import random as _r
    _r.seed(0)
    from tests.test_mock_full_game import _MockAgent, _drive_full_game
    agents = [_MockAgent(i) for i in range(9)]
    _drive_full_game(env_9p, agents, max_steps=200)

    log_file = os.path.join(str(tmp_path), 'game_log.json')
    assert os.path.exists(log_file), "game_log.json 未生成"
    with open(log_file, 'r', encoding='utf-8') as f:
        written = json.load(f)

    # 找到 skill_wolf 事件，验证 source/target 是 1-based
    # source 必为真实玩家 (>=1)；target 可能为 0（弃刀：0-based -1 → 1-based 0）
    skill_wolfs = [e for e in written if e.get('event') == 'skill_wolf']
    assert skill_wolfs, "写盘日志中无 skill_wolf 事件"
    for e in skill_wolfs:
        assert e['source'] >= 1, f"写盘日志 source 非 1-based: {e['source']}"
        assert e['target'] >= 0, f"写盘日志 target 异常: {e['target']}"
