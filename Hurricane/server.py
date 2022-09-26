from __future__ import annotations

from typing import Awaitable, Callable, Coroutine

import asyncio
from asyncio import StreamReader, StreamWriter
from uuid import UUID
import sys
import traceback

from Hurricane.message import Message
from Hurricane.client import Client, ClientBuilder

# Used to keep a reference to any tasks
# asyncio.create_task only creates a weak reference to the task
# If no other reference is kept, the garbage collector can destroy it before the task runs
# See https://docs.python.org/3/library/asyncio-task.html#creating-tasks
task_references = set()


class Server:
    def __init__(self, timeout=30):
        self._clients: dict[UUID, Client] = {}
        self._new_connection_callback: Callable[[Client], Coroutine] | None = None
        self._received_message_callback: Callable[[Message], Coroutine] | None = None
        self._client_disconnect_callback: Callable[[Client], Coroutine] | None = None
        self._client_reconnect_callback: Callable[[Client], Coroutine] | None = None
        self.reconnect_timeout: int = timeout

    def __new_client(self, reader: StreamReader, writer: StreamWriter):
        new_client = ClientBuilder()
        new_client.reader = reader
        new_client.writer = writer
        new_client.disconnect_callback = self._client_disconnect_callback
        new_client.reconnect_timeout = self.reconnect_timeout

        new_task = asyncio.create_task(self.__client_setup(reader, new_client))
        task_references.add(new_task)
        new_task.add_done_callback(task_references.remove)

    async def __client_setup(
        self, tcp_reader: StreamReader, client_builder: ClientBuilder
    ):
        uuid = await tcp_reader.readexactly(16)
        client_builder.uuid = UUID(bytes=uuid)

        if client_builder.uuid in self._clients:
            # Client is reconnecting
            client = self._clients[client_builder.uuid]
            try:
                await client.reconnect(client_builder.reader, client_builder.writer)
            except ConnectionError:
                pass
            else:
                if self._client_reconnect_callback:
                    await self._client_reconnect_callback(client)
                return

        client = client_builder.construct()
        self._clients[client.uuid] = client

        await self._new_connection_callback(client)
        client.start_receiving(self._received_message_callback)

    def start(self, host, port):
        async def runner():
            server = await asyncio.start_server(self.__new_client, host=host, port=port)
            async with server:
                await server.serve_forever()

        asyncio.run(runner())

    def on_new_connection(
        self, coro: Callable[[Client], Awaitable]
    ) -> Callable[[Client], Awaitable]:
        async def wrapper(client: Client):
            try:
                await coro(client)
            except Exception as e:
                traceback.print_exception(e, file=sys.stderr)

        self._new_connection_callback = wrapper
        return wrapper

    def on_receiving_message(
        self, coro: Callable[[Message], Awaitable]
    ) -> Callable[[Message], Awaitable]:
        async def wrapper(message: Message):
            try:
                await coro(message)
            except Exception as e:
                traceback.print_exception(e, file=sys.stderr)

        self._received_message_callback = wrapper
        return wrapper

    def on_client_disconnect(
        self, coro: Callable[[Client], Awaitable]
    ) -> Callable[[Client], Awaitable]:
        async def wrapper(client: Client):
            del self._clients[client.uuid]
            try:
                await coro(client)
            except Exception as e:
                traceback.print_exception(e, file=sys.stderr)

        self._client_disconnect_callback = wrapper
        return wrapper

    def on_client_reconnect(
        self, coro: Callable[[Client], Awaitable]
    ) -> Callable[[Client], Awaitable]:
        async def wrapper(client: Client):
            try:
                await coro(client)
            except Exception as e:
                traceback.print_exception(e, file=sys.stderr)

        self._client_reconnect_callback = wrapper
        return wrapper


class Group:
    ...
