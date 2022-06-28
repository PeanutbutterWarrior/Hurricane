from typing import Any, Dict, Tuple, Callable
from io import BytesIO

MAXIMUM_SIZE = 64 * 1024 - 1  # 64 KiB


class ObjectTooLargeException(Exception):
    pass


class CannotBeSerialised(Exception):
    pass


def serialise(obj: Any) -> bytes:
    output = BytesIO()

    serialiser, _ = known_types.get(type(obj), (None, None))
    if serialiser is not None:
        output.write(
            type_to_discriminant[type(obj)]
            .to_bytes(1, 'big')
        )
        serialiser(obj, output)
    else:
        raise NotImplemented

    return output.getvalue()


def deserialise(data: bytes) -> Any:
    stream = BytesIO(data)
    discriminant = int.from_bytes(stream.read(1), 'big')
    object_type = discriminant_to_type.get(discriminant, None)
    if object_type is not None:
        _, deserialiser = known_types[object_type]
        return deserialiser(stream)
    else:
        raise NotImplemented


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


discriminant_to_type = {
    0: None,  # indicates a custom type
    1: int,
    2: str,
    # 3: bool,
    # 4: tuple,
    # 5: list,
    # 6: dict,
    # 7: set,
    # 8: complex
}

# Reverse keys and values for lookup in either direction
type_to_discriminant = dict(zip(discriminant_to_type.values(), discriminant_to_type.keys()))


known_types: Dict[type, Tuple[Callable[[Any, BytesIO], None], Callable[[BytesIO], Any]]] = {
    int: (serialise_int, deserialise_int),
    str: (serialise_str, deserialise_str),
}
