# 🐺 AI狼人杀游戏 | Werewolf AI Game

<div align="center">

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Game](https://img.shields.io/badge/Game-Werewolf-red.svg)](https://en.wikipedia.org/wiki/Mafia_(party_game))

一个基于大语言模型的智能狼人杀游戏，支持AI vs AI和人类 vs AI对战模式

[功能特点](#-功能特点) • [快速开始](#-快速开始) • [游戏说明](#-游戏说明) • [配置](#-配置) • [开发](#-开发)

</div>

---

## ✨ 功能特点

- 🤖 **AI对战**：支持各种OpenAI API格式的大语言模型（GPT、Qwen等）
- 👤 **人机对战**：人类玩家可以与AI进行对战
- 🎭 **完整规则**：实现了狼人杀的完整游戏逻辑和角色体系
- 🌐 **中文界面**：全中文化的游戏界面和提示信息
- 📊 **游戏记录**：自动记录游戏日志，支持可视化回放
- 🎮 **简单易用**：交互式启动器，一键开始游戏

## 📦 安装

### 环境要求

- Python 3.10+
- pip 包管理器

### 安装步骤

1. 克隆项目

```bash
git clone git@gitcode.com:mumu_xsy/werewolf_ai.git
cd werewolf_ai
```

2. 安装依赖

```bash
pip install -e .
```

或手动安装：

```bash
pip install gymnasium openai transformers tenacity pyyaml torch tiktoken
```

## 🚀 快速开始

### 使用启动器（推荐）

```bash
python start_game.py
```

启动后会看到游戏菜单，选择你想要的游戏模式即可开始！

### 命令行启动

```bash
# AI vs AI 模式
python run_battle.py --config configs/qwen_vs_qwen.yaml --log_save_path ./logs/game_1

# 人类 vs AI 模式
python run_battle.py --config configs/human_vs_qwen.yaml --log_save_path ./logs/game_2
```

## 🎮 游戏说明

### 游戏规则

**狼人杀**是一款多人策略游戏，玩家分为两个阵营：

- **🐺 狼人阵营**：每晚猎杀一名村民，目标是杀死所有村民
- **👥 村民阵营**：通过投票驱逐狼人，目标是找出所有狼人

### 角色说明

#### 村民阵营
- **🔮 预言家（Seer）**：每晚可以查验一名玩家的身份
- **🧪 女巫（Witch）**：拥有一瓶解药和一瓶毒药
  - 解药：可以救活被狼人杀死的玩家
  - 毒药：可以毒杀一名玩家
- **🛡️ 守卫（Guard）**：每晚守护一名玩家，防止其被狼人杀死
- **🔫 猎人（Hunter）**：被投票出局或被杀死时可以开枪带走一名玩家
- **👤 平民（Villager）**：没有特殊能力，通过投票和发言帮助村民获胜

#### 狼人阵营
- **🐺 狼人（Werewolf）**：每晚集体选择猎杀一名村民

### 游戏流程

1. **🌙 夜晚阶段**
   - 狼人选择猎杀目标
   - 预言家查验身份
   - 守卫守护玩家
   - 女巫使用药品

2. **☀️ 白天阶段**
   - 公布夜晚死亡信息
   - 玩家依次发言讨论
   - 投票放逐可疑玩家
   - 如有平票，进入PK环节

3. **🏆 胜利条件**
   - 狼人获胜：狼人数量 ≥ 好人数量
   - 村民获胜：所有狼人被淘汰

### 人类玩家操作指南

#### 发言阶段
直接输入你的发言内容，可以：
- 分享你的身份信息
- 分析当前局势
- 提出投票建议
- 质疑其他玩家

#### 动作阶段
系统会显示可选动作列表：

```
📋 可选动作列表：
============================================================
  [0] {'杀害':'否'}
  [1] {'杀害':'1'}
  [2] {'杀害':'2'}
  ...
============================================================
```

**两种输入方式**：
1. **输入索引号**（推荐）：直接输入 `1` 选择第1个动作
2. **输入完整字符串**：输入 `{'杀害':'1'}`

## ⚙️ 配置

### 配置文件

项目使用YAML格式的配置文件，位于 `configs/` 目录：

- `qwen_vs_qwen.yaml` - AI自我对战（Qwen模型）
- `qwen_vs_gpt.yaml` - Qwen vs GPT对战
- `human_vs_qwen.yaml` - 人类 vs AI对战

### 配置说明

```yaml
# 游戏环境配置
env_config:
    n_player: 9        # 玩家数量
    n_role: 5          # 角色种类
    n_werewolf: 3      # 狼人数量
    n_seer: 1          # 预言家数量
    n_guard: 1         # 守卫数量
    n_witch: 1         # 女巫数量
    n_villager: 3      # 平民数量
    n_hunter: 0        # 猎人数量

# AI模型配置
agent_config:
    werewolf:          # 狼人阵营使用的模型
        model_type: qwen3-coder-plus
        model_params:
            llm: qwen3-coder-plus
            temperature: 0.7
            base_url: https://your-api-endpoint/v1/chat/completions
            api_key: your-api-key
    villager:          # 村民阵营使用的模型
        model_type: qwen3-coder-plus
        model_params:
            llm: qwen3-coder-plus
            temperature: 0.7
            base_url: https://your-api-endpoint/v1/chat/completions
            api_key: your-api-key
```

### 支持的AI模型

项目支持所有兼容OpenAI API格式的模型：
- OpenAI GPT系列（GPT-4, GPT-3.5等）
- 通义千问（Qwen）系列
- 其他OpenAI兼容的API

## 📂 项目结构

```
werewolf_ai/
├── configs/              # 游戏配置文件
│   ├── qwen_vs_qwen.yaml
│   ├── qwen_vs_gpt.yaml
│   └── human_vs_qwen.yaml
├── werewolf/            # 核心游戏逻辑
│   ├── agents/          # AI智能体
│   │   ├── base_agent.py
│   │   ├── gpt_agent.py        # GPT/Qwen等模型智能体
│   │   ├── human_agent.py      # 人类玩家智能体
│   │   ├── llm_agent.py
│   │   └── prompt_template_v0.py
│   ├── envs/            # 游戏环境
│   │   └── werewolf_text_env_v0.py
│   ├── helper/          # 辅助工具
│   │   ├── log_utils.py
│   │   └── utils.py
│   └── registry.py      # 智能体注册中心
├── script/              # 实用脚本
│   ├── game_visualizer.py      # 游戏可视化工具
│   └── stats_winning.py        # 胜率统计
├── start_game.py        # 游戏启动器
├── run_battle.py        # 游戏运行主程序
├── setup.py             # 安装配置
└── README.md            # 项目说明
```

## 🎯 使用示例

### 示例1：Qwen自我对战

```bash
python run_battle.py \
    --config configs/qwen_vs_qwen.yaml \
    --log_save_path ./logs/qwen_game \
    --num_games 5
```

### 示例2：人类对战AI

```bash
python run_battle.py \
    --config configs/human_vs_qwen.yaml \
    --log_save_path ./logs/human_game
```

### 示例3：使用自定义API

修改配置文件中的 `base_url` 和 `api_key`：

```yaml
agent_config:
    werewolf:
        model_params:
            base_url: https://your-custom-api.com/v1/chat/completions
            api_key: your-custom-key
```

## 📊 游戏日志

游戏日志保存在指定的目录中，包括：

- `game_log.json` - 完整游戏日志（JSON格式）
- `Player_X.jsonl` - 每个玩家的操作日志

### 查看游戏回放

```bash
python script/game_visualizer.py
```

## 🛠️ 开发

### 添加新的AI模型

1. 在 `werewolf/agents/gpt_agent.py` 中注册模型名称
2. 在 `werewolf/registry.py` 中添加模型类型检测
3. 创建对应的配置文件

### 调试技巧

- 设置环境变量查看详细日志：
  ```bash
  export LOG_LEVEL=DEBUG
  ```
- 查看API响应（已内置调试输出）
- 分析游戏日志文件

## 🤝 贡献

欢迎提交Issue和Pull Request！

## 📄 许可证

本项目采用MIT许可证 - 详见 [LICENSE](LICENSE) 文件

## 🙏 致谢

- 感谢OpenAI和通义千问团队提供优秀的大语言模型
- 感谢所有贡献者和使用者

## 📮 联系方式

如有问题或建议，请：
- 提交Issue
- 发送邮件至项目维护者

---

<div align="center">

**享受游戏，玩得开心！🎮**

Made with ❤️ by Werewolf AI Team

</div>
