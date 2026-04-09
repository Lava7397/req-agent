"""CLI entry point for req-agent."""

from __future__ import annotations
import os
import json
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich.syntax import Syntax

from req_agent.pipeline import Pipeline

app = typer.Typer(
    name="req-agent",
    help="一句话需求 -> 完整 PRD 文档",
    no_args_is_help=True,
)
console = Console()

CONFIG_DIR = Path.home() / ".config" / "req-agent"
CONFIG_FILE = CONFIG_DIR / "config.env"


def _load_config():
    if CONFIG_FILE.exists():
        from dotenv import dotenv_values
        for k, v in dotenv_values(str(CONFIG_FILE)).items():
            if v and k not in os.environ:
                os.environ[k] = v


def _ensure_api_key() -> bool:
    keys = ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "OPENROUTER_API_KEY"]
    return any(os.getenv(k) for k in keys) or os.getenv("OLLAMA_BASE_URL")


def _show_step_result(title: str, data: dict):
    """Pretty-print a step result as a summary table."""
    table = Table(title=title, show_lines=True, expand=True)
    table.add_column("Field", style="cyan", width=20)
    table.add_column("Content", style="white")

    for key, value in data.items():
        if isinstance(value, list):
            display = "\n".join(f"  - {v}" if isinstance(v, str) else f"  - {json.dumps(v, ensure_ascii=False)}" for v in value)
        elif isinstance(value, dict):
            display = json.dumps(value, ensure_ascii=False, indent=2)
        else:
            display = str(value)
        table.add_row(key, display)

    console.print(table)


@app.command("setup")
def setup():
    """首次配置 - 设置 API Key 和模型"""
    console.print(Panel(
        "[bold]req-agent 首次配置[/bold]\n\n"
        "选择 LLM 提供商：\n"
        "  [cyan]1.[/cyan] OpenRouter (推荐，支持 200+ 模型)\n"
        "  [cyan]2.[/cyan] OpenAI\n"
        "  [cyan]3.[/cyan] Anthropic\n"
        "  [cyan]4.[/cyan] Ollama (本地，免费)",
        border_style="cyan",
    ))

    choice = Prompt.ask("选择", choices=["1", "2", "3", "4"], default="1")

    provider_map = {
        "1": ("OpenRouter", "OPENROUTER_API_KEY", "openrouter/qwen/qwen3-coder", "https://openrouter.ai/keys"),
        "2": ("OpenAI", "OPENAI_API_KEY", "gpt-4o", "https://platform.openai.com/api-keys"),
        "3": ("Anthropic", "ANTHROPIC_API_KEY", "claude-sonnet-4-20250514", "https://console.anthropic.com/"),
        "4": ("Ollama", None, "ollama/qwen2.5:7b", None),
    }

    name, key_name, default_model, url = provider_map[choice]
    config_lines = [f"DEFAULT_MODEL={default_model}"]

    if key_name:
        console.print(f"\n[dim]获取 Key: {url}[/dim]")
        api_key = Prompt.ask(f"输入 {name} API Key")
        if api_key:
            config_lines.append(f"{key_name}={api_key}")
        else:
            console.print("[red]未提供 Key[/red]")
            raise typer.Exit(1)
    else:
        ollama_url = Prompt.ask("Ollama 地址", default="http://localhost:11434")
        config_lines.append(f"OLLAMA_BASE_URL={ollama_url}")

    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text("\n".join(config_lines) + "\n")
    console.print(f"\n[green]配置已保存:[/green] {CONFIG_FILE}")


@app.callback()
def main_callback():
    _load_config()


@app.command()
def generate(
    requirement: str = typer.Argument(..., help="一句话产品需求"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="输出文件路径"),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="指定模型"),
    temperature: float = typer.Option(0.3, "--temperature", "-t", help="温度 (0-1)"),
):
    """快速生成 PRD（一句话 -> 完整文档）

    示例:
      req-agent generate "代码片段管理 CLI 工具"
      req-agent generate "AI 菜谱推荐 App" -o prd.md
    """
    if not _ensure_api_key():
        console.print("[yellow]未检测到 API Key[/yellow] 运行 [cyan]req-agent setup[/cyan] 配置")
        raise typer.Exit(1)

    console.print(Panel(f"[bold]需求:[/bold] {requirement}", title="[cyan]req-agent[/cyan]", border_style="cyan"))

    try:
        pipeline = Pipeline(model=model, temperature=temperature)
        prd_md = pipeline.run(requirement)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(prd_md, encoding="utf-8")
        console.print(f"\n[green]PRD 已保存:[/green] {output}")
    else:
        console.print(Markdown(prd_md))


