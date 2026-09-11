"""The provenance tagger: a decorator that wraps every tool function so each
call is recorded — tool name, timestamp, inputs, outputs — in the global audit
log. This is the mechanism that makes the /audit-log page and the applicant
detail provenance strip possible, and it is applied uniformly whether a tool
was invoked by the Claude-driven planner or the deterministic fallback path.
"""

import functools
import inspect
from datetime import datetime, timezone
from typing import Any, Callable

from app import store
from app.models.schemas import ToolCallRecord


def traced(tool_name: str) -> Callable:
    def decorator(fn: Callable) -> Callable:
        signature = inspect.signature(fn)

        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            bound = signature.bind(*args, **kwargs)
            bound.apply_defaults()
            inputs = dict(bound.arguments)

            outputs = fn(*args, **kwargs)

            record = ToolCallRecord(
                id=store.next_audit_id(),
                applicant_id=str(inputs.get("applicant_id", "")),
                tool_name=tool_name,
                timestamp=datetime.now(timezone.utc),
                inputs=inputs,
                outputs=outputs if isinstance(outputs, dict) else {"result": outputs},
            )
            store.append_audit(record)
            return outputs

        return wrapper

    return decorator
