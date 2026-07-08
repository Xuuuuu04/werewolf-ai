import random
from werewolf.envs.werewolf_text_env_v0 import WerewolfTextEnvV0
from werewolf.helper.console_ui import ConsoleUI
from werewolf.config_loader import load_config
import time
import argparse
import os
from werewolf.agents import agent_registry


def eval(env, agent_list, roles_):
    for agent in agent_list:
        agent.reset()
    done = False
    obs = env.reset(roles=roles_)

    # 显示初始状态
    display_current_state(env, obs)

    while not done:
        current_act_idx = obs['current_act_idx']
        action = agent_list[current_act_idx - 1].act(obs)

        # 执行动作并立即显示更新
        obs, reward, done, info = env.step(action)
        display_current_state(env, obs)

        # 如果是人类玩家，等待用户输入后继续
        agent = agent_list[current_act_idx - 1]
        if getattr(agent, 'debug', False) and 'human' in type(agent).__name__.lower():
            input("\n按回车键继续...")

    if done:
        if info['Werewolf'] == 1:
            ConsoleUI.print_game_result('🐺 狼人阵营获胜！', is_win=False)
            return '🐺 狼人获胜'
        elif info['Werewolf'] == -1:
            ConsoleUI.print_game_result('👥 村民阵营获胜！', is_win=True)
            return '👥 村民获胜'


def display_current_state(env, obs):
    """实时显示当前游戏状态"""
    from werewolf.helper.console_ui import ConsoleUI

    # 获取当前游戏日志并格式化显示
    log_text = format_game_log(env.game_log)

    # 清屏并显示当前状态
    ConsoleUI.clear_screen()
    ConsoleUI.print_header(f"🎮 {ConsoleUI.get_phase_text(obs['phase'])}", color=ConsoleUI.COLORS['info'])

    # 显示玩家信息
    if 'current_act_idx' in obs and obs['current_act_idx']:
        ConsoleUI.print_player_info(obs['current_act_idx'], obs['identity'], obs['phase'])

    # 显示游戏日志
    ConsoleUI.print_section("📜 实时游戏日志", color=ConsoleUI.COLORS['info'])
    ConsoleUI.print_game_log(log_text, obs.get('current_act_idx'))

    # 如果是投票或发言阶段，显示提示
    if 'speech' in obs['phase']:
        ConsoleUI.print_tips([
            "观察其他玩家的发言",
            "分析逻辑和可信度",
            "准备自己的发言策略"
        ])
    elif 'vote' in obs['phase']:
        ConsoleUI.print_tips([
            "分析所有发言内容",
            "注意归票避免平票",
            "重点关注可疑玩家"
        ])


def format_game_log(game_log):
    """格式化游戏日志为可读文本。

    委托给共享实现 `werewolf.helper.log_utils.format_game_log`，
    与 `LLMAgent.format_log` 同一来源，避免文案分叉。
    """
    from werewolf.helper.log_utils import format_game_log as _format
    return _format(game_log)

def get_replaced_wolf_id(replace_players, assgined_roles):
    replace_type = replace_players.split("_")[1]
    if replace_type == "last":
        reversed_lst = assgined_roles[::-1]
        index_in_reversed = reversed_lst.index("Werewolf")
        replace_id = len(assgined_roles) - 1 - index_in_reversed
    elif replace_type == "random":
        indexes = [i for i, x in enumerate(assgined_roles) if x == "Werewolf"]
        replace_id = random.choice(indexes)
    else:
        raise NotImplementedError
    return replace_id

def get_replaced_simple_villager_ids(assgined_roles, replace_number):
    indexes = [i for i, x in enumerate(assgined_roles) if x == "Villager"]
    replace_ids = random.sample(indexes, replace_number)
    return replace_ids

def get_replaced_villager_ids(assgined_roles, replace_number):
    indexes = [i for i, x in enumerate(assgined_roles) if x != "Werewolf"]
    replace_ids = random.sample(indexes, replace_number)
    return replace_ids


