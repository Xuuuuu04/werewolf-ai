# Werewolf AI（AI 狼人杀）- 项目体检

最后复核：2026-02-05

## 状态
- 状态标签：active
- 定位：LLM 驱动的狼人杀模拟环境，支持 AI vs AI 与人机混合对战；配置驱动（YAML）。

## 架构速览
- 入口：
  - 交互式启动：`start_game.py`
  - 批量对战：`run_battle.py`
- 环境：`werewolf/envs/werewolf_text_env_v0.py`（基于 gymnasium 的文本环境）
- Agent：
  - `werewolf/agents/llm_agent.py`：提示词构造 + 行为生成
  - `werewolf/agents/human_agent.py`：人类玩家输入
- 模型接入：`werewolf/registry.py` 使用 OpenAI SDK，可指定 `base_url` + `api_key`（兼容 Qwen/各类 OpenAI-format 服务）
- 日志与 UI：`werewolf/helper/console_ui.py`、`werewolf/helper/log_utils.py`

## 当前实现亮点
- 配置化程度高：角色数量、模型参数、端点、debug 等均可在 YAML 控制。
- UI 体验：实时状态输出、颜色区分、可选 debug 模式。

## 风险与建议（优先级）
- `LLMAgent` 里对 response 的兼容分支较多，建议补“离线回归样例”（固定 seed + mock client）保证行为解析不回归。
- 建议把“valid action 格式”与“输出解析规则”文档化，方便换模型时快速定位失败原因。

