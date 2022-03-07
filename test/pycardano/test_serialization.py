from dataclasses import dataclass, field
from test.pycardano.util import check_two_way_cbor

from pycardano.serialization import (
    ArrayCBORSerializable,
    DictCBORSerializable,
    MapCBORSerializable,
)


def test_array_cbor_serializable():
    @dataclass
    class Test1(ArrayCBORSerializable):
        a: str
        b: str = None

    @dataclass
    class Test2(ArrayCBORSerializable):
        c: str
        test1: Test1

    t = Test2(c="c", test1=Test1(a="a"))
    assert t.to_cbor() == "826163826161f6"
    check_two_way_cbor(t)


def test_array_cbor_serializable_optional_field():
    @dataclass
    class Test1(ArrayCBORSerializable):
        a: str
        b: str = field(default=None, metadata={"optional": True})

    @dataclass
    class Test2(ArrayCBORSerializable):
        c: str
        test1: Test1

    t = Test2(c="c", test1=Test1(a="a"))
    assert t.test1.to_shallow_primitive() == ["a"]
    assert t.to_cbor() == "826163816161"
    check_two_way_cbor(t)


def test_map_cbor_serializable():
    @dataclass
    class Test1(MapCBORSerializable):
        a: str = ""
        b: str = ""

    @dataclass
    class Test2(MapCBORSerializable):
        c: str = None
        test1: Test1 = Test1()

    t = Test2(test1=Test1(a="a"))
    assert t.to_cbor() == "a26163f6657465737431a261616161616260"
    check_two_way_cbor(t)


def test_map_cbor_serializable_custom_keys():
    @dataclass
    class Test1(MapCBORSerializable):
        a: str = field(default="", metadata={"key": "0"})
        b: str = field(default="", metadata={"key": "1"})

    @dataclass
    class Test2(MapCBORSerializable):
        c: str = field(default=None, metadata={"key": "0", "optional": True})
        test1: Test1 = field(default=Test1(), metadata={"key": "1"})

    t = Test2(test1=Test1(a="a"))
    assert t.to_primitive() == {"1": {"0": "a", "1": ""}}
    assert t.to_cbor() == "a16131a261306161613160"
    check_two_way_cbor(t)


class MyTestDict(DictCBORSerializable):
    KEY_TYPE = bytes
    VALUE_TYPE = int


def test_dict_cbor_serializable():

    a = MyTestDict()
    a[b"110"] = 1
    a[b"100"] = 2
    a[b"1"] = 3

    b = MyTestDict()
    b[b"100"] = 2
    b[b"1"] = 3
    b[b"110"] = 1

    assert a.to_cbor() == "a341310343313030024331313001"
    check_two_way_cbor(a)

    # Make sure the cbor of a and b are exactly the same even when their items are inserted in different orders.
    assert a.to_cbor() == b.to_cbor()
