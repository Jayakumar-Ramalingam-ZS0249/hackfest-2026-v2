"""
ROI (Business Impact) calculator.

Pure math, no LLM involvement whatsoever -- consistent with the
"models/solvers do the math, the LLM never touches numbers that must be
auditable" principle already used by eligibility.py's threshold logic.
"""


def calculate_roi(
    annual_volume: int,
    mins_per_request: float,
    automation_pct: float,
    cost_per_hour: float = 25,
    agent_count: int = 0,  # reserved for future per-agent cost modeling; not used in the math below
) -> dict:
    if annual_volume <= 0:
        return {"current_hours": 0.0, "future_hours": 0.0, "saved_hours": 0.0, "annual_savings": 0.0}

    current_hours = (annual_volume * mins_per_request) / 60
    # Guard explicitly rather than relying on float multiplication happening
    # to land on exactly 0.0 -- 100% automation must show a clean zero.
    future_hours = 0.0 if automation_pct >= 1.0 else current_hours * (1 - automation_pct)
    saved_hours = current_hours - future_hours
    annual_savings = saved_hours * cost_per_hour

    return {
        "current_hours": round(current_hours, 2),
        "future_hours": round(future_hours, 2),
        "saved_hours": round(saved_hours, 2),
        "annual_savings": round(annual_savings, 2),
    }
