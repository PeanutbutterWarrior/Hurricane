from __future__ import annotations
from typing import Coroutine, List, Awaitable, Callable

import asyncio
from datetime import datetime

from Message import Message

# Used to keep a reference to any tasks
# asyncio.create_task only creates a weak reference to the task
# If no other reference is kept, the garbage collector can destroy it before the task runs
# A callback to discard() should be used to remove the task once it has finished running
# See https://docs.python.org/3/library/asyncio-task.html#creating-tasks
task_references = set()


class Server:
    def __init__(self):
        self._clients: List[Client] = []
        self._new_connection_callback: Callable[[Client], Awaitable] = None
        self._recieved_message_callback: Callable[[Message], Awaitable] = None

    def __new_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        new_client = Client(reader, writer, None, None)
        self._clients.append(new_client)

        if self._new_connection_callback:
            new_connection_task = asyncio.create_task(self._new_connection_callback(new_client))

            if self._recieved_message_callback:
                new_connection_task.add_done_callback(
                    lambda _: new_client.start_recieving(self._recieved_message_callback)
                )

            new_connection_task.add_done_callback(task_references.discard)
            task_references.add(new_connection_task)
        
        elif self._recieved_message_callback:
            new_client.start_recieving(self._recieved_message_callback)
        

    def start(self, host, port):
        async def runner():
            server = await asyncio.start_server(self.__new_client, host=host, port=port)
            async with server:
                await server.serve_forever()

        asyncio.run(runner())

    def on_new_connection(self, coro: Callable[[Client], Awaitable]) -> Callable[[Client], Awaitable]:
        self._new_connection_callback = coro
        return coro
    
    def on_recieving_message(self, coro: Callable[[Message], Awaitable]) -> Callable[[Message], Awaitable]:
        self._recieved_message_callback = coro
        return coro


class Client:
    def __init__(self,
                 tcp_reader: asyncio.StreamReader,
                 tcp_writer: asyncio.StreamWriter,
                 udp_reader: asyncio.StreamReader,
                 udp_writer: asyncio.StreamWriter,
                 ):

        self.__tcp_reader: asyncio.StreamReader = tcp_reader
        self.__tcp_writer: asyncio.StreamWriter = tcp_writer
        self.__socket_read_task = None

    async def _wait_for_read(self, callback: Callable[[Message], Awaitable]):
        while True:
            message = await Message.from_StreamReader(self, self.__tcp_reader)
            asyncio.create_task(callback(message))

    def start_recieving(self, callback:  Callable[[Message], Awaitable]):
        if not self.__socket_read_task:
            self.__socket_read_task = asyncio.create_task(
                self._wait_for_read(callback)
            )

    async def send(self, data: bytes):
        self.__tcp_writer.write(data)
        await self.__tcp_writer.drain()


class Group:
    ...
