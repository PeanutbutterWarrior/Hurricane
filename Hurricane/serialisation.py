from typing import Any, Dict, Tuple, Callable, List, Set
import importlib
from io import BytesIO
import struct

MAXIMUM_SIZE = 64 * 1024 - 1  # 64 KiB


class ObjectTooLargeException(Exception):
    pass


class CannotBeSerialised(Exception):
    pass


class MalformedDataError(Exception):
    def __init__(self, causing_exception):
        self.caused_by = causing_exception


#  These 4 public functions are named to match pickle, marshal, json, etc.
def dumps(obj: Any) -> bytes:
    output = BytesIO()

    dump(obj, output)

    return output.getvalue()


def dump(obj: Any, stream: BytesIO):
    serialiser, _ = known_types.get(type(obj), (None, None))
    if serialiser is not None:
        stream.write(
            _type_to_discriminant[type(obj)]
            .to_bytes(1, 'big')
        )
        serialiser(obj, stream)
    else:
        raise NotImplementedError
        _serialise_object(obj, stream)


def loads(data: bytes) -> Any:
    stream = BytesIO(data)
    return load(stream)


def load(stream: BytesIO) -> Any:
    discriminant = int.from_bytes(stream.read(1), 'big')
    object_type = _discriminant_to_type.get(discriminant, None)
    if object_type is not None:
        _, deserialiser = known_types[object_type]
        try:
            return deserialiser(stream)
        except Exception as e:
            raise MalformedDataError(e)
    else:
        raise NotImplementedError
        try:
            return _deserialise_object(stream)
        except Exception as e:
            raise MalformedDataError(e)


def _serialise_object(obj: Any, stream: BytesIO):
    has_slots = getattr(obj, '__slots__', None) is not None
    has_dict = getattr(obj, '__dict__', None) is not None

    if not has_slots and not has_dict:
        raise CannotBeSerialised(f"{type(obj)} object does not have __dict__ or __slots__")

    stream.write(b'\x00')  # Custom class
    stream.write(  # Used in deserialising to interpret the data as slots, dict, or both
        (has_slots << 1 + has_dict)
        .to_bytes(1, 'big')
    )
    _serialise_str(
        obj.__module__,
        stream,
    )
    _serialise_str(
        obj.__qualname__,
        stream,
    )

    if has_slots:
        ...  # TODO

    if has_dict:
        _serialise_dict(obj.__dict__, stream)


def _deserialise_object(stream: BytesIO) -> Any:
    contents = int.from_bytes(
        stream.read(1),
        'big'
    )
    has_slots = bool(contents & 2)
    has_dict = bool(contents & 1)

    module_name = _deserialise_str(stream)
    class_name = _deserialise_str(stream)
    module = importlib.import_module(module_name)
    object_class = getattr(module, class_name)

    new_object = object_class.__new__(object_class)

    if has_slots:
        ...

    if has_dict:
        new_object.__dict__ = _deserialise_dict(stream)

    return new_object


def _serialise_int(obj: int, stream: BytesIO):
    raw_bytes = obj.to_bytes(
        (obj.bit_length() + 6) // 7,  # + 7 makes it round upwards
        'big',
        signed=True
    )

    if len(raw_bytes) > MAXIMUM_SIZE:
        raise ObjectTooLargeException

    # Force it to use at least 1 byte
    if len(raw_bytes) == 0:
        raw_bytes = b'\x00'

    stream.write(len(raw_bytes).to_bytes(2, 'big'))
    stream.write(raw_bytes)


def _deserialise_int(stream: BytesIO) -> int:
    length = int.from_bytes(
        stream.read(2),
        'big',
    )
    return int.from_bytes(
        stream.read(length),
        'big',
        signed=True
    )


def _serialise_str(obj: str, stream: BytesIO):
    encoded = obj.encode("utf-8")

    if len(encoded) > MAXIMUM_SIZE:
        raise ObjectTooLargeException("String too large to be serialised.")

    stream.write(
        len(encoded).to_bytes(2, 'big')
    )
    stream.write(encoded)


def _deserialise_str(stream: BytesIO) -> str:
    length = int.from_bytes(
        stream.read(2),
        'big'
    )
    return stream.read(length).decode("utf-8")


def _serialise_bool(obj: bool, stream: BytesIO):
    if obj:
        stream.write(b'\x01')
    else:
        stream.write(b'\x00')


def _deserialise_bool(stream: BytesIO) -> bool:
    if stream.read(1)[0]:
        return True
    else:
        return False


def _serialise_tuple(obj: tuple, stream: BytesIO):
    if len(obj) > MAXIMUM_SIZE:
        raise ObjectTooLargeException

    stream.write(
        len(obj).to_bytes(2, 'big')
    )

    for item in obj:
        dump(item, stream)


def _deserialise_tuple(stream: BytesIO) -> tuple:
    length = int.from_bytes(
        stream.read(2), 'big'
    )

    return tuple(
        load(stream)
        for _ in range(length)
    )


