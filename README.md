# req-agent

一句话需求 → 完整 PRD 文档的 AI Agent。

## 功能

- **一句话输入**: 描述你的产品想法，自动生成完整 PRD
- **引导式生成**: 逐步确认，每步可重试，随时调整
- **4 步 Pipeline**: 需求扩展 → 用户分析 → 功能需求 → 非功能需求/里程碑/风险
- **多 LLM 后端**: OpenRouter / OpenAI / Anthropic / Ollama
- **模型自动降级**: 主模型失败时自动切换备用模型
- **中文输出**: 默认生成中文 PRD
- **Markdown 输出**: 可直接导入 Notion / 飞书 / Obsidian

## 安装

```bash
# 推荐：pipx（隔离环境）
pipx install req-agent

# 或者：pip
python3 -m pip install req-agent

# 如果没有 pip
python3 -m ensurepip --upgrade
```

## 更新

```bash
python3 -m pip install -U req-agent
```

## 首次配置

```bash
req-agent setup
```

支持的 Provider：
- **OpenRouter**（推荐，200+ 模型）— https://openrouter.ai/keys
- **OpenAI** — https://platform.openai.com/api-keys
- **Anthropic** — https://console.anthropic.com/
- **Ollama**（本地免费，无需 Key）

配置保存在 `~/.config/req-agent/config.env`。

## 使用

### 引导式生成（推荐）

```bash
req-agent guide
```

流程：
1. 输入你的产品想法
2. 回答 5 个澄清问题（可跳过）
3. 逐步确认需求扩展 / 用户分析 / 功能需求 / 非功能需求
4. 每步可输入 `ok` 确认或 `retry` 重新生成
5. 选择保存路径，生成最终 PRD

### 快速生成

```bash
# 基本用法
req-agent generate "做一个帮助程序员管理代码片段的 CLI 工具"

# 输出到文件
req-agent generate "AI 驱动的食谱推荐 App" -o prd.md

# 指定模型
req-agent generate "内部 HR 管理系统" -m openrouter/qwen/qwen3-coder

# 指定温度
req-agent generate "健身打卡 App" -t 0.5 -o fitness-prd.md
```

### 单步调试

```bash
# 只运行某一步查看效果
req-agent step "智能记账 App" 1
```

步骤说明：
- `1` — 需求扩展（产品名/问题/用户/范围/KPI）
- `2` — 用户分析（画像 + User Stories + 验收标准）
- `3` — 功能需求（模块 + 需求清单 + 数据模型 + API）
- `4` — 非功能需求 + 里程碑 + 风险

## PRD 输出结构

```
1. Product Overview     — 问题 / 用户 / 价值 / 成功指标
2. Scope               — 范围边界（In / Out）
3. User Analysis       — 用户画像 + User Stories + 验收标准
4. Functional Req      — 功能模块 + 数据模型 + API 概览
5. Non-Functional Req  — 性能 / 安全 / 可用性
6. Milestones          — 阶段规划
7. Risk Analysis       — 风险矩阵 + 应对策略
8. Tech Recommendations — 技术栈建议
```

## 配置

配置文件：`~/.config/req-agent/config.env`

| 变量 | 说明 |
|------|------|
| `DEFAULT_MODEL` | 默认模型 |
| `OPENROUTER_API_KEY` | OpenRouter key |
| `OPENAI_API_KEY` | OpenAI key |
| `ANTHROPIC_API_KEY` | Anthropic key |
| `OLLAMA_BASE_URL` | Ollama 地址 |

## 架构

```
src/req_agent/
├── cli.py          # CLI 入口（generate / guide / step / setup）
├── llm.py          # LLM 客户端（HTTP 直连 + 自动降级）
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
