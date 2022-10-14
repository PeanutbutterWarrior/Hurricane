from __future__ import annotations

from datetime import datetime
from typing import Any, TYPE_CHECKING
from dataclasses import dataclass

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
