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
        address,
        port,
        family=socket.AF_INET,
        type=socket.SOCK_STREAM,  # Shadows builtin 'type()', kept to match socket.socket()
        proto=0,
        fileno=None,
    ):
        self._socket = socket.socket(
            family=family, type=type, proto=proto, fileno=fileno
        )
        self._socket.connect((address, port))
        self._prepare_encryption()
        self._prepare_uuid()

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

    def _prepare_uuid(self):
        self._uuid = uuid4()
        encrypted_uuid = self._encrypter.encrypt(self._uuid.bytes)
        self._socket.sendall(encrypted_uuid)

    @staticmethod
    def from_socket(sock: socket.socket):
        obj = ServerConnection.__new__(ServerConnection)
        obj._socket = sock
        obj._prepare_encryption()
        obj._prepare_uuid()
        return obj

    @property
    def socket(self):
        return self._socket

    def send(self, message: Any):
        data = serialisation.dumps(message)
        header = struct.pack("!d", datetime.now().timestamp())
        plaintext = header + data
        ciphertext = self._encrypter.encrypt(plaintext)

        self._socket.sendall(len(ciphertext).to_bytes(2, "big", signed=False))
        self._socket.sendall(ciphertext)

    def recv(self) -> AnonymousMessage:
        message_size = self._socket.recv(2)
        message_size = int.from_bytes(message_size, "big", signed=False)

        encrypted_data = self._socket.recv(message_size)
        received_at = datetime.now()

        raw_data = self._encrypter.decrypt(encrypted_data)
        sent_at, data = raw_data[:8], raw_data[8:]

        sent_at = datetime.fromtimestamp(struct.unpack("!d", sent_at)[0])
        contents = serialisation.loads(data)

        return AnonymousMessage(contents, sent_at, received_at)
