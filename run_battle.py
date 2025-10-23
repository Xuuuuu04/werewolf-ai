import random
from werewolf.envs.werewolf_text_env_v0 import WerewolfTextEnvV0
from transformers import AutoTokenizer, AutoModelForCausalLM
import time
import argparse
import os
from werewolf.agents import agent_registry
import yaml

def eval(env, agent_list, roles_):
    print(agent_list)
    for agent in agent_list:
        agent.reset()
    done = False
    obs = env.reset(roles=roles_)
    while not done:
        current_act_idx = obs['current_act_idx']
        action = agent_list[current_act_idx - 1].act(obs)
        obs, reward, done, info = env.step(action)
    if done:
        if info['Werewolf'] == 1:
            return '🐺 狼人获胜'
        elif info['Werewolf'] == -1:
            return '👥 村民获胜'

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


def assign_agents_and_roles(assgined_roles, all_agent_models, env_param, agent_config):
    agent_list = []
    if "replace" not in agent_config:
        for i, role in enumerate(assgined_roles):
            log_file = os.path.join(args.log_save_path, f"Player_{i+1}.jsonl")
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
            log_file = os.path.join(args.log_save_path, f"Player_{i+1}.jsonl")
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
            log_file = os.path.join(args.log_save_path, f"Player_{i+1}.jsonl")
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
            log_file = os.path.join(args.log_save_path, f"Player_{i+1}.jsonl")
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
            log_file = os.path.join(args.log_save_path, f"Player_{i+1}.jsonl")
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
            log_file = os.path.join(args.log_save_path, f"Player_{i+1}.jsonl")
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


def define_agents(agent_config, env_config, args, assgined_roles):
    env_param = {
        "n_player": env_config["n_player"],
        "n_role": env_config["n_role"]
    }
    all_agent_models = {} 
    for group in agent_config.keys(): 
        agent_config[group]["model_params"].update(env_param)
        model_type = agent_config[group]["model_type"]
        if model_type not in [i[0] for g,i in all_agent_models.items()]:
            all_agent_models[group] = agent_registry.build(model_type, **agent_config[group]["model_params"])
        else:
            for g, i in all_agent_models.items():
                if model_type == i[0]:
                    all_agent_models[group] = model_type, i[1]
                    break
    return assign_agents_and_roles(assgined_roles, all_agent_models, env_param, agent_config)


def check_agent_config(agent_config):
    if "sft" in agent_config["werewolf"]["model_type"].lower() or "makto" in agent_config["werewolf"]["model_type"].lower():
        assert agent_config["werewolf"]["model_params"].get("port", None) is not None, f'No port provided for werewolf model (vllm): {agent_config["werewolf"]["model_type"]}'
    if "sft" in agent_config["villager"]["model_type"].lower() or "makto" in agent_config["villager"]["model_type"].lower():
        assert agent_config["villager"]["model_params"].get("port", None) is not None, f'No port provided for villager model (vllm): {agent_config["villager"]["model_type"]}'



def main_cli(args):
    os.makedirs(args.log_save_path, exist_ok=True)
    parsed_yaml = yaml.safe_load(open(args.config))
    agent_config = parsed_yaml["agent_config"]
    env_config = parsed_yaml["env_config"]
    parent_directory = os.path.dirname(args.log_save_path)
    if not os.path.exists(os.path.join(parent_directory, "config.yaml")):
        with open(os.path.join(parent_directory, "config.yaml"), "w") as f:
            yaml.dump(parsed_yaml, f)
    env_config["log_save_path"] = args.log_save_path
    env = WerewolfTextEnvV0(**env_config)
    roles = ["Werewolf"] * env_config["n_werewolf"] + ["Villager"] * env_config["n_villager"] + \
            ["Seer"] * env_config["n_seer"] + ["Witch"] * env_config["n_witch"] + \
            ["Guard"] * env_config["n_guard"] + ["Hunter"] * env_config["n_hunter"]
    random.shuffle(roles)
    print("🎮 新游戏开始，角色分配: ", roles)


    check_agent_config(agent_config)

    agent_list = define_agents(agent_config, env_config, args, roles)
    begin = time.time()
    result = eval(env, agent_list, roles)
    print("⏱️ 游戏耗时: {:.2f}秒 | 🏆 结果: {}".format(time.time() - begin, result))


if __name__ == '__main__':
    argparser = argparse.ArgumentParser()
    argparser.add_argument('--config',
                           type=str, default="configs/gpt4_vs_gpt4.yaml",
                           help="path to the config file of the game")
    argparser.add_argument('--log_save_path', type=str, default=None)
    args = argparser.parse_args()
    main_cli(args)
