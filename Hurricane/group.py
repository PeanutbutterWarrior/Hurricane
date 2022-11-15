from __future__ import annotations

import asyncio
from typing import Any, Iterable
from weakref import WeakSet

from Hurricane.client import Client


class Group:
    def __init__(self):
        self._members: WeakSet[Group | Client] = WeakSet()

    def __hash__(self) -> int:
        return id(self)

    def __iter__(self) -> Iterable[Group | Client]:
        return iter(self._members)

    def __contains__(self, item: Group | Client) -> bool:
        return item in self._members

    def __len__(self) -> len:
        return len(self._members)

    async def send(self, message: Any) -> None:
        await self.checked_send(message, set())

    async def checked_send(self, message: Any, already_sent_to: set) -> None:
        new_already_sent_to = already_sent_to.copy()
        for member in self._members:
            new_already_sent_to.add(member)

        groups_to_send_to = []
        clients_to_send_to = []
        for member in self._members:
            if member not in already_sent_to:
                if type(member) == Group:
                    groups_to_send_to.append(member)
                else:
                    clients_to_send_to.append(member)

        await asyncio.gather(
            *[
                member.checked_send(message, new_already_sent_to)
                for member in groups_to_send_to
            ]
        )
        await asyncio.gather(*[member.send(message) for member in clients_to_send_to])

    def add(self, new_member: Group | Client) -> None:
        self._members.add(new_member)

    def remove(self, member: Group | Client) -> None:
        self._members.remove(member)
