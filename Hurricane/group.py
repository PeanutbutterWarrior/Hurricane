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

    def __contains__(self, item):
        return item in self._members

    async def send(self, message: Any):
        await self.checked_send(message, set())

    async def checked_send(self, message: Any, already_sent_to: set):
        new_already_sent_to = already_sent_to.copy()
        for member in self._members:
            new_already_sent_to.add(member)

        await asyncio.gather(
            member.checked_send(message, new_already_sent_to)
            for member in self._members
            if member not in already_sent_to
        )

    def add(self, new_member: Group | Client):
        self._members.add(new_member)

    def remove(self, member: Group | Client):
        self._members.remove(member)
