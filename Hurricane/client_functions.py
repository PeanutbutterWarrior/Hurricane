from __future__ import annotations

from Crypto.Cipher import PKCS1_OAEP
from Crypto.PublicKey import RSA
from datetime import datetime
import socket
import struct
from typing import Any
from uuid import uuid4


from Hurricane import serialisation
from Hurricane.message import AnonymousMessage
from Hurricane.encryption import ClientEncryption


class ServerConnection:
    def __init__(
        self,
        address: str,
        port: int,
        family: socket.AddressFamily = socket.AF_INET,
        type: socket.SocketKind = socket.SOCK_STREAM,  # Shadows builtin 'type()', kept to match socket.socket()
        proto: int = 0,
        fileno: int = None,
    ) -> None:
        self._socket = socket.socket(
            family=family, type=type, proto=proto, fileno=fileno
        )
        self._address = address
        self._port = port
        self._socket.connect((address, port))
        self._prepare_encryption()
        self._create_uuid()
        self._send_uuid()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._socket.shutdown(0)
        self._socket.close()

    def _prepare_encryption(self):
        n = int.from_bytes(self._socket.recv(256), "big", signed=False)
        e = int.from_bytes(self._socket.recv(256), "big", signed=False)
        rsa_key = RSA.construct((n, e))
        rsa_cipher = PKCS1_OAEP.new(rsa_key)

        self._encrypter: ClientEncryption = ClientEncryption()

        aes_secret_encrypted = rsa_cipher.encrypt(self._encrypter.aes_secret)
        self._socket.sendall(aes_secret_encrypted)

    def _create_uuid(self) -> None:
        self._uuid = uuid4()

    def _send_uuid(self) -> None:
        encrypted_uuid = self._encrypter.encrypt(self._uuid.bytes)
        self._socket.sendall(encrypted_uuid)

    def _reconnect(self) -> None:
        print("reconnecting")
        new_socket = socket.socket(self._socket.family, self._socket.type, self._socket.proto)
        new_socket.connect((self._address, self._port))
        self._socket = new_socket
        self._prepare_encryption()
        self._send_uuid()

    @staticmethod
    def from_socket(sock: socket.socket) -> ServerConnection:
        obj = ServerConnection.__new__(ServerConnection)
        obj._socket = sock
        obj._prepare_encryption()
        obj._create_uuid()
        obj._send_uuid()
        return obj

    @property
    def socket(self) -> socket.socket:
        return self._socket

    def send(self, message: Any) -> None:
        data = serialisation.dumps(message)
        header = struct.pack("!d", datetime.now().timestamp())
        plaintext = header + data
        ciphertext = self._encrypter.encrypt(plaintext)

        try:
            self._socket.sendall(len(ciphertext).to_bytes(2, "big", signed=False))
            self._socket.sendall(ciphertext)
        except (ConnectionError, OSError):
            self._reconnect()

    def recv(self) -> AnonymousMessage:
        while True:
            try:
                message_size = self._socket.recv(2)
            except (ConnectionError, OSError):
                self._reconnect()
                continue

            if not message_size:
                self._reconnect()
                continue

            message_size = int.from_bytes(message_size, "big", signed=False)

            try:
                encrypted_data = self._socket.recv(message_size)
                received_at = datetime.now()
            except (ConnectionError, OSError):
                self._reconnect()
                continue

            if not encrypted_data:
                self._reconnect()
                continue

            raw_data = self._encrypter.decrypt(encrypted_data)
            sent_at_bytes, data = raw_data[:8], raw_data[8:]

            sent_at = datetime.fromtimestamp(struct.unpack("!d", sent_at_bytes)[0])
            contents = serialisation.loads(data)

            return AnonymousMessage(contents, sent_at, received_at)
