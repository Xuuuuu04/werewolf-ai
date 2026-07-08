"""config_loader 安全机制测试。

确保已泄露的旧 API key 无法被加载，占位符能从环境变量解析。
"""
import os
import tempfile

import pytest

from werewolf.config_loader import load_config, _resolve_secrets, make_example_config


def test_leaked_key_rejected(tmp_path):
    """残留旧密钥时应抛 ValueError。"""
    cfg_path = tmp_path / "bad.yaml"
    cfg_path.write_text(
        "agent_config:\n  werewolf:\n    model_params:\n      api_key: 'sk-f3ee5353f375f45271fd55792e91564a'\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="已泄露"):
        load_config(str(cfg_path))


def test_placeholder_resolved_from_env(monkeypatch):
    """${LLM_API_KEY} 占位符能从环境变量解析。"""
    monkeypatch.setenv("LLM_API_KEY", "sk-test-secret-12345")
    resolved = _resolve_secrets("${LLM_API_KEY}")
    assert resolved == "sk-test-secret-12345"


def test_placeholder_without_env_raises(monkeypatch):
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    with pytest.raises(ValueError, match="未设置环境变量"):
        _resolve_secrets("${LLM_API_KEY}")


def test_plain_value_passthrough():
    assert _resolve_secrets("qwen3-coder-plus") == "qwen3-coder-plus"
    assert _resolve_secrets(42) == 42
    assert _resolve_secrets(None) is None


def test_nested_dict_resolution(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "sk-test")
    cfg = {
        "agent_config": {
            "werewolf": {
                "model_params": {
                    "api_key": "${LLM_API_KEY}",
                    "llm": "qwen3",
                }
            }
        }
    }
    resolved = _resolve_secrets(cfg)
    assert resolved["agent_config"]["werewolf"]["model_params"]["api_key"] == "sk-test"


def test_make_example_config_scrubs_keys(tmp_path):
    """make_example_config 应把密钥替换为占位符。"""
    src = tmp_path / "src.yaml"
    src.write_text(
        "agent_config:\n  werewolf:\n    model_params:\n      api_key: 'sk-real-secret-abc'\n",
        encoding="utf-8",
    )
    target = tmp_path / "out.example.yaml"
    make_example_config(str(target), str(src))

    text = target.read_text(encoding="utf-8")
    assert "sk-real-secret-abc" not in text
    assert "${LLM_API_KEY}" in text
