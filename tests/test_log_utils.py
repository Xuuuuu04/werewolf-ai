"""log_utils 共享格式化函数测试。"""
from werewolf.helper.log_utils import Log, format_log_entry, format_game_log


def test_format_skill_seer_bad():
    log = Log(viewer=[1], source=1, target=2,
              content={'查验结果': 'bad'}, day=1, time='第1天夜晚',
              event='skill_seer')
    out = format_log_entry(log)
    assert '狼人' in out
    assert '2号' in out


def test_format_skill_seer_good():
    log = Log(viewer=[1], source=1, target=3,
              content={'查验结果': 'good'}, day=1, time='第1天夜晚',
              event='skill_seer')
    out = format_log_entry(log)
    assert '好人' in out
    assert '3号' in out


def test_format_speech_with_content():
    log = Log(viewer=[1], source=4, target=-1,
              content={'发言内容': '我是预言家'}, day=1, time='第1天白天',
              event='speech')
    out = format_log_entry(log)
    assert '我是预言家' in out
    assert '4号' in out


def test_format_speech_empty():
    log = Log(viewer=[1], source=4, target=-1,
              content={'发言内容': ''}, day=1, time='第1天白天',
              event='speech')
    out = format_log_entry(log)
    assert '为空' in out


def test_format_vote_target():
    log = Log(viewer=[1], source=1, target=5,
              content={}, day=1, time='第1天白天', event='vote')
    assert '5号' in format_log_entry(log)


def test_format_vote_abstain():
    log = Log(viewer=[1], source=1, target=-1,
              content={}, day=1, time='第1天白天', event='vote')
    out = format_log_entry(log)
    assert '放弃投票' in out


def test_format_witch_heal():
    log = Log(viewer=[1], source=2, target=3,
              content={'解药目标': 3}, day=1, time='第1天夜晚',
              event='skill_witch')
    out = format_log_entry(log)
    assert '解药' in out
    assert '3号' in out


def test_format_witch_poison():
    log = Log(viewer=[1], source=2, target=4,
              content={'毒药目标': 4}, day=1, time='第1天夜晚',
              event='skill_witch')
    out = format_log_entry(log)
    assert '毒药' in out
    assert '4号' in out


def test_format_end_vote_player_out():
    log = Log(viewer=[1], source=-1, target=-1,
              content={'投票结果': 5, '被放逐玩家': 5},
              day=1, time='第1天白天', event='end_vote')
    out = format_log_entry(log)
    assert '5号' in out
    assert '驱逐' in out


def test_format_end_vote_tie():
    log = Log(viewer=[1], source=-1, target=-1,
              content={'投票结果': '平票', 'speech_queue': [3, 7], 'vote_queue': [1, 2, 4, 5, 6, 8, 9]},
              day=1, time='第1天白天', event='end_vote')
    out = format_log_entry(log)
    assert '平票' in out
    # 列表用顿号分隔、不含 "号" 后缀
    assert '3、7' in out
    assert '1、2、4' in out


def test_format_game_log_filters_internal_views():
    """god_view / self_identity 等内部事件不应出现在输出。"""
    logs = [
        Log(viewer=[1], source=1, target=-1, content={}, day=0, time='', event='god_view'),
        Log(viewer=[1], source=1, target=-1, content={'身份': 'Seer'}, day=0, time='', event='self_identity'),
        Log(viewer=[1], source=1, target=2, content={'查验结果': 'bad'},
            day=1, time='第1天夜晚', event='skill_seer'),
    ]
    out = format_game_log(logs)
    assert 'god_view' not in out
    assert 'self_identity' not in out
    assert '预言家' in out


def test_format_game_log_resilient_to_single_failure():
    """单条格式化失败不应影响整体。"""
    bad = Log(viewer=[1], source=None, target=None, content=None,
              day=1, time=None, event='unknown_event')
    good = Log(viewer=[1], source=1, target=2, content={'查验结果': 'bad'},
               day=1, time='第1天夜晚', event='skill_seer')
    out = format_game_log([bad, good])
    assert '预言家' in out  # good 仍应被格式化
