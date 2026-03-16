# gateway/policy/layers.py

from gateway.policy.config import POLICY_CONFIG
from gateway.models import ToolCallRequest, PolicyDecision
import os



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
    allowlist = POLICY_CONFIG.get("allowlist", [])

    # Nếu allowlist rỗng → không dùng whitelist
    if not allowlist:
        return PolicyDecision(
            allowed=True,
            reason="",
            layer="allowlist"
        )

    # Tool không nằm trong whitelist
    if request.tool_name not in allowlist:
        return PolicyDecision(
            allowed=False,
            reason=f"Tool '{request.tool_name}' không có trong allowlist",
            layer="allowlist"
        )

    # Tool hợp lệ
    return PolicyDecision(
        allowed=True,
        reason="",
        layer="allowlist"
    )


def check_channel(request: ToolCallRequest) -> PolicyDecision:
    channel_rules = POLICY_CONFIG.get("channel_rules", {})

    rules = channel_rules.get(request.channel)

    # Channel chưa được cấu hình → không giới hạn
    if rules is None:
        return PolicyDecision(
            allowed=True,
            reason="",
            layer="channel"
        )

    # Wildcard → cho phép tất cả tool
    if rules == "*":
        return PolicyDecision(
            allowed=True,
            reason="",
            layer="channel"
        )

    # Nếu rules là list → check tool
    if request.tool_name not in rules:
        return PolicyDecision(
            allowed=False,
            reason=f"Tool '{request.tool_name}' không được phép trên channel '{request.channel}'",
            layer="channel"
        )

    return PolicyDecision(
        allowed=True,
        reason="",
        layer="channel"
    )


def check_agent(request: ToolCallRequest) -> PolicyDecision:
    agent_rules = POLICY_CONFIG.get("agent_rules", {})

    rules = agent_rules.get(request.agent_id)

    # Agent chưa được config → không giới hạn
    if rules is None:
        return PolicyDecision(
            allowed=True,
            reason="",
            layer="agent"
        )

    # Wildcard → cho phép mọi tool
    if rules == "*":
        return PolicyDecision(
            allowed=True,
            reason="",
            layer="agent"
        )

    # Nếu rules là list → kiểm tra tool
    if request.tool_name not in rules:
        return PolicyDecision(
            allowed=False,
            reason=f"Tool '{request.tool_name}' không được phép cho agent '{request.agent_id}'",
            layer="agent"
        )

    return PolicyDecision(
        allowed=True,
        reason="",
        layer="agent"
    )



_call_counts: dict = {}

def check_loop(request: ToolCallRequest) -> PolicyDecision:
    loop_limit = POLICY_CONFIG.get("loop_limit", 5)

    key = f"{request.session_key}:{request.tool_name}"

    # tăng counter
    count = _call_counts.get(key, 0) + 1
    _call_counts[key] = count

    # vượt quá limit
    if count > loop_limit:
        return PolicyDecision(
            allowed=False,
            reason=f"Tool '{request.tool_name}' đã được gọi quá {loop_limit} lần trong session",
            layer="loop"
        )

    return PolicyDecision(
        allowed=True,
        reason="",
        layer="loop"
    )



def check_sandbox(request: ToolCallRequest) -> PolicyDecision:
    FILE_TOOLS = ["read_file", "write_file", "delete_file", "exec"]

    tool_name = request.tool_name

    # Nếu tool không phải file tool → bỏ qua sandbox
    if tool_name not in FILE_TOOLS:
        return PolicyDecision(
            allowed=True,
            reason="",
            layer="sandbox"
        )

    # Lấy path từ tool_args
    tool_args = request.tool_args or {}
    path = tool_args.get("path")

    # Nếu tool không thao tác path cụ thể → allow
    if not path:
        return PolicyDecision(
            allowed=True,
            reason="",
            layer="sandbox"
        )

    workspace_path = POLICY_CONFIG.get("workspace_path", "workspace/")

    # Normalize path
    abs_workspace = os.path.abspath(workspace_path)
    abs_path = os.path.abspath(path)

    # Kiểm tra path có nằm trong workspace không
    if not abs_path.startswith(abs_workspace):
        return PolicyDecision(
            allowed=False,
            reason=f"Path '{path}' nằm ngoài workspace sandbox",
            layer="sandbox"
        )

    return PolicyDecision(
        allowed=True,
        reason="",
        layer="sandbox"
    )

    

def check_profile(request: ToolCallRequest) -> PolicyDecision:
    profile = POLICY_CONFIG.get("profile", "full")

    PROFILE_TOOLS = {
        "minimal": ["web_search", "read_file"],
        "full": "*"
    }

    rules = PROFILE_TOOLS.get(profile, "*")

    # Wildcard → cho phép mọi tool
    if rules == "*":
        return PolicyDecision(True, "", "profile")

    if request.tool_name not in rules:
        return PolicyDecision(
            False,
            f"Tool '{request.tool_name}' không được phép trong profile '{profile}'",
            "profile"
        )

    return PolicyDecision(True, "", "profile")
    

def check_provider(request: ToolCallRequest) -> PolicyDecision:
    provider = POLICY_CONFIG.get("provider", "gemini")

    PROVIDER_RULES = {
        "gemini": "*",
        "gemini-flash": ["web_search", "read_file"]
    }

    rules = PROVIDER_RULES.get(provider, "*")

    if rules == "*":
        return PolicyDecision(True, "", "provider")

    if request.tool_name not in rules:
        return PolicyDecision(
            False,
            f"Tool '{request.tool_name}' không được phép với provider '{provider}'",
            "provider"
        )

    return PolicyDecision(True, "", "provider")





def check_approval(request: ToolCallRequest) -> PolicyDecision:
    approval_required = POLICY_CONFIG.get("approval_required", [])

    if request.tool_name not in approval_required:
        return PolicyDecision(
            allowed=True,
            reason="",
            layer="approval"
        )

    return PolicyDecision(
        allowed=False,
        reason="Tool cần được phê duyệt thủ công trước khi chạy",
        layer="approval"
    )