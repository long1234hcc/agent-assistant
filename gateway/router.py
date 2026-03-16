from gateway.models import MsgContext, SessionKey
from gateway.auth import is_allowed


def resolve_session_key(msg: MsgContext, agent_id) -> SessionKey:
    return SessionKey(
        agent_id=agent_id,
        channel=msg.channel,
        user_id=msg.sender_id
    )


def detect_command(msg: MsgContext) -> MsgContext:
    VALID_COMMANDS = ["/reset", "/status", "/help"]
    text = msg.text
    channel = msg.channel
    sender_id = msg.sender_id
    if not text.startswith("/"):
        msg.command_authorized = False
        msg.is_command = False
        return msg

    if text not in VALID_COMMANDS:
        msg.command_authorized = False
        msg.is_command = True
        return msg
    else:
        if (channel == 'http' or is_allowed(sender_id, channel)):
            msg.command_authorized = True
            msg.is_command = True
            return msg
        else:
            msg.command_authorized = False
            msg.is_command = True
            return msg
