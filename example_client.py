import socket
from Hurricane.client_functions import receive_message, send_message


message = "hello server"
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.connect(("localhost", 65432))
    while True:
        send_message(input("> "), s)
        print("Message sent")
        reply, sent_at, received_at = receive_message(s)
        print(f'"{reply}" received at {received_at}, sent at {sent_at}')

