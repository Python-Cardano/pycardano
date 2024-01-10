from dataclasses import dataclass, field
from test.pycardano.util import check_two_way_cbor
from typing import Any, Dict, List, Optional, Set, Tuple, Union

import cbor2
import pytest

from pycardano import Datum, RawPlutusData
from pycardano.exception import DeserializeException
from pycardano.plutus import PlutusV1Script, PlutusV2Script
from pycardano.serialization import (
    ArrayCBORSerializable,
    CBORSerializable,
    DictCBORSerializable,
    IndefiniteList,
    MapCBORSerializable,
    limit_primitive_type,
)


@pytest.mark.single
def test_limit_primitive_type():
    class MockClass(CBORSerializable):
        @classmethod
        def from_primitive(*args):
            return

    wrapped = limit_primitive_type(int, str, bytes, list, dict, tuple, dict)(
        MockClass.from_primitive
    )
    wrapped(MockClass, 1)
    wrapped(MockClass, "")
    wrapped(MockClass, b"")
    wrapped(MockClass, [])
    wrapped(MockClass, tuple())
    wrapped(MockClass, {})

    wrapped = limit_primitive_type(int)(MockClass.from_primitive)
    with pytest.raises(DeserializeException):
        wrapped(MockClass, "")


def test_array_cbor_serializable():
    @dataclass
    class Test1(ArrayCBORSerializable):
        a: str
        b: Union[str, None] = None

    @dataclass
    class Test2(ArrayCBORSerializable):
        c: str
        test1: Test1

    t = Test2(c="c", test1=Test1(a="a"))
    assert t.to_cbor_hex() == "826163826161f6"
    check_two_way_cbor(t)


def test_array_cbor_serializable_unknown_fields():
    @dataclass
    class Test1(ArrayCBORSerializable):
        a: str
        b: str

    t = Test1.from_primitive(["a", "b", "c"])
    assert hasattr(t, "unknown_field0") and t.unknown_field0 == "c"


def test_array_cbor_serializable_optional_field():
    @dataclass
    class Test1(ArrayCBORSerializable):
        a: str
        b: Optional[str] = field(default=None, metadata={"optional": True})

    @dataclass
    class Test2(ArrayCBORSerializable):
        c: str
        test1: Test1

    t = Test2(c="c", test1=Test1(a="a"))
    assert t.test1.to_shallow_primitive() == ["a"]
    assert t.to_cbor_hex() == "826163816161"
    check_two_way_cbor(t)


def test_map_cbor_serializable():
    @dataclass
    class Test1(MapCBORSerializable):
        a: str = ""
        b: str = ""

    @dataclass
    class Test2(MapCBORSerializable):
        c: Union[str, None] = None
        test1: Test1 = field(default_factory=Test1)

    t = Test2(test1=Test1(a="a"))
    assert t.to_cbor_hex() == "a26163f6657465737431a261616161616260"
    check_two_way_cbor(t)


def test_map_cbor_serializable_custom_keys():
    @dataclass
    class Test1(MapCBORSerializable):
        a: str = field(default="", metadata={"key": "0"})
        b: str = field(default="", metadata={"key": "1"})

    @dataclass
    class Test2(MapCBORSerializable):
        c: Optional[str] = field(default=None, metadata={"key": "0", "optional": True})
        test1: Test1 = field(default_factory=Test1, metadata={"key": "1"})

    t = Test2(test1=Test1(a="a"))
    assert t.to_primitive() == {"1": {"0": "a", "1": ""}}
    assert t.to_cbor_hex() == "a16131a261306161613160"
    check_two_way_cbor(t)


def test_dict_cbor_serializable():
    class MyTestDict(DictCBORSerializable):
        KEY_TYPE = bytes
        VALUE_TYPE = int

    a = MyTestDict()
    a[b"110"] = 1
    a[b"100"] = 2
    a[b"1"] = 3

    b = MyTestDict()
    b[b"100"] = 2
    b[b"1"] = 3
    b[b"110"] = 1

    assert a.to_cbor_hex() == "a341310343313030024331313001"
    check_two_way_cbor(a)

    # Make sure the cbor of a and b are exactly the same even when their items are inserted in different orders.
    assert a.to_cbor_hex() == b.to_cbor_hex()


