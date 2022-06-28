from Hurricane import serialisation
import pytest


class TestInt:
    def test_five(self):
        five = 5
        five_serialised = serialisation.serialise(five)
        assert five_serialised == b"\x01\x00\x01\x05"
        assert serialisation.deserialise(five_serialised) == five

    def test_zero(self):
        zero = 0
        zero_serialised = serialisation.serialise(zero)
        assert zero_serialised == b"\x01\x00\x01\x00"
        assert serialisation.deserialise(zero_serialised) == zero

    def test_negative(self):
        minus_three = -3
        minus_three_serialised = serialisation.serialise(minus_three)
        assert minus_three_serialised == b"\x01\x00\x01\xFD"
        assert serialisation.deserialise(minus_three_serialised) == minus_three

    def test_large(self):
        large = 460843424409  # Minimum of 5 bytes
        large_serialised = serialisation.serialise(large)
        assert serialisation.deserialise(large_serialised) == large

    def test_too_large(self):
        with pytest.raises(serialisation.ObjectTooLargeException):
            serialisation.serialise(2 ** (64 * 1024 * 8) + 1)


class TestStr:
    def test_small(self):
        message = 'Hello Serialiser'
        serialised = serialisation.serialise(message)
        assert serialised == b'\x02\x00\x10Hello Serialiser'
        assert serialisation.deserialise(serialised) == message

    def test_large(self):
        message = 'testing' * 1000
        serialised = serialisation.serialise(message)
        assert serialisation.deserialise(serialised) == message

    def test_empty(self):
        message = ''
        serialised = serialisation.serialise(message)
        assert serialised == b'\x02\x00\x00'
        assert serialisation.deserialise(serialised) == message

    def test_utf8(self):
        message = 'Њଛp!\x00▰👋'
        serialised = serialisation.serialise(message)
        assert serialisation.deserialise(serialised) == message

    def test_malformed_utf8(self):
        malformed_data = b'\x02\x00\x03\xE2\x06\xB0'
        with pytest.raises(serialisation.MalformedDataError):
            serialisation.deserialise(malformed_data)

    def test_wrong_size(self):
        malformed = b'\x02\x00\x05abc'
        assert serialisation.deserialise(malformed) == 'abc'
        malformed = b'\x02\x00\x02abc'
        assert serialisation.deserialise(malformed) == 'ab'
