from __future__ import annotations

from typing import Any, Dict, Callable
import importlib
from io import BytesIO
import struct


class ObjectTooLargeException(Exception):
    pass


class CannotBeSerialised(Exception):
    pass


class MalformedDataError(Exception):
    def __init__(self, causing_exception):
        self.caused_by = causing_exception


class Serialiser:
    MAXIMUM_SIZE: int = 64 * 1024 - 1  # 64 KiB

    def __init__(self, stream: BytesIO):
        self.stream: BytesIO = stream

    def serialise(self, obj: Any):
        serialiser = self._type_to_serialiser.get(type(obj), None)
        if serialiser is not None:
            self.stream.write(
                _type_to_discriminant[type(obj)]
                .to_bytes(1, 'big')
            )
            serialiser(self, obj)
        else:
            raise NotImplementedError
            self._serialise_object(obj, stream)

    def get_data(self) -> bytes:
        return self.stream.getvalue()

    def _serialise_object(self, obj: Any):
        has_slots = hasattr(obj, '__slots__')
        has_dict = hasattr(obj, '__dict__')

        if not has_slots and not has_dict:
            raise CannotBeSerialised(f"{type(obj)} object does not have __dict__ or __slots__")

        self.stream.write(b'\x00')  # Custom class
        self.stream.write(  # Used in deserialising to interpret the data as slots, dict, or both
            (has_slots << 1 + has_dict)
                .to_bytes(1, 'big')
        )
        self._serialise_str(obj.__module__)
        self._serialise_str(obj.__qualname__)

        if has_slots:
            for slot_name in obj.__slots__:
                if hasattr(obj, slot_name):  # An entry in __slots__ does not guarantee the attribute is initialised
                    self.stream.write(b'\xFE')
                    self.serialise(getattr(obj, slot_name),)
                else:
                    self.stream.write(b'\xFF')

        if has_dict:
            self._serialise_dict(obj.__dict__)

    def _serialise_int(self, obj: int):
        raw_bytes = obj.to_bytes(
            (obj.bit_length() + 6) // 7,  # + 7 makes it round upwards
            'big',
            signed=True
        )

        if len(raw_bytes) > self.MAXIMUM_SIZE:
            raise ObjectTooLargeException

        # Force it to use at least 1 byte
        if len(raw_bytes) == 0:
            raw_bytes = b'\x00'

        self.stream.write(len(raw_bytes).to_bytes(2, 'big'))
        self.stream.write(raw_bytes)

    def _serialise_str(self, obj: str):
        encoded = obj.encode("utf-8")

        if len(encoded) > self.MAXIMUM_SIZE:
            raise ObjectTooLargeException("String too large to be serialised.")

        self.stream.write(
            len(encoded).to_bytes(2, 'big')
        )
        self.stream.write(encoded)

    def _serialise_bool(self, obj: bool):
        if obj:
            self.stream.write(b'\x01')
        else:
            self.stream.write(b'\x00')

    def _serialise_tuple(self, obj: tuple):
        if len(obj) > self.MAXIMUM_SIZE:
            raise ObjectTooLargeException

        self.stream.write(
            len(obj).to_bytes(2, 'big')
        )

        for item in obj:
            self.serialise(item)

    def _serialise_list(self, obj: list):
        if len(obj) > self.MAXIMUM_SIZE:
            raise ObjectTooLargeException

        self.stream.write(
            len(obj).to_bytes(2, 'big')
        )

        for item in obj:
            self.serialise(item)

    def _serialise_dict(self, obj: dict):
        if len(obj) > self.MAXIMUM_SIZE // 2:
            raise ObjectTooLargeException

        self.stream.write(
            len(obj).to_bytes(2, 'big')
        )

        for key, value in obj.items():
            self.serialise(key)
            self.serialise(value)

    def _serialise_set(self, obj: set):
        if len(obj) > self.MAXIMUM_SIZE:
            raise ObjectTooLargeException

        self.stream.write(
            len(obj).to_bytes(2, 'big')
        )

        for item in obj:
            self.serialise(item)

    def _serialise_float(self, obj: float):
        self.stream.write(
            struct.pack("d", obj)
        )

    def _serialise_complex(self, obj: complex):
        self._serialise_float(obj.real)
        self._serialise_float(obj.imag)

    def _serialise_bytes(self, obj: bytes):
        if len(obj) > self.MAXIMUM_SIZE:
            raise ObjectTooLargeException

        self.stream.write(
            len(obj).to_bytes(2, 'big')
        )

        self.stream.write(obj)

    def _serialise_bytearray(self, obj: bytearray):
        self._serialise_bytes(obj)

    def _serialise_frozenset(self, obj: frozenset):
        if len(obj) > self.MAXIMUM_SIZE:
            raise ObjectTooLargeException

        self.stream.write(
            len(obj).to_bytes(2, 'big')
        )

        for item in obj:
            self.serialise(item)

    def _serialise_none(self, obj: None):
        # None is a singleton, no data is stored about it
        return

    _type_to_serialiser: Dict[type, Callable[[Serialiser, Any], None]] = {
        int: _serialise_int,
        str: _serialise_str,
        bool: _serialise_bool,
        tuple: _serialise_tuple,
        list: _serialise_list,
        dict: _serialise_dict,
        set: _serialise_set,
        float: _serialise_float,
        complex: _serialise_complex,
        bytes: _serialise_bytes,
        bytearray: _serialise_bytearray,
        frozenset: _serialise_frozenset,
        type(None): _serialise_none,
    }


