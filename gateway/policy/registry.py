from typing import Callable, Dict, Any

from gateway.policy.pipeline import apply
from gateway.models import ToolCallRequest
from gateway.models import PolicyDecision


class PolicyAwareRegistry:
    """
    Wrapper quanh tools registry gốc để enforce policy trước khi tool chạy.
    """

    def __init__(self, registry, agent_id: str, channel: str, session_key: str):
        self._registry = registry
        self._agent_id = agent_id
        self._channel = channel
        self._session_key = session_key

    def get(self, tool_name: str) -> Callable:
        tool_func = self._registry.get(tool_name)

        def wrapped(**tool_args: Any):
            request = ToolCallRequest(
                tool_name=tool_name,
                tool_args=tool_args,
                agent_id=self._agent_id,
                channel=self._channel,
                session_key=self._session_key
            )
            decision = apply(request)
            if not decision.allowed:
                return f"[POLICY DENIED][{decision.layer}] {decision.reason}"
            return tool_func(**tool_args)

        # Giữ nguyên tên và metadata của tool gốc
        wrapped.__name__ = tool_func.__name__
        wrapped.__doc__ = tool_func.__doc__

        return wrapped

    def all(self) -> Dict[str, Callable]:
        """
        Trả về toàn bộ tools nhưng đã wrapped.
        """

        wrapped_tools = {}

        for name, func in self._registry.all().items():
            wrapped_tools[name] = self.get(name)

        return wrapped_tools