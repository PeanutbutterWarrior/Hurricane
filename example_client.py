import socket
from uuid import uuid4
from Hurricane.client_functions import receive_message, send_message

uuid = uuid4()
while True:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect(("localhost", 65432))
        s.sendall(uuid.bytes)
        while True:
            message = input("> ")
            if message == "reconnect":
                break
            send_message(message, s)
            print("Message sent")
            reply, sent_at, received_at = receive_message(s)
            print(f'"{reply}" received at {received_at}, sent at {sent_at}')

