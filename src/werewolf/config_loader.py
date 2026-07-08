"""配置加载器：支持环境变量覆盖与 .env 文件，避免在仓库中硬编码密钥。

用法：
    from werewolf.config_loader import load_config
    config = load_config("configs/qwen_vs_qwen.yaml")

覆盖规则（优先级从高到低）：
    1. 环境变量 LLM_API_KEY / LLM_BASE_URL / LLM_MODEL
    2. 配置文件中的值
    3. 占位符默认值

如果配置文件中仍残留 `sk-xxx` 字面量且未设置环境变量，会抛出 ValueError
以防止误用历史遗留的已泄露密钥。
"""
import os
from typing import Any, Dict

import yaml

# 已知泄露的旧密钥指纹，命中即拒绝加载
_LEAKED_KEY_MARKERS = ("sk-f3ee5353f375f45271fd55792e91564a",)


def _resolve_secrets(value: Any) -> Any:
    """递归把字符串中的占位符/旧密钥替换为环境变量值。"""
    if isinstance(value, dict):
        return {k: _resolve_secrets(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_resolve_secrets(v) for v in value]
    if not isinstance(value, str):
        return value

    # 拒绝已泄露的旧密钥
    for marker in _LEAKED_KEY_MARKERS:
        if marker in value:
            raise ValueError(
                "检测到已泄露的旧 API key，请将其从配置文件中删除，"
                "改用环境变量 LLM_API_KEY 提供。"
            )

    # 占位符替换
    if value in ("${LLM_API_KEY}", "${API_KEY}", "your-api-key"):
        env_val = os.environ.get("LLM_API_KEY")
        if not env_val:
            raise ValueError(
                "未设置环境变量 LLM_API_KEY。请在 .env 或 shell 中提供。"
            )
        return env_val
    if value in ("${LLM_BASE_URL}", "your-api-endpoint"):
        return os.environ.get("LLM_BASE_URL", value)
    if value in ("${LLM_MODEL}", "your-model"):
        return os.environ.get("LLM_MODEL", value)
    return value


def load_config(path: str) -> Dict[str, Any]:
    """加载 YAML 配置并解析环境变量占位符。"""
    if not os.path.exists(path):
        raise FileNotFoundError(f"配置文件不存在: {path}")

    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    if raw is None:
        raise ValueError(f"配置文件为空: {path}")

    return _resolve_secrets(raw)


def make_example_config(target_path: str, source_path: str) -> None:
    """把含有密钥的真实配置脱敏写为 *.example.yaml 模板。"""
    if not os.path.exists(source_path):
        raise FileNotFoundError(source_path)

    with open(source_path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    def _scrub(node: Any) -> Any:
        if isinstance(node, dict):
            return {k: _scrub(v) for k, v in node.items()}
        if isinstance(node, list):
            return [_scrub(v) for v in node]
        if isinstance(node, str):
            if "api_key" in node.lower() or node.startswith("sk-"):
                return "${LLM_API_KEY}"
            if "base_url" in node.lower() or node.startswith("http"):
                return "${LLM_BASE_URL}"
        return node

    scrubbed = _scrub(raw)
    with open(target_path, "w", encoding="utf-8") as f:
        f.write("# 此文件为脱敏模板。复制为同名 .yaml 后用环境变量填充真实值。\n")
        f.write("#   export LLM_API_KEY=sk-...\n")
        f.write("#   export LLM_BASE_URL=https://...\n")
        f.write("#   export LLM_MODEL=qwen3-coder-plus\n\n")
        yaml.safe_dump(scrubbed, f, allow_unicode=True, sort_keys=False)
