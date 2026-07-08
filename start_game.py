#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
狼人杀游戏启动器
提供交互式命令行界面来选择游戏模式和配置
"""
import os
import sys
import subprocess
import time
from pathlib import Path

from colorama import init, Fore, Style

# 初始化colorama（Windows兼容）
init(autoreset=True)

# 支持从 src/ 导入 werewolf 包（与 run_battle.py 保持一致）
_SRC = Path(__file__).resolve().parent / 'src'
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))


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


def check_api_env():
    """检查必要的 API 环境变量是否已设置。"""
    missing = []
    if not os.environ.get('LLM_API_KEY'):
        missing.append('LLM_API_KEY')
    if not os.environ.get('LLM_BASE_URL'):
        missing.append('LLM_BASE_URL')
    if missing:
        print(f"\n{Fore.YELLOW}⚠️  以下环境变量未设置：{', '.join(missing)}{Style.RESET_ALL}")
        print(f"{Fore.LIGHTBLACK_EX}   请先 export LLM_API_KEY=... LLM_BASE_URL=...{Style.RESET_ALL}")
        print(f"{Fore.LIGHTBLACK_EX}   否则配置中的占位符无法被解析。{Style.RESET_ALL}\n")
        return False
    return True


def configure_debug_mode():
    """配置调试模式（仅返回布尔值，不写回配置文件）。"""
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
    """获取可用的配置文件（脱敏模板 .example.yaml）。

    用户如需自定义，可把 .example.yaml 复制为 .yaml 并填入真实值。
    """
    configs_dir = Path("configs")
    if not configs_dir.exists():
        return {}

    config_files = {
        "1": "qwen_vs_qwen.example.yaml",
        "2": "qwen_vs_gpt.example.yaml",
        "3": "human_player.example.yaml",
        "4": "human_vs_qwen.example.yaml",
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
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            log_path = f"./game_logs/game_{timestamp}"
            print(f"\n✅ 日志将保存到: {log_path}")
            return log_path
        elif choice == "2":
            log_path = input("\n请输入日志保存路径: ").strip()
            if log_path:
                print(f"\n✅ 日志将保存到: {log_path}")
                return log_path
            print("\n❌ 路径不能为空，请重新输入")
        elif choice == "3":
            print("\n✅ 游戏将不保存日志")
            return None
        else:
            print("\n❌ 无效选项，请重新选择")


def run_game(config_path, log_path=None, debug_mode=False):
    """运行游戏。

    debug_mode 通过命令行参数 --debug/--no-debug 传给 run_battle.py，
    在内存中覆盖配置，不再写回配置文件。
    """
    print("\n" + "=" * 60)
    print("🎮 正在启动游戏...")
    print(f"📝 配置文件: {config_path}")
    print(f"🐛 调试模式: {'开启' if debug_mode else '关闭'}")
    if log_path:
        print(f"📁 日志路径: {log_path}")
    else:
        print("📁 日志路径: 不保存")
    print("=" * 60 + "\n")

    # 构建 Python 解释器与命令
    py = sys.executable or "python"
    cmd = [py, "run_battle.py", "--config", config_path]

    if log_path:
        cmd.extend(["--log_save_path", log_path])

    # 通过命令行参数控制 debug（在 run_battle.py 内存中覆盖，不写回文件）
    if debug_mode:
        cmd.append("--debug")
    else:
        cmd.append("--no-debug")

    try:
        result = subprocess.run(cmd, check=False)

        if result.returncode == 0:
            print("\n" + "=" * 60)
            print("✅ 游戏成功完成！")
            print("=" * 60)
        else:
            print("\n" + "=" * 60)
            print(f"❌ 游戏异常退出 (退出码: {result.returncode})")
            print("=" * 60)

    except KeyboardInterrupt:
        print("\n\n⚠️  游戏被用户中断")
    except Exception as e:
        print(f"\n❌ 启动游戏时出错: {e}")


def run_visualizer():
    """运行游戏日志可视化工具"""
    print("\n🔍 启动游戏日志可视化工具...")

    visualizer_path = Path("src") / "script" / "game_visualizer.py"

    if not visualizer_path.exists():
        print(f"❌ 找不到可视化工具: {visualizer_path}")
        return

    py = sys.executable or "python"
    try:
        subprocess.run([py, str(visualizer_path)])
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

    # 检查 werewolf 包（位于 src/werewolf，命名空间包，无 __init__.py）
    if not (Path("src") / "werewolf").is_dir():
        errors.append("❌ 找不到 src/werewolf 包")
    elif not (Path("src") / "werewolf" / "registry.py").exists():
        errors.append("❌ src/werewolf 包不完整（缺 registry.py）")

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
        print("\n❌ 找不到任何配置文件（.example.yaml）")
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
            # 检查 API 环境变量
            if not check_api_env():
                proceed = input("是否仍要继续？(y/n): ").strip().lower()
                if proceed != 'y':
                    continue

            # 获取配置文件路径
            config_path = available_configs[choice]

            # 配置调试模式
            debug_mode = configure_debug_mode()

            # 获取日志路径
            log_path = get_log_path()

            # 运行游戏（debug 通过命令行参数传递，不写回配置文件）
            run_game(config_path, log_path, debug_mode)

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
