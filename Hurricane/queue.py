from asyncio.locks import Lock
from collections import deque
from typing import TypeVar, Generic

T = TypeVar("T")


class Queue(Generic[T]):
    def __init__(self) -> None:
        self._q: deque[T] = deque()
        self._has_item: Lock = Lock()
        # There is no way to synchronously acquire a lock
        # There is no alternative primitive that can perform this synchronously
        # The __init__ method cannot be made asynchronous
        # The push() method is much more useful synchronous
        #
        self._has_item._locked = True

    def __len__(self) -> int:
        return len(self._q)

    def __str__(self) -> str:
        return f"Queue(length={len(self)})"

    def push(self, value: T) -> None:
        self._q.append(value)
        if self._has_item.locked():
            self._has_item.release()

    def pop(self) -> T:
        if len(self) == 0:
            raise IndexError("pop from an empty Queue")
        item = self._q.popleft()
        # See comment in __init__()
        self._has_item._locked = True
        return item

    async def async_pop(self) -> T:
        if len(self) > 0:
            return self.pop()

        await self._has_item.acquire()
        return self.pop()
