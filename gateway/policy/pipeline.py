@dataclass
class ToolCallRequest():
    tool_name: str
    tool_args: dict
    session_key: SessionKey
    agent_id: str
    channel: str
