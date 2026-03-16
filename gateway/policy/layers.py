# gateway/policy/layers.py

from gateway.policy.config import POLICY_CONFIG
from gateway.models import ToolCallRequest, PolicyDecision


def check_denylist(request: ToolCallRequest) -> PolicyDecision:

    denylist = POLICY_CONFIG.get("denylist", [])

    if request.tool_name in denylist:
        return PolicyDecision(
            allowed=False,
            reason=f"Tool '{request.tool_name}' bị cấm bởi denylist",
            layer="denylist"
        )

    return PolicyDecision(
        allowed=True,
        reason="",
        layer="denylist"
    )


def check_allowlist(request: ToolCallRequest) -> PolicyDecision:
