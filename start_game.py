#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
狼人杀游戏启动器
提供交互式命令行界面来选择游戏模式和配置
"""

import os
import sys
import subprocess
from pathlib import Path


def print_banner():
    """打印游戏标题"""
    banner = """
    ╔═══════════════════════════════════════════════════════════╗
    ║                                                           ║
    ║        🐺  狼 人 杀 游 戏 启 动 器  🎭                    ║
    ║                                                           ║
    ║              MaKTO Werewolf Game Launcher                 ║
    ║                                                           ║
    ╚═══════════════════════════════════════════════════════════╝
    """
    print(banner)


def print_menu():
    """打印主菜单"""
    menu = """
    ┌───────────────────────────────────────────────────────────┐
    │                     请选择游戏模式                         │
    ├───────────────────────────────────────────────────────────┤
    │                                                           │
    │  1. 🤖 AI vs AI (Qwen)  - Qwen模型自我对战               │
    │  2. 🤖 Qwen vs GPT      - Qwen对战GPT模型                │
    │  3. 👤 人类单玩家模式    - 你控制1个角色，其他AI控制      │
    │  4. 👥 人类阵营模式      - 你控制整个阵营                │
    │                                                           │
    │  8. 📊 查看游戏日志     - 可视化游戏记录                  │
    │  0. 🚪 退出            - 退出游戏启动器                   │
    │                                                           │
    └───────────────────────────────────────────────────────────┘
    """
    print(menu)


def apply_debug_config(config_path, debug_mode):
    """应用debug配置到配置文件"""
    try:
        import yaml

        # 读取配置文件
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        # 更新所有agent的debug设置
        if 'agent_config' in config:
            for group_name, group_config in config['agent_config'].items():
                if 'model_params' in group_config:
                    config['agent_config'][group_name]['model_params']['debug'] = debug_mode

        # 更新human_player模式下的AI配置
        if 'human_player' in config and config['human_player'].get('enabled', False):
            if 'agent_config' in config and 'ai_model' in config['agent_config']:
                if 'model_params' in config['agent_config']['ai_model']:
                    config['agent_config']['ai_model']['model_params']['debug'] = debug_mode

        # 写回配置文件
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True)

        if debug_mode:
            print(f"\n{Fore.YELLOW}✅ 已启用调试模式，将显示API响应等详细信息{Style.RESET_ALL}")
        else:
            print(f"\n{Fore.GREEN}✅ 已隐藏调试信息，界面更加清爽{Style.RESET_ALL}")

    except Exception as e:
        print(f"\n{Fore.RED}❌ 应用debug配置失败: {e}{Style.RESET_ALL}")


def configure_debug_mode():
    """配置调试模式"""
    print(f"\n{Fore.CYAN}🔧 调试模式配置{Style.RESET_ALL}")
    print(f"{Fore.WHITE}是否显示API响应等调试信息？{Style.RESET_ALL}")
    print(f"{Fore.LIGHTBLACK_EX}  0. ❌ 隐藏调试信息（推荐）{Style.RESET_ALL}")
    print(f"{Fore.LIGHTBLACK_EX}  1. ✅ 显示调试信息{Style.RESET_ALL}")

    while True:
        choice = input(f"\n{Fore.YELLOW}➤ 请选择 (0-1): {Style.RESET_ALL}")
        if choice in ['0', '1']:
            return choice == '1'
        print(f"{Fore.RED}❌ 无效选择，请输入 0 或 1{Style.RESET_ALL}")


def get_available_configs():
    """获取可用的配置文件"""
    configs_dir = Path("configs")
    if not configs_dir.exists():
        return []

    config_files = {
        "1": "qwen_vs_qwen.yaml",
        "2": "qwen_vs_gpt.yaml",
        "3": "human_player.yaml",
        "4": "human_vs_qwen.yaml"
    }
    
    available = {}
    for key, filename in config_files.items():
        config_path = configs_dir / filename
        if config_path.exists():
            available[key] = str(config_path)
    
    return available


def get_log_path():
    """获取游戏日志保存路径"""
    while True:
        print("\n📁 请选择日志保存选项：")
        print("  1. 自动生成路径（推荐）")
        print("  2. 自定义路径")
        print("  3. 不保存日志")
        
        choice = input("\n请输入选项 (1-3): ").strip()
        
        if choice == "1":
            # 自动生成路径
            import time
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            log_path = f"./game_logs/game_{timestamp}"
            print(f"\n✅ 日志将保存到: {log_path}")
            return log_path
        elif choice == "2":
            # 自定义路径
            log_path = input("\n请输入日志保存路径: ").strip()
            if log_path:
                print(f"\n✅ 日志将保存到: {log_path}")
                return log_path
            else:
                print("\n❌ 路径不能为空，请重新输入")
        elif choice == "3":
            print("\n✅ 游戏将不保存日志")
            return None
        else:
            print("\n❌ 无效选项，请重新选择")


def get_game_rounds():
    """获取游戏局数"""
    while True:
        print("\n🎮 请输入游戏局数：")
        print("  提示：输入数字（例如：1, 5, 10）")
        print("  默认：1局")
        
        rounds = input("\n请输入局数 (直接回车使用默认): ").strip()
        
        if not rounds:
            return 1
        
        try:
            rounds_int = int(rounds)
            if rounds_int > 0:
                return rounds_int
            else:
                print("\n❌ 局数必须大于0")
        except ValueError:
            print("\n❌ 请输入有效的数字")


def run_game(config_path, log_path=None, rounds=1):
    """运行游戏"""
    print("\n" + "="*60)
    print(f"🎮 正在启动游戏...")
    print(f"📝 配置文件: {config_path}")
    print(f"🎯 游戏局数: {rounds}局")
    if log_path:
        print(f"📁 日志路径: {log_path}")
    else:
        print(f"📁 日志路径: 不保存")
    print("="*60 + "\n")
    
    # 构建命令
    cmd = ["python", "run_battle.py", "--config", config_path]
    
    if log_path:
        cmd.extend(["--log_save_path", log_path])
    
    if rounds > 1:
        cmd.extend(["--num_games", str(rounds)])
    
    try:
        # 运行游戏
        result = subprocess.run(cmd, check=False)
        
        if result.returncode == 0:
            print("\n" + "="*60)
            print("✅ 游戏成功完成！")
            print("="*60)
        else:
            print("\n" + "="*60)
            print(f"❌ 游戏异常退出 (退出码: {result.returncode})")
            print("="*60)
            
    except KeyboardInterrupt:
        print("\n\n⚠️  游戏被用户中断")
    except Exception as e:
        print(f"\n❌ 启动游戏时出错: {e}")


def run_visualizer():
    """运行游戏日志可视化工具"""
    print("\n🔍 启动游戏日志可视化工具...")
    
    visualizer_path = Path("script") / "game_visualizer.py"
    
    if not visualizer_path.exists():
        print(f"❌ 找不到可视化工具: {visualizer_path}")
        return
    
    try:
        subprocess.run(["python", str(visualizer_path)])
    except Exception as e:
        print(f"❌ 启动可视化工具时出错: {e}")


def check_environment():
    """检查运行环境"""
    errors = []
    
    # 检查配置目录
    if not Path("configs").exists():
        errors.append("❌ 找不到 configs 目录")
    
    # 检查运行脚本
    if not Path("run_battle.py").exists():
        errors.append("❌ 找不到 run_battle.py 文件")
    
    # 检查werewolf包
    if not Path("werewolf").exists():
        errors.append("❌ 找不到 werewolf 包")
    
    if errors:
        print("\n⚠️  环境检查失败：")
        for error in errors:
            print(f"  {error}")
        print("\n请确保在项目根目录下运行此脚本")
        return False
    
    return True


def main():
    """主函数"""
    # 清屏
    os.system('cls' if os.name == 'nt' else 'clear')
    
    # 打印标题
    print_banner()
    
    # 检查环境
    if not check_environment():
        input("\n按回车键退出...")
        sys.exit(1)
    
    # 获取可用配置
    available_configs = get_available_configs()
    
    if not available_configs:
        print("\n❌ 找不到任何配置文件")
        input("\n按回车键退出...")
        sys.exit(1)
    
    while True:
        # 打印菜单
        print_menu()

        # 获取用户选择
        choice = input("请输入选项 (0-9): ").strip()

        if choice == "0":
            print("\n👋 感谢使用，再见！\n")
            break

        elif choice == "8":
            # 查看游戏日志
            run_visualizer()
            input("\n按回车键继续...")
            os.system('cls' if os.name == 'nt' else 'clear')
            print_banner()
            continue

        elif choice in available_configs:
            # 获取配置文件路径
            config_path = available_configs[choice]

            # 配置调试模式
            debug_mode = configure_debug_mode()

            # 获取日志路径
            log_path = get_log_path()

            # 获取游戏局数
            rounds = get_game_rounds()

            # 应用debug配置到配置文件
            apply_debug_config(config_path, debug_mode)

            # 运行游戏
            run_game(config_path, log_path, rounds)
            
            # 游戏结束后询问是否继续
            print("\n")
            continue_game = input("是否继续玩游戏？(y/n): ").strip().lower()
            if continue_game != 'y':
                print("\n👋 感谢使用，再见！\n")
                break
            
            # 清屏并重新显示菜单
            os.system('cls' if os.name == 'nt' else 'clear')
            print_banner()
        
        else:
            print("\n❌ 无效选项，请重新选择")
            input("\n按回车键继续...")
            os.system('cls' if os.name == 'nt' else 'clear')
            print_banner()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 程序被用户中断，再见！\n")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ 程序异常退出: {e}\n")
        import traceback
        traceback.print_exc()
        input("\n按回车键退出...")
        sys.exit(1)

