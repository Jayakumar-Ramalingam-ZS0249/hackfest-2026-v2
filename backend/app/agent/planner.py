"""The planner loop: Claude decides which verification/compliance/calculation
tools to call, and in what order, for a given applicant. Claude is never given
the applicant's raw data directly — it must call a tool to learn anything, and
every tool call is executed against the trusted server-side record identified
by `applicant_id`, never against whatever else Claude might place in its tool
call arguments. Claude's only output that matters here is *which* tools it
calls; the actual recommendation and amount are derived afterwards, by pure
Python (see app.agent.decision_rules), never by Claude.
"""

import json
import logging
from typing import Any, Dict, List, Tuple

import anthropic

from app import config
from app.tools.registry import CLAUDE_TOOL_SCHEMAS, TOOL_FUNCTIONS

logger = logging.getLogger(__name__)

MAX_PLANNER_TURNS = 6

PLANNER_SYSTEM_PROMPT = """You are the orchestration layer for a health insurance claims review \
pipeline used by an operations team. You cannot verify identities, detect fraud, check policy \
compliance, or calculate amounts yourself — you have no access to applicant data except through \
the tools you are given. Every fact and every number must come from a tool result, never from \
your own estimate.

Guidelines:
- Call verify_identity first for the applicant under review.
- If identity verification fails, you may skip the remaining checks since there is nothing left \
to safely act on.
- Otherwise call check_fraud_flags and check_policy_compliance to gather the facts a compliance \
reviewer would need.
- Only call calculate_risk_adjusted_amount once identity has been verified — it is the sole \
source of the approved amount and should not be called for an applicant who fails verification.
- Once you have called the tools needed to fully assess this applicant, stop calling tools and \
reply with one short sentence confirming the review is complete. Do not state a recommendation, \
an amount, or any other number in that reply — a separate deterministic process reads your tool \
calls and makes the final decision."""


def _client() -> anthropic.Anthropic:
    return anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)


def run_planner(applicant_id: str) -> Tuple[Dict[str, Dict[str, Any]], List[str]]:
    """Runs the Claude-driven tool-calling loop for one applicant.

    Returns (tool_outputs_by_name, tool_call_order). Raises on any unrecoverable
    API error so the caller (app.agent.pipeline) can fall back to the
    deterministic rule-based orchestration.
    """
    client = _client()
    messages: List[Dict[str, Any]] = [
        {
            "role": "user",
            "content": (
                f"Review claim application {applicant_id}. Use the available tools to gather "
                f"every fact you need — begin the review now."
            ),
        }
    ]

    tool_outputs: Dict[str, Dict[str, Any]] = {}
    call_order: List[str] = []

    for _turn in range(MAX_PLANNER_TURNS):
        response = client.messages.create(
            model=config.CLAUDE_MODEL,
            max_tokens=1024,
            system=PLANNER_SYSTEM_PROMPT,
            tools=CLAUDE_TOOL_SCHEMAS,
            output_config={"effort": "low"},
            messages=messages,
        )
        messages.append({"role": "assistant", "content": response.content})

        tool_use_blocks = [block for block in response.content if block.type == "tool_use"]
        if not tool_use_blocks:
            break

        tool_results = []
        for block in tool_use_blocks:
            fn = TOOL_FUNCTIONS.get(block.name)
            if fn is None:
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps({"error": f"unknown tool '{block.name}'"}),
                        "is_error": True,
                    }
                )
                continue

            try:
                # Execute against the trusted server-side applicant_id regardless
                # of whatever Claude echoed in block.input — Claude can trigger
                # the computation but never feed data into it.
                output = fn(applicant_id=applicant_id)
                tool_outputs[block.name] = output
                call_order.append(block.name)
                tool_results.append(
                    {"type": "tool_result", "tool_use_id": block.id, "content": json.dumps(output)}
                )
            except Exception as exc:  # noqa: BLE001 - reported back to Claude, not raised
                logger.exception("Tool %s failed for %s", block.name, applicant_id)
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps({"error": str(exc)}),
                        "is_error": True,
                    }
                )

        messages.append({"role": "user", "content": tool_results})
    else:
        logger.warning("Planner for %s hit MAX_PLANNER_TURNS without stopping naturally", applicant_id)

    return tool_outputs, call_order
