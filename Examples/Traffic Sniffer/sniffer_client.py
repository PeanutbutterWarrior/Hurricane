from Hurricane.client_functions import ServerConnection
import socket


class MockSocket:
    def __init__(self, sock):
        self.socket = sock

    def sendall(self, data):
        print("send", data.hex())
        self.socket.sendall(data)

    def recv(self, amount):
        data = self.socket.recv(amount)
        print("recv", data.hex())
        return data

    def close(self):
        self.socket.close()

    def shutdown(self, x):
        self.socket.shutdown(x)


with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.connect(("localhost", 65432))
    mock_socket = MockSocket(s)
    with ServerConnection.from_socket(mock_socket) as server:
        server.send("Hello")
        server.send(True)
        server.send(None)
        server.send([1, 2, 3])
