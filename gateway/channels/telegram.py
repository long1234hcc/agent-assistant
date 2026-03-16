import requests

from gateway.models import MsgContext, ReplyPayload, SessionKey
from gateway.channels.base import ChannelAdapter


class TelegramAdapter(ChannelAdapter):
    """
    Telegram channel adapter.

    - parse_inbound(): nhận webhook payload từ Telegram → MsgContext
    - send_outbound(): gọi Telegram Bot API để gửi message
    """

    def __init__(self, bot_token: str):
        self._bot_token = bot_token
        self._chat_id: int | None = None

    def parse_inbound(self, raw: dict) -> MsgContext:
        """
        Parse webhook payload từ Telegram.
        """

        message = raw.get("message", {})

        text = message.get("text", "")
        sender_id = str(message.get("from", {}).get("id", "unknown"))

        # lưu chat_id để dùng khi reply
        self._chat_id = message.get("chat", {}).get("id")

        session_key = SessionKey(
            agent_id="orchestrator",
            channel="telegram",
            user_id=sender_id
        )

        return MsgContext(
            text=text,
            sender_id=sender_id,
            channel="telegram",
            session_key=session_key,
            reply_fn=lambda payload: self.send_outbound(payload)
        )

    def send_outbound(self, reply: ReplyPayload) -> None:
        """
        Gửi message về Telegram bằng Bot API.
        Nếu text dài > chunk_limit → chia thành nhiều message.
        """

        if self._chat_id is None:
            return

        text = reply.text or ""
        limit = reply.chunk_limit or 4096

        url = f"https://api.telegram.org/bot{self._bot_token}/sendMessage"

        # split text thành chunks
        chunks = [
            text[i:i + limit]
            for i in range(0, len(text), limit)
        ] or [""]

        for chunk in chunks:
            requests.post(
                url,
                json={
                    "chat_id": self._chat_id,
                    "text": chunk
                },
                timeout=10
            )