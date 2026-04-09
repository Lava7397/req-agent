"""PRD generation pipeline — multi-step agent workflow."""

from __future__ import annotations
import sys
from pathlib import Path
from datetime import datetime

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from req_agent.models import (
    PRDContext, RequirementBrief, UserAnalysis, FunctionalSpec, NonFunctionalSpec,
)
from req_agent.llm import LLMClient
from req_agent import prompts

console = Console()


INTERACTIVE_QUESTIONS = [
    ("What is the primary platform?", "Web app / Mobile / CLI / API / Desktop"),
    ("Who is the target market?", "B2B / B2C / Internal tool / Open source"),
    ("What's the expected scale?", "Small (<100 users) / Medium (<10K) / Large (100K+)"),
    ("Any hard tech constraints?", "Must use specific stack / cloud / budget limits"),
    ("Timeline expectation?", "MVP in 1 month / 3 months / 6+ months"),
]


class Pipeline:
    """Orchestrates the 4-step PRD generation."""

    def __init__(self, model: str | None = None, temperature: float = 0.3):
        self.llm = LLMClient(model=model, temperature=temperature)
        self.ctx: PRDContext | None = None

    def interactive_qa(self) -> dict[str, str]:
        """Ask clarifying questions before starting."""
        console.print("\n[bold cyan]Let me ask a few clarifying questions:[/bold cyan]\n")
        answers = {}
        for question, hint in INTERACTIVE_QUESTIONS:
            console.print(f"  [yellow]?[/yellow] {question} [dim]({hint})[/dim]")
            answer = input("  > ").strip()
            if answer:
                answers[question] = answer
            console.print()
        return answers

    def run(self, requirement: str, interactive: bool = False, depth: str = "standard") -> str:
        """Run full pipeline, returns final PRD markdown."""
        self.ctx = PRDContext(original_input=requirement)

        if interactive:
            self.ctx.interactive_answers = self.interactive_qa()

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            # Step 1: Requirement Brief
            task = progress.add_task("Step 1/4: Expanding requirement...", total=None)
            self._step1_brief()
            progress.update(task, description="[green]Step 1/4: Brief complete ✓")

            # Step 2: User Analysis
            task = progress.add_task("Step 2/4: Analyzing users...", total=None)
            self._step2_users()
            progress.update(task, description="[green]Step 2/4: Users complete ✓")

            # Step 3: Functional Requirements
            task = progress.add_task("Step 3/4: Defining functions...", total=None)
            self._step3_functional()
            progress.update(task, description="[green]Step 3/4: Functions complete ✓")

            # Step 4: Non-functional + Risks + Milestones
            task = progress.add_task("Step 4/4: Finalizing spec...", total=None)
            self._step4_nonfunctional()
            progress.update(task, description="[green]Step 4/4: Spec complete ✓")

        # Render PRD
        prd = self._render()
        return prd

    def run_interactive_step(self, requirement: str, step: int) -> str:
        """Run a single step and return intermediate result for review.
        Returns JSON string of the step output."""
        if not self.ctx:
            self.ctx = PRDContext(original_input=requirement)

        step_map = {
            1: (self._step1_brief, lambda: self.ctx.brief.model_dump_json(indent=2)),
            2: (self._step2_users, lambda: self.ctx.user_analysis.model_dump_json(indent=2)),
            3: (self._step3_functional, lambda: self.ctx.functional.model_dump_json(indent=2)),
            4: (self._step4_nonfunctional, lambda: self.ctx.nonfunctional.model_dump_json(indent=2)),
        }
        if step not in step_map:
            raise ValueError(f"Invalid step {step}. Must be 1-4.")

        step_fn, getter = step_map[step]
        step_fn()
        return getter()

    def _step1_brief(self):
        self.ctx.brief = self.llm.complete(
            system=prompts.SYSTEM_PROMPT,
            user=prompts.step1_prompt(self.ctx),
            response_format=RequirementBrief,
        )

    def _step2_users(self):
        self.ctx.user_analysis = self.llm.complete(
            system=prompts.SYSTEM_PROMPT,
            user=prompts.step2_prompt(self.ctx),
            response_format=UserAnalysis,
        )

    def _step3_functional(self):
        self.ctx.functional = self.llm.complete(
            system=prompts.SYSTEM_PROMPT,
            user=prompts.step3_prompt(self.ctx),
            response_format=FunctionalSpec,
        )

    def _step4_nonfunctional(self):
        self.ctx.nonfunctional = self.llm.complete(
            system=prompts.SYSTEM_PROMPT,
            user=prompts.step4_prompt(self.ctx),
            response_format=NonFunctionalSpec,
        )

    def _render(self) -> str:
        from jinja2 import Environment, FileSystemLoader
        template_dir = Path(__file__).parent / "templates"
        env = Environment(loader=FileSystemLoader(str(template_dir)), keep_trailing_newline=True)
        template = env.get_template("prd.md.j2")

        return template.render(
            brief=self.ctx.brief,
            user_analysis=self.ctx.user_analysis,
            functional=self.ctx.functional,
            nonfunctional=self.ctx.nonfunctional,
            original_input=self.ctx.original_input,
            interactive_answers=self.ctx.interactive_answers,
            date=datetime.now().strftime("%Y-%m-%d %H:%M"),
        )
