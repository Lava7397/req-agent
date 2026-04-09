"""CLI entry point for req-agent."""

from __future__ import annotations
import os
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

from req_agent.pipeline import Pipeline

app = typer.Typer(
    name="req-agent",
    help="Turn one sentence into a full PRD document.",
    no_args_is_help=True,
)
console = Console()

CONFIG_DIR = Path.home() / ".config" / "req-agent"
CONFIG_FILE = CONFIG_DIR / "config.env"


def _load_config():
    """Load user config if exists."""
    if CONFIG_FILE.exists():
        from dotenv import dotenv_values
        for k, v in dotenv_values(str(CONFIG_FILE)).items():
            if v and k not in os.environ:
                os.environ[k] = v


def _ensure_api_key() -> bool:
    """Check if any LLM API key is configured."""
    keys = ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "OPENROUTER_API_KEY"]
    has_key = any(os.getenv(k) for k in keys)
    has_ollama = os.getenv("OLLAMA_BASE_URL")
    return has_key or has_ollama


@app.command("setup")
def setup():
    """Interactive setup — configure your API key and default model."""
    console.print(Panel(
        "[bold]req-agent Setup[/bold]\n"
        "Configure your LLM provider.\n\n"
        "Supported providers:\n"
        "  [cyan]1.[/cyan] OpenRouter (200+ models, recommended)\n"
        "  [cyan]2.[/cyan] OpenAI\n"
        "  [cyan]3.[/cyan] Anthropic\n"
        "  [cyan]4.[/cyan] Ollama (local, free)",
        border_style="cyan",
    ))

    choice = console.input("[yellow]Choose provider (1-4):[/yellow] ").strip()

    provider_map = {
        "1": ("OpenRouter", "OPENROUTER_API_KEY", "openrouter/anthropic/claude-sonnet-4", "https://openrouter.ai/keys"),
        "2": ("OpenAI", "OPENAI_API_KEY", "gpt-4o", "https://platform.openai.com/api-keys"),
        "3": ("Anthropic", "ANTHROPIC_API_KEY", "claude-sonnet-4-20250514", "https://console.anthropic.com/"),
        "4": ("Ollama", None, "ollama/llama3", None),
    }

    if choice not in provider_map:
        console.print("[red]Invalid choice[/red]")
        raise typer.Exit(1)

    name, key_name, default_model, url = provider_map[choice]

    config_lines = [f"DEFAULT_MODEL={default_model}"]

    if key_name:
        console.print(f"\n[dim]Get your API key at: {url}[/dim]")
        api_key = console.input(f"[yellow]Enter your {name} API key:[/yellow] ").strip()
        if api_key:
            config_lines.append(f"{key_name}={api_key}")
        else:
            console.print("[red]No key provided[/red]")
            raise typer.Exit(1)
    else:
        ollama_url = console.input(
            "[yellow]Ollama URL[/yellow] [dim](default: http://localhost:11434)[/dim]: "
        ).strip() or "http://localhost:11434"
        config_lines.append(f"OLLAMA_BASE_URL={ollama_url}")

    # Save config
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text("\n".join(config_lines) + "\n")
    console.print(f"\n[green]Config saved to:[/green] {CONFIG_FILE}")
    console.print("[dim]You can now run: req-agent \"your product idea\"[/dim]")


@app.callback()
def main_callback():
    """Load config before any command."""
    _load_config()


@app.command()
def generate(
    requirement: str = typer.Argument(..., help="One-sentence product requirement"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output file path"),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="LLM model (LiteLLM format)"),
    interactive: bool = typer.Option(False, "--interactive", "-i", help="Ask clarifying questions first"),
    temperature: float = typer.Option(0.3, "--temperature", "-t", help="LLM temperature (0-1)"),
):
    """Generate a full PRD from a one-sentence requirement.

    Examples:
      req-agent "build a code snippet manager for developers"
      req-agent "AI-powered recipe app" -i -o prd.md
      req-agent "internal HR tool" --model claude-sonnet-4-20250514
    """
    if not _ensure_api_key():
        console.print("[yellow]No API key found.[/yellow] Run [cyan]req-agent setup[/cyan] first.")
        raise typer.Exit(1)

    console.print(Panel(
        f"[bold]Requirement:[/bold] {requirement}\n"
        f"[bold]Model:[/bold] {model or 'default'}\n"
        f"[bold]Interactive:[/bold] {interactive}",
        title="[cyan]req-agent[/cyan]",
        border_style="cyan",
    ))

    try:
        pipeline = Pipeline(model=model, temperature=temperature)
        prd_md = pipeline.run(requirement, interactive=interactive)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    # Output
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(prd_md, encoding="utf-8")
        console.print(f"\n[green]PRD saved to:[/green] {output}")
    else:
        console.print("\n" + "=" * 60 + "\n")
        console.print(Markdown(prd_md))


@app.command("step")
def step_by_step(
    requirement: str = typer.Argument(..., help="One-sentence product requirement"),
    step: int = typer.Argument(..., help="Step number (1-4)"),
    model: Optional[str] = typer.Option(None, "--model", "-m"),
    temperature: float = typer.Option(0.3, "--temperature", "-t"),
):
    """Run a single pipeline step for review/debugging.

    Steps:
      1 - Requirement Brief
      2 - User Analysis (personas + stories)
      3 - Functional Requirements
      4 - Non-functional + Risks + Milestones
    """
    if not _ensure_api_key():
        console.print("[yellow]No API key found.[/yellow] Run [cyan]req-agent setup[/cyan] first.")
        raise typer.Exit(1)

    if step < 1 or step > 4:
        console.print("[red]Step must be 1-4[/red]")
        raise typer.Exit(1)

    try:
        pipeline = Pipeline(model=model, temperature=temperature)
        result = pipeline.run_interactive_step(requirement, step)
        console.print(Panel(result, title=f"Step {step} Output", border_style="cyan"))
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@app.command("interactive")
def interactive_mode(
    model: Optional[str] = typer.Option(None, "--model", "-m"),
    temperature: float = typer.Option(0.3, "--temperature", "-t"),
):
    """Interactive mode — enter requirement and answer clarifying questions."""
    if not _ensure_api_key():
        console.print("[yellow]No API key found.[/yellow] Run [cyan]req-agent setup[/cyan] first.")
        raise typer.Exit(1)

    console.print(Panel(
        "[bold]Interactive PRD Generator[/bold]\n"
        "Enter your product idea, answer questions, get a full PRD.",
        border_style="cyan",
    ))

    requirement = console.input("[yellow]Describe your product idea:[/yellow] ").strip()
    if not requirement:
        console.print("[red]Empty requirement[/red]")
        raise typer.Exit(1)

    output_path = console.input(
        "[yellow]Output file path[/yellow] [dim](default: prd.md)[/dim]: "
    ).strip() or "prd.md"

    try:
        pipeline = Pipeline(model=model, temperature=temperature)
        prd_md = pipeline.run(requirement, interactive=True)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(prd_md, encoding="utf-8")
    console.print(f"\n[green]PRD saved to:[/green] {path}")
    console.print(f"[dim]({len(prd_md)} chars, {prd_md.count(chr(10))} lines)[/dim]")


def main():
    app()


if __name__ == "__main__":
    main()
