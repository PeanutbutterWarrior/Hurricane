from __future__ import annotations

import asyncio
from typing import Any
from weakref import WeakSet

from Hurricane.client import Client


class Group:
    def __init__(self):
        self._members: WeakSet[Group | Client] = WeakSet()

    def __hash__(self):
        return id(self)

    def __iter__(self):
        return iter(self._members)

    async def send(self, message: Any):
        await asyncio.gather(member.send(message) for member in self._members)

    def add(self, new_member: Group | Client):
        self._members.add(new_member)
