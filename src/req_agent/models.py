"""Pydantic data models for PRD generation pipeline."""

from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, Field


class RequirementBrief(BaseModel):
    """Step 1: Expanded requirement brief from one-liner."""
    product_name: str = Field(description="Suggested product/feature name")
    problem_statement: str = Field(description="Clear problem being solved")
    target_users: list[str] = Field(description="Primary user groups")
    core_value: str = Field(description="Core value proposition in 1-2 sentences")
    scope_in: list[str] = Field(description="What's IN scope")
    scope_out: list[str] = Field(description="What's OUT of scope (explicit exclusions)")
    success_metrics: list[str] = Field(description="How to measure success (KPIs)")


class UserPersona(BaseModel):
    """A user persona."""
    name: str
    role: str
    goals: list[str]
    pain_points: list[str]


class UserStory(BaseModel):
    """A user story with acceptance criteria."""
    id: str = Field(description="US-001 format")
    title: str
    as_a: str = Field(description="As a [user type]")
    i_want: str = Field(description="I want to [action]")
    so_that: str = Field(description="So that [benefit]")
    acceptance_criteria: list[str]
    priority: str = Field(description="P0/P1/P2")


class UserAnalysis(BaseModel):
    """Step 2: User personas and stories."""
    personas: list[UserPersona]
    user_stories: list[UserStory]
    key_scenarios: list[str] = Field(description="Critical user scenarios/journeys")


class FunctionalRequirement(BaseModel):
    """A functional requirement."""
    id: str = Field(description="FR-001 format")
    title: str
    description: str
    user_stories: list[str] = Field(description="Related user story IDs")
    acceptance_criteria: list[str]
    priority: str = Field(description="P0/P1/P2")


class FunctionalSpec(BaseModel):
    """Step 3: Functional requirements."""
    modules: list[str] = Field(description="Feature modules/groups")
    requirements: list[FunctionalRequirement]
    data_entities: list[str] = Field(description="Key data entities/models")
    api_overview: list[str] = Field(description="High-level API endpoints or interfaces")


class NonFunctionalRequirement(BaseModel):
    """A non-functional requirement."""
    category: str = Field(description="performance/security/usability/reliability/etc")
    requirement: str
    target: str = Field(description="Measurable target")


class Milestone(BaseModel):
    """A project milestone."""
    name: str
    duration: str
    deliverables: list[str]
    dependencies: list[str] = []


class Risk(BaseModel):
    """A project risk."""
    description: str
    impact: str = Field(description="high/medium/low")
    probability: str = Field(description="high/medium/low")
    mitigation: str


class NonFunctionalSpec(BaseModel):
    """Step 4: Non-functional requirements, milestones, risks."""
    nfr: list[NonFunctionalRequirement]
    milestones: list[Milestone]
    risks: list[Risk]
    tech_recommendations: list[str] = Field(description="Suggested tech stack choices")


class PRDContext(BaseModel):
    """Complete context for PRD generation."""
    original_input: str
    interactive_answers: dict[str, str] = {}
    brief: Optional[RequirementBrief] = None
    user_analysis: Optional[UserAnalysis] = None
    functional: Optional[FunctionalSpec] = None
    nonfunctional: Optional[NonFunctionalSpec] = None
