#!/bin/bash

game_dir="trial_logs"
game_type=9p_seer_witch_guard
sft_model_regx="sft_agent"
out_dir="KTO_selected_data_${game_type}"
mkdir -p $out_dir


python3 get_bad_speech.py --game_dir $game_dir --game_type $game_type \
    --sft_model_regx=$sft_model_regx --out $out_dir

python3 get_bad_action.py --game_dir $game_dir --game_type $game_type  \
    --sft_model_regx=$sft_model_regx --out $out_dir

python3 get_good_action.py --game_dir $game_dir --game_type $game_type \
    --sft_model_regx=$sft_model_regx --out $out_dir

python3 get_bad_vote.py --game_dir $game_dir --game_type $game_type \
    --sft_model_regx=$sft_model_regx --out $out_dir --strict

python3 get_good_vote.py --game_dir $game_dir --game_type $game_type \
     --sft_model_regx=$sft_model_regx --out $out_dir

echo "Now we will extract good speech"
python3 get_good_speech.py --game_dir $game_dir --game_type $game_type \
    --sft_model_regx=$sft_model_regx \
    --out $out_dir/tmp_good_speech.json


echo "Detect whether there are some fact conflicts in good speech, using LLM: aws_claude35_sdk_sonnet"
mkdir -p $out_dir/conflict_speech
python3 filter_conflict_from_good_speech.py --game_type $game_type \
    --good_speech_file $out_dir/tmp_good_speech.json \
    --out_to $out_dir/conflict_speech/reverify_speeches.jsonl \
    --llm_verifier aws_claude35_sdk_sonnet

echo "Formatting data"
python3 format_training_data.py --selected_path $out_dir \
    --conflict_speech_path $out_dir/conflict_speech \
    --save_prefix $out_dir/kto_dataset