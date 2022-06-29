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
            serialisation.serialise(2 ** (serialisation.MAXIMUM_SIZE * 8) + 1)


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


class TestBool:
    def test_true(self):
        serialised = serialisation.serialise(True)
        assert serialised == b'\x03\x01'
        assert serialisation.deserialise(serialised) is True

    def test_false(self):
        serialised = serialisation.serialise(False)
        assert serialised == b'\x03\x00'
        assert serialisation.deserialise(serialised) is False


class TestList:
    def test_small_homogenous(self):
        li = [2, 3, 1]
        serialised = serialisation.serialise(li)
        assert serialised == b'\x05\x00\x03' + b''.join(serialisation.serialise(i) for i in li)
        assert serialisation.deserialise(serialised) == li

    def test_small_heterogenous(self):
        li = [1, 'bagel', False]
        serialised = serialisation.serialise(li)
        assert serialised == b'\x05\x00\x03' + b''.join(serialisation.serialise(i) for i in li)
        assert serialisation.deserialise(serialised) == li

    def test_large(self):
        li = list(range(0, serialisation.MAXIMUM_SIZE))
        serialised = serialisation.serialise(li)
        assert serialised == b'\x05\xff\xff' + b''.join(serialisation.serialise(i) for i in li)
        assert serialisation.deserialise(serialised) == li

    def test_too_large(self):
        li = list(range(serialisation.MAXIMUM_SIZE + 1))
        with pytest.raises(serialisation.ObjectTooLargeException):
            serialisation.serialise(li)


class TestDict:
    def test_small(self):
        di = {1: 5, 2: 4, 3: 3, 4: 2, 5: 1}
        serialised = serialisation.serialise(di)
        assert serialisation.deserialise(serialised) == di

    def test_heterogenous(self):
        di = {1: True, False: 3, 'abc': 'cba', 'li': ['a', 'b', 'c']}
        serialised = serialisation.serialise(di)
        assert serialisation.deserialise(serialised) == di

    def test_large(self):
        di = dict((i, i + 1) for i in range(serialisation.MAXIMUM_SIZE // 2))
        serialised = serialisation.serialise(di)
        assert serialisation.deserialise(serialised) == di

    def test_nested(self):
        di = {
            1: {'a': 1, 'b': 1},
            2: {'c': 2, 'd': 2},
        }

        serialised = serialisation.serialise(di)
        assert serialisation.deserialise(serialised) == di


class TestSet:
    def test_small(self):
        se = {1, 2, 3}
        serialised = serialisation.serialise(se)
        assert serialisation.deserialise(serialised) == se

    def test_heterogenous(self):
        se = {2, 'abc', False}
        serialised = serialisation.serialise(se)
        assert serialisation.deserialise(serialised) == se

    def test_large(self):
        se = set(range(serialisation.MAXIMUM_SIZE))
        serialised = serialisation.serialise(se)
        assert serialisation.deserialise(serialised) == se

    def test_too_large(self):
        se = set(range(serialisation.MAXIMUM_SIZE + 1))
        with pytest.raises(serialisation.ObjectTooLargeException):
            serialisation.serialise(se)
