"""PRD generation pipeline."""

from __future__ import annotations
from pathlib import Path
from datetime import datetime

from req_agent.models import (
    PRDContext, RequirementBrief, UserAnalysis, FunctionalSpec, NonFunctionalSpec,
)
from req_agent.llm import LLMClient
from req_agent import prompts


class Pipeline:
    """Orchestrates the 4-step PRD generation."""

    def __init__(self, model: str | None = None, temperature: float = 0.3):
        self.llm = LLMClient(model=model, temperature=temperature)
        self.ctx: PRDContext | None = None

    def run(self, requirement: str) -> str:
        """Run full pipeline, returns final PRD markdown."""
        self.ctx = PRDContext(original_input=requirement)
        self._step1()
        self._step2()
        self._step3()
        self._step4()
        return self._render()

    def run_interactive_step(self, requirement: str, step: int) -> str:
        """Run a single step, returns JSON string of the result."""
        if not self.ctx:
            self.ctx = PRDContext(original_input=requirement)

        step_map = {
            1: (self._step1, lambda: self.ctx.brief.model_dump_json(indent=2)),
            2: (self._step2, lambda: self.ctx.user_analysis.model_dump_json(indent=2)),
            3: (self._step3, lambda: self.ctx.functional.model_dump_json(indent=2)),
            4: (self._step4, lambda: self.ctx.nonfunctional.model_dump_json(indent=2)),
        }
        if step not in step_map:
            raise ValueError(f"Invalid step {step}. Must be 1-4.")

        step_fn, getter = step_map[step]
        step_fn()
        return getter()

    def _step(self, step_name: str, prompt_fn, response_type):
        """Run a single pipeline step with retry."""
        for attempt in range(5):
            try:
                result = self.llm.complete(
                    system=prompts.SYSTEM_PROMPT,
                    user=prompt_fn(),
                    response_format=response_type,
                    max_retries=3,
                )
                setattr(self.ctx, step_name, result)
                return
            except Exception as e:
                if attempt == 4:
                    raise
                continue

    def _step1(self):
        self._step("brief", lambda: prompts.step1_prompt(self.ctx), RequirementBrief)

    def _step2(self):
        self._step("user_analysis", lambda: prompts.step2_prompt(self.ctx), UserAnalysis)

    def _step3(self):
        self._step("functional", lambda: prompts.step3_prompt(self.ctx), FunctionalSpec)

    def _step4(self):
        self._step("nonfunctional", lambda: prompts.step4_prompt(self.ctx), NonFunctionalSpec)

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
