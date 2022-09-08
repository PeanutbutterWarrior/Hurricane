from __future__ import annotations

from asyncio import StreamReader
from datetime import datetime
from typing import Any, TYPE_CHECKING
import struct
from Hurricane import serialisation

if TYPE_CHECKING:
    from Hurricane import server


class Message:
    HEADER_SIZE = 12

    def __init__(self,
                 contents: Any,
                 author: server.Client,
                 sent_at: datetime,
                 received_at: datetime
                 ):
        
        self.contents: Any = contents
        self.sent_at: datetime = sent_at
        self.received_at: datetime = received_at
        self.author: server.Client = author

    @staticmethod
    async def read_stream(author: server.Client, connection: StreamReader) -> Message:
        header = await connection.readexactly(Message.HEADER_SIZE)
        message_size, time_sent = struct.unpack('!Id', header)
        received_data = await connection.readexactly(message_size)

        time_received = datetime.now()
        time_sent = datetime.fromtimestamp(time_sent)
        contents = serialisation.loads(received_data)

        return Message(contents, author, time_sent, time_received)
