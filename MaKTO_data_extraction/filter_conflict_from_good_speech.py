import argparse
import json
import tqdm
import os
from utils import get_system_prompt, create_message, get_game_description
import openai
import re

if "AWS_CLAUDE_API_BASE" not in os.environ:
    raise ValueError("AWS_CLAUDE_API_BASE not set, we recommand you use AWS Claude API, or you can change use OpenAI GPT model")

client = openai.AzureOpenAI(
        azure_endpoint=os.environ["AWS_CLAUDE_API_BASE"],
        api_version=os.environ["AWS_CLAUDE_API_VERSION"],
        api_key=os.environ["AWS_CLAUDE_API_KEY"]
    )

def get_answer(messages, llm="aws_claude35_sdk_sonnet"):
    response = client.chat.completions.create(
        model=llm, messages=messages, temperature=0, max_tokens=3200, # 最大生成字符数
        top_p=1,  frequency_penalty=0, presence_penalty=0, stop=None
    )
    return response.choices[0].message.content

def parse_final_judge(text):
    # 使用正则表达式提取 <final_judge> 和 </final_judge> 之间的内容
    pattern = r'<final_judge>(.*?)</final_judge>'
    match = re.search(pattern, text, re.DOTALL)
    if not match:
        return {}
    judge_text = match.group(1).strip()
    # 初始化结果字典
    result = {
        "含有和客观信息矛盾": True,
        "含有武断判断": True,
        "含有不恰当的推理": True
    }
    for line in judge_text.split('\n'):
        line = line.strip()
        if "不存在和客观信息矛盾" in line:
            result["含有和客观信息矛盾"] = False
        if "不存在武断判断" in line:
            result["含有武断判断"] = False
        if "不存在不恰当的推理" in line:
            result["含有不恰当的推理"] = False
    return result

def check_conflict(llm_model, sytem_prompt, input_prompt, output_response, game_type):
    game_rule = get_game_description(game_type)
    system_prompt = sytem_prompt.replace("{{GAME_RULE}}", game_rule)
    input_query = f"**输入**：\n{input_prompt}\n\n**输出**：\n{output_response}"
    messages = [
        create_message("system", system_prompt),
        create_message("user", input_query),
    ]
    raw_output = get_answer(messages, llm=llm_model).replace("\n\n", "\n")
    final_judge = parse_final_judge(raw_output)
    return final_judge, raw_output

def give_final_judgement(judge_dict, reason):
    ret = {
        "judge_json": judge_dict,
        "reason": reason,
        "final_judge": None,
        "final_judge_strict": None
    }
    if len(judge_dict) == 0:
        ret["final_judge"] = "reject"
        ret["final_judge_strict"] = "reject"
    else:
        if judge_dict["含有和客观信息矛盾"]:
            ret["final_judge"] = "reject"
        else:
            ret["final_judge"] = "accept"

        if judge_dict["含有和客观信息矛盾"] or judge_dict["含有武断判断"] or judge_dict["含有不恰当的推理"]:
            ret["final_judge_strict"] = "reject"
        else:
            ret["final_judge_strict"] = "accept"
    return ret
    

if __name__ == '__main__':
    argparser = argparse.ArgumentParser()
    argparser.add_argument('--good_speech_file',
                           type=str, default="./KTO_selected_data_9p_seer_witch_guard/tmp_good-speech.json",
                           help="path to the json file")
    argparser.add_argument('--game_type',
                           type=str, default=None,
                           help="choose from: 9p_seer_witch_guard, 9p_seer_witch_hunter, 7p_seer_guard")
    argparser.add_argument('--out_to', type=str, default="reverify_speeches.jsonl")
    argparser.add_argument('--llm_verifier', type=str, default="aws_claude35_sdk_sonnet",
                           help="Default: aws_claude35_sdk_sonnet, or you may choose from openai_gpt4 or deepseek-v3, etc..")
    args = argparser.parse_args()

    if args.game_type is None:
        args.game_type = args.good_speech_file.split("/")[-1].split("-")[0]

    with open("llm_verifier_sys_prompt.txt", "r") as f:
        system_prompt = f.read().strip()

    with open(args.good_speech_file, "r") as f:
        good_speech = json.loads(f.read())

    fout = open(args.out_to, "a+")
    cnt = 0
    for game_i, (game_path, detail) in enumerate(good_speech.items()):
        print(f"processing game {game_i}")
        for player_id, phase_list in tqdm.tqdm(detail.items()):
            with open(os.path.join(game_path, f"Player_{player_id}.jsonl"), "r") as f:
                for line in f:
                    player_game_play_info = json.loads(line.strip())
                    if player_game_play_info["phase"] in phase_list:
                        system_prompt = get_system_prompt(args.game_type)
                        input_prompt = player_game_play_info["prompt"]
                        response = player_game_play_info["response"]
                        # check whether there is conflict
                        judge_dict, reason = check_conflict(args.llm_verifier, system_prompt, input_prompt, response, args.game_type)
                        final_judge = give_final_judgement(judge_dict, reason)
                        json_out = {
                            "game_path": game_path,
                            "player_id": player_id,
                            "phase": player_game_play_info["phase"],
                            "system_prompt": system_prompt,
                            "prompt": input_prompt,
                            "response": response,
                            "judge_by_llm": final_judge,
                        }
                        fout.write(json.dumps(json_out, ensure_ascii=False) + "\n")
                        cnt += 1

        if cnt % 100 == 0:
            print(f"processed {cnt} samples")
    fout.close()
