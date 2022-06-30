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


class TestTuple:
    def test_small(self):
        tup = (1, 'a', True)
        serialised = serialisation.serialise(tup)
        assert serialisation.deserialise(serialised) == tup

    def test_large(self):
        tup = tuple(range(1, serialisation.MAXIMUM_SIZE))
        serialised = serialisation.serialise(tup)
        assert serialisation.deserialise(serialised) == tup

    def test_empty(self):
        serialised = serialisation.serialise(tuple())
        assert serialisation.deserialise(serialised) == tuple()

    def test_too_large(self):
        tup = tuple(range(0, serialisation.MAXIMUM_SIZE + 1))
        with pytest.raises(serialisation.ObjectTooLargeException):
            serialisation.serialise(tup)


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

    def test_empty(self):
        serialised = serialisation.serialise([])
        assert serialisation.deserialise(serialised) == []


class TestDict:
    def test_small(self):
        di = {1: 5, 2: 4, 3: 3, 4: 2, 5: 1}
        serialised = serialisation.serialise(di)
        assert serialisation.deserialise(serialised) == di

    def test_heterogenous(self):
        di = {
            1: True,
            False: 3,
            'abc': 'cba',
            'li': ['a', 'b', 'c']
        }
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

    def test_empty(self):
        serialised = serialisation.serialise({})
        assert serialisation.deserialise(serialised) == {}


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

    def test_empty(self):
        serialised = serialisation.serialise(set())
        assert serialisation.deserialise(serialised) == set()


class TestFloat:
    def test_integer(self):
        serialised = serialisation.serialise(4.0)
        assert serialisation.deserialise(serialised) == 4.0
        assert type(serialisation.deserialise(serialised)) is float

    def test_negative(self):
        num = -7 / 3
        serialised = serialisation.serialise(num)
        assert serialisation.deserialise(serialised) == num

    def test_rational(self):
        serialised = serialisation.serialise(2.5)
        assert serialisation.deserialise(serialised) == 2.5

    def test_irrational(self):
        serialised = serialisation.serialise(5 / 3)
        assert serialisation.deserialise(serialised) == 5 / 3

    def test_inf(self):
        inf = float("inf")
        serialised = serialisation.serialise(inf)
        assert serialisation.deserialise(serialised) == inf

    def test_zero(self):
        serialised = serialisation.serialise(0.0)
        assert serialisation.deserialise(serialised) == 0.0
        assert type(serialisation.deserialise(serialised)) is float

    def test_nan(self):
        nan = float("nan")
        serialised = serialisation.serialise(nan)
        deserialised = serialisation.deserialise(serialised)
        assert deserialised != deserialised  # NaN is the only float not equal to itself


class TestComplex:
    def test_real(self):
        serialised = serialisation.serialise(4 + 0j)
        assert serialisation.deserialise(serialised) == 4 + 0j
        assert type(serialisation.deserialise(serialised)) is complex

    def test_imaginary(self):
        serialised = serialisation.serialise(2j)
        assert serialisation.deserialise(serialised) == 2j
        assert type(serialisation.deserialise(serialised)) is complex

    def test_complex(self):
        serialised = serialisation.serialise(3 + 4j)
        assert serialisation.deserialise(serialised) == 3 + 4j

    def test_float_parts(self):
        serialised = serialisation.serialise(4.5 + 2.3j)
        assert serialisation.deserialise(serialised) == 4.5 + 2.3j


class TestBytes:
    def test_small(self):
        by = b'agd'
        serialised = serialisation.serialise(by)
        assert serialisation.deserialise(serialised) == by

    def test_large(self):
        by = b'abcd' * (serialisation.MAXIMUM_SIZE // 4)
        serialised = serialisation.serialise(by)
        assert serialisation.deserialise(serialised) == by

    def test_empty(self):
        serialised = serialisation.serialise(b'')
        assert serialisation.deserialise(serialised) == b''

    def test_too_large(self):
        with pytest.raises(serialisation.ObjectTooLargeException):
            serialisation.serialise(
                b'a' * (serialisation.MAXIMUM_SIZE + 1)
            )


class TestBytearray:
    def test_small(self):
        by = bytearray(b'agd')
        serialised = serialisation.serialise(by)
        assert serialisation.deserialise(serialised) == by

    def test_large(self):
        by = bytearray(b'abcd' * (serialisation.MAXIMUM_SIZE // 4))
        serialised = serialisation.serialise(by)
        assert serialisation.deserialise(serialised) == by

    def test_empty(self):
        serialised = serialisation.serialise(bytearray())
        assert serialisation.deserialise(serialised) == bytearray()

    def test_too_large(self):
        with pytest.raises(serialisation.ObjectTooLargeException):
            serialisation.serialise(
                bytearray(b'a' * (serialisation.MAXIMUM_SIZE + 1))
            )


class TestFrozenset:
    def test_small(self):
        se = frozenset({1, 2, 3})
        serialised = serialisation.serialise(se)
        assert serialisation.deserialise(serialised) == se

    def test_heterogenous(self):
        se = frozenset({2, 'abc', False})
        serialised = serialisation.serialise(se)
        assert serialisation.deserialise(serialised) == se

    def test_large(self):
        se = frozenset(range(serialisation.MAXIMUM_SIZE))
        serialised = serialisation.serialise(se)
        assert serialisation.deserialise(serialised) == se

    def test_too_large(self):
        se = frozenset(range(serialisation.MAXIMUM_SIZE + 1))
        with pytest.raises(serialisation.ObjectTooLargeException):
            serialisation.serialise(se)

    def test_empty(self):
        serialised = serialisation.serialise(frozenset())
        assert serialisation.deserialise(serialised) == frozenset()


class TestNone:
    def test_none(self):
        serialised = serialisation.serialise(None)
        assert serialisation.deserialise(serialised) is None
