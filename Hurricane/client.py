from __future__ import annotations

import asyncio
from asyncio import StreamReader, StreamWriter
from asyncio.locks import Event
from datetime import datetime
from enum import Enum
import struct
from typing import Any, Callable, Coroutine
from uuid import UUID


from Hurricane.message import Message
from Hurricane import serialisation
from Hurricane.queue import Queue
from Hurricane.encryption import ServerEncryption


class ClientState(Enum):
    OPEN = 1
    RECONNECTING = 2
    CLOSED = 3


class Client:
    def __init__(
        self,
        tcp_reader: StreamReader,
        tcp_writer: StreamWriter,
        uuid: UUID,
        client_disconnect_callback,
        reconnect_timeout: int,
        encrypter: ServerEncryption,
    ):

        self._tcp_reader: StreamReader = tcp_reader
        self._tcp_writer: StreamWriter = tcp_writer
        self._state: ClientState = ClientState.OPEN
        self._uuid: UUID = uuid
        self._socket_read_task = None
        self._disconnect_task_handle = None
        self._message_dispatch_task = None
        self._outgoing_message_queue: Queue[Any] = Queue()
        self._incoming_message_queue: Queue[Message] = Queue()
        self._reconnect_event: Event = Event()
        self._encrypter: ServerEncryption = encrypter

        self._client_disconnect_callback: Callable[
            [Client], Coroutine
        ] = client_disconnect_callback

        self.peer_address: tuple[str, int] = tcp_writer.transport.get_extra_info(
            "peername"
        )
        self.reconnect_timeout = reconnect_timeout

    def __hash__(self):
        return self._uuid.int

    @property
    def state(self) -> ClientState:
        return self._state

    @property
    def uuid(self) -> UUID:
        return self._uuid

    async def _read_from_socket(self):
        while True:
            try:
                message_size = await self._tcp_reader.readexactly(2)
                message_size = int.from_bytes(message_size, "big", signed=False)

                encrypted_data = await self._tcp_reader.readexactly(message_size)
                received_at = datetime.now()

                raw_data = self._encrypter.decrypt(encrypted_data)
                sent_at, data = raw_data[:8], raw_data[8:]  # Double is 8 bytes long

                sent_at = datetime.fromtimestamp(struct.unpack("!d", sent_at)[0])
                contents = serialisation.loads(data)

                message = Message(contents, sent_at, received_at, self)

                self._incoming_message_queue.push(message)
            except asyncio.IncompleteReadError:
                # EOF was received, nothing more can be read
                # Assume that the client has stopped listening
                self._reconnect_event.clear()
                self._state = ClientState.RECONNECTING
                self._disconnect_task_handle = asyncio.get_running_loop().call_later(
                    self.reconnect_timeout, self.shutdown
                )
                await self._reconnect_event.wait()

    async def _dispatch_messages_to_callback(
        self, callback: Callable[[Message], Coroutine]
    ):
        while True:
            message = await self._incoming_message_queue.async_pop()
            await callback(message)

    def start_receiving(self, callback: Callable[[Message], Coroutine]):
        if not self._socket_read_task:  # Make sure this is idempotent
            self._socket_read_task = asyncio.create_task(self._read_from_socket())
            if callback:
                self._message_dispatch_task = asyncio.create_task(
                    self._dispatch_messages_to_callback(callback)
                )

    async def reconnect(self, proto: ClientBuilder):
        if self._state != ClientState.RECONNECTING:
            raise RuntimeError("Client does not need to reconnect")

        self._tcp_reader = proto.reader
        self._tcp_writer = proto.writer
        self._encrypter = proto.encrypter
        self._disconnect_task_handle.cancel()
        self._state = ClientState.OPEN

        while self._outgoing_message_queue:
            await self.send(self._outgoing_message_queue.pop())
        self._reconnect_event.set()

    async def send(self, message: Any):
        if self.state == ClientState.RECONNECTING:
            self._outgoing_message_queue.push(message)
            return

        data = serialisation.dumps(message)
        header = struct.pack("!d", datetime.now().timestamp())
        plaintext = header + data

        data = self._encrypter.encrypt(plaintext)

        self._tcp_writer.write(len(data).to_bytes(2, "big", signed=False))
        self._tcp_writer.write(data)
        await self._tcp_writer.drain()

    async def receive(self) -> Message:
        return await self._incoming_message_queue.async_pop()

    def shutdown(self):
        self._state = ClientState.CLOSED
        self._tcp_writer.close()
        self._socket_read_task.cancel()
        self._socket_read_task = None
        self._message_dispatch_task.cancel()
        self._message_dispatch_task = None

        if self._client_disconnect_callback:
            asyncio.create_task(
                self._client_disconnect_callback(self)
            )


class ClientBuilder:
    def __init__(self):
        self.reader: StreamReader | None = None
        self.writer: StreamWriter | None = None
        self.disconnect_callback: Callable[[Client], Coroutine] | None = None
        self.uuid: UUID | None = None
        self.reconnect_timeout: int | None = None
        self.encrypter: ServerEncryption | None = None

    def construct(self) -> Client:
        return Client(
            self.reader,
            self.writer,
            self.uuid,
            self.disconnect_callback,
            self.reconnect_timeout,
            self.encrypter,
        )
