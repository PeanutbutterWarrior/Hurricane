import abc
from Crypto.Cipher import AES
import hmac
from itertools import count
import os
from typing import Iterator, TYPE_CHECKING

if TYPE_CHECKING:
    from Crypto.Cipher._mode_ctr import CtrMode as CtrAES


class BaseEncryption(abc.ABC):
    def __init__(self, secret: bytes | None = None):
        self._secret: bytes
        if secret is None:
            self._secret = os.urandom(32)
        else:
            self._secret = secret
        self._server_counter: Iterator[int] = count()
        self._client_counter: Iterator[int] = count(start=2**63)

    @abc.abstractmethod
    def get_encryption_nonce(self) -> int:
        ...

    @abc.abstractmethod
    def get_decryption_nonce(self) -> int:
        ...

    @property
    def aes_secret(self) -> bytes:
        return self._secret

    def get_aes_key(self, nonce: bytes) -> CtrAES:
        return AES.new(self._secret, AES.MODE_CTR, nonce=nonce)

    def get_hmac(self, data: bytes) -> bytes:
        return hmac.digest(self._secret, data, "sha256")

    def encrypt(self, data: bytes) -> bytes:
        aes_key = self.get_aes_key(
            self.get_encryption_nonce().to_bytes(8, "big", signed=False)
        )
        encrypted_data = aes_key.encrypt(data)
        hmac_digest = self.get_hmac(encrypted_data)
        return hmac_digest + encrypted_data

    def decrypt(self, data: bytes) -> bytes:
        hmac_digest_received, encrypted_data = data[:32], data[32:]
        hmac_digest_computed = self.get_hmac(encrypted_data)
        if not hmac.compare_digest(hmac_digest_received, hmac_digest_computed):
            raise ValueError("HMAC is incorrect")

        aes_key = self.get_aes_key(
            self.get_decryption_nonce().to_bytes(8, "big", signed=False)
        )
        return aes_key.decrypt(encrypted_data)


class ServerEncryption(BaseEncryption):
    def get_encryption_nonce(self) -> int:
        return next(self._server_counter)

    def get_decryption_nonce(self) -> int:
        return next(self._client_counter)


class ClientEncryption(BaseEncryption):
    def get_encryption_nonce(self) -> int:
        return next(self._client_counter)

    def get_decryption_nonce(self) -> int:
        return next(self._server_counter)
