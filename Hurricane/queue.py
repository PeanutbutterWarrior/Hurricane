from asyncio.locks import Lock
from collections import deque
from typing import TypeVar, Generic

T = TypeVar("T")


class Queue(Generic[T]):
    def __init__(self):
        self._q: deque[T] = deque()
        self._has_item: Lock = Lock()
        self._has_item._locked = True

    def __len__(self):
        return len(self._q)

    def __str__(self):
        return f"Queue(length={len(self)})"

    def push(self, value: T):
        self._q.append(value)
        if self._has_item.locked():
            self._has_item.release()

    def pop(self) -> T:
        if len(self) == 0:
            raise IndexError("pop from an empty Queue")
        item = self._q.popleft()
        self._has_item._locked = True
        return item

    async def async_pop(self) -> T:
        if len(self) > 0:
            return self.pop()

        await self._has_item.acquire()
        return self.pop()