def assign_agents_and_roles(assgined_roles, all_agent_models, env_param, agent_config, log_save_path):
    agent_list = []
    if "replace" not in agent_config:
        for i, role in enumerate(assgined_roles):
            log_file = os.path.join(log_save_path, f"Player_{i+1}.jsonl")
            if role.lower() == "werewolf":
                type, agent_param = all_agent_models["werewolf"]
            else:
                type, agent_param = all_agent_models["villager"]
            agent = agent_registry.build_agent(type, i, agent_param, env_param, log_file)
            agent_list.append(agent)
        return agent_list
    replace_players = agent_config["replace"]["replace_player"]
    replace_role = replace_players.split("_")[0]
    if replace_role == "werewolf":
        repalce_id = get_replaced_wolf_id(replace_players, assgined_roles)
        for i, role in enumerate(assgined_roles):
            log_file = os.path.join(log_save_path, f"Player_{i+1}.jsonl")
            if role.lower() == "werewolf" and i != repalce_id:
                type, agent_param = all_agent_models["werewolf"]
            elif role.lower() == "werewolf" and i == repalce_id:
                type, agent_param = all_agent_models["replace"]
            else:
                type, agent_param = all_agent_models["villager"]
            agent = agent_registry.build_agent(type, i, agent_param, env_param, log_file)
            agent_list.append(agent)
        return agent_list
    elif replace_role in ["seer", "guard", "witch", "hunter"]:
        for i, role in enumerate(assgined_roles):
            log_file = os.path.join(log_save_path, f"Player_{i+1}.jsonl")
            if role.lower() == "werewolf":
                type, agent_param = all_agent_models["werewolf"]
            elif role.lower() == replace_role:
                type, agent_param = all_agent_models["replace"]
            else:
                type, agent_param = all_agent_models["villager"]
            agent = agent_registry.build_agent(type, i, agent_param, env_param, log_file)
            agent_list.append(agent)
        return agent_list
    elif replace_role == "gods":
        replace_gods = replace_players.split("_")[1].split("-")
        for i, role in enumerate(assgined_roles):
            log_file = os.path.join(log_save_path, f"Player_{i+1}.jsonl")
            if role.lower() == "werewolf":
                type, agent_param = all_agent_models["werewolf"]
            elif role.lower() in replace_gods:
                type, agent_param = all_agent_models["replace"]
            else:
                type, agent_param = all_agent_models["villager"]
            agent = agent_registry.build_agent(type, i, agent_param, env_param, log_file)
            agent_list.append(agent)
        return agent_list
    elif replace_role == "simplevillager":
        replace_number = int(replace_players.split("_")[1])
        replace_ids = get_replaced_simple_villager_ids(assgined_roles, replace_number)
        for i, role in enumerate(assgined_roles):
            log_file = os.path.join(log_save_path, f"Player_{i+1}.jsonl")
            if role.lower() == "werewolf":
                type, agent_param = all_agent_models["werewolf"]
            elif i in replace_ids:
                type, agent_param = all_agent_models["replace"]
            else:
                type, agent_param = all_agent_models["villager"]
            agent = agent_registry.build_agent(type, i, agent_param, env_param, log_file)
            agent_list.append(agent)
        return agent_list
    elif replace_role == "villager":
        replace_number = int(replace_players.split("_")[1].replace("random", ""))
        replace_ids = get_replaced_villager_ids(assgined_roles, replace_number)
        for i, role in enumerate(assgined_roles):
            log_file = os.path.join(log_save_path, f"Player_{i+1}.jsonl")
            if role.lower() == "werewolf":
                type, agent_param = all_agent_models["werewolf"]
            elif i in replace_ids:
                type, agent_param = all_agent_models["replace"]
            else:
                type, agent_param = all_agent_models["villager"]
            agent = agent_registry.build_agent(type, i, agent_param, env_param, log_file)
            agent_list.append(agent)
        return agent_list
    else:
        raise NotImplementedError


def define_agents_with_human_player(human_config, ai_config, env_config, args, assigned_roles):
    """
    定义包含单个人类玩家的智能体列表
    human_config: 人类玩家配置
    ai_config: AI模型配置
    """
    from werewolf.helper.console_ui import ConsoleUI

    env_param = {
        "n_player": env_config["n_player"],
        "n_role": env_config["n_role"]
    }

    # 确定人类玩家编号
    if 'player_id' in human_config and human_config['player_id']:
        human_player_id = human_config['player_id'] - 1  # 转换为0-based索引
    else:
        # 随机分配
        human_player_id = random.randint(0, len(assigned_roles) - 1)

    # 构建AI模型
    ai_config["model_params"].update(env_param)
    # 添加debug参数
    debug_mode = ai_config["model_params"].get("debug", False)
    ai_config["model_params"]["debug"] = debug_mode

    ai_model_type, ai_agent_param = agent_registry.build(
        ai_config["model_type"],
        **ai_config["model_params"]
    )

    # 构建人类玩家模型
    human_model_type = "human"
    human_param = {
        "client": None,
        "tokenizer": None,
        "llm": None,
        "temperature": 0
    }
    human_param.update(env_param)
    # 添加debug参数
    debug_mode = human_param.get("debug", False)
    human_param["debug"] = debug_mode

    _, human_agent_param = agent_registry.build(human_model_type, **human_param)

    # 创建智能体列表
    agent_list = []
    for i, role in enumerate(assigned_roles):
        log_file = os.path.join(args.log_save_path, f"Player_{i+1}.jsonl")

        if i == human_player_id:
            # 人类玩家
            agent = agent_registry.build_agent(
                human_model_type, i, human_agent_param, env_param, log_file
            )
            # 显示人类玩家信息
            ConsoleUI.print_info(f"🎮 你将扮演 {i+1} 号玩家，身份是: {ConsoleUI.ICONS.get(role.lower(), '👤')} {role}")
        else:
            # AI玩家
            agent = agent_registry.build_agent(
                ai_model_type, i, ai_agent_param, env_param, log_file
            )

        agent_list.append(agent)

    return agent_list


