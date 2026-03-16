from gateway.models import ToolCallRequest, PolicyDecision
from gateway.policy.layers import (
    check_profile, check_provider, check_channel,
    check_agent, check_allowlist, check_denylist,
    check_approval, check_loop, check_sandbox
)


def apply(request: ToolCallRequest) -> PolicyDecision:
    layers = [
        check_profile,
        check_provider,
        check_channel,
        check_agent,
        check_allowlist,
        check_denylist,
        check_approval,
        check_loop,
        check_sandbox,
    ]
    for layer_fn in layers:
        decisions = layer_fn(request)
        if not decisions.allowed:
            return decisions
    return PolicyDecision(allowed=True, reason="", layer="pipeline")


