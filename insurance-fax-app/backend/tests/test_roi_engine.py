from app.agents.roi_engine import calculate_roi


def test_standard_roi_example_is_exactly_correct():
    result = calculate_roi(annual_volume=200000, mins_per_request=12, automation_pct=0.75)
    assert result["current_hours"] == 40000
    assert result["future_hours"] == 10000
    assert result["saved_hours"] == 30000
    assert result["annual_savings"] == 750000


def test_zero_volume_yields_all_zeros_with_no_errors():
    result = calculate_roi(annual_volume=0, mins_per_request=12, automation_pct=0.75)
    assert result == {"current_hours": 0.0, "future_hours": 0.0, "saved_hours": 0.0, "annual_savings": 0.0}


def test_full_automation_yields_exactly_zero_future_hours():
    result = calculate_roi(annual_volume=200000, mins_per_request=12, automation_pct=1.0)
    assert result["future_hours"] == 0.0
    assert result["saved_hours"] == result["current_hours"]


def test_custom_cost_per_hour_scales_savings():
    result = calculate_roi(annual_volume=200000, mins_per_request=12, automation_pct=0.75, cost_per_hour=50)
    assert result["annual_savings"] == 1_500_000
