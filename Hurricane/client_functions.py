from __future__ import annotations

import socket
import struct
from datetime import datetime
from typing import Any, TYPE_CHECKING
import os

from Hurricane.message import Message
from Hurricane import serialisation

from Crypto.PublicKey import RSA
from Crypto.Cipher import AES, PKCS1_OAEP

from Crypto.Hash import HMAC, SHA256
from Crypto.Signature.pss import MGF1


def send_message(
    contents: Any, connection: socket.socket, aes_secret: bytes, nonce: bytes
):
    aes_key = AES.new(aes_secret, AES.MODE_CTR, nonce=nonce)

    data = serialisation.dumps(contents)
    header = struct.pack("!d", datetime.now().timestamp())
    plaintext = header + data
    ciphertext = aes_key.encrypt(plaintext)

    connection.send(len(ciphertext).to_bytes(2, "big", signed=False))
    connection.send(ciphertext)


def receive_message(
    connection: socket.socket, aes_secret: bytes, nonce: bytes
) -> (Any, datetime, datetime):
    message_size = connection.recv(2)
    message_size = int.from_bytes(message_size, "big", signed=False)

    aes_key = AES.new(aes_secret, AES.MODE_CTR, nonce=nonce)

    data = connection.recv(message_size)
    received_at = datetime.now()
    data = aes_key.decrypt(data)
    sent_at, contents = data[:8], data[8:]
    sent_at = datetime.fromtimestamp(struct.unpack("!d", sent_at)[0])
    contents = serialisation.loads(contents)

    return contents, sent_at, received_at


def handshake(connection: socket.socket) -> bytes:
    n = connection.recv(256)
    n = int.from_bytes(n, "big", signed=False)
    e = connection.recv(256)
    e = int.from_bytes(e, "big", signed=False)
    rsa_key = RSA.construct((n, e))
    rsa_cipher = PKCS1_OAEP.new(rsa_key)

    aes_secret = os.urandom(32)

    sending = rsa_cipher.encrypt(aes_secret)
    connection.sendall(sending)

    return aes_secret
