from __future__ import annotations

from typing import Awaitable, Callable, Optional, Coroutine

import asyncio
from uuid import UUID

from Hurricane.message import Message
from Hurricane.client import Client, ClientBuilder

# Used to keep a reference to any tasks
# asyncio.create_task only creates a weak reference to the task
# If no other reference is kept, the garbage collector can destroy it before the task runs
# See https://docs.python.org/3/library/asyncio-task.html#creating-tasks
task_references = set()


class Server:
    def __init__(self):
        self._clients: list[Client] = []
        self._new_connection_callback: Optional[Callable[[Client], Coroutine]] = None
        self._received_message_callback: Optional[Callable[[Message], Coroutine]] = None
        self._client_disconnect_callback: Optional[Callable[[Client], Coroutine]] = None

    def __new_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        new_client = ClientBuilder()
        new_client.reader = reader
        new_client.writer = writer
        new_client.disconnect_callback = self._client_disconnect_callback
        asyncio.create_task(self.__client_setup(reader, new_client))

    async def __client_setup(self, tcp_reader: asyncio.StreamReader, client_builder: ClientBuilder):
        uuid = await tcp_reader.readexactly(16)
        client_builder.uuid = UUID(bytes=uuid)

        client = client_builder.construct()
        self._clients.append(client)

        await self._new_connection_callback(client)

        client.start_receiving(self._received_message_callback)

    def start(self, host, port):
        async def runner():
            server = await asyncio.start_server(self.__new_client, host=host, port=port)
            async with server:
                await server.serve_forever()

        asyncio.run(runner())

    def on_new_connection(self, coro: Callable[[Client], Awaitable]) -> Callable[[Client], Awaitable]:
        self._new_connection_callback = coro
        return coro

    def on_receiving_message(self, coro: Callable[[Message], Awaitable]) -> Callable[[Message], Awaitable]:
        self._received_message_callback = coro
        return coro
    
    def on_client_disconnect(self, coro: Callable[[Client], Awaitable]) -> Callable[[Client], Awaitable]:
        self._client_disconnect_callback = coro
        return coro


class Group:
    ...
