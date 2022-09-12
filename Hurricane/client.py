import asyncio
from enum import Enum
import struct
from typing import Any, Callable, Coroutine
from datetime import datetime
from uuid import UUID

from Hurricane.message import Message
from Hurricane import serialisation


class ClientState(Enum):
    OPEN = 1
    CLOSED = 2


class Client:
    def __init__(self,
                 tcp_reader: asyncio.StreamReader,
                 tcp_writer: asyncio.StreamWriter,
                 uuid: UUID,
                 client_disconnect_callback,
                 ):

        self.__tcp_reader: asyncio.StreamReader = tcp_reader
        self.__tcp_writer: asyncio.StreamWriter = tcp_writer
        self.__state: ClientState = ClientState.OPEN
        self.__uuid: UUID = uuid
        self.__socket_read_task = None

        self._client_disconnect_callback: Callable[[Client], Coroutine] = client_disconnect_callback

        self.peer_address: tuple[str, int] = tcp_writer.transport.get_extra_info("peername")

    def __hash__(self):
        return self.__uuid.int

    @property
    def state(self) -> ClientState:
        return self.__state

    @property
    def uuid(self) -> UUID:
        return self.__uuid

    async def _wait_for_read(self, callback: Callable[[Message], Coroutine]):
        while True:
            try:
                message = await Message.read_stream(self, self.__tcp_reader)
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

    async def send(self, message: Any):
        data = serialisation.dumps(message)
        header = struct.pack('!Id', len(data), datetime.now().timestamp())
        self.__tcp_writer.write(header)
        self.__tcp_writer.write(data)
        await self.__tcp_writer.drain()

    async def shutdown(self):
        self.__state = ClientState.CLOSED
        self.__tcp_writer.close()
        await self.__tcp_writer.wait_closed()


class ClientBuilder:
    def __init__(self):
        self.reader: asyncio.StreamReader | None = None
        self.writer: asyncio.StreamWriter | None = None
        self.disconnect_callback: Callable[[Client], Coroutine] | None = None
        self.uuid: UUID | None = None

    def construct(self) -> Client:
        return Client(
            self.reader,
            self.writer,
            self.uuid,
            self.disconnect_callback,
        )
