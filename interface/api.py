from __future__ import annotations

from pathlib import Path
from fastapi import FastAPI, HTTPException
from interface.chat import router as chat_router

from interface.schemas import (
    HealthResponse,
    DailyDigestRequest,
    DailyDigestResponse,
    WeeklySummaryRequest,
    WeeklySummaryResponse,
    ScenarioSimulationRequest,
    ScenarioSimulationResponse,
)

from orchestration.controller_adapter import (
    tool_run_daily_digest_impl,
    tool_run_weekly_summary_impl,
    tool_simulate_scenario_impl,
    tool_explain_log_entry_impl,
)

# ------------------------------------------------------------------
# Path configuration (hard-coded, simple, reliable)
# ------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parents[1]
CONFIG_DIR = BASE_DIR / "config"
DATA_DIR = BASE_DIR / "data"
LOG_DIR = BASE_DIR / "log"

# ------------------------------------------------------------------
# FastAPI app
# ------------------------------------------------------------------

app = FastAPI(
    title="Financial Controller API",
    description="HTTP interface for the Financial Controller engine",
    version="1.0.0",
)
app.include_router(chat_router)



# ------------------------------------------------------------------
# Health
# ------------------------------------------------------------------

@app.get("/health", response_model=HealthResponse)
def health_check():
    return HealthResponse()


# ------------------------------------------------------------------
# Daily Digest
# ------------------------------------------------------------------

@app.post("/daily-digest", response_model=DailyDigestResponse)
def run_daily_digest(request: DailyDigestRequest):
    try:
        result = tool_run_daily_digest_impl(
            config_dir=CONFIG_DIR,
            data_dir=DATA_DIR,
            log_dir=LOG_DIR,
            as_of_date_str=request.as_of_date,
            mode=request.mode,
        )
        return result
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


# ------------------------------------------------------------------
# Weekly Summary
# ------------------------------------------------------------------

@app.post("/weekly-summary", response_model=WeeklySummaryResponse)
def run_weekly_summary(request: WeeklySummaryRequest):
    try:
        result = tool_run_weekly_summary_impl(
            log_dir=LOG_DIR,
            week_ending_date_str=request.week_ending_date,
        )
        return result
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


# ------------------------------------------------------------------
# Scenario Simulation
# ------------------------------------------------------------------

@app.post("/simulate", response_model=ScenarioSimulationResponse)
def simulate_scenario(request: ScenarioSimulationRequest):
    try:
        result = tool_simulate_scenario_impl(
            config_dir=CONFIG_DIR,
            data_dir=DATA_DIR,
            as_of_date_str=request.as_of_date,
            one_off_spend=(
                request.one_off_spend.dict()
                if request.one_off_spend
                else None
            ),
            envelope_adjustments=(
                [adj.dict() for adj in request.envelope_adjustments]
                if request.envelope_adjustments
                else None
            ),
        )
        return result
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


# ------------------------------------------------------------------
# Explain Log Entry
# ------------------------------------------------------------------

@app.get("/log/{date}")
def explain_log_entry(date: str):
    try:
        result = tool_explain_log_entry_impl(
            log_dir=LOG_DIR,
            date_str=date,
        )
        return result
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
