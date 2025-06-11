# Werewolf Game Dataset

This repository contains <b>sample</b> data in the paper, including both samples of raw game data and the script to process raw data in to SFT datasets.


## Dataset Structure


### Raw Data

* ⚠️ Due to file size limitations, we provide samples of 3 games for each setting in both training and test datasets. Full dataset will be released upon acceptance of the paper.

The raw data is located in the `raw` folder. Each game consists of two files:

1. `event.json`: Contains the game regular record and thinking process data, including:
   - regular record:
      - Nocturnal action records of god roles and werewolves
      - Daytime speeches of players
      - Daytime votes of players
      - Game review
   - thinking process:
      - Speech summary including intended labels for others and voting intentions
      - Voting rationale

2. `note.json`: Contains the thinking process data, including:
   - Future strategies which includes action rationale and the target
   - Notes which includes a summary of the day's events


The file structure of one game:
```bash
├── seer_witch_guard
│   └── game_1
│       ├── event_en.json
│       ├── event_zh.json
│       ├── note_en.json
│       ├── note_zh.json
```

`_zh` indicates Chinese version (original), and `_en` indicates English version (Claude-translated).

**Note:** The English game data is automatically translated by ``Claude-3.5-Sonnet-V2``. If some of the data translation is missing, you can prompt LLM again to translate it by yourself.


## Data Processing

The scripts for processing the raw data are located in the `process_script` folder:

- `process_data.py`
- `utils.py`

To construct the dataset, run the following commands:

```bash
# For training data, use zh as default
python3 process_script/process_data.py --read_path './raw/train/7_player_game/seer_guard','./raw/train/7_player_game/seer_witch','./raw/train/9_player_game/guard_witch_seer','./raw/train/9_player_game/hunter_witch_seer' --language zh --save_path ./game_behavior --add_rolepred True

python3 process_script/csv_to_parquet.py --csv_paths ./game_behavior

# For test data
python3 process_script/process_data.py --read_path './raw/test/7_player_game/seer_guard','./raw/test/7_player_game/seer_witch','./raw/test/9_player_game/guard_witch_seer','./raw/test/9_player_game/hunter_witch_seer' --language zh --save_path ./test --add_rolepred True
```

When executing this script, the following parameters must be specified:
- `--read_path`: This is used to specify the path to read the raw data. 
- `--language`: Used to specify the language of the processed data. You may choose `zh` or `en`. The default is `zh`.
- `--save_path`: Used to specify the path where the processed data will be saved. 
- `--add_rolepred`: If this parameter is set to `True`, it means that the role prediction task will be added.

After executing the above command, multiple formats of data files will be generated in the specified save path `./game_behavior`, including `csv` and `parquet` formats:
- **Original Data Format Files**
  - `action.csv`, `speech.csv`, and `vote.csv` store the data related to actions, speeches, and votes in the game behavior in `csv` format respectively. 
- **Configuration File**
  - The `config.json` file is used to record some statistical information of processed instruction data, including the raw data path, the total number of different types of data and the detailed prompts length.
- **Role Distribution File**
  - The `roles_distribution.json` file records the distribution of roles in the game.



