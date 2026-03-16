# gateway/policy/config.py
POLICY_CONFIG = {
    "profile": "full",
    "provider": "gemini",
    "channel_rules": {
        "telegram": ["web_search", "read_file"],
        "http": "*"  # tất cả
    },
    "agent_rules": {
        "orchestrator": "*",
        "todoist_agent": ["todoist_get_tasks", "todoist_create_task"],
        "research_agent": ["web_search", "github_search"]
    },
    "allowlist": [],
    "denylist": ["exec", "delete_file", "rm"],
    "approval_required": [],
    "loop_limit": 5,
    "workspace_path": "workspace/"
}
