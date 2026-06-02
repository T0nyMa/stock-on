"""Stub notification module — satisfies imports, no-op sending."""
from __future__ import annotations
import logging
from enum import Enum
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class NotificationChannel(str, Enum):
    WECHAT = "wechat"
    TELEGRAM = "telegram"
    EMAIL = "email"
    NTFY = "ntfy"
    GOTIFY = "gotify"
    FEISHU = "feishu"
    DISCORD = "discord"
    SLACK = "slack"


class NotificationService:
    """Stub notification service that logs instead of sending."""

    def __init__(self, source_message=None):
        self._source_message = source_message

    def send(self, content, **kwargs) -> bool:
        logger.debug("Notification stub: content length=%d", len(str(content)))
        return True

    def is_available(self) -> bool:
        return True

    def generate_aggregate_report(self, results, report_type: str = "simple") -> str:
        from src.enums import ReportType
        return "# Aggregate Report\n\n" + "\n".join(
            f"- {getattr(r, 'name', '?')} ({getattr(r, 'code', '?')}): score={getattr(r, 'sentiment_score', '?')}"
            for r in (results or [])
        )
