from Hurricane import serialisation
import pytest


class TestInt:
    def test_five(self):
        five = 5
        five_serialised = serialisation.dumps(five)
        assert five_serialised == b"\x01\x00\x01\x05"
        assert serialisation.loads(five_serialised) == five

    def test_zero(self):
        zero = 0
        zero_serialised = serialisation.dumps(zero)
        assert zero_serialised == b"\x01\x00\x01\x00"
        assert serialisation.loads(zero_serialised) == zero

    def test_negative(self):
        minus_three = -3
        minus_three_serialised = serialisation.dumps(minus_three)
        assert minus_three_serialised == b"\x01\x00\x01\xFD"
        assert serialisation.loads(minus_three_serialised) == minus_three

    def test_large(self):
        large = 460843424409  # Minimum of 5 bytes
        large_serialised = serialisation.dumps(large)
        assert serialisation.loads(large_serialised) == large

    def test_too_large(self):
        with pytest.raises(serialisation.ObjectTooLargeException):
            serialisation.dumps(2 ** (serialisation.MAXIMUM_SIZE * 8) + 1)


class TestStr:
    def test_small(self):
        message = 'Hello Serialiser'
        serialised = serialisation.dumps(message)
        assert serialised == b'\x02\x00\x10Hello Serialiser'
        assert serialisation.loads(serialised) == message

    def test_large(self):
        message = 'testing' * 1000
        serialised = serialisation.dumps(message)
        assert serialisation.loads(serialised) == message

    def test_empty(self):
        message = ''
        serialised = serialisation.dumps(message)
        assert serialised == b'\x02\x00\x00'
        assert serialisation.loads(serialised) == message

    def test_utf8(self):
        message = 'Њଛp!\x00▰👋'
        serialised = serialisation.dumps(message)
        assert serialisation.loads(serialised) == message

    def test_malformed_utf8(self):
        malformed_data = b'\x02\x00\x03\xE2\x06\xB0'
        with pytest.raises(serialisation.MalformedDataError):
            serialisation.loads(malformed_data)

    def test_wrong_size(self):
        malformed = b'\x02\x00\x05abc'
        assert serialisation.loads(malformed) == 'abc'
        malformed = b'\x02\x00\x02abc'
        assert serialisation.loads(malformed) == 'ab'


class TestBool:
    def test_true(self):
        serialised = serialisation.dumps(True)
        assert serialised == b'\x03\x01'
        assert serialisation.loads(serialised) is True

    def test_false(self):
        serialised = serialisation.dumps(False)
        assert serialised == b'\x03\x00'
        assert serialisation.loads(serialised) is False


class TestTuple:
    def test_small(self):
        tup = (1, 'a', True)
        serialised = serialisation.dumps(tup)
        assert serialisation.loads(serialised) == tup

    def test_large(self):
        tup = tuple(range(1, serialisation.MAXIMUM_SIZE))
        serialised = serialisation.dumps(tup)
        assert serialisation.loads(serialised) == tup

    def test_empty(self):
        serialised = serialisation.dumps(tuple())
        assert serialisation.loads(serialised) == tuple()

    def test_too_large(self):
        tup = tuple(range(0, serialisation.MAXIMUM_SIZE + 1))
        with pytest.raises(serialisation.ObjectTooLargeException):
            serialisation.dumps(tup)


class TestList:
    def test_small_homogenous(self):
        li = [2, 3, 1]
        serialised = serialisation.dumps(li)
        assert serialised == b'\x05\x00\x03' + b''.join(serialisation.dumps(i) for i in li)
        assert serialisation.loads(serialised) == li

    def test_small_heterogenous(self):
        li = [1, 'bagel', False]
        serialised = serialisation.dumps(li)
        assert serialised == b'\x05\x00\x03' + b''.join(serialisation.dumps(i) for i in li)
        assert serialisation.loads(serialised) == li

    def test_large(self):
        li = list(range(0, serialisation.MAXIMUM_SIZE))
        serialised = serialisation.dumps(li)
        assert serialised == b'\x05\xff\xff' + b''.join(serialisation.dumps(i) for i in li)
        assert serialisation.loads(serialised) == li

    def test_too_large(self):
        li = list(range(serialisation.MAXIMUM_SIZE + 1))
        with pytest.raises(serialisation.ObjectTooLargeException):
            serialisation.dumps(li)

    def test_empty(self):
        serialised = serialisation.dumps([])
        assert serialisation.loads(serialised) == []


