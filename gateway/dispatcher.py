from gateway.models import MsgContext, ReplyPayload
from gateway import auth, router, session_store
from agents.orchestration.orchestrator import create_orchestrator
from agents.core.session import Session


def handle_command(msg, session_key):

    text = msg.text.strip()

    if text == "/reset":

        # reset token metadata
        session_store.update(session_key, 0)

        # clear transcript history
        session = Session(session_id=session_key)
        session.clear()

        msg.reply_fn(
            ReplyPayload(text="Session reset.")
        )
        return

    if text == "/status":

        session = session_store.get(session_key)

        if session is None:
            msg.reply_fn(
                ReplyPayload(text="No active session.")
            )
            return

        token_count = session["token_count"]
        last_active = session["last_active"]

        msg.reply_fn(
            ReplyPayload(
                text=(
                    f"Tokens used: {token_count}\n"
                    f"Last active: {last_active}"
                )
            )
        )
        return

    msg.reply_fn(
        ReplyPayload(text="Unknown command.")
    )


# Create agent once (singleton)
_agent = create_orchestrator()


def dispatchInboundMessage(msg: MsgContext):

    # 1. Auth check
    allowed, reason = auth.check(msg)
    if not allowed:
        msg.reply_fn(ReplyPayload(text=f"Unauthorized: {reason}"))
        return

    # 2. Detect command
    router.detect_command(msg)

    # 3. Resolve session key
    session_key = router.resolve_session_key(msg, agent_id="orchestrator")

    # 4. Convert to string
    session_key_str = session_key.to_str()

    # 5. Load or create session metadata
    metadata = session_store.get_or_create(session_key_str)

    # 6. Command handling
    if msg.is_command:

        if msg.command_authorized:
            handle_command(msg, session_key_str)
        else:
            msg.reply_fn(
                ReplyPayload(text="Không có quyền.")
            )

        return

    # 7. Normal chat → run agent
    answer = _agent.run(msg.text)

    # 8. Estimate token count
    total_chars = sum(
        len(str(m["content"]))
        for m in _agent.history.get_history()
    )

    token_count = total_chars // 4

    session_store.update(session_key_str, token_count)

    # 9. Reply to user
    msg.reply_fn(
        ReplyPayload(text=answer)
    )
