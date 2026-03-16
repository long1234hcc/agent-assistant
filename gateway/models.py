from dataclasses import dataclass, field
from typing import Optional, Callable


@dataclass
class SessionKey:
    agent_id: str = "default"
    channel: str = "default"
    user_id: str = "default"

    def to_str(self):
        return f"agent:{self.agent_id}:{self.channel}:{self.user_id}"

    @classmethod
    def from_str(cls, text: str):
        _, agent_id, channel, user_id = text.split(":")
        return cls(agent_id=agent_id, channel=channel, user_id=user_id)


@dataclass
class MsgContext:
    text: str
    sender_id: str
    channel: str
    session_key: SessionKey
    command_authorized: bool = False
    is_command: bool = False
    reply_fn: Optional[Callable[[str], None]] = None


@dataclass
class ReplyPayload:
    text: str
    chunk_limit: int = 4096
    media_urls: list = field(default_factory=list)


@dataclass
class ToolCallRequest():
    tool_name: str
    tool_args: dict
    session_key: SessionKey
    agent_id: str
    channel: str


@dataclass
class PolicyDecision():
    allowed: bool
    reason: str
    layer: str
