from __future__ import annotations
from typing import List, Awaitable, Callable, Optional, Coroutine

import asyncio

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
        self._new_connection_callback: Optional[Callable[[Client], Coroutine]] = None
        self._recieved_message_callback: Optional[Callable[[Message], Coroutine]] = None
        self._client_disconnect_callback: Optional[Callable[[Client], Coroutine]] = None

    def __new_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        new_client = Client(reader, writer, self._client_disconnect_callback)
        self._clients.append(new_client)

        if self._new_connection_callback:
            new_connection_task = asyncio.create_task(self._new_connection_callback(new_client))

            if self._received_message_callback:
                new_connection_task.add_done_callback(
                    lambda _: new_client.start_receiving(self._received_message_callback)
                )

            new_connection_task.add_done_callback(task_references.discard)
            task_references.add(new_connection_task)

        elif self._received_message_callback:
            new_client.start_receiving(self._received_message_callback)

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

    async def _wait_for_read(self, callback: Callable[[Message], Coroutine]):
        while True:
            try:
                message = await Message.from_StreamReader(self, self.__tcp_reader)
            except asyncio.IncompleteReadError:
                # Recieved an empty string from the socket
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

    async def send(self, data: bytes):
        self.__tcp_writer.write(data)
        await self.__tcp_writer.drain()

    async def shutdown(self):
        self.__tcp_writer.close()
        await self.__tcp_writer.wait_closed()



class Group:
    ...
