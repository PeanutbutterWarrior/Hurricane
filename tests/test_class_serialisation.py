from hurricane import serialisation
import pytest


@serialisation.make_serialisable
class Empty:
    def __eq__(self, other):
        return type(other) is Empty


@serialisation.make_serialisable
class HasDict:
    def __init__(self, a):
        self.dict_value = a

    def __eq__(self, other):
        return type(other) is HasDict and other.dict_value == self.dict_value


@serialisation.make_serialisable
class HasSlots:
    __slots__ = ('slots_value',)

    def __init__(self, a):
        self.slots_value = a

    def __eq__(self, other):
        if type(other) is not HasSlots:
            return False

        if not hasattr(self, "slots_value"):
            if not hasattr(other, "slots_value"):
                return True
            return False

        return self.slots_value == other.slots_value


@serialisation.make_serialisable
class HasDictAndSlots:
    __slots__ = ('__dict__', 'slots_value')

    def __init__(self, a, b):
        self.slots_value = a
        self.dict_value = b

    def __eq__(self, other):
        if type(other) is not HasDictAndSlots:
            return False

        return self.slots_value == other.slots_value and self.dict_value == other.dict_value


@serialisation.make_serialisable
class ClassValue:
    class_value = 3

    def __init__(self, a):
        self.dict_value = a

    def __eq__(self, other):
        return type(other) is HasDict and other.dict_value == self.dict_value


class NotSerialisable:
    def __eq__(self, other):
        return type(other) is NotSerialisable


def test_empty():
    instance = Empty()
    serialised = serialisation.dumps(instance)
    assert serialisation.loads(serialised) == instance


def test_dict():
    instance = HasDict(5)
    serialised = serialisation.dumps(instance)
    deserialised = serialisation.loads(serialised)
    assert hasattr(deserialised, "dict_value")
    assert deserialised == instance


def test_slots():
    instance = HasSlots(12)
    serialised = serialisation.dumps(instance)
    print(serialised)
    deserialised = serialisation.loads(serialised)
    assert hasattr(deserialised, "slots_value")
    assert deserialised == instance


def test_dict_and_slots():
    instance = HasDictAndSlots(12, 7)
    serialised = serialisation.dumps(instance)
    deserialised = serialisation.loads(serialised)
    assert hasattr(deserialised, "dict_value")
    assert hasattr(deserialised, "slots_value")
    assert deserialised == instance


def test_class_value():
    instance = ClassValue(4)
    assert instance.class_value == 3
    serialised = serialisation.dumps(instance)

    ClassValue.class_value = 5

    deserialised = serialisation.loads(serialised)
    assert deserialised.class_value == 5
    assert deserialised.dict_value == instance.dict_value


def test_unserialisable():
    with pytest.raises(serialisation.CannotBeSerialised):
        serialisation.dumps(NotSerialisable())
