"""Prompts for PRD generation pipeline."""

from req_agent.models import PRDContext

SYSTEM_PROMPT = (
    "You are a senior product manager. "
    "Transform ideas into structured product requirements. "
    "Always reply with valid JSON only, no extra text. "
    "Use Chinese for all content fields."
)


def step1_prompt(ctx: PRDContext) -> str:
    extras = ""
    if ctx.interactive_answers:
        qa = "\n".join(f"  - {q}: {a}" for q, a in ctx.interactive_answers.items())
        extras = f"\n\nAdditional context:\n{qa}"

    return f"""Analyze this product requirement and create a structured brief.

Requirement: "{ctx.original_input}"{extras}

Reply with JSON:
{{
  "product_name": "product name",
  "problem_statement": "problem description (2-3 sentences)",
  "target_users": ["user group 1", "user group 2"],
  "core_value": "value proposition (1-2 sentences)",
  "scope_in": ["item 1", "item 2", ...],
  "scope_out": ["excluded item 1", ...],
  "success_metrics": ["measurable KPI 1", ...]
}}

Rules:
- Be specific about user roles
- Keep scope realistic for MVP
- Make success metrics measurable
- All content in Chinese"""


def step2_prompt(ctx: PRDContext) -> str:
    brief = ctx.brief
    return f"""Create user analysis for this product.

Product: {brief.product_name}
Problem: {brief.problem_statement}
Users: {brief.target_users}
Value: {brief.core_value}
Scope: {brief.scope_in}

Reply with JSON:
{{
  "personas": [
    {{
      "name": "name",
      "role": "role",
      "goals": ["goal 1", "goal 2"],
      "pain_points": ["pain 1", "pain 2"]
    }}
  ],
  "user_stories": [
    {{
      "id": "US-001",
      "title": "title",
      "as_a": "user type",
      "i_want": "action",
      "so_that": "benefit",
      "acceptance_criteria": ["criterion 1", ...],
      "priority": "P0"
    }}
  ],
  "key_scenarios": ["scenario 1", ...]
}}

Rules:
- 2-3 distinct personas
- 8-15 user stories covering all scope items
- Each story needs 2+ acceptance criteria
- P0=must have, P1=important, P2=nice to have
- All content in Chinese"""


def step3_prompt(ctx: PRDContext) -> str:
    brief = ctx.brief
    ua = ctx.user_analysis
    stories_text = "\n".join(
        f"  [{s.id}] ({s.priority}) {s.title}"
        for s in ua.user_stories
    )
    return f"""Define functional requirements.

Product: {brief.product_name}
User Stories:
{stories_text}

Reply with JSON:
{{
  "modules": ["module 1", "module 2", ...],
  "requirements": [
    {{
      "id": "FR-001",
      "title": "title",
      "description": "description",
      "user_stories": ["US-001"],
      "acceptance_criteria": ["criterion 1", ...],
      "priority": "P0"
    }}
  ],
  "data_entities": ["Entity1 (fields)", ...],
  "api_overview": ["GET /endpoint - description", ...]
}}

Rules:
- Group into logical modules
- Map to user stories
- 10-20 requirements typically
- All content in Chinese"""


def step4_prompt(ctx: PRDContext) -> str:
    brief = ctx.brief
    return f"""Define non-functional requirements, milestones, and risks.

Product: {brief.product_name}
Scope: {brief.scope_in}

Reply with JSON:
{{
  "nfr": [
    {{
      "category": "performance|security|usability|reliability",
      "requirement": "what is required",
      "target": "measurable target"
    }}
  ],
  "milestones": [
    {{
      "name": "milestone name",
      "duration": "e.g., 2 weeks",
      "deliverables": ["deliverable 1", ...],
      "dependencies": []
    }}
  ],
  "risks": [
    {{
      "description": "risk",
      "impact": "high|medium|low",
      "probability": "high|medium|low",
      "mitigation": "strategy"
    }}
  ],
  "tech_recommendations": ["recommendation 1", ...]
}}

Rules:
- Cover performance, security, usability
- 3-5 milestones for MVP
- 4-8 risks
- All content in Chinese"""