class TestDict:
    def test_small(self):
        di = {1: 5, 2: 4, 3: 3, 4: 2, 5: 1}
        serialised = serialisation.dumps(di)
        assert serialisation.loads(serialised) == di

    def test_heterogenous(self):
        di = {
            1: True,
            False: 3,
            'abc': 'cba',
            'li': ['a', 'b', 'c']
        }
        serialised = serialisation.dumps(di)
        assert serialisation.loads(serialised) == di

    def test_large(self):
        di = dict((i, i + 1) for i in range(serialisation.MAXIMUM_SIZE // 2))
        serialised = serialisation.dumps(di)
        assert serialisation.loads(serialised) == di

    def test_nested(self):
        di = {
            1: {'a': 1, 'b': 1},
            2: {'c': 2, 'd': 2},
        }

        serialised = serialisation.dumps(di)
        assert serialisation.loads(serialised) == di

    def test_empty(self):
        serialised = serialisation.dumps({})
        assert serialisation.loads(serialised) == {}


class TestSet:
    def test_small(self):
        se = {1, 2, 3}
        serialised = serialisation.dumps(se)
        assert serialisation.loads(serialised) == se

    def test_heterogenous(self):
        se = {2, 'abc', False}
        serialised = serialisation.dumps(se)
        assert serialisation.loads(serialised) == se

    def test_large(self):
        se = set(range(serialisation.MAXIMUM_SIZE))
        serialised = serialisation.dumps(se)
        assert serialisation.loads(serialised) == se

    def test_too_large(self):
        se = set(range(serialisation.MAXIMUM_SIZE + 1))
        with pytest.raises(serialisation.ObjectTooLargeException):
            serialisation.dumps(se)

    def test_empty(self):
        serialised = serialisation.dumps(set())
        assert serialisation.loads(serialised) == set()


class TestFloat:
    def test_integer(self):
        serialised = serialisation.dumps(4.0)
        assert serialisation.loads(serialised) == 4.0
        assert type(serialisation.loads(serialised)) is float

    def test_negative(self):
        num = -7 / 3
        serialised = serialisation.dumps(num)
        assert serialisation.loads(serialised) == num

    def test_rational(self):
        serialised = serialisation.dumps(2.5)
        assert serialisation.loads(serialised) == 2.5

    def test_irrational(self):
        serialised = serialisation.dumps(5 / 3)
        assert serialisation.loads(serialised) == 5 / 3

    def test_inf(self):
        inf = float("inf")
        serialised = serialisation.dumps(inf)
        assert serialisation.loads(serialised) == inf

    def test_zero(self):
        serialised = serialisation.dumps(0.0)
        assert serialisation.loads(serialised) == 0.0
        assert type(serialisation.loads(serialised)) is float

    def test_nan(self):
        nan = float("nan")
        serialised = serialisation.dumps(nan)
        deserialised = serialisation.loads(serialised)
        assert deserialised != deserialised  # NaN is the only float not equal to itself


class TestComplex:
    def test_real(self):
        serialised = serialisation.dumps(4 + 0j)
        assert serialisation.loads(serialised) == 4 + 0j
        assert type(serialisation.loads(serialised)) is complex

    def test_imaginary(self):
        serialised = serialisation.dumps(2j)
        assert serialisation.loads(serialised) == 2j
        assert type(serialisation.loads(serialised)) is complex

    def test_complex(self):
        serialised = serialisation.dumps(3 + 4j)
        assert serialisation.loads(serialised) == 3 + 4j

    def test_float_parts(self):
        serialised = serialisation.dumps(4.5 + 2.3j)
        assert serialisation.loads(serialised) == 4.5 + 2.3j


class TestBytes:
    def test_small(self):
        by = b'agd'
        serialised = serialisation.dumps(by)
        assert serialisation.loads(serialised) == by

    def test_large(self):
        by = b'abcd' * (serialisation.MAXIMUM_SIZE // 4)
        serialised = serialisation.dumps(by)
        assert serialisation.loads(serialised) == by

    def test_empty(self):
        serialised = serialisation.dumps(b'')
        assert serialisation.loads(serialised) == b''

    def test_too_large(self):
        with pytest.raises(serialisation.ObjectTooLargeException):
            serialisation.dumps(
                b'a' * (serialisation.MAXIMUM_SIZE + 1)
            )


class TestBytearray:
    def test_small(self):
        by = bytearray(b'agd')
        serialised = serialisation.dumps(by)
        assert serialisation.loads(serialised) == by

    def test_large(self):
        by = bytearray(b'abcd' * (serialisation.MAXIMUM_SIZE // 4))
        serialised = serialisation.dumps(by)
        assert serialisation.loads(serialised) == by

    def test_empty(self):
        serialised = serialisation.dumps(bytearray())
        assert serialisation.loads(serialised) == bytearray()

    def test_too_large(self):
        with pytest.raises(serialisation.ObjectTooLargeException):
            serialisation.dumps(
                bytearray(b'a' * (serialisation.MAXIMUM_SIZE + 1))
            )


class TestFrozenset:
    def test_small(self):
        se = frozenset({1, 2, 3})
        serialised = serialisation.dumps(se)
        assert serialisation.loads(serialised) == se

    def test_heterogenous(self):
        se = frozenset({2, 'abc', False})
        serialised = serialisation.dumps(se)
        assert serialisation.loads(serialised) == se

    def test_large(self):
        se = frozenset(range(serialisation.MAXIMUM_SIZE))
        serialised = serialisation.dumps(se)
        assert serialisation.loads(serialised) == se

    def test_too_large(self):
        se = frozenset(range(serialisation.MAXIMUM_SIZE + 1))
        with pytest.raises(serialisation.ObjectTooLargeException):
            serialisation.dumps(se)

    def test_empty(self):
        serialised = serialisation.dumps(frozenset())
        assert serialisation.loads(serialised) == frozenset()


class TestNone:
    def test_none(self):
        serialised = serialisation.dumps(None)
        assert serialisation.loads(serialised) is None
