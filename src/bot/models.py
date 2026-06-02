"""Stub bot models."""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class BotMessage:
    text: str = ""
    session_id: str = ""
    user_id: str = ""
    platform: str = ""
    channel_id: str = ""
