"""start_game 启动器辅助函数测试。

这些函数是交互式 CLI 的辅助逻辑，可独立测试而无需 stdin 交互。
"""
import os
import sys
from pathlib import Path
from unittest import mock

import pytest

# 让测试能导入项目根的 start_game
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import start_game


def test_get_available_configs_finds_examples():
    """应发现 4 个 .example.yaml 配置。"""
    configs = start_game.get_available_configs()
    assert len(configs) == 4
    assert configs["1"].endswith("qwen_vs_qwen.example.yaml")
    assert configs["2"].endswith("qwen_vs_gpt.example.yaml")
    assert configs["3"].endswith("human_player.example.yaml")
    assert configs["4"].endswith("human_vs_qwen.example.yaml")


def test_check_environment_passes_in_project_root(tmp_path, monkeypatch):
    """在含 configs/ + run_battle.py + src/werewolf/ 的目录应通过。"""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "configs").mkdir()
    (tmp_path / "run_battle.py").write_text("# stub")
    src_werewolf = tmp_path / "src" / "werewolf"
    src_werewolf.mkdir(parents=True)
    (src_werewolf / "registry.py").write_text("# stub")

    assert start_game.check_environment() is True


def test_check_environment_fails_without_werewolf_pkg(tmp_path, monkeypatch):
    """缺 src/werewolf 应失败。"""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "configs").mkdir()
    (tmp_path / "run_battle.py").write_text("# stub")
    # 不创建 src/werewolf

    assert start_game.check_environment() is False


def test_check_api_env_returns_true_when_set(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "sk-test")
    monkeypatch.setenv("LLM_BASE_URL", "https://test.example.com")
    assert start_game.check_api_env() is True


def test_check_api_env_returns_false_when_missing(monkeypatch, capsys):
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("LLM_BASE_URL", raising=False)
    assert start_game.check_api_env() is False
    captured = capsys.readouterr()
    assert "LLM_API_KEY" in captured.out
    assert "LLM_BASE_URL" in captured.out


def test_configure_debug_mode_returns_bool(monkeypatch):
    """模拟用户输入，验证返回布尔值且不写任何文件。"""
    # 输入 '1' 应返回 True
    monkeypatch.setattr("builtins.input", lambda *a: "1")
    assert start_game.configure_debug_mode() is True

    monkeypatch.setattr("builtins.input", lambda *a: "0")
    assert start_game.configure_debug_mode() is False


def test_run_game_builds_correct_command(monkeypatch, tmp_path):
    """验证 run_game 构建的命令行包含正确的参数，且不含 --num_games。"""
    captured_cmd = []

    class _FakeResult:
        returncode = 0

    def _fake_run(cmd, check=False):
        captured_cmd.extend(cmd)
        return _FakeResult()

    monkeypatch.setattr(start_game.subprocess, "run", _fake_run)
    monkeypatch.setattr(sys, "executable", "/usr/bin/python3")

    start_game.run_game(
        config_path="configs/qwen_vs_qwen.example.yaml",
        log_path="./logs/test",
        debug_mode=True,
    )

    assert "run_battle.py" in captured_cmd
    assert "--config" in captured_cmd
    assert "configs/qwen_vs_qwen.example.yaml" in captured_cmd
    assert "--log_save_path" in captured_cmd
    assert "./logs/test" in captured_cmd
    assert "--debug" in captured_cmd
    # 关键：不应再传不存在的 --num_games
    assert "--num_games" not in captured_cmd


def test_run_game_no_debug_flag(monkeypatch):
    """debug_mode=False 应传 --no-debug。"""
    captured_cmd = []

    class _FakeResult:
        returncode = 0

    def _fake_run(cmd, check=False):
        captured_cmd.extend(cmd)
        return _FakeResult()

    monkeypatch.setattr(start_game.subprocess, "run", _fake_run)
    monkeypatch.setattr(sys, "executable", "/usr/bin/python3")

    start_game.run_game(
        config_path="configs/qwen_vs_qwen.example.yaml",
        log_path=None,
        debug_mode=False,
    )
    assert "--no-debug" in captured_cmd
    assert "--debug" not in captured_cmd