def test_dict_complex_key_cbor_serializable():
    @dataclass(unsafe_hash=True)
    class MyTest(ArrayCBORSerializable):
        a: int

    class MyTestDict(DictCBORSerializable):
        KEY_TYPE = MyTest
        VALUE_TYPE = int

    a = MyTestDict()
    a[MyTest(0)] = 1
    a[MyTest(1)] = 2

    assert a.to_cbor_hex() == "a2810001810102"
    check_two_way_cbor(a)


def test_indefinite_list():
    a = IndefiniteList([4, 5])

    a.append(6)
    # append should add element and return IndefiniteList
    assert a == IndefiniteList([4, 5, 6]) and type(a) == IndefiniteList

    b = a + IndefiniteList([7, 8])
    # addition of two IndefiniteLists should return IndefiniteList
    assert type(b) == IndefiniteList

    a.extend([7, 8])
    # extend should add elements and return IndefiniteList
    assert a == IndefiniteList([4, 5, 6, 7, 8]) and type(a) == IndefiniteList

    # testing eq operator
    assert a == b

    b.pop()
    # pop should remove last element and return IndefiniteList
    assert b == IndefiniteList([4, 5, 6, 7]) and type(b) == IndefiniteList

    b.remove(5)
    # remove should remove element and return IndefiniteList
    assert b == IndefiniteList([4, 6, 7]) and type(b) == IndefiniteList


def test_any_type():
    @dataclass
    class Test1(MapCBORSerializable):
        a: str = ""
        b: Any = ""

    t = Test1(a="a", b=1)

    check_two_way_cbor(t)


def test_datum_type():
    @dataclass
    class Test1(MapCBORSerializable):
        b: Datum

    # make sure that no "not iterable" error is thrown
    t = Test1(b=RawPlutusData(cbor2.CBORTag(125, [])))

    check_two_way_cbor(t)

    # Make sure that iterable objects are not deserialized to the wrong object
    t = Test1(b=b"hello!")

    check_two_way_cbor(t)


def test_wrong_primitive_type():
    @dataclass
    class Test1(MapCBORSerializable):
        a: str = ""

    with pytest.raises(TypeError):
        Test1(a=1).to_cbor_hex()


def test_wrong_union_type():
    @dataclass
    class Test1(MapCBORSerializable):
        a: Union[str, int] = ""

    with pytest.raises(TypeError):
        Test1(a=1.0).to_cbor_hex()


def test_wrong_optional_type():
    @dataclass
    class Test1(MapCBORSerializable):
        a: Optional[str] = ""

    with pytest.raises(TypeError):
        Test1(a=1.0).to_cbor_hex()


def test_wrong_list_type():
    @dataclass
    class Test1(MapCBORSerializable):
        a: List[str] = ""

    with pytest.raises(TypeError):
        Test1(a=[1]).to_cbor_hex()


def test_wrong_dict_type():
    @dataclass
    class Test1(MapCBORSerializable):
        a: Dict[str, int] = ""

    with pytest.raises(TypeError):
        Test1(a={1: 1}).to_cbor_hex()


def test_wrong_tuple_type():
    @dataclass
    class Test1(MapCBORSerializable):
        a: Tuple[str, int] = ""

    with pytest.raises(TypeError):
        Test1(a=(1, 1)).to_cbor_hex()


def test_wrong_set_type():
    @dataclass
    class Test1(MapCBORSerializable):
        a: Set[str] = ""

    with pytest.raises(TypeError):
        Test1(a={1}).to_cbor_hex()


def test_wrong_nested_type():
    @dataclass
    class Test1(MapCBORSerializable):
        a: str = ""

    @dataclass
    class Test2(MapCBORSerializable):
        a: Test1 = ""
        b: Optional[Test1] = None

    with pytest.raises(TypeError):
        Test2(a=1).to_cbor_hex()

    with pytest.raises(TypeError):
        Test2(a=Test1(a=1)).to_cbor_hex()


def test_script_deserialize():
    @dataclass
    class Test(MapCBORSerializable):
        script_1: PlutusV1Script
        script_2: PlutusV2Script

    datum = Test(
        script_1=PlutusV1Script(b"dummy test script"),
        script_2=PlutusV2Script(b"dummy test script"),
    )

    datum.from_cbor(datum.to_cbor())
