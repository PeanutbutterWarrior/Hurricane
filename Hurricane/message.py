from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from Hurricane import client


@dataclass
class AnonymousMessage:
    contents: Any
    sent_at: datetime
    received_at: datetime


@dataclass
class Message(AnonymousMessage):
    author: client.Client
