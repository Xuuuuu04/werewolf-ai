# Project Structure

Updated: 2026-02-07

## Top-level Layout
```text
.
- .gitignore
- BUG_FIXES.md
- DEBUG_MODE_GUIDE.md
- HUMAN_PLAYER_MODE.md
- INTERFACE_OPTIMIZATION.md
- INTERFACE_UPGRADE.md
- LICENSE
- README.md
- README_EN.md
- REFACTOR_SUMMARY.md
- config.yaml
- configs
- docs
- requirements.txt
- run_battle.py
- script
- setup.py
- src
- start_game.py
- werewolf
- 游戏启动说明.md
```

## Conventions
- Keep executable/business code under src/ as the long-term target.
- Keep docs under docs/ (or doc/ for Cangjie projects).
- Keep local runtime artifacts and secrets out of version control.
