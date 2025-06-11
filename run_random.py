import random
from werewolf.envs.werewolf_text_env_v0 import WerewolfTextEnvV0
from transformers import AutoTokenizer, AutoModelForCausalLM
import time
import argparse
import os
from werewolf.agents import agent_registry
import yaml
import random
import json


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
            return 'Werewolf win'
        elif info['Werewolf'] == -1:
            return 'Villager win'


def assign_agents(candidate_agent_models, env_config, args, assigined_roles, must_include):
    werewolf_team = ["Werewolf"]
    villager_team = ["Villager", "Seer", "Witch", "Guard", "Hunter"]

    env_param = {
        "n_player": env_config["n_player"],
        "n_role": env_config["n_role"]
    }
    all_agent_models = {}
    role2agent_list = []
    sample_ratio = [a["sample_ratio"] for a in candidate_agent_models]
    while not any(m in role2agent_list for m in must_include):
        print("model not in must_include")
        all_agent_models = {}
        role2agent_list = []
        villager_team_model = []
        werewolf_team_model = []
        for i, role in enumerate(assigined_roles):
            if role in werewolf_team:
                while True:
                    model = random.choices(candidate_agent_models, weights=sample_ratio, k=1)[0]
                    if model["model_type"] not in villager_team_model:
                        werewolf_team_model.append(model["model_type"])
                        break
            elif role in villager_team:
                while True:
                    model = random.choices(candidate_agent_models, weights=sample_ratio, k=1)[0]
                    if model["model_type"] not in werewolf_team_model:
                        villager_team_model.append(model["model_type"])
                        break
            # model = random.choices(candidate_agent_models, weights=sample_ratio, k=1)[0]
            # model = random.choice(candidate_agent_models) # randomly choose a model from all_agent_models
            model_type = model["model_type"]
            model_params = model["model_params"]
            if model_type not in all_agent_models:
                # build model
                all_agent_models[model_type] = agent_registry.build(model_type, **model_params)
            role2agent_list.append(model_type)

    agent_list = []
    for i, role in enumerate(assigined_roles):
        log_file = os.path.join(args.log_save_path, f"Player_{i + 1}.jsonl")
        agent_type = role2agent_list[i]
        type, agent_param = all_agent_models[agent_type]
        agent = agent_registry.build_agent(type, i, agent_param, env_param, log_file)
        agent_list.append(agent)
    return role2agent_list, agent_list


def main_cli(args):
    os.makedirs(args.log_save_path, exist_ok=True)
    parsed_yaml = yaml.safe_load(open(args.config))
    agent_config = parsed_yaml["agent_config"]
    all_candidate_agents = agent_config["all_candidates"]
    env_config = parsed_yaml["env_config"]
    parent_directory = os.path.dirname(args.log_save_path)
    if not os.path.exists(os.path.join(parent_directory, "config.yaml")):
        with open(os.path.join(parent_directory, "config.yaml"), "w") as f:
            yaml.dump(parsed_yaml, f)
    env_config["log_save_path"] = args.log_save_path
    env = WerewolfTextEnvV0(**env_config)
    # assign role and models
    roles = ["Werewolf"] * env_config["n_werewolf"] + ["Villager"] * env_config["n_villager"] + \
            ["Seer"] * env_config["n_seer"] + ["Witch"] * env_config["n_witch"] + \
            ["Guard"] * env_config["n_guard"] + ["Hunter"] * env_config["n_hunter"]
    random.shuffle(roles)
    print("New rollout: ", roles)

    with open("script/all_models_us.yaml", "r") as f:
        all_models = yaml.safe_load(f)
    must_include = []
    for key, value in all_models.items():
        must_include.append(value["inenv"])
    role2agent_list, agent_list = assign_agents(all_candidate_agents, env_config, args, roles,
                                                must_include=must_include)
    print("\n\n")
    for r, a in zip(roles, role2agent_list):
        print(r, "\t", a)
    # make sure role2agent_list must have training model, or repeat

    assert len(roles) == len(role2agent_list), "The length of roles and role2agent_list must be the same"

    records = []
    for i in range(len(roles)):
        record = {
            "id": i + 1,
            "role": roles[i],
            "model": role2agent_list[i]
        }
        records.append(record)

    output_file = os.path.join(args.log_save_path, 'roles_model_assignment.json')
    with open(output_file, 'w', encoding='utf-8') as json_file:
        json.dump(records, json_file, ensure_ascii=False, indent=4)

    print(agent_list)
    begin = time.time()
    result = eval(env, agent_list, roles)
    print(time.time() - begin, result)


if __name__ == '__main__':
    argparser = argparse.ArgumentParser()
    argparser.add_argument('--config',
                           type=str, default="configs/random_models.yaml",
                           help="path to the config file of the game")
    argparser.add_argument('--log_save_path', type=str, default=None)
    argparser.add_argument('--use_vllm', action='store_true', default=False,
                           help='whether to use vllm, if set, remember add '
                                '``CUDA_VISIBLE_DEVICES=0 python3 -m vllm.entrypoints.openai.api_server --model xxx --port 1307``'
                                'to launch a vllm server before running the experiment.')
    args = argparser.parse_args()
    main_cli(args)