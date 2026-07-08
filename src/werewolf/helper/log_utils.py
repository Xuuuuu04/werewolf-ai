import logging
import json


class Log():
    def __init__(self, viewer, source, target, content, day, time, event):
        self.viewer = viewer
        self.source = source
        self.target = target
        self.content = content
        self.day = day
        self.time = time
        self.event = event


class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_record = record.__dict__.copy()
        non_custom_fields = [
            'name', 'msg', 'args', 'levelname', 'levelno',
            'pathname', 'filename', 'module', 'exc_info',
            'exc_text', 'stack_info', 'lineno', 'funcName',
            'created', 'msecs', 'relativeCreated', 'thread',
            'threadName', 'processName', 'process', 'message',
        ]
        for field in non_custom_fields:
            if field in log_record:
                del log_record[field]

        log_record['message'] = record.getMessage()
        return json.dumps(log_record, ensure_ascii=False)


class CustomLoggerAdapter(logging.LoggerAdapter):
    def process(self, msg, kwargs):
        if 'extra' not in kwargs:
            kwargs['extra'] = {}
        kwargs['extra'].update(self.extra)
        return msg, kwargs


# 角色中文名映射，供日志格式化使用
_ROLE_CN = {
    "Werewolf": "狼人",
    "Seer": "预言家",
    "Witch": "女巫",
    "Guard": "守卫",
    "Hunter": "猎人",
    "Villager": "村民",
}


def format_log_entry(log) -> str:
    """把单条 Log 对象格式化为人类可读的中文文本。

    这是 run_battle.py 的 `format_game_log` 与 llm_agent.py 的
    `format_log` 共享的单一来源，避免两份中文文案分叉。

    日志字段说明：
    - log.event: 见 WerewolfTextEnvV0 中各 append 的 event 名
    - log.source/log.target: 已是 1-based 玩家编号
    - log.content: 含中文 key 的字典
    """
    event = log.event
    content = getattr(log, 'content', {}) or {}
    src = log.source
    tgt = log.target
    day = log.day
    time = log.time

    if event == 'game_setting':
        text = '本局游戏各个身份和对应数量如下：\n'
        for key, value in content.items():
            text += "- {}:{}\n".format(_ROLE_CN.get(key, key), value)
        return text

    if event == 'werewolf_team_info':
        wolf_team = '、'.join(str(i) for i in content.get('wolf_team', []))
        return "狼人队伍的成员是{}。\n".format(wolf_team)

    if event == 'god_view':
        # 内部视图，对外不应展示
        return ""

    if event == 'self_identity':
        return ""

    if event == 'skill_wolf':
        return "{}号是狼人，他在{}准备猎杀{}号。\n".format(src, time, tgt)

    if event == 'kill_decision':
        return "狼人队伍在{}猎杀了{}号。\n".format(time, tgt)

    if event == 'skill_seer':
        checked = content.get('查验结果')
        verdict = '狼人' if checked == 'bad' else '好人'
        return "{}号是预言家，你在{}查验了{}号的身份是{}。\n".format(src, time, tgt, verdict)

    if event == 'skill_guard':
        return "{}号是守卫，你在{}守护了{}号。\n".format(src, time, tgt)

    if event == 'skill_witch':
        if '解药目标' in content:
            return "{}号是女巫，你在{}使用解药治疗了{}号。\n".format(src, time, tgt)
        if '毒药目标' in content:
            return "{}号是女巫，你在{}使用毒药毒害了{}号。\n".format(src, time, tgt)
        return "{}号是女巫，你在{}放弃行动。\n".format(src, time)

    if event == 'skill_hunter':
        return "{}号是猎人，他在{}射杀了{}号。\n".format(src, time, tgt)

    if event in ('speech', 'speech_pk'):
        text = content.get('发言内容', '')
        if text:
            return "{}号在{}发言内容：{}。\n".format(src, time, text)
        return "{}号在{}发言内容为空。\n".format(src, time)

    if event == 'vote':
        if tgt and tgt > 0:
            return "{}号在{}投票给{}号。\n".format(src, time, tgt)
        return "{}号在{}放弃投票。\n".format(src, time)

    if event == 'vote_pk':
        if tgt and tgt > 0:
            return "{}号在{}pk环节投票给{}号。\n".format(src, time, tgt)
        return "{}号在{}pk环节放弃投票。\n".format(src, time)

    if event == 'end_game':
        return "游戏结束！\n"

    if event == 'end_night':
        dead_list = content.get('死亡名单', [])
        if dead_list:
            dead_str = '、'.join(str(i) for i in dead_list)
            return "{}死亡的玩家是{}。\n".format(time, dead_str)
        return "{}无人死亡。\n".format(time)

    if event == 'end_vote':
        result = content.get('投票结果')
        if result == '全员弃票':
            return "{}所有玩家放弃投票，直接进入夜晚。\n".format(time)
        if result == 'PK阶段全员弃票':
            return "{}再次发言，所有玩家放弃投票，直接进入夜晚。\n".format(time)
        if result == '平票':
            pk_speech = '、'.join(str(i) for i in content.get('speech_queue', []))
            pk_vote = '、'.join(str(i) for i in content.get('vote_queue', []))
            return "{}平票，由{}再次发言，{}进行投票。\n".format(time, pk_speech, pk_vote)
        if result == 'PK阶段平票':
            return "{}再次平票，直接进入夜晚。\n".format(time)
        if isinstance(result, int):
            expelled = content.get('被放逐玩家', result)
            return "{}通过投票驱逐了{}号。\n".format(time, expelled)
        return ""

    return ""


def format_game_log(game_log) -> str:
    """把多条 Log 格式化为单个字符串，过滤掉内部视图事件。"""
    pieces = []
    for log in game_log:
        try:
            text = format_log_entry(log)
        except Exception as e:  # 单条失败不影响整体
            text = "[log format error: {}]\n".format(e)
        if text:
            pieces.append(text)
    return ''.join(pieces)


