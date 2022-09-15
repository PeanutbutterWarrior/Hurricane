import asyncio
from asyncio import StreamReader, StreamWriter
from enum import Enum
import struct
from typing import Any, Callable, Coroutine
from datetime import datetime
from uuid import UUID

from Hurricane.message import Message
from Hurricane import serialisation


class ClientState(Enum):
    OPEN = 1
    DISCONNECTED = 2
    CLOSED = 3


class Client:
    def __init__(self,
                 tcp_reader: StreamReader,
                 tcp_writer: StreamWriter,
                 uuid: UUID,
                 client_disconnect_callback,
                 reconnect_timeout: int,
                 ):

        self.__tcp_reader: StreamReader = tcp_reader
        self.__tcp_writer: StreamWriter = tcp_writer
        self.__state: ClientState = ClientState.OPEN
        self.__uuid: UUID = uuid
        self.__socket_read_task = None
        self.__reconnect_wait_task = None

        self._client_disconnect_callback: Callable[[Client], Coroutine] = client_disconnect_callback

        self.peer_address: tuple[str, int] = tcp_writer.transport.get_extra_info("peername")
        self.reconnect_timeout = reconnect_timeout

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
                # TODO do not drop exception and use partial read when reconnected

                # EOF was received, nothing more can be read
                # Assume that the client has stopped listening
                self.__state = ClientState.DISCONNECTED

                self.__reconnect_wait_task = asyncio.create_task(asyncio.sleep(self.reconnect_timeout))
                try:
                    await self.__reconnect_wait_task
                except asyncio.CancelledError:
                    # Client.reconnect has been called, no action needed
                    self.__reconnect_wait_task = None
                else:
                    # Client did not reconnect within the timeout
                    break
            else:
                asyncio.create_task(callback(message))
        
        # This must be set here to avoid Client.reconnect failing silently
        # If it waited for the event loop to schedule self.shutdown(), another coroutine could call Client.reconnect
        # but the reading loop would not be re-entered, disconnecting the client
        self.__state = ClientState.CLOSED
        await self.shutdown()
        self.__socket_read_task = None

    def start_receiving(self, callback: Callable[[Message], Coroutine]):
        if not self.__socket_read_task:
            self.__socket_read_task = asyncio.create_task(
                self._wait_for_read(callback)
            )
    
    def reconnect(self, tcp_reader: StreamReader, tcp_writer: StreamWriter):
        if self.__state == ClientState.CLOSED:
            # This has been scheduled before self.shutdown(), but after the read loop has been exited
            # Reconnection is not possible
            raise ConnectionError

        self.__tcp_reader = tcp_reader
        self.__tcp_writer = tcp_writer
        self.__reconnect_wait_task.cancel()
        self.__state = ClientState.OPEN

    async def send(self, message: Any):
        data = serialisation.dumps(message)
        header = struct.pack('!Id', len(data), datetime.now().timestamp())
        self.__tcp_writer.write(header)
        self.__tcp_writer.write(data)
        await self.__tcp_writer.drain()

    async def shutdown(self):
        self.__state = ClientState.CLOSED
        self.__tcp_writer.close()
        await asyncio.gather(self.__tcp_writer.wait_closed(), self._client_disconnect_callback(self))


class ClientBuilder:
    def __init__(self):
        self.reader: StreamReader | None = None
        self.writer: StreamWriter | None = None
        self.disconnect_callback: Callable[[Client], Coroutine] | None = None
        self.uuid: UUID | None = None
        self.reconnect_timeout: int | None = None

    def construct(self) -> Client:
        return Client(
            self.reader,
            self.writer,
            self.uuid,
            self.disconnect_callback,
            self.reconnect_timeout,
        )
