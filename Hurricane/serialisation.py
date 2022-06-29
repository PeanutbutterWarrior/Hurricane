from typing import Any, Dict, Tuple, Callable, List, Set
from io import BytesIO

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
    return _deserialise(BytesIO(data))


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


def serialise_list(obj: List[Any], stream: BytesIO):
    if len(obj) > MAXIMUM_SIZE:
        raise ObjectTooLargeException

    stream.write(
        len(obj).to_bytes(2, 'big')
    )

    for item in obj:
        _serialise(item, stream)


def deserialise_list(stream: BytesIO) -> List[Any]:
    length = int.from_bytes(stream.read(2), 'big')

    new_list = [None] * length  # Initialise a list with the correct size to avoid reallocations
    for i in range(length):
        new_list[i] = _deserialise(stream)

    return new_list


def serialise_dict(obj: Dict[Any, Any], stream: BytesIO):
    if len(obj) > MAXIMUM_SIZE // 2:
        raise ObjectTooLargeException

    stream.write(
        len(obj).to_bytes(2, 'big')
    )

    for key, value in obj.items():
        _serialise(key, stream)
        _serialise(value, stream)


def deserialise_dict(stream: BytesIO) -> Dict[Any, Any]:
    length = int.from_bytes(stream.read(2), 'big')

    new_dict = {}
    for _ in range(length):
        key = _deserialise(stream)
        value = _deserialise(stream)
        new_dict[key] = value

    return new_dict


def serialise_set(obj: Set[Any], stream: BytesIO):
    if len(obj) > MAXIMUM_SIZE:
        raise ObjectTooLargeException

    stream.write(
        len(obj).to_bytes(2, 'big')
    )

    for item in obj:
        _serialise(item, stream)


def deserialise_set(stream: BytesIO) -> Set[Any]:
    length = int.from_bytes(stream.read(2), 'big')

    new_set = set()
    for _ in range(length):
        new_set.add(
            _deserialise(stream)
        )

    return new_set


discriminant_to_type = {
    0: None,  # indicates a custom type
    1: int,
    2: str,
    3: bool,
    # 4: tuple,
    5: list,
    6: dict,
    7: set,
    # 8: complex
}

# Reverse keys and values for lookup in either direction
type_to_discriminant = dict(zip(discriminant_to_type.values(), discriminant_to_type.keys()))


known_types: Dict[type, Tuple[Callable[[Any, BytesIO], None], Callable[[BytesIO], Any]]] = {
    int:  (serialise_int, deserialise_int),
    str:  (serialise_str, deserialise_str),
    bool: (serialise_bool, deserialise_bool),
    list: (serialise_list, deserialise_list),
    dict: (serialise_dict, deserialise_dict),
    set:  (serialise_set, deserialise_set),
}
