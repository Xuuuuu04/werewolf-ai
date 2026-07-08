#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
控制台界面美化工具
提供彩色输出、格式化显示等功能
"""

from colorama import init, Fore, Style
import os
import re

# 初始化colorama（Windows兼容）
init(autoreset=True)


class ConsoleUI:
    """控制台UI美化类"""
    
    # 颜色主题 - 每个玩家固定颜色
    PLAYER_COLORS = [
        Fore.RED,          # 玩家1 - 红色
        Fore.GREEN,        # 玩家2 - 绿色
        Fore.YELLOW,       # 玩家3 - 黄色
        Fore.BLUE,         # 玩家4 - 蓝色
        Fore.MAGENTA,      # 玩家5 - 洋红色
        Fore.CYAN,         # 玩家6 - 青色
        Fore.WHITE,        # 玩家7 - 白色
        Fore.LIGHTRED_EX,  # 玩家8 - 亮红色
        Fore.LIGHTGREEN_EX, # 玩家9 - 亮绿色
    ]

    # 角色颜色（用于身份显示）
    COLORS = {
        'Werewolf': Fore.RED,           # 狼人-红色
        'Seer': Fore.CYAN,               # 预言家-青色
        'Witch': Fore.MAGENTA,           # 女巫-洋红色
        'Guard': Fore.BLUE,              # 守卫-蓝色
        'Hunter': Fore.GREEN,            # 猎人-绿色
        'Villager': Fore.WHITE,          # 村民-白色

        # 阶段颜色
        'night': Fore.BLUE,              # 夜晚-蓝色
        'day': Fore.YELLOW,              # 白天-黄色
        'vote': Fore.CYAN,               # 投票-青色
        'speech': Fore.GREEN,            # 发言-绿色

        # 状态颜色
        'success': Fore.GREEN,           # 成功-绿色
        'warning': Fore.YELLOW,          # 警告-黄色
        'error': Fore.RED,               # 错误-红色
        'info': Fore.CYAN,               # 信息-青色
        'highlight': Fore.LIGHTYELLOW_EX, # 高亮-亮黄色
    }
    
    # 图标
    ICONS = {
        'night': '🌙',
        'day': '☀️',
        'wolf': '🐺',
        'seer': '🔮',
        'witch': '🧪',
        'guard': '🛡️',
        'hunter': '🔫',
        'villager': '👤',
        'death': '💀',
        'vote': '🗳️',
        'speech': '💬',
        'skill': '✨',
        'win': '🏆',
        'lose': '💔',
        'warning': '⚠️',
        'info': 'ℹ️',
        'question': '❓',
        'success': '✅',
        'error': '❌',
    }
    
    @classmethod
    def clear_screen(cls):
        """清屏"""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    @classmethod
    def print_header(cls, title, icon='', color=None):
        """打印标题头部"""
        if color is None:
            color = Fore.CYAN
        
        width = 70
        line = "=" * width
        
        print(f"\n{color}{line}{Style.RESET_ALL}")
        print(f"{color}{icon} {title.center(width-4)}{Style.RESET_ALL}")
        print(f"{color}{line}{Style.RESET_ALL}\n")
    
    @classmethod
    def print_section(cls, title, content='', color=None):
        """打印章节"""
        if color is None:
            color = Fore.WHITE
        
        print(f"{color}{'─' * 70}{Style.RESET_ALL}")
        print(f"{Fore.LIGHTYELLOW_EX}{title}{Style.RESET_ALL}")
        if content:
            print(f"{color}{content}{Style.RESET_ALL}")
        print(f"{color}{'─' * 70}{Style.RESET_ALL}\n")
    
    @classmethod
    def print_player_info(cls, player_num, identity, phase):
        """打印玩家信息"""
        identity_color = cls.COLORS.get(identity, Fore.WHITE)
        identity_icon = cls.ICONS.get(identity.lower(), '👤')
        
        phase_text = cls.get_phase_text(phase)
        phase_color = cls.COLORS.get('info', Fore.CYAN)
        
        print(f"{Fore.LIGHTCYAN_EX}{'─' * 70}{Style.RESET_ALL}")
        print(f"{Fore.LIGHTCYAN_EX}│{Style.RESET_ALL} {identity_icon} 玩家编号: {Fore.LIGHTYELLOW_EX}#{player_num}{Style.RESET_ALL}")
        print(f"{Fore.LIGHTCYAN_EX}│{Style.RESET_ALL} {cls.ICONS['info']} 你的身份: {identity_color}{identity}{Style.RESET_ALL}")
        print(f"{Fore.LIGHTCYAN_EX}│{Style.RESET_ALL} {cls.ICONS['skill']} 当前阶段: {phase_color}{phase_text}{Style.RESET_ALL}")
        print(f"{Fore.LIGHTCYAN_EX}{'─' * 70}{Style.RESET_ALL}\n")
    
    @classmethod
    def print_action_list(cls, actions, title="可选动作"):
        """打印动作列表"""
        print(f"\n{Fore.LIGHTCYAN_EX}{'═' * 70}{Style.RESET_ALL}")
        print(f"{Fore.LIGHTYELLOW_EX}📋 {title}{Style.RESET_ALL}")
        print(f"{Fore.LIGHTCYAN_EX}{'═' * 70}{Style.RESET_ALL}")
        
        for idx, action in enumerate(actions):
            # 根据动作类型使用不同颜色
            action_str = str(action)
            color = Fore.WHITE
            
            if '杀害' in action_str:
                color = Fore.RED
            elif '查验' in action_str:
                color = Fore.CYAN
            elif '守护' in action_str:
                color = Fore.BLUE
            elif '解药' in action_str or '毒药' in action_str:
                color = Fore.MAGENTA
            elif '投票' in action_str:
                color = Fore.YELLOW
            elif '否' in action_str:
                color = Fore.LIGHTBLACK_EX
            
            print(f"  {Fore.LIGHTCYAN_EX}[{idx}]{Style.RESET_ALL} {color}{action}{Style.RESET_ALL}")
        
        print(f"{Fore.LIGHTCYAN_EX}{'═' * 70}{Style.RESET_ALL}\n")
    
    @classmethod
    def print_game_log(cls, log_text, current_player_id=None):
        """打印游戏日志"""
        print(f"{Fore.LIGHTBLACK_EX}{'┄' * 70}{Style.RESET_ALL}")

        # 高亮特殊信息
        for line in log_text.split('\n'):
            if not line.strip():
                continue

            # 检查是否是玩家发言（格式：X号在第Y天白天发言内容：...）
            player_match = re.search(r'(\d+)号.*发言内容：', line)
            if player_match:
                player_id = int(player_match.group(1))
                player_color = cls.get_player_color(player_id)
                print(f"  {player_color}{line}{Style.RESET_ALL}")
            # 根据内容高亮
            elif any(keyword in line for keyword in ['死亡', '出局', '被杀']):
                print(f"{cls.ICONS['death']} {Fore.RED}{line}{Style.RESET_ALL}")
            elif any(keyword in line for keyword in ['预言家', '查验', '金水', '查杀']):
                print(f"{cls.ICONS['seer']} {Fore.CYAN}{line}{Style.RESET_ALL}")
            elif any(keyword in line for keyword in ['女巫', '解药', '毒药', '银水']):
                print(f"{cls.ICONS['witch']} {Fore.MAGENTA}{line}{Style.RESET_ALL}")
            elif any(keyword in line for keyword in ['守卫', '守护']):
                print(f"{cls.ICONS['guard']} {Fore.BLUE}{line}{Style.RESET_ALL}")
            elif any(keyword in line for keyword in ['狼人', '猎杀']):
                print(f"{cls.ICONS['wolf']} {Fore.RED}{line}{Style.RESET_ALL}")
            elif any(keyword in line for keyword in ['投票', '驱逐']):
                print(f"{cls.ICONS['vote']} {Fore.YELLOW}{line}{Style.RESET_ALL}")
            elif any(keyword in line for keyword in ['发言']):
                print(f"{cls.ICONS['speech']} {Fore.GREEN}{line}{Style.RESET_ALL}")
            else:
                print(f"  {Fore.WHITE}{line}{Style.RESET_ALL}")

        print(f"{Fore.LIGHTBLACK_EX}{'┄' * 70}{Style.RESET_ALL}\n")
    
    @classmethod
    def print_input_prompt(cls, prompt, color=None):
        """打印输入提示"""
        if color is None:
            color = Fore.LIGHTYELLOW_EX
        
        return input(f"{color}➤ {prompt}{Style.RESET_ALL}")
    
    @classmethod
    def print_success(cls, message):
        """打印成功消息"""
        print(f"{cls.ICONS['success']} {Fore.GREEN}{message}{Style.RESET_ALL}\n")
    
    @classmethod
    def print_error(cls, message):
        """打印错误消息"""
        print(f"{cls.ICONS['error']} {Fore.RED}{message}{Style.RESET_ALL}\n")
    
    @classmethod
    def print_warning(cls, message):
        """打印警告消息"""
        print(f"{cls.ICONS['warning']} {Fore.YELLOW}{message}{Style.RESET_ALL}\n")
    
    @classmethod
    def print_info(cls, message):
        """打印信息消息"""
        print(f"{cls.ICONS['info']} {Fore.CYAN}{message}{Style.RESET_ALL}\n")
    
    @classmethod
    def print_game_result(cls, winner, is_win=True):
        """打印游戏结果"""
        icon = cls.ICONS['win'] if is_win else cls.ICONS['lose']
        color = Fore.GREEN if is_win else Fore.RED
        
        print(f"\n{color}{'═' * 70}{Style.RESET_ALL}")
        print(f"{icon} {color}{winner.center(60)}{Style.RESET_ALL}")
        print(f"{color}{'═' * 70}{Style.RESET_ALL}\n")
    
    @classmethod
    def get_player_color(cls, player_id):
        """根据玩家编号获取固定颜色"""
        if 1 <= player_id <= len(cls.PLAYER_COLORS):
            return cls.PLAYER_COLORS[player_id - 1]
        return Fore.WHITE  # 默认白色

    @classmethod
    def get_phase_text(cls, phase):
        """获取阶段文本"""
        phase_map = {
            'night': '🌙 夜晚',
            'skill_wolf': '🐺 狼人行动',
            'skill_seer': '🔮 预言家查验',
            'skill_guard': '🛡️ 守卫守护',
            'skill_witch': '🧪 女巫行动',
            'day': '☀️ 白天',
            'speech': '💬 发言阶段',
            'vote': '🗳️ 投票阶段',
        }

        for key, value in phase_map.items():
            if key in phase:
                return value

        return phase
    
    @classmethod
    def print_tips(cls, tips_list):
        """打印提示信息"""
        print(f"{Fore.LIGHTBLACK_EX}{'┄' * 70}{Style.RESET_ALL}")
        print(f"{cls.ICONS['info']} {Fore.CYAN}💡 游戏提示{Style.RESET_ALL}")
        for tip in tips_list:
            print(f"  {Fore.LIGHTBLACK_EX}•{Style.RESET_ALL} {Fore.WHITE}{tip}{Style.RESET_ALL}")
        print(f"{Fore.LIGHTBLACK_EX}{'┄' * 70}{Style.RESET_ALL}\n")


# 快捷函数
def print_colored(text, color=Fore.WHITE):
    """打印彩色文本"""
    print(f"{color}{text}{Style.RESET_ALL}")


def print_role(identity):
    """打印角色信息"""
    icon = ConsoleUI.ICONS.get(identity.lower(), '👤')
    color = ConsoleUI.COLORS.get(identity, Fore.WHITE)
    return f"{icon} {color}{identity}{Style.RESET_ALL}"