def define_agents(agent_config, env_config, args, assgined_roles):
    env_param = {
        "n_player": env_config["n_player"],
        "n_role": env_config["n_role"]
    }
    all_agent_models = {}
    for group in agent_config.keys():
        agent_config[group]["model_params"].update(env_param)
        # 添加debug参数支持（默认隐藏调试信息）
        debug_mode = agent_config[group]["model_params"].get("debug", False)
        agent_config[group]["model_params"]["debug"] = debug_mode

        model_type = agent_config[group]["model_type"]
        if model_type not in [i[0] for g, i in all_agent_models.items()]:
            all_agent_models[group] = agent_registry.build(model_type, **agent_config[group]["model_params"])
        else:
            for g, i in all_agent_models.items():
                if model_type == i[0]:
                    all_agent_models[group] = model_type, i[1]
                    break

    # 确保env_param中也有debug参数
    # 从第一个有效的agent组获取debug设置
    env_param["debug"] = False
    for group in agent_config.keys():
        if "model_params" in agent_config[group]:
            env_param["debug"] = agent_config[group]["model_params"].get("debug", False)
            break

    return assign_agents_and_roles(assgined_roles, all_agent_models, env_param, agent_config, args.log_save_path)


def check_agent_config(agent_config):
    if "sft" in agent_config["werewolf"]["model_type"].lower() or "makto" in agent_config["werewolf"]["model_type"].lower():
        assert agent_config["werewolf"]["model_params"].get("port", None) is not None, f'No port provided for werewolf model (vllm): {agent_config["werewolf"]["model_type"]}'
    if "sft" in agent_config["villager"]["model_type"].lower() or "makto" in agent_config["villager"]["model_type"].lower():
        assert agent_config["villager"]["model_params"].get("port", None) is not None, f'No port provided for villager model (vllm): {agent_config["villager"]["model_type"]}'



def main_cli(args):
    os.makedirs(args.log_save_path, exist_ok=True)
    parsed_yaml = load_config(args.config)
    agent_config = parsed_yaml["agent_config"]
    env_config = parsed_yaml["env_config"]

    # 检查是否启用单个人类玩家模式
    human_player_config = parsed_yaml.get("human_player", None)

    # 在内存中应用 debug 标志，不写回配置文件以避免污染源文件
    if args.debug or args.no_debug:
        debug_flag = bool(args.debug)
        for group_name, group_config in agent_config.items():
            if "model_params" in group_config:
                group_config["model_params"]["debug"] = debug_flag

    env_config["log_save_path"] = args.log_save_path
    env = WerewolfTextEnvV0(**env_config)
    roles = ["Werewolf"] * env_config["n_werewolf"] + ["Villager"] * env_config["n_villager"] + \
            ["Seer"] * env_config["n_seer"] + ["Witch"] * env_config["n_witch"] + \
            ["Guard"] * env_config["n_guard"] + ["Hunter"] * env_config["n_hunter"]
    random.shuffle(roles)

    # 美化游戏开始提示
    ConsoleUI.print_header("🎮 狼人杀游戏开始", icon='', color=ConsoleUI.COLORS['info'])
    print(f"{ConsoleUI.COLORS['info']}角色配置：{roles}{ConsoleUI.COLORS['info']}\n")

    # 根据配置选择agent定义方式
    if human_player_config and human_player_config.get("enabled", False):
        # 单个人类玩家模式
        ConsoleUI.print_info("🎮 模式：单人类玩家 + AI")
        ai_model_config = agent_config.get("ai_model", agent_config.get("villager"))
        agent_list = define_agents_with_human_player(
            human_player_config, ai_model_config, env_config, args, roles
        )
    else:
        # 传统阵营模式
        check_agent_config(agent_config)
        agent_list = define_agents(agent_config, env_config, args, roles)
    begin = time.time()
    result = eval(env, agent_list, roles)

    # 美化游戏结束提示
    elapsed_time = time.time() - begin
    ConsoleUI.print_info(f"⏱️ 游戏耗时: {elapsed_time:.2f}秒")
    ConsoleUI.print_info(f"🏆 游戏结果: {result}")


if __name__ == '__main__':
    argparser = argparse.ArgumentParser()
    argparser.add_argument('--config',
                           type=str, default="configs/qwen_vs_qwen.example.yaml",
                           help="path to the config file of the game")
    argparser.add_argument('--log_save_path', type=str, default="logs/default")
    argparser.add_argument('--debug',
                           action='store_true',
                           help="show debug information (API responses, etc.)")
    argparser.add_argument('--no-debug',
                           action='store_true',
                           help="hide debug information (default)")
    args = argparser.parse_args()

    # 如果同时设置了--debug和--no-debug，--debug优先
    if args.debug and args.no_debug:
        args.debug = True
        args.no_debug = False

    main_cli(args)