class Deserialiser:
    def __init__(self, stream):
        self.stream = stream

    def deserialise(self) -> Any:
        discriminant = int.from_bytes(self.stream.read(1), 'big')
        object_type = _discriminant_to_type.get(discriminant, None)
        if object_type is not None:
            deserialiser = self._type_to_deserialiser[object_type]
            try:
                return deserialiser(self)
            except Exception as e:
                raise MalformedDataError(e)
        else:
            raise NotImplementedError
            try:
                return self._deserialise_object(stream)
            except Exception as e:
                raise MalformedDataError(e)

    def _deserialise_object(self) -> Any:
        contents = int.from_bytes(
            self.stream.read(1),
            'big'
        )
        has_slots = bool(contents & 2)
        has_dict = bool(contents & 1)

        module_name = self._deserialise_str()
        class_name = self._deserialise_str()
        module = importlib.import_module(module_name)
        object_class = getattr(module, class_name)

        new_object = object_class.__new__(object_class)

        if has_slots:
            for slot_name in new_object.__slots__:
                if self.stream.read(1) == 254:
                    setattr(
                        new_object,
                        slot_name,
                        self.deserialise()
                    )

        if has_dict:
            new_object.__dict__ = self._deserialise_dict()

        return new_object

    def _deserialise_int(self) -> int:
        length = int.from_bytes(
            self.stream.read(2),
            'big',
        )
        return int.from_bytes(
            self.stream.read(length),
            'big',
            signed=True
        )

    def _deserialise_str(self) -> str:
        length = int.from_bytes(
            self.stream.read(2),
            'big'
        )
        return self.stream.read(length).decode("utf-8")

    def _deserialise_bool(self) -> bool:
        if self.stream.read(1)[0]:
            return True
        else:
            return False

    def _deserialise_tuple(self) -> tuple:
        length = int.from_bytes(
            self.stream.read(2), 'big'
        )

        return tuple(
            self.deserialise()
            for _ in range(length)
        )

    def _deserialise_list(self) -> list:
        length = int.from_bytes(self.stream.read(2), 'big')

        new_list = []
        for i in range(length):
            new_list.append(self.deserialise())

        return new_list

    def _deserialise_dict(self) -> dict:
        length = int.from_bytes(self.stream.read(2), 'big')

        new_dict = {}
        for _ in range(length):
            key = self.deserialise()
            value = self.deserialise()
            new_dict[key] = value

        return new_dict

    def _deserialise_set(self) -> set:
        length = int.from_bytes(self.stream.read(2), 'big')

        new_set = set()
        for _ in range(length):
            new_set.add(
                self.deserialise()
            )

        return new_set

    def _deserialise_float(self) -> float:
        return struct.unpack(
            "d",
            self.stream.read(8)
        )[0]

    def _deserialise_complex(self) -> complex:
        real = self._deserialise_float()
        imag = self._deserialise_float()
        return complex(real, imag)

    def _deserialise_bytes(self) -> bytes:
        length = int.from_bytes(self.stream.read(2), 'big')
        return self.stream.read(length)

    def _deserialise_bytearray(self) -> bytearray:
        return bytearray(self._deserialise_bytes())

    def _deserialise_frozenset(self) -> frozenset:
        length = int.from_bytes(self.stream.read(2), 'big')

        return frozenset(
            self.deserialise()
            for _ in range(length)
        )

    def _deserialise_none(self):
        return None

    _type_to_deserialiser: Dict[type, Callable[[Deserialiser], Any]] = {
        int: _deserialise_int,
        str: _deserialise_str,
        bool: _deserialise_bool,
        tuple: _deserialise_tuple,
        list: _deserialise_list,
        dict: _deserialise_dict,
        set: _deserialise_set,
        float: _deserialise_float,
        complex: _deserialise_complex,
        bytes: _deserialise_bytes,
        bytearray: _deserialise_bytearray,
        frozenset: _deserialise_frozenset,
        type(None): _deserialise_none,
    }


# These 4 public functions are named to match pickle, marshal, json, etc. 
def dumps(obj: Any) -> bytes:
    output = BytesIO()
    dump(obj, output)
    return output.getvalue()


def dump(obj: Any, stream: BytesIO):
    serialiser = Serialiser(stream)
    serialiser.serialise(obj)
    return serialiser.get_data()


def loads(data: bytes) -> Any:
    stream = BytesIO(data)
    return load(stream)


def load(stream: BytesIO) -> Any:
    deserialiser = Deserialiser(stream)
    return deserialiser.deserialise()


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
    13: type(None),  # The NoneType is not accessible otherwise in 3.8

    254: ...,  # Reserved for use internally
    255: ...,  # Reserved for use internally
}

# Reverse keys and values for lookup in either direction
_type_to_discriminant = dict(zip(_discriminant_to_type.values(), _discriminant_to_type.keys()))

MAXIMUM_SIZE = Serialiser.MAXIMUM_SIZE
