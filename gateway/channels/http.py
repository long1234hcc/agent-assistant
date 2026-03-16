from gateway.models import MsgContext, ReplyPayload, SessionKey
from gateway.channels.base import ChannelAdapter


class HttpAdapter(ChannelAdapter):
    """
    HTTP adapter.

    HTTP là request/response synchronous:
    - parse_inbound() đọc request body → MsgContext
    - send_outbound() không gửi API mà lưu reply tạm
    - server.py gọi get_reply() để lấy response trả về client
    """

    def __init__(self):
        self._pending_reply: ReplyPayload | None = None

    def parse_inbound(self, raw: dict) -> MsgContext:
        """
        Convert HTTP request body thành MsgContext.
        """

        text = raw.get("text", "")
        sender_id = raw.get("sender_id", "http_user")

        # session key tạm (router sẽ resolve lại sau)
        session_key = SessionKey(
            agent_id="orchestrator",
            channel="http",
            user_id=sender_id
        )

        return MsgContext(
            text=text,
            sender_id=sender_id,
            channel="http",
            session_key=session_key,
            reply_fn=lambda payload: self.send_outbound(payload)
        )

    def send_outbound(self, reply: ReplyPayload) -> None:
        """
        HTTP không push message được.
        Chỉ lưu reply để server.py trả về HTTP response.
        """
        self._pending_reply = reply

    def get_reply(self) -> ReplyPayload | None:
        """
        server.py gọi hàm này sau khi dispatcher chạy xong
        để lấy response trả về client.
        """
        reply = self._pending_reply
        self._pending_reply = None
        return reply