import socket
from Hurricane.client_functions import ServerConnection

while True:
    with ServerConnection('localhost', 65432, socket.AF_INET, socket.SOCK_STREAM) as s:
        while True:
            message = input("> ")
            s.send(message)
            print(f"Received {s.recv()}")