@app.command()
def guide(
    model: Optional[str] = typer.Option(None, "--model", "-m", help="指定模型"),
    temperature: float = typer.Option(0.3, "--temperature", "-t", help="温度 (0-1)"),
):
    """引导式 PRD 生成 - 逐步确认，可随时调整

    流程:
      1. 输入你的产品想法
      2. 回答 5 个澄清问题
      3. 确认/修改需求扩展
      4. 确认/修改用户分析
      5. 确认/修改功能需求
      6. 确认/修改非功能需求
      7. 生成最终 PRD
    """
    if not _ensure_api_key():
        console.print("[yellow]未检测到 API Key[/yellow] 运行 [cyan]req-agent setup[/cyan] 配置")
        raise typer.Exit(1)

    console.print(Panel(
        "[bold]req-agent 引导式 PRD 生成[/bold]\n\n"
        "我会逐步帮你生成 PRD，每一步你都可以确认或修改。\n"
        "输入 [cyan]ok[/cyan] 确认，或直接输入修改意见。",
        border_style="cyan",
    ))

    # Step 0: 输入需求
    requirement = Prompt.ask("\n[bold yellow]一句话描述你的产品想法[/bold yellow]")
    if not requirement:
        console.print("[red]需求不能为空[/red]")
        raise typer.Exit(1)

    # Step 0.5: 澄清问题
    console.print("\n[bold]回答几个问题帮助我更好理解（可跳过）：[/bold]")
    answers = {}
    questions = [
        ("目标平台", "Web / App / CLI / API"),
        ("目标用户", "B2B / B2C / 内部工具"),
        ("预期规模", "小型 (<100) / 中型 (<1万) / 大型 (10万+)"),
        ("技术限制", "特定技术栈 / 预算限制 / 无"),
        ("预期周期", "1 个月 / 3 个月 / 半年+"),
    ]
    for q, hint in questions:
        ans = Prompt.ask(f"  [yellow]{q}[/yellow] [dim]({hint})[/dim]", default="")
        if ans:
            answers[q] = ans

    pipeline = Pipeline(model=model, temperature=temperature)
    from req_agent.models import PRDContext
    pipeline.ctx = PRDContext(original_input=requirement, interactive_answers=answers)

    steps = [
        ("需求扩展", "brief", 1),
        ("用户分析", "user_analysis", 2),
        ("功能需求", "functional", 3),
        ("非功能需求 + 里程碑 + 风险", "nonfunctional", 4),
    ]

    for step_title, attr, step_num in steps:
        while True:
            console.print(f"\n[bold cyan]━━━ Step {step_num}/4: {step_title} ━━━[/bold cyan]")
            console.print("[dim]正在生成...[/dim]")

            try:
                pipeline.run_interactive_step(requirement, step_num)
                data = getattr(pipeline.ctx, attr)
                _show_step_result(step_title, data.model_dump())
            except Exception as e:
                console.print(f"[red]生成失败:[/red] {e}")
                raise typer.Exit(1)

            action = Prompt.ask(
                "\n[bold]确认？[/bold]",
                choices=["ok", "retry", "quit"],
                default="ok",
            )

            if action == "ok":
                break
            elif action == "retry":
                console.print("[dim]重新生成...[/dim]")
                continue
            elif action == "quit":
                console.print("[yellow]已取消[/yellow]")
                raise typer.Exit(0)

    # 生成最终 PRD
    console.print("\n[bold cyan]━━━ 生成最终 PRD ━━━[/bold cyan]")
    prd_md = pipeline._render()

    # 输出
    default_name = f"{pipeline.ctx.brief.product_name.replace(' ', '-')}-PRD.md"
    output_path = Prompt.ask(
        f"[bold]保存路径[/bold]",
        default=default_name,
    )

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(prd_md, encoding="utf-8")

    console.print(f"\n[green]PRD 已保存:[/green] {path}")
    console.print(f"[dim]{len(prd_md)} 字符, {prd_md.count(chr(10))} 行[/dim]")

    # 询问是否打开预览
    if Confirm.ask("打开预览？", default=True):
        console.print(Markdown(prd_md[:3000] + "\n\n... (已截断，查看完整文件)"))


@app.command("step")
def step_by_step(
    requirement: str = typer.Argument(..., help="一句话产品需求"),
    step: int = typer.Argument(..., help="步骤号 (1-4)"),
    model: Optional[str] = typer.Option(None, "--model", "-m"),
    temperature: float = typer.Option(0.3, "--temperature", "-t"),
):
    """单步调试 - 运行单个步骤查看效果

    步骤:
      1 - 需求扩展
      2 - 用户分析 (画像 + 用户故事)
      3 - 功能需求
      4 - 非功能需求 + 里程碑 + 风险
    """
    if not _ensure_api_key():
        console.print("[yellow]未检测到 API Key[/yellow] 运行 [cyan]req-agent setup[/cyan] 配置")
        raise typer.Exit(1)

    if step < 1 or step > 4:
        console.print("[red]步骤号必须是 1-4[/red]")
        raise typer.Exit(1)

    try:
        pipeline = Pipeline(model=model, temperature=temperature)
        result = pipeline.run_interactive_step(requirement, step)
        _show_step_result(f"Step {step}", json.loads(result))
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


def main():
    app()


if __name__ == "__main__":
    main()
