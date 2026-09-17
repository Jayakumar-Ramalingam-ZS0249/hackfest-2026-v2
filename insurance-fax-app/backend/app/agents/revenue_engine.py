"""
Revenue opportunity calculator.

Pure math, no LLM involvement whatsoever -- same principle as
roi_engine.py.
"""

BASE_GOVERNANCE_FEE = 150_000

# Deliberate product improvement over the original standalone prototype,
# which used one flat governance number regardless of domain. Healthcare
# carries materially higher compliance/audit burden than customer
# service, so its governance retainer should reflect that -- this is a
# real product gap being addressed here, not just a formula tweak.
GOVERNANCE_DOMAIN_MULTIPLIER: dict[str, float] = {
    "healthcare": 1.4,
    "collections": 1.15,
    "customer_service": 0.85,
    "general": 1.0,
}


def calculate_revenue(touchpoints: int, agent_count: int, domain: str = "general") -> dict:
    touchpoints = max(0, touchpoints)
    agent_count = max(0, agent_count)

    assessment = 50_000 + touchpoints * 5_000
    architecture = 100_000 + agent_count * 25_000
    implementation = 300_000 + agent_count * 100_000
    governance = round(BASE_GOVERNANCE_FEE * GOVERNANCE_DOMAIN_MULTIPLIER.get(domain, 1.0))
    managed = int(implementation * 0.20)  # annual recurring -- intentionally excluded from `total` below
    total = assessment + architecture + implementation + governance

    return {
        "assessment": assessment,
        "architecture": architecture,
        "implementation": implementation,
        "governance": governance,
        "managed": managed,
        "total": total,
        "domain": domain,
    }
