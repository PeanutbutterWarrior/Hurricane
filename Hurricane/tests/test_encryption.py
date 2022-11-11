from Hurricane import encryption
import pytest
import os


# Makes os.urandom only a single byte
# Automatically applied to all tests
@pytest.fixture(autouse=True)
def no_randomness(monkeypatch):
    def deterministic_bytes(x):
        return b'A' * x
    monkeypatch.setattr(os, 'urandom', deterministic_bytes)


class TestBaseEncryption:
    def test_key_generation(self):
        encrypter = encryption.ServerEncryption()
        assert encrypter.aes_secret == b'A' * 32

    def test_encryption(self):
        encrypter = encryption.ServerEncryption()
        data = b'hello'
        encrypted_data_1 = encrypter.encrypt(data)
        encrypted_data_2 = encrypter.encrypt(data)
        assert data != encrypted_data_1
        assert data != encrypted_data_2
        assert encrypted_data_1 != encrypted_data_2

    def test_decryption(self):
        server_encrypter = encryption.ServerEncryption()
        client_encrypter = encryption.ClientEncryption()
        data = b'world'
        encrypted_data = server_encrypter.encrypt(data)
        assert client_encrypter.decrypt(encrypted_data) == data
        encrypted_data = client_encrypter.encrypt(data)
        assert server_encrypter.decrypt(encrypted_data) == data

    def test_tamper_protection(self):
        server_encrypter = encryption.ServerEncryption()
        client_encrypter = encryption.ClientEncryption()
        data = b'hello'
        encrypted_data = server_encrypter.encrypt(data)
        tampered_data = b'0' + encrypted_data[1:]
        with pytest.raises(ValueError):
            client_encrypter.decrypt(tampered_data)


class TestServerEncryption:
    def test_get_nonces(self):
        encrypter = encryption.ServerEncryption()
        assert encrypter.get_encryption_nonce() == 0
        assert encrypter.get_encryption_nonce() == 1
        assert encrypter.get_encryption_nonce() == 2

        assert encrypter.get_decryption_nonce() == 2 ** 63
        assert encrypter.get_decryption_nonce() == 2 ** 63 + 1
        assert encrypter.get_decryption_nonce() == 2 ** 63 + 2


class TestClientEncryption:
    def test_get_nonces(self):
        encrypter = encryption.ClientEncryption()
        assert encrypter.get_encryption_nonce() == 2 ** 63
        assert encrypter.get_encryption_nonce() == 2 ** 63 + 1
        assert encrypter.get_encryption_nonce() == 2 ** 63 + 2

        assert encrypter.get_decryption_nonce() == 0
        assert encrypter.get_decryption_nonce() == 1
        assert encrypter.get_decryption_nonce() == 2
