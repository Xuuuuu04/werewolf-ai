"""registry 注册机制测试。"""
import pytest

from werewolf.agents import agent_registry
from werewolf.agents.base_agent import Agent, RandomAgent


def test_registry_has_entries():
    """初始化时应有内置 agent 类型注册。"""
    assert len(agent_registry.entries) > 0


def test_registry_register_decorator():
    """自定义类型可通过 @register 注册。"""

    @agent_registry.register(["custom-fixture-type"])
    class _FixtureAgent(Agent):
        def act(self, observation):
            return None

    assert "custom-fixture-type" in agent_registry.entries


def test_registry_build_unknown_type_raises():
    """未知类型应抛 ValueError。"""
    with pytest.raises(ValueError):
        agent_registry.build("totally-nonexistent-model-type-xyz")


def test_known_agent_types_registered():
    """gpt/qwen/human 等内置类型应注册。"""
    entries = agent_registry.entries
    assert "gpt" in entries
    assert "qwen" in entries
    assert "human" in entries


def test_registry_entries_are_subclasses_of_agent():
    """所有注册类应是 Agent 的子类。"""
    for cls in agent_registry.entries.values():
        assert issubclass(cls, Agent)
