from __future__ import annotations
from typing import Callable, Coroutine, Set

import asyncio

from .message import Message
from .group import Group


class Client:
    def __init__(self,
                 tcp_reader: asyncio.StreamReader,
                 tcp_writer: asyncio.StreamWriter,
                 client_disconnect_callback,
                 ):

        self.__tcp_reader: asyncio.StreamReader = tcp_reader
        self.__tcp_writer: asyncio.StreamWriter = tcp_writer
        self.__socket_read_task = None
        self._client_disconnect_callback = client_disconnect_callback

        self._parent_groups: Set[Group] = set()

    async def _wait_for_read(self, callback: Callable[[Message], Coroutine]):
        while True:
            try:
                message = await Message.from_StreamReader(self, self.__tcp_reader)
            except asyncio.IncompleteReadError:
                # Received an empty string from the socket
                # Nothing more will be received from the socket
                # Assume that the client is no longer listening
                break
            asyncio.create_task(callback(message))
        await self.shutdown()
        if self._client_disconnect_callback:
            await self._client_disconnect_callback(self)
        self.__socket_read_task = None

    def start_receiving(self, callback: Callable[[Message], Coroutine]):
        if not self.__socket_read_task:
            self.__socket_read_task = asyncio.create_task(
                self._wait_for_read(callback)
            )

    def _join_group(self, group: Group):
        self._parent_groups.add(group)

    def _leave_group(self, group: Group):
        self._parent_groups.remove(group)

    @property
    def groups(self):
        return self._parent_groups

    async def send(self, data: bytes):
        self.__tcp_writer.write(data)
        await self.__tcp_writer.drain()

    async def shutdown(self):
        self.__tcp_writer.close()
        await self.__tcp_writer.wait_closed()
