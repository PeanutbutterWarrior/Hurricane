from __future__ import annotations

from datetime import datetime
from typing import Any, TYPE_CHECKING
from dataclasses import dataclass

if TYPE_CHECKING:
    from Hurricane import client


@dataclass
class Message:
    contents: Any
    author: client.Client
    sent_at: datetime
    received_at: datetime
