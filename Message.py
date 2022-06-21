from __future__ import annotations

from asyncio import StreamReader
from datetime import datetime
import struct

import Server


class Message:
    HEADER_SIZE = 12

    def __init__(self,
                 contents: bytes,
                 author: Server.Client,
                 sent_at: datetime,
                 received_at: datetime
                 ):
        
        self.contents: bytes = contents
        self.sent_at: datetime = sent_at
        self.received_at: datetime = received_at
        self.author: Server.Client = author

    @staticmethod
    async def from_StreamReader(author: Server.Client, connection: StreamReader) -> Message:
        header = await connection.readexactly(Message.HEADER_SIZE)
        message_size, time_sent = struct.unpack('!Id', header)

        contents = await connection.readexactly(message_size)

        time_sent = datetime.fromtimestamp(time_sent)
        time_received = datetime.now()

        return Message(contents, author, time_sent, time_received)
