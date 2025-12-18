from __future__ import annotations

from typing import Dict, List, Optional
from pydantic import BaseModel, Field


# -------- Health --------

class HealthResponse(BaseModel):
    status: str = "ok"


# -------- Daily Digest --------

class DailyDigestRequest(BaseModel):
    as_of_date: str = Field(..., description="YYYY-MM-DD")
    mode: str = Field("summary", description="summary or full")


class RuleEvaluationResponse(BaseModel):
    rule_id: str
    status: str
    severity: str
    message: str


class RecommendationResponse(BaseModel):
    id: str
    priority: int
    action_type: str
    description: str
    details: Dict[str, str] = {}


class DailyDigestResponse(BaseModel):
    date: str
    status_label: str
    accounts_summary: Dict[str, str]
    envelopes_spend: Dict[str, str]
    envelopes_remaining: Dict[str, str]
    rule_evaluations: List[RuleEvaluationResponse]
    recommendations: List[RecommendationResponse]
    text_summary: str


# -------- Weekly Summary --------

class WeeklySummaryRequest(BaseModel):
    week_ending_date: str = Field(..., description="YYYY-MM-DD")


class WeeklySummaryResponse(BaseModel):
    start_date: str
    end_date: str
    days_covered: int
    average_daily_spend_per_envelope: Dict[str, str]
    rule_violation_counts: Dict[str, int]
    overall_status_label: str
    weekly_narrative: str


# -------- Scenario Simulation --------

class OneOffSpend(BaseModel):
    amount: str
    envelope_id: str
    description: str


class EnvelopeAdjustment(BaseModel):
    envelope_id: str
    new_budget_amount: str


class ScenarioSimulationRequest(BaseModel):
    as_of_date: str
    one_off_spend: Optional[OneOffSpend] = None
    envelope_adjustments: Optional[List[EnvelopeAdjustment]] = None


class ScenarioSimulationResponse(BaseModel):
    baseline_envelopes_remaining: Dict[str, str]
    scenario_envelopes_remaining: Dict[str, str]
    impact_summary: str
