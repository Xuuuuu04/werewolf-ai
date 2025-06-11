This is the implementation of paper [Multi-agent KTO: Reinforcing Strategic Interactions of Large Language Model in Language Game](https://arxiv.org/abs/2501.14225)


## Dataset

All the dataset can be downloaded at https://huggingface.co/datasets/ReneeYe/werewolf_game_reasoning.

The following is how to prepare SFT data from the raw game record.

### SFT Dataset preparation
The sample of dataset is under `data_sample/`. Due to the limitation of file size, in the path, we provide samples of 10 games and script to process the game behavoior data into SFT dataset. See `data_sample/README.md` for more details.

### SFT
After prepared SFT dataset in json format, you can train SFT model based on Base model like [Qwen2.5-14B-Instruct](https://huggingface.co/Qwen/Qwen2.5-14B-Instruct).

For SFT training, you may follow the instructions in [TRL](https://huggingface.co/docs/trl/en/sft_trainer) or use [LLaMA-Factory](https://github.com/hiyouga/LLaMA-Factory) code base.

## How to run Werewolf Game
Now you have a SFT model, you can run Werewolf Game with it.
### 0. Installation

We recommend do it in a virtual env. Take `conda` for example:
```Bash
conda create -n werewolf python=3.10
conda activate werewolf
pip install -e .
```
The commands will create and activate an env called `werewolf`. And the dependencies and packages will be correctly installed.

### 1. Set OpenAI API Key
To run game with OpenAI API, you need to set your OpenAI API key. We use Azure OpenAI API by default, for example:
```Bash
export AZURE_OPENAI_API_KEY={your_api_key}
export AZURE_OPENAI_API_BASE={your_api_base}
export AZURE_OPENAI_API_VERSION={your_api_version}
```
In the script we use Azure OpenAI API by default, if you want to use OpenAI API, you need to change to code in `werewolf/registry.py` to
```Python
client = openai.OpenAI(api_key={your_api_key})
```

### 2. Start VLLM API
For trained model, start a vllm service.

```Bash
python3 -m vllm.entrypoints.openai.api_server --model {model_path} --served-model-name {served_name}  --port {port}
```
where {served_name} is "sft_agent" or "makto_agent".
* No worry😊, the training of makto_agent will be introduced later.


### 3. Define Config Yaml
Second, define config yaml file as in `configs/gpt4_vs_makto.yaml`, `configs/gpt4_vs_sft.yaml` or `configs/human_vs_makto.yaml`.

Example:
```Bash
#  role assignment
env_config:
    n_player: 9 # number of players
    n_role: 4 # number of roles
    n_werewolf: 3 
    n_seer: 1
    n_guard: 1
    n_witch: 1
    n_villager: 3
    n_hunter: 0

#  agent assignment
agent_config:
    werewolf: # agents of werewolf
        model_type: gpt
        model_params:
            tokenizer: null
            llm: {gpt_model_name}
            temperature: {temperature}
    villager: # agents of villager
        model_type: makto_agent  # model_type must be same as served_name.
        model_params:
            port: {port}
            tokenizer: {model_path}
            llm: {model_path}
            ip: {ip}
            temperature: {temperature}
```
We support 4 types of agents: `gpt`, `makto_agent`, `sft_agent` and `human`. The `human` agent is for human interaction.


### 4. Run battles
Run battles using the example scripts:
#### Run a single head-to-head game:
```bash
game_path=./trial_logs
python3 run_battle.py --config configs/gpt4_vs_makto.yaml --log_save_path ${game_path}/game_1 --use_vllm
```
#### Run multiple games:
```Bash
game_path=./trial_logs
Bash run_batch.sh configs/gpt4_vs_makto.yaml ${game_path} 10 
```

Then, you will get logs under `./trial_logs/game_1/`:
```angular2html
./trial_logs/game_1
├── game_log.json    // all game log as defined in `envs/werewolf_text_env_v0.py` 
├── Player_1.jsonl   // the detailed logs of player 1
├── Player_2.jsonl
├── Player_3.jsonl
├── ...
├── Player_10.jsonl
```
For each line in `Player_${i}.jsonl`, it is a json object with the following fields:
```angular2html
{
    "message": "<phase>",
    "prompt": "<prompt>",
    "response": "<response>",
    "phase": "<phase>",
    "gen_times": "<gen_times>" 
}
```
#### Run random competition:
Or, you may run random competition with various models/APIs in the game. The configuration file is `configs/random_models.yaml`.
In the config file, all the candidate models are listed and sampled to play different roles in the game, to make the game more interesting and diversified.

```Bash
game_path=./random_competition_logs
Bash run_random.py --config configs/random_models.yaml --log_save_path ${game_path}/game_1 --use_vllm
```

### 5. View Battle Results
1. You may use `stats_winning.py` to stats the winning rate of each agent.
```Bash
cd scripts
python3 stats_winning.py --game_dir {game_path}
```

2. You may use `game_visualizer.py` to visualize the game log.
```Bash
cd scripts
python3 game_visualizer.py --game_dir {game_path} --model_setting {model_setting}
```
This script will start a gradio server, you can view the game log and the detailed behavior of each agent player in the browser.

`game_path` is the path to the game log directory, e.g., `./trial_logs`, and `model_setting` is the setting of games in the format `w-{werewolf_model_type}_vs_v-{villager_model_type}`, e.g., `w-sft_vs_v-gpt4o`.

## MaKTO training
After accumulated enough behavior data of SFT model, you can apply Multi-agent KTO to train a Makto agent. The training process includes data preparation and KTO training.

### 1. Training data preparation
All the data preparation scripts are under `MaKTO_data_extraction/`. A sample script to extract preference data is provided in `MaKTO_data_extraction/extract_script.sh`.

Here are some explanations:
- `get_bad_speech.py`: Extract bad speech from game logs.
- `get_bad_action.py`: Extract bad actions from game logs, using Heuristic-based method.
- `get_good_action.py`: Extract good actions from game logs, using Heuristic-based method.
- `get_bad_vote.py`: Extract bad votes from game logs.
- `get_good_vote.py`: Extract good votes from game logs.
- For good speech, in addition to judge the speech is good or not based on the voting result, we need extra steps to filter conflict from good speech, using LLM as verifier.
    - `get_good_speech.py`: Extract good speech from game logs, based on the voting result.
    - `filter_conflict_from_good_speech.py`: Filter conflict from good speech.
- After extracting and filtering, apply `format_training_data.py` to format the data into KTO training format. 
    * In this script, we consider the <b>unbalanced</b> situation for different roles and phases in the game, and do upsampling or downsampling to make the training data more balanced. E.g., the behavior data of ordinary villager appears more than the behavior data of other roles, so we need to downsample them. The behavior data in phase 3 or more is less appeared, thus we need to upsample them. You may adjust the sampling strategy by your own in the script.

### 2. MaKTO training
After prepared data, you can train MaKTO agent. You may apply [TRL](https://huggingface.co/docs/trl/main/en/kto_trainer) or [LLaMA-Factory](https://github.com/hiyouga/LLaMA-Factory) to do KTO training.

## Models
Due to the anonymous policy, we will release `MaKTO-14b` and `MaKTO-72b` model upon acceptance for re-production.
The models follow <b>CC BY-NA-SA 4.0</b> license.