from typing import Any, Dict, Tuple, Callable, List, Set
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


def serialise(obj: Any) -> bytes:
    output = BytesIO()

    _serialise(obj, output)

    return output.getvalue()


def _serialise(obj: Any, stream: BytesIO):
    serialiser, _ = known_types.get(type(obj), (None, None))
    if serialiser is not None:
        stream.write(
            type_to_discriminant[type(obj)]
            .to_bytes(1, 'big')
        )
        serialiser(obj, stream)
    else:
        raise NotImplementedError


def deserialise(data: bytes) -> Any:
    stream = BytesIO(data)
    return _deserialise(stream)


def _deserialise(stream: BytesIO) -> Any:
    discriminant = int.from_bytes(stream.read(1), 'big')
    object_type = discriminant_to_type.get(discriminant, None)
    if object_type is not None:
        _, deserialiser = known_types[object_type]
        try:
            return deserialiser(stream)
        except Exception as e:
            raise MalformedDataError(e)
    else:
        raise NotImplementedError


def serialise_int(obj: int, stream: BytesIO):
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


def deserialise_int(stream: BytesIO) -> int:
    length = int.from_bytes(
        stream.read(2),
        'big',
    )
    return int.from_bytes(
        stream.read(length),
        'big',
        signed=True
    )


def serialise_str(obj: str, stream: BytesIO):
    encoded = obj.encode("utf-8")

    if len(encoded) > MAXIMUM_SIZE:
        raise ObjectTooLargeException("String too large to be serialised.")

    stream.write(
        len(encoded).to_bytes(2, 'big')
    )
    stream.write(encoded)


def deserialise_str(stream: BytesIO) -> str:
    length = int.from_bytes(
        stream.read(2),
        'big'
    )
    return stream.read(length).decode("utf-8")


def serialise_bool(obj: bool, stream: BytesIO):
    if obj:
        stream.write(b'\x01')
    else:
        stream.write(b'\x00')


def deserialise_bool(stream: BytesIO) -> bool:
    if stream.read(1)[0]:
        return True
    else:
        return False


def serialise_tuple(obj: tuple, stream: BytesIO):
    if len(obj) > MAXIMUM_SIZE:
        raise ObjectTooLargeException

    stream.write(
        len(obj).to_bytes(2, 'big')
    )

    for item in obj:
        _serialise(item, stream)


def deserialise_tuple(stream: BytesIO) -> tuple:
    length = int.from_bytes(
        stream.read(2), 'big'
    )

    return tuple(
        _deserialise(stream)
        for _ in range(length)
    )


def serialise_list(obj: list, stream: BytesIO):
    if len(obj) > MAXIMUM_SIZE:
        raise ObjectTooLargeException

    stream.write(
        len(obj).to_bytes(2, 'big')
    )

    for item in obj:
        _serialise(item, stream)


def deserialise_list(stream: BytesIO) -> list:
    length = int.from_bytes(stream.read(2), 'big')

    new_list = []
    for i in range(length):
        new_list.append(_deserialise(stream))

    return new_list


def serialise_dict(obj: dict, stream: BytesIO):
    if len(obj) > MAXIMUM_SIZE // 2:
        raise ObjectTooLargeException

    stream.write(
        len(obj).to_bytes(2, 'big')
    )

    for key, value in obj.items():
        _serialise(key, stream)
        _serialise(value, stream)


def deserialise_dict(stream: BytesIO) -> dict:
    length = int.from_bytes(stream.read(2), 'big')

    new_dict = {}
    for _ in range(length):
        key = _deserialise(stream)
        value = _deserialise(stream)
        new_dict[key] = value

    return new_dict


def serialise_set(obj: set, stream: BytesIO):
    if len(obj) > MAXIMUM_SIZE:
        raise ObjectTooLargeException

    stream.write(
        len(obj).to_bytes(2, 'big')
    )

    for item in obj:
        _serialise(item, stream)


def deserialise_set(stream: BytesIO) -> set:
    length = int.from_bytes(stream.read(2), 'big')

    new_set = set()
    for _ in range(length):
        new_set.add(
            _deserialise(stream)
        )

    return new_set


def serialise_float(obj: float, stream: BytesIO):
    stream.write(
        struct.pack("d", obj)
    )


def deserialise_float(stream: BytesIO) -> float:
    return struct.unpack(
        "d",
        stream.read(8)
    )[0]


def serialise_complex(obj: complex, stream: BytesIO):
    serialise_float(obj.real, stream)
    serialise_float(obj.imag, stream)


def deserialise_complex(stream: BytesIO) -> complex:
    real = deserialise_float(stream)
    imag = deserialise_float(stream)
    return complex(real, imag)


def serialise_bytes(obj: bytes, stream: BytesIO):
    if len(obj) > MAXIMUM_SIZE:
        raise ObjectTooLargeException

    stream.write(
        len(obj).to_bytes(2, 'big')
    )

    stream.write(obj)


def deserialise_bytes(stream: BytesIO) -> bytes:
    length = int.from_bytes(stream.read(2), 'big')
    return stream.read(length)


def serialise_bytearray(obj: bytearray, stream: BytesIO):
    serialise_bytes(obj, stream)


def deserialise_bytearray(stream: BytesIO):
    return bytearray(deserialise_bytes(stream))


discriminant_to_type = {
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
    # 12: frozenset,
    # 13: type(None)  # The NoneType is not accessible otherwise in 3.8
}

# Reverse keys and values for lookup in either direction
type_to_discriminant = dict(zip(discriminant_to_type.values(), discriminant_to_type.keys()))


known_types: Dict[type, Tuple[Callable[[Any, BytesIO], None], Callable[[BytesIO], Any]]] = {
    int: (serialise_int, deserialise_int),
    str: (serialise_str, deserialise_str),
    bool: (serialise_bool, deserialise_bool),
    tuple: (serialise_tuple, deserialise_tuple),
    list: (serialise_list, deserialise_list),
    dict: (serialise_dict, deserialise_dict),
    set: (serialise_set, deserialise_set),
    float: (serialise_float, deserialise_float),
    complex: (serialise_complex, deserialise_complex),
    bytes: (serialise_bytes, deserialise_bytes),
    bytearray: (serialise_bytearray, deserialise_bytearray),
}
