"""通用工具函数。

历史上下面的工具类/函数曾被外部脚本使用，但模块顶层实例化
OpenAI 客户端 + GPU 探测属于不必要的导入副作用，已移除。
需要 client 时请走 `werewolf.registry.Registry.build`。
"""
import re
import os

# 兼容历史 import：tokenizer encoding 由调用方按需创建
tiktoken_encoding = None


def _lazy_tiktoken():
    """按需加载 tiktoken 编码，避免模块顶层强依赖。"""
    global tiktoken_encoding
    if tiktoken_encoding is None:
        import tiktoken
        tiktoken_encoding = tiktoken.encoding_for_model("gpt-4-32k-0613")
    return tiktoken_encoding


MAX_ERROR = 3


# 英文角色 -> 中文角色（修复：Hunter 应为「猎人」而非「村民」）
role_en2cn = {
    "Werewolf": "狼人",
    "Villager": "普通村民",
    "Seer": "预言家",
    "Guard": "守卫",
    "Witch": "女巫",
    "Hunter": "猎人",
}

# 中文角色 -> 英文角色
role_cn2en = {
    "狼人": "Werewolf",
    "村民": "Villager",
    "普通村民": "Villager",
    "预言家": "Seer",
    "守卫": "Guard",
    "女巫": "Witch",
    "猎人": "Hunter",
}


def get_gpu_memory_map():
    """查询 GPU 显存占用。仅在 CUDA 环境下可用。"""
    import subprocess
    result = subprocess.check_output(
        [
            'nvidia-smi', '--query-gpu=memory.used,memory.total',
            '--format=csv,nounits,noheader'
        ], encoding='utf-8')
    gpu_memory = [x.split(',') for x in result.strip().split('\n')]
    gpu_memory_map = {
        i: {'used': int(memory_used), 'total': int(memory_total)}
        for i, (memory_used, memory_total) in enumerate(gpu_memory)
    }
    return gpu_memory_map


def get_available_devices(threshold=50000):
    """选择可用 GPU 设备；无 CUDA 时回退 CPU。"""
    try:
        import torch
    except ImportError:
        return "cpu"

    device = "auto"
    if torch.cuda.is_available():
        n_gpu = torch.cuda.device_count()
        if n_gpu == 1:
            device = "cuda:0"
        else:
            gpu_memory_map = get_gpu_memory_map()
            for i, gpu_status in gpu_memory_map.items():
                if gpu_status["used"] < threshold:
                    device = f"cuda:{i}"
                    break
    else:
        device = "cpu"
    return device


class Matcher:
    """正则匹配器，用于从早期 v3 prompt 输出中抽取笔记/投票等结构化字段。

    注意：v3 prompt 当前未被环境/agent 实际使用，保留以兼容旧实验日志分析脚本。
    """

    def __init__(self):
        self.summary_pattern = r"总结：\s*(.*?)(?=投票原因)"
        self.summary_pattern_v2 = r"总结：\s*(.*?)\n综上"
        self.detailed_summary_pattern = r'\*\*(.*?)\*\*：(.*?)(?=\*\*|#|$)'
        self.vote_pattern = r"投票原因：\s*(.*?)。\n基于上述"
        self.role_pred_pattern = r"基于上述分析，可以预测玩家身份为：\s*(.*?)\s*。\n综上"
        self.detail_role_pred_pattern = r"(\d+)号玩家是(.*?)。"
        self.role_pred_in_note_pattern = r"主观身份判断：\s*(.*?)\n"

        self.role_pattern = r"你是(\d+)号玩家。\n你的身份是：(.*?)。\n"
        self.day1_summary_pattern = r"第1天总结：\s*(.*?)第1天投票记录"
        self.day2_summary_pattern = r"第2天总结：\s*(.*?)第2天投票记录"
        self.my_vote_pattern = r"# 我的投票：\s*(.*?);"
        self.last_night_happened_pattern = r"昨晚发生：\s*(.*?);"
        self.last_night_action_pattern = r"昨晚行动：\s*(.*?);"
        self.previous_speech_pattern = r'本轮在你之前的玩家发言：(.*?)请根据上述内容形成你本轮的发言。'

    def match_note(self, text, output_str=False):
        text = text.replace("#投票原因", "投票原因")
        summary_match = re.search(self.summary_pattern, text, re.DOTALL)
        can_return_dict = False
        if summary_match:
            summary = summary_match.group(1)
            can_return_dict = True
        else:
            can_return_dict = False
            summary_match_2 = re.search(self.summary_pattern_v2, text, re.DOTALL)
            if summary_match_2:
                summary = summary_match_2.group(1)
            else:
                summary = text
        if can_return_dict:
            matches = re.findall(self.detailed_summary_pattern, summary, re.DOTALL)
            summary_dict = {match[0]: match[1].strip() for match in matches}
            res = ""
            if output_str:
                for key, value in summary_dict.items():
                    res += f"{key}: {value}\n"
                return res
            return summary_dict
        else:
            assert output_str == True
            return summary

    def match_role_pred_in_note(self, text):
        match = re.search(self.role_pred_in_note_pattern, text + "\n", re.DOTALL)
        if match:
            role_prediction_text = match.group(1).strip()
        else:
            role_prediction_text = None
        return role_prediction_text

    def match_vote_reason(self, text):
        match = re.search(self.vote_pattern, text.replace("# 综上，", "综上，"), re.DOTALL)
        if match:
            vote_reason = match.group(1).strip()
        else:
            vote_reason = text
        return vote_reason.replace("根据上述观察，可以做出如下分析：", "")

    def match_role_prediction(self, text, output_str=False):
        match = re.search(self.role_pred_pattern, text, re.DOTALL)
        role_prediction_text = text
        if match:
            role_prediction_text = match.group(1).strip()

        if output_str:
            return role_prediction_text

        matches = re.findall(self.detail_role_pred_pattern, role_prediction_text)
        pred_player_roles = {int(num): role for num, role in matches}
        return pred_player_roles

    def extract_info_from_prompt(self, prompt, return_str=False):
        short_prompt_info = ""
        day1_summary_match = re.search(self.day1_summary_pattern, prompt, re.DOTALL)
        day2_summary_match = re.search(self.day2_summary_pattern, prompt, re.DOTALL)
        my_vote_match = re.search(self.my_vote_pattern, prompt, re.DOTALL)
        last_night_happened_match = re.search(self.last_night_happened_pattern, prompt, re.DOTALL)
        last_night_action_match = re.search(self.last_night_action_pattern, prompt, re.DOTALL)
        previous_speech = re.search(self.previous_speech_pattern, prompt, re.DOTALL)

        if day1_summary_match:
            short_prompt_info += f"第1天总结：{day1_summary_match.group(1)}\n"
        if day2_summary_match:
            short_prompt_info += f"第2天总结：{day2_summary_match.group(1)}\n"
        if my_vote_match:
            short_prompt_info += f"我的投票：{my_vote_match.group(1)}\n"
        if last_night_happened_match:
            short_prompt_info += f"昨晚发生：{last_night_happened_match.group(1)}\n"
        if last_night_action_match:
            short_prompt_info += f"昨晚行动：{last_night_action_match.group(1)}\n"
        if previous_speech:
            short_prompt_info += f"前置位发言：\n{previous_speech.group(1)}\n"

        return short_prompt_info
