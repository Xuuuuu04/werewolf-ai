#!/bin/bash

export AZURE_OPENAI_API_KEY={YOUR_AZURE_OPENAI_API_KEY}
export AZURE_OPENAI_API_BASE={YOUR_AZURE_OPENAI_API_BASE}
export AZURE_OPENAI_API_VERSION={YOUR_AZURE_OPENAI_API_VERSION}


game_config=$1
game_dir=$2
num=$3
shift 3

mkdir -p $game_dir

for ((i=1; i<=num; i++))
do
    python3 run_battle.py --config $game_config --log_save_path $game_dir/game_${i} $@
done