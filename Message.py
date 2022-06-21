from __future__ import annotations

from asyncio import StreamReader
from datetime import datetime
import struct

class Message:
    HEADER_SIZE = 12

    def __init__(self, contents: bytes, sent_at: datetime, recieved_at: datetime) -> Message:
        self.contents = contents
        self.sent_at = sent_at
        self.recieved_at = recieved_at

    @staticmethod
    async def from_StreamReader(connection: StreamReader) -> Message:
        header = await connection.readexactly(Message.HEADER_SIZE)
        message_size, time_sent = struct.unpack('!Id', header)

        contents = await connection.readexactly(message_size)

        time_sent = datetime.fromtimestamp(time_sent)
        time_recieved = datetime.now()

        return Message(contents, time_sent, time_recieved)

    # author: Client
    # contents: str
    # sent_at: datetime
    # recieved_at: datetime