def _serialise_list(obj: list, stream: BytesIO):
    if len(obj) > MAXIMUM_SIZE:
        raise ObjectTooLargeException

    stream.write(
        len(obj).to_bytes(2, 'big')
    )

    for item in obj:
        dump(item, stream)


def _deserialise_list(stream: BytesIO) -> list:
    length = int.from_bytes(stream.read(2), 'big')

    new_list = []
    for i in range(length):
        new_list.append(load(stream))

    return new_list


def _serialise_dict(obj: dict, stream: BytesIO):
    if len(obj) > MAXIMUM_SIZE // 2:
        raise ObjectTooLargeException

    stream.write(
        len(obj).to_bytes(2, 'big')
    )

    for key, value in obj.items():
        dump(key, stream)
        dump(value, stream)


def _deserialise_dict(stream: BytesIO) -> dict:
    length = int.from_bytes(stream.read(2), 'big')

    new_dict = {}
    for _ in range(length):
        key = load(stream)
        value = load(stream)
        new_dict[key] = value

    return new_dict


def _serialise_set(obj: set, stream: BytesIO):
    if len(obj) > MAXIMUM_SIZE:
        raise ObjectTooLargeException

    stream.write(
        len(obj).to_bytes(2, 'big')
    )

    for item in obj:
        dump(item, stream)


def _deserialise_set(stream: BytesIO) -> set:
    length = int.from_bytes(stream.read(2), 'big')

    new_set = set()
    for _ in range(length):
        new_set.add(
            load(stream)
        )

    return new_set


def _serialise_float(obj: float, stream: BytesIO):
    stream.write(
        struct.pack("d", obj)
    )


def _deserialise_float(stream: BytesIO) -> float:
    return struct.unpack(
        "d",
        stream.read(8)
    )[0]


def _serialise_complex(obj: complex, stream: BytesIO):
    _serialise_float(obj.real, stream)
    _serialise_float(obj.imag, stream)


def _deserialise_complex(stream: BytesIO) -> complex:
    real = _deserialise_float(stream)
    imag = _deserialise_float(stream)
    return complex(real, imag)


def _serialise_bytes(obj: bytes, stream: BytesIO):
    if len(obj) > MAXIMUM_SIZE:
        raise ObjectTooLargeException

    stream.write(
        len(obj).to_bytes(2, 'big')
    )

    stream.write(obj)


def _deserialise_bytes(stream: BytesIO) -> bytes:
    length = int.from_bytes(stream.read(2), 'big')
    return stream.read(length)


def _serialise_bytearray(obj: bytearray, stream: BytesIO):
    _serialise_bytes(obj, stream)


def _deserialise_bytearray(stream: BytesIO) -> bytearray:
    return bytearray(_deserialise_bytes(stream))


def _serialise_frozenset(obj: frozenset, stream: BytesIO):
    if len(obj) > MAXIMUM_SIZE:
        raise ObjectTooLargeException

    stream.write(
        len(obj).to_bytes(2, 'big')
    )

    for item in obj:
        dump(item, stream)


def _deserialise_frozenset(stream: BytesIO) -> frozenset:
    length = int.from_bytes(stream.read(2), 'big')

    return frozenset(
        load(stream)
        for _ in range(length)
    )


def _serialise_none(obj: None, stream: BytesIO):
    # None is a singleton, no data is stored about it
    return


def _deserialise_none(stream: BytesIO):
    return None


_discriminant_to_type = {
    0: None,  # indicates a custom type
    1: int,
    2: str,
    3: bool,
    4: tuple,
    5: list,
    6: dict,
    7: set,
    8: complex,
    9: float,
    10: bytes,
    11: bytearray,
    12: frozenset,
    13: type(None)  # The NoneType is not accessible otherwise in 3.8
}

# Reverse keys and values for lookup in either direction
_type_to_discriminant = dict(zip(_discriminant_to_type.values(), _discriminant_to_type.keys()))


known_types: Dict[type, Tuple[Callable[[Any, BytesIO], None], Callable[[BytesIO], Any]]] = {
    int: (_serialise_int, _deserialise_int),
    str: (_serialise_str, _deserialise_str),
    bool: (_serialise_bool, _deserialise_bool),
    tuple: (_serialise_tuple, _deserialise_tuple),
    list: (_serialise_list, _deserialise_list),
    dict: (_serialise_dict, _deserialise_dict),
    set: (_serialise_set, _deserialise_set),
    float: (_serialise_float, _deserialise_float),
    complex: (_serialise_complex, _deserialise_complex),
    bytes: (_serialise_bytes, _deserialise_bytes),
    bytearray: (_serialise_bytearray, _deserialise_bytearray),
    frozenset: (_serialise_frozenset, _deserialise_frozenset),
    type(None): (_serialise_none, _deserialise_none),
}
