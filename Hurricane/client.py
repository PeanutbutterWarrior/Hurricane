from __future__ import annotations

import asyncio
from asyncio import StreamReader, StreamWriter
from asyncio.locks import Event
from Crypto.Cipher import AES
from datetime import datetime
from enum import Enum
import itertools
import struct
from typing import Any, Callable, Coroutine, Iterator
from uuid import UUID


from Hurricane.message import Message
from Hurricane import serialisation
from Hurricane.queue import Queue


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
        encryption: bool,
        aes_secret: bytes,
    ):

        self.__tcp_reader: StreamReader = tcp_reader
        self.__tcp_writer: StreamWriter = tcp_writer
        self.__state: ClientState = ClientState.OPEN
        self.__uuid: UUID = uuid
        self.__encryption = encryption
        self.__socket_read_task = None
        self.__disconnect_task_handle = None
        self.__message_dispatch_task = None
        self.__outgoing_message_queue: Queue[Any] = Queue()
        self.__incoming_message_queue: Queue[Message] = Queue()
        self.__reconnect_event: Event = Event()
        self.__aes_secret: bytes = aes_secret
        self.__aes_counter: Iterator[int] = itertools.count()

        self._client_disconnect_callback: Callable[
            [Client], Coroutine
        ] = client_disconnect_callback

        self.peer_address: tuple[str, int] = tcp_writer.transport.get_extra_info(
            "peername"
        )
        self.reconnect_timeout = reconnect_timeout

    def __hash__(self):
        return self.__uuid.int

    @property
    def state(self) -> ClientState:
        return self.__state

    @property
    def uuid(self) -> UUID:
        return self.__uuid

    async def _read_from_socket(self):
        while True:
            try:
                message_size = await self.__tcp_reader.readexactly(2)
                message_size = int.from_bytes(message_size, "big", signed=False)

                data = await self.__tcp_reader.readexactly(message_size)
                aes_key = AES.new(
                    self.__aes_secret, AES.MODE_CTR, nonce=self._aes_nonce()
                )
                data = aes_key.decrypt(data)
                received_at = datetime.now()
                sent_at, contents = data[:8], data[8:]
                sent_at = datetime.fromtimestamp(struct.unpack("!d", sent_at)[0])
                contents = serialisation.loads(contents)

                message = Message(contents, sent_at, received_at, self)

                self.__incoming_message_queue.push(message)
            except asyncio.IncompleteReadError:  # TODO do not drop exception and use partial read when reconnected
                # EOF was received, nothing more can be read
                # Assume that the client has stopped listening
                self.__reconnect_event.clear()
                self.__state = ClientState.RECONNECTING
                self.__disconnect_task_handle = asyncio.get_running_loop().call_later(
                    self.reconnect_timeout, self.shutdown
                )
                await self.__reconnect_event.wait()

    async def _dispatch_messages_to_callback(
        self, callback: Callable[[Message], Coroutine]
    ):
        while True:
            message = await self.__incoming_message_queue.async_pop()
            await callback(message)

    def _aes_nonce(self):
        return next(self.__aes_counter).to_bytes(8, "big", signed=False)

    def start_receiving(self, callback: Callable[[Message], Coroutine]):
        if not self.__socket_read_task:
            self.__socket_read_task = asyncio.create_task(self._read_from_socket())
            self.__message_dispatch_task = asyncio.create_task(
                self._dispatch_messages_to_callback(callback)
            )

    async def reconnect(self, proto: ClientBuilder):
        self.__tcp_reader = proto.reader
        self.__tcp_writer = proto.writer
        self.__aes_secret = proto.aes_secret
        self.__disconnect_task_handle.cancel()
        self.__state = ClientState.OPEN

        while self.__outgoing_message_queue:
            await self.send(self.__outgoing_message_queue.pop())
        self.__reconnect_event.set()

    async def send(self, message: Any):
        if self.state == ClientState.RECONNECTING:
            self.__outgoing_message_queue.push(message)
            return

        data = serialisation.dumps(message)
        header = struct.pack("!d", datetime.now().timestamp())
        plaintext = header + data

        aes_key = AES.new(self.__aes_secret, AES.MODE_CTR, nonce=self._aes_nonce())
        ciphertext = aes_key.encrypt(plaintext)
        self.__tcp_writer.write(len(ciphertext).to_bytes(2, "big", signed=False))
        self.__tcp_writer.write(ciphertext)
        await self.__tcp_writer.drain()

    async def receive(self) -> Message:
        return await self.__incoming_message_queue.async_pop()

    def shutdown(self):
        self.__state = ClientState.CLOSED
        self.__tcp_writer.close()
        self.__socket_read_task.cancel()
        self.__socket_read_task = None
        self.__message_dispatch_task.cancel()
        self.__message_dispatch_task = None

        asyncio.create_task(
            self._client_disconnect_callback(self)
        )  # TODO keep reference, maybe delegate to Server?


class ClientBuilder:
    def __init__(self):
        self.reader: StreamReader | None = None
        self.writer: StreamWriter | None = None
        self.disconnect_callback: Callable[[Client], Coroutine] | None = None
        self.uuid: UUID | None = None
        self.reconnect_timeout: int | None = None
        self.encryption: bool | None = None
        self.aes_secret: bytes | None = None

    def construct(self) -> Client:
        return Client(
            self.reader,
            self.writer,
            self.uuid,
            self.disconnect_callback,
            self.reconnect_timeout,
            self.encryption,
            self.aes_secret,
        )
