from app.agents.revenue_engine import calculate_revenue


def test_revenue_breakdown_contains_all_expected_keys_and_correct_total():
    result = calculate_revenue(touchpoints=4, agent_count=5)
    for key in ("assessment", "architecture", "implementation", "governance", "managed", "total"):
        assert key in result
    # total is the one-time program cost -- assessment + architecture + implementation + governance.
    assert result["total"] == (
        result["assessment"] + result["architecture"] + result["implementation"] + result["governance"]
    )
    # managed is a separate ANNUAL recurring line, not folded into the one-time total.
    assert result["managed"] > 0


def test_higher_complexity_yields_higher_revenue():
    higher = calculate_revenue(touchpoints=10, agent_count=6)
    lower = calculate_revenue(touchpoints=3, agent_count=2)
    assert higher["total"] > lower["total"]


def test_governance_is_always_present_and_non_zero():
    result = calculate_revenue(touchpoints=0, agent_count=0)
    assert result["governance"] > 0


def test_healthcare_domain_has_higher_governance_than_customer_service():
    healthcare = calculate_revenue(touchpoints=5, agent_count=3, domain="healthcare")
    customer_service = calculate_revenue(touchpoints=5, agent_count=3, domain="customer_service")
    assert healthcare["governance"] > customer_service["governance"]
