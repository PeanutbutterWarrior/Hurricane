import socket
from uuid import uuid4
from Hurricane.client_functions import receive_message, send_message, handshake
from itertools import count

uuid = uuid4()
aes_counter = count()
while True:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect(("localhost", 65432))
        s.sendall(uuid.bytes)
        aes_key = handshake(s)
        while True:
            message = input("> ")
            if message == "reconnect":
                break
            send_message(
                message, s, aes_key, next(aes_counter).to_bytes(8, "big", signed=False)
            )
            reply, sent_at, received_at = receive_message(
                s, aes_key, next(aes_counter).to_bytes(8, "big", signed=False)
            )
            print(f'"{reply}" received at {received_at}, sent at {sent_at}')
