# req-agent

一句话需求 → 完整 PRD 文档的 AI Agent。

## 功能

- **一句话输入**: 描述你的产品想法即可
- **4 步 Pipeline**: 需求扩展 → 用户分析 → 功能需求 → 非功能需求/里程碑/风险
- **多 LLM 后端**: 支持 OpenAI / Claude / OpenRouter / Ollama（LiteLLM）
- **交互模式**: 可选回答澄清问题，提升输出质量
- **标准 PRD 输出**: Markdown 格式，可直接导入 Notion/飞书/Obsidian

## 安装

```bash
# 推荐：pipx（隔离环境，不污染系统 Python）
pipx install req-agent

# 或者：pip
python3 -m pip install req-agent

# 如果没有 pip
python3 -m ensurepip --upgrade
```

## 首次配置

```bash
# 交互式配置 API Key（只需一次）
req-agent setup
```

支持的 Provider：
- **OpenRouter**（推荐，200+ 模型）— https://openrouter.ai/keys
- **OpenAI** — https://platform.openai.com/api-keys
- **Anthropic** — https://console.anthropic.com/
- **Ollama**（本地免费，无需 Key）

配置保存在 `~/.config/req-agent/config.env`，可随时重新运行 `req-agent setup` 修改。

## 使用

### 快速生成

```bash
# 基本用法
req-agent "做一个帮助程序员管理代码片段的工具"

# 指定输出文件
req-agent "AI 驱动的食谱推荐 App" -o prd.md

# 指定模型
req-agent "内部 HR 管理系统" --model openrouter/anthropic/claude-sonnet-4

# 交互模式（先回答澄清问题）
req-agent "健身打卡社交应用" -i -o fitness-prd.md
```

### 交互式 CLI

```bash
req-agent interactive
# 按提示输入需求和回答问题
```

### 单步调试

```bash
# 只运行 Step 1 看需求扩展结果
req-agent step "智能记账 App" 1
```

## PRD 输出结构

```
1. Product Overview     — 问题/用户/价值/成功指标
2. Scope               — 范围边界
3. User Analysis       — 用户画像 + User Stories + 验收标准
4. Functional Req      — 功能模块 + 数据模型 + API
5. Non-Functional Req  — 性能/安全/可用性
6. Milestones          — 阶段规划
7. Risk Analysis       — 风险矩阵
8. Tech Recommendations — 技术建议
```

## 配置

环境变量（.env 文件）：

| 变量 | 说明 |
|------|------|
| `DEFAULT_MODEL` | 默认模型（LiteLLM 格式） |
| `OPENAI_API_KEY` | OpenAI key |
| `ANTHROPIC_API_KEY` | Anthropic key |
| `OPENROUTER_API_KEY` | OpenRouter key |
| `OLLAMA_BASE_URL` | Ollama 地址（默认 localhost:11434） |

## 架构

```
src/req_agent/
├── cli.py          # Typer CLI 入口
├── llm.py          # LiteLLM 封装（多 Provider）
├── pipeline.py     # 4 步 Pipeline 编排
├── models.py       # Pydantic 数据模型
├── prompts.py      # 各步骤 Prompt
└── templates/
    └── prd.md.j2   # Jinja2 PRD 模板
```

## 自定义

### 修改 Prompt

编辑 `src/req_agent/prompts.py` 中的各 step 函数。

### 修改 PRD 格式

编辑 `src/req_agent/templates/prd.md.j2`。

### 添加新步骤

1. 在 `models.py` 添加数据模型
2. 在 `prompts.py` 添加 prompt
3. 在 `pipeline.py` 添加 step 方法
4. 更新模板
