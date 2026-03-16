from abc import ABC, abstractmethod

from gateway.models import MsgContext, ReplyPayload


class ChannelAdapter(ABC):
    """
    Abstract interface cho mọi channel adapter.

    Channel adapter chịu trách nhiệm:
    1. Parse inbound payload từ platform → MsgContext chuẩn hóa
    2. Gửi outbound reply từ hệ thống → platform
    """

    @abstractmethod
    def parse_inbound(self, raw: dict) -> MsgContext:
        """
        Convert raw payload từ platform thành MsgContext chuẩn.

        Parameters
        ----------
        raw : dict
            Payload gốc nhận từ platform (Telegram, Slack, HTTP...)

        Returns
        -------
        MsgContext
            Context chuẩn hóa để dispatcher và agent xử lý.
        """
        pass

    @abstractmethod
    def send_outbound(self, reply: ReplyPayload) -> None:
        """
        Gửi reply từ hệ thống về platform.

        Parameters
        ----------
        reply : ReplyPayload
            Payload chuẩn hóa chứa text, attachments...
        """
        pass