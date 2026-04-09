"""System and step prompts for PRD generation pipeline."""

from req_agent.models import PRDContext

SYSTEM_PROMPT = """You are an expert Product Manager. You transform vague ideas into precise,
structured product requirements. Always respond in the exact JSON schema requested.
Think critically — identify gaps, assumptions, and edge cases. Be specific and actionable."""


def step1_prompt(ctx: PRDContext) -> str:
    extras = ""
    if ctx.interactive_answers:
        qa = "\n".join(f"  Q: {q}\n  A: {a}" for q, a in ctx.interactive_answers.items())
        extras = f"\n\nAdditional context from user:\n{qa}"

    return f"""Analyze this one-sentence product requirement and expand it into a structured brief.

Original requirement: "{ctx.original_input}"{extras}

Respond with JSON matching this schema:
{{
  "product_name": "suggested product/feature name",
  "problem_statement": "clear problem statement (2-3 sentences)",
  "target_users": ["user group 1", "user group 2"],
  "core_value": "core value proposition (1-2 sentences)",
  "scope_in": ["in-scope item 1", "in-scope item 2", ...],
  "scope_out": ["explicitly out-of-scope item 1", ...],
  "success_metrics": ["measurable KPI 1", "measurable KPI 2", ...]
}}

Guidelines:
- Be specific about WHO the users are (roles, demographics)
- Scope should be realistic for an MVP — don't boil the ocean
- Success metrics must be measurable (e.g., "80% of users complete onboarding in < 5 min")
- scope_out is critical — clearly define boundaries"""


def step2_prompt(ctx: PRDContext) -> str:
    brief = ctx.brief
    return f"""Based on this requirement brief, create detailed user analysis.

Product: {brief.product_name}
Problem: {brief.problem_statement}
Target Users: {brief.target_users}
Value: {brief.core_value}
In Scope: {brief.scope_in}

Respond with JSON:
{{
  "personas": [
    {{
      "name": "Persona Name",
      "role": "their role",
      "goals": ["goal 1", "goal 2"],
      "pain_points": ["pain 1", "pain 2"]
    }}
  ],
  "user_stories": [
    {{
      "id": "US-001",
      "title": "short title",
      "as_a": "user type",
      "i_want": "to do something",
      "so_that": "achieve some benefit",
      "acceptance_criteria": ["given/when/then criteria 1", ...],
      "priority": "P0"
    }}
  ],
  "key_scenarios": ["critical user journey 1", ...]
}}

Guidelines:
- Create 2-3 personas max, make them distinct
- Write 8-15 user stories covering all scope items
- Every user story needs at least 2 acceptance criteria
- P0 = must-have for MVP, P1 = important, P2 = nice-to-have
- Include at least one edge case scenario"""


def step3_prompt(ctx: PRDContext) -> str:
    brief = ctx.brief
    ua = ctx.user_analysis
    stories_text = "\n".join(
        f"  [{s.id}] ({s.priority}) {s.title}: As {s.as_a}, I want {s.i_want} so that {s.so_that}"
        for s in ua.user_stories
    )
    return f"""Based on user analysis, define functional requirements.

Product: {brief.product_name}
User Stories:
{stories_text}

Respond with JSON:
{{
  "modules": ["module/group 1", "module/group 2", ...],
  "requirements": [
    {{
      "id": "FR-001",
      "title": "short title",
      "description": "detailed description",
      "user_stories": ["US-001", "US-002"],
      "acceptance_criteria": ["criterion 1", ...],
      "priority": "P0"
    }}
  ],
  "data_entities": ["Entity1 (key fields)", ...],
  "api_overview": ["GET /endpoint - description", ...]
}}

Guidelines:
- Group requirements into logical modules (e.g., "User Management", "Core Feature", "Analytics")
- Map each requirement to relevant user stories
- Data entities should list key fields/types
- API overview should cover main CRUD operations and integrations
- 10-20 functional requirements typically"""


def step4_prompt(ctx: PRDContext) -> str:
    brief = ctx.brief
    func = ctx.functional
    modules_text = ", ".join(func.modules)
    return f"""Define non-functional requirements, milestones, and risks.

Product: {brief.product_name}
Modules: {modules_text}
Scope: {brief.scope_in}

Respond with JSON:
{{
  "nfr": [
    {{
      "category": "performance|security|usability|reliability|scalability|accessibility",
      "requirement": "what is required",
      "target": "measurable target"
    }}
  ],
  "milestones": [
    {{
      "name": "Milestone name",
      "duration": "e.g., 2 weeks",
      "deliverables": ["deliverable 1", ...],
      "dependencies": ["dependency 1", ...]
    }}
  ],
  "risks": [
    {{
      "description": "risk description",
      "impact": "high|medium|low",
      "probability": "high|medium|low",
      "mitigation": "mitigation strategy"
    }}
  ],
  "tech_recommendations": ["recommended tech/approach 1", ...]
}}

Guidelines:
- NFR: cover at least performance, security, and usability
- Milestones: 3-5 milestones for MVP delivery (typical: Foundation → Core → Beta → Launch)
- Risks: identify 4-8 risks covering technical, market, and resource risks
- Tech recommendations should be practical and justified"""


PRD_TEMPLATE_HEADER = """# PRD: {product_name}

> Generated by req-agent from: *"{original_input}"*
> Date: {date}

---

"""
