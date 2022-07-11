from __future__ import annotations
from typing import List, Union, Set

import random

from .client import Client


class Group:
    general_group: Group = None

    def __init__(self):
        self._members: Set[GroupMember] = set()
        self._parent_groups: Set[Group] = set()
        self.id = random.randbytes(16)

    def __hash__(self):
        return self.id

    def __eq__(self, other):
        return self.id == other.id

    @property
    def clients(self):
        yield from filter(lambda i: type(i) == Client, self._members)

    @property
    def child_groups(self):
        yield from filter(lambda i: type(i) == Group, self._members)

    @property
    def members(self):
        return self._members

    def add(self, member: GroupMember):
        self._members.add(member)
        member._join_group(self)

    def remove(self, member: GroupMember):
        self._members.remove(member)
        member._leave_group(self)

    def clear(self):
        self._members.clear()

    def _join_group(self, group: Group):
        self._parent_groups.add(group)

    def _leave_group(self, group: Group):
        self._parent_groups.remove(group)

    async def send(self, message: bytes):
        for member in self._members:
            await member.send(message)


GroupMember = Union[Group, Client]
Group.general_group = Group()
