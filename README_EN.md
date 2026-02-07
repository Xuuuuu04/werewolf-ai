# Werewolf AI

LLM-powered Werewolf game supporting AI-vs-AI and human-vs-AI modes.

## Language
- Chinese: [README](./README.md)
- English: [README_EN](./README_EN.md)

## Project Structure
Game logic: src/werewolf/; Configs: configs/; Entry scripts: start_game.py, run_battle.py

## Quick Start
pip install -e . && python start_game.py

## Source Directory
- Unified source entry: [src](./src)

## Development Status
- This repository is maintained for open-source collaboration.
- Progress is tracked via commits and issues.

## Migration Note
- Core folders have been moved to `src/werewolf` and `src/script`.
- Root `werewolf` / `script` are compatibility symlinks, so existing entry commands remain valid.
