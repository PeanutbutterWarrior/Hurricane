from collections import deque
from typing import TypeVar, Generic
from asyncio.locks import Event

T = TypeVar("T")


class Queue(Generic[T]):
    def __init__(self):
        self._q: deque[T] = deque()
        self._has_item: Event = Event()

    def __len__(self):
        return len(self._q)

    def __str__(self):
        return f"Queue(length={len(self)})"

    def push(self, value: T):
        self._q.append(value)
        self._has_item.set()

    def pop(self) -> T:
        if len(self) == 0:
            raise IndexError("pop from an empty Queue")
        self._has_item.clear()
        return self._q.popleft()

    async def async_pop(self) -> T:
        if len(self) > 0:
            return self.pop()

        await self._has_item.wait()
        return self.pop()
