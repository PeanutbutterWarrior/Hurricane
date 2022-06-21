import socket
import struct
from datetime import datetime

message = "hello server"
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.connect(("localhost", 65432))
    header = struct.pack('!Id', len(message), datetime.now().timestamp())
    s.sendall(header + message.encode("utf-8"))
    print("Sent data")
