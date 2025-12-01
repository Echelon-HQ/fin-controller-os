from __future__ import annotations

"""
Defines JSON schemas for Financial Controller tools.

These schemas are framework-agnostic and can be used with OpenAI tools,
AgentKit, LangGraph, or any other agent framework that supports JSON-typed
tools or function calling.
"""

run_daily_digest_input_schema = {
    "type": "object",
    "properties": {
        "as_of_date": {
            "type": "string",
            "description": "Evaluation date in YYYY-MM-DD format.",
        },
        "mode": {
            "type": "string",
            "description": (
                "Output mode, 'summary' returns a compact view, "
                "'full' returns the entire digest."
            ),
            "enum": ["summary", "full"],
            "default": "summary",
        },
    },
    "required": ["as_of_date"],
}

run_daily_digest_output_schema = {
    "type": "object",
    "properties": {
        "date": {"type": "string"},
        "status_label": {
            "type": "string",
            "description": (
                "High-level status for the day, such as 'stable', "
                "'tight', or 'critical'."
            ),
        },
        "accounts_summary": {
            "type": "object",
            "additionalProperties": {
                "type": "string",
                "description": "Balance as a stringified decimal.",
            },
        },
        "envelopes_spend": {
            "type": "object",
            "additionalProperties": {
                "type": "string",
                "description": "Total spend per envelope as a stringified decimal.",
            },
        },
        "envelopes_remaining": {
            "type": "object",
            "additionalProperties": {
                "type": "string",
                "description": "Remaining budget per envelope as a stringified decimal.",
            },
        },
        "rule_evaluations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "rule_id": {"type": "string"},
                    "status": {"type": "string"},
                    "severity": {"type": "string"},
                    "message": {"type": "string"},
                },
                "required": ["rule_id", "status", "severity", "message"],
            },
        },
        "recommendations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "priority": {"type": "integer"},
                    "action_type": {"type": "string"},
                    "description": {"type": "string"},
                    "details": {
                        "type": "object",
                        "additionalProperties": {"type": "string"},
                    },
                },
                "required": ["id", "priority", "action_type", "description"],
            },
        },
        "text_summary": {"type": "string"},
    },
    "required": [
        "date",
        "status_label",
        "accounts_summary",
        "envelopes_spend",
        "envelopes_remaining",
        "rule_evaluations",
        "recommendations",
        "text_summary",
    ],
}

run_weekly_summary_input_schema = {
    "type": "object",
    "properties": {
        "week_ending_date": {
            "type": "string",
            "description": (
                "Week ending date in YYYY-MM-DD format. "
                "The summary will cover the prior seven days including this date."
            ),
        }
    },
    "required": ["week_ending_date"],
}

run_weekly_summary_output_schema = {
    "type": "object",
    "properties": {
        "start_date": {"type": "string"},
        "end_date": {"type": "string"},
        "days_covered": {"type": "integer"},
        "average_daily_spend_per_envelope": {
            "type": "object",
            "additionalProperties": {"type": "string"},
        },
        "rule_violation_counts": {
            "type": "object",
            "additionalProperties": {"type": "integer"},
        },
        "overall_status_label": {"type": "string"},
        "weekly_narrative": {"type": "string"},
    },
    "required": [
        "start_date",
        "end_date",
        "days_covered",
        "average_daily_spend_per_envelope",
        "rule_violation_counts",
        "overall_status_label",
        "weekly_narrative",
    ],
}

simulate_scenario_input_schema = {
    "type": "object",
    "properties": {
        "as_of_date": {
            "type": "string",
            "description": "Reference date for the scenario in YYYY-MM-DD format.",
        },
        "one_off_spend": {
            "type": "object",
            "description": "Optional one-off planned spend event to simulate.",
            "properties": {
                "amount": {
                    "type": "string",
                    "description": (
                        "Amount as a stringified decimal in the same base currency."
                    ),
                },
                "envelope_id": {"type": "string"},
                "description": {
                    "type": "string",
                    "description": (
                        "Narrative description of the planned spend, such as 'Sofa purchase'."
                    ),
                },
            },
            "required": ["amount", "envelope_id", "description"],
        },
        "envelope_adjustments": {
            "type": "array",
            "description": (
                "Optional list of envelope budget adjustments to simulate."
            ),
            "items": {
                "type": "object",
                "properties": {
                    "envelope_id": {"type": "string"},
                    "new_budget_amount": {
                        "type": "string",
                        "description": (
                            "New budget for the envelope as a stringified decimal."
                        ),
                    },
                },
                "required": ["envelope_id", "new_budget_amount"],
            },
        },
    },
    "required": ["as_of_date"],
}

simulate_scenario_output_schema = {
    "type": "object",
    "properties": {
        "baseline_envelopes_remaining": {
            "type": "object",
            "additionalProperties": {"type": "string"},
        },
        "scenario_envelopes_remaining": {
            "type": "object",
            "additionalProperties": {"type": "string"},
        },
        "impact_summary": {
            "type": "string",
            "description": (
                "Short text summary of the most important changes caused by the scenario."
            ),
        },
    },
    "required": [
        "baseline_envelopes_remaining",
        "scenario_envelopes_remaining",
        "impact_summary",
    ],
}

explain_log_entry_input_schema = {
    "type": "object",
    "properties": {
        "date": {
            "type": "string",
            "description": "Date of the log entry to explain in YYYY-MM-DD format.",
        }
    },
    "required": ["date"],
}

explain_log_entry_output_schema = {
    "type": "object",
    "properties": {
        "date": {"type": "string"},
        "rule_summary": {"type": "string"},
        "recommendation_summary": {"type": "string"},
        "narrative_explanation": {"type": "string"},
    },
    "required": [
        "date",
        "rule_summary",
        "recommendation_summary",
        "narrative_explanation",
    ],
}