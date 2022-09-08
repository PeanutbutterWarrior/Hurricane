import socket
import struct
from datetime import datetime
from typing import Any

from Hurricane.Message import Message
from Hurricane import serialisation


def send_message(contents: Any, connection: socket.socket):
    data = serialisation.dumps(contents)
    header = struct.pack('!Id', len(data), datetime.now().timestamp())
    connection.send(header)
    connection.send(data)


def receive_message(connection: socket.socket) -> (Any, datetime, datetime):
    header = connection.recv(Message.HEADER_SIZE)
    message_size, time_sent = struct.unpack('!Id', header)

    recieved_data = connection.recv(message_size)

    time_received = datetime.now()
    time_sent = datetime.fromtimestamp(time_sent)

    contents = serialisation.loads(recieved_data)

    return contents, time_sent, time_received
