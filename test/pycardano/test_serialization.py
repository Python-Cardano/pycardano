from dataclasses import dataclass, field
from test.pycardano.util import check_two_way_cbor
from typing import Any, Dict, List, Optional, Set, Tuple, Union

import cbor2
import pytest

import pycardano
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

    assert datum == datum.from_cbor(datum.to_cbor())


def test_deserialize_empty_value():
    """
    This should not crash even though there is an empty value in the transaction
    """
    transaction = pycardano.Transaction.from_cbor(
        "84a300818258202c9d507f93b5e46e9c807aff51e7bf0d015430fe1df0d2c6866df5c21febaf23020183a400581d707959ca93792ac3025823f706e9b12e8201d841bb96aed97a62db62a801821a009abef6a0028201d81843d8798003d818590859820259085459085101000032323232323232323222232325333008323232323232323232325333012002100114a0a666022a66602266e1c00d200113371e00e6eb8c024c03cc008c03c038528099b8f005375c6004601e6004601e01c2940c94ccc044cdc3a400000226464a66602c6032004266e3c004dd718059808980598088080b1bae30170013758602c602e602e602e602e602e602e602e602e601e6012601e018264646464646464646464646464a66603c66e24dd69807980e1806180e180b180e00d9991191919299981199b8748008004520001375a60506042004604200264a66604466e1d200200114c103d87a8000132323300100100222533302800114c103d87a800013232323253330293371e014004266e9520003302d375000297ae0133006006003375a60540066eb8c0a0008c0b0008c0a8004dd598139810001181000099198008008051129998128008a6103d87a800013232323253330263371e010004266e9520003302a374c00297ae01330060060033756604e0066eb8c094008c0a4008c09c004dd7180b180e180b180e1806180e180b180e00d9bae300f301c3016301c300c301c3016301c01b1323300100100422533302300114a226464a666044646600200200c44a66604e00229404c8c94ccc098cdc78010030a51133004004001302b002375c60520022660080080022940c09c008dd718128008a503322323300100100322533302400110031330253026001330020023027001330213015301b3015301b300b301b3015301b01a4bd70180180099299980e99b87480052000100113233333009002014001222325333022300e00114c103d87a800013374a9000198131ba60014bd701999980580080aa400244464a66604a66e1c005200014c103d87a800013374a9000198149ba80014bd7019b8000100200e00b3232002323300100100222533302300114984c94ccc09000452613232323232323253330283370e9000000899805005198160030028b1813000998098010009bae3026003375c604a0066052006604e004604c004604c0026604266ec0dd4808a6010120004bd6f7b6301bab300d301a300d301a3232325333022302500210011630230013300c3758602a603600246464a66604066e1d200000114a02944c078004c058c070c058c070c03cc070004c050c06805cc0040108c008004c004004894ccc07400452f5c026603c6036603e002660040046040002664464646466600200200497adef6c60222533302100210011333003003302400232323330010010030022225333025002100113233300400430290033333300e002375c60480026eacc094004888c94ccc09cc04c0045300103d87a800013374a9000198159ba60014bd70191998008008018011112999816001080089919980200218180019999980a0011bae302b001375a605800244464a66605c66e1c005200014c0103d87a800013374a9000198191ba80014bd7019b80002001017302e002010302700237566046004646600200200444a66603e002297ae0133020374c6eacc034c068c084004cc008008c088004cc020dd61803980b800919baf30123018301230180013374a90001980f1ba90034bd701bae300f3015300f3015014300f3015012222223233001001006225333020001133021337606ea4018dd4002a5eb7bdb1804c8c8c8c94ccc084cdd799803805001260103d8798000133025337606ea4028dd40048028a99981099b8f00a0021323253330233370e900000089981399bb037520186050604200400a200a604200266601001401200226604a66ec0dd48011ba800133006006003375a60440066eb8c080008c090008c08800488888c8cc004004018894ccc07c0044cc080cdd81ba9006374c00a97adef6c6013232323253330203375e6600e01400498103d8798000133024337606ea4028dd30048028a99981019b8f00a0021323253330223370e900000089981319bb03752018604e604000400a200a604000266601001401200226604866ec0dd48011ba600133006006003375660420066eb8c07c008c08c008c08400494ccc0600045288a50225333015337200040022980103d8798000153330153371e0040022980103d87a800014c103d87b8000230183019301900122323300100100322533301800114bd7009919299980b980280109980d80119802002000899802002000980e001180d00098078061180a980b0009bad30130013013002375c602200260220046eb8c03c004c8c8c94ccc03cc048008400458dd618080009919198008008011129998080008a5eb804c8ccc888c8cc00400400c894ccc058004400c4c8cc060dd39980c1ba90063301837526eb8c054004cc060dd41bad30160014bd7019801801980d001180c0009bae300f00137566020002660060066028004602400264646600200200444a666020002297adef6c6013232323253330113371e9101000021003133015337606ea4008dd3000998030030019bab3012003375c6020004602800460240026eacc03cc040c040c040c040c020004c004c01c0108c038004526136563253330083370e90000008a99980598030020a4c2c2a66601066e1d20020011533300b300600414985858c01800cc8c94ccc020cdc3a4000002264646464a66601e60240042646493180380119299980699b87480000044c8c8c8c8c8c94ccc058c0640084c9263253330143370e9000000899191919299980d980f00109924c60240062c6eb4c070004c070008c068004c04800858c04800458c05c004c05c008dd7180a800980a8011bae3013001300b00416300b0031630100013010002300e001300600516300600423253330083370e9000000899191919299980798090010a4c2c6eb8c040004c040008dd7180700098030010b1803000918029baa001230033754002ae6955ceaab9e5573eae815d0aba21a400581d707959ca93792ac3025823f706e9b12e8201d841bb96aed97a62db62a801821a005788a2a0028201d81843d8798003d81859045b820259045659045301000033232323232323232322322253330073232323232323232533300f00114a22646464a66602a60300042646464646464646464a666036a666036a666036002200a2940400852808018a50533301a533301a3370e01a9001099b8f011375c6026603000a29404cdc78079bae3003301800514a066e212000375a6004602e6014602e00c66e1cc8c8c8c94ccc070cdc3a40040022900009bad3021301a002301a00132533301b3370e90010008a6103d87a8000132323300100100222533302100114c103d87a800013232323253330223371e02e004266e95200033026375000297ae0133006006003375a60460066eb8c084008c094008c08c004dd59810180c801180c800991980080080111299980f0008a6103d87a8000132323232533301f3371e02c004266e95200033023374c00297ae0133006006003375660400066eb8c078008c088008c080004dd59800980b0038059180e980f0009991191980080080191299980e8008a5013232533301c3371e00400a29444cc010010004c084008dd7180f8009bac301b301c301c301c301c301c301c301c301c3014300f3014010375c601e602800660340026034004603000260206644a66602866e1d20043013001132325333019301c0021320023253330173370e9000000899191919299980f18108010991924c601400464a66603866e1d2000001132323232323253330253028002132498c94ccc08ccdc3a4000002264646464a666054605a00426493180a8018b1bad302b001302b002302900130210021630210011630260013026002375c604800260480046eb8c088004c06801058c06800c58c07c004c07c008c074004c05400858c05400458c068004c048004588c94ccc050cdc3a4000002264646464a666036603c0042930b1bae301c001301c002375c603400260240042c6024002600660200022c602c00264646600200200444a66602c002297ae0132325333015323253330173370e9001000899b8f013375c6038602a0042940c054004c038c04cc038c04c0084cc064008cc0100100044cc010010004c068008c060004dd618009807180498070051180a980b180b00099b8700148004dd6980900098090011bae30100013010002375c601c002646464a66601c602200420022c6eb0c03c004c8c8cc004004008894ccc03c00452f5c0264666444646600200200644a66602a00220062646602e6e9ccc05cdd48031980b9ba9375c60280026602e6ea0dd6980a800a5eb80cc00c00cc064008c05c004dd718070009bab300f001330030033013002301100132323300100100222533300f00114bd6f7b630099191919299980819b8f489000021003133014337606ea4008dd3000998030030019bab3011003375c601e004602600460220026eacc038c03cc03cc03cc03cc01c004c004c0180088c03400452613656375c0024600a6ea80048c00cdd5000ab9a5573aaae7955cfaba05742ae8930011e581c44942234591eee784947f20ab51826428bac8589b372aa9086ee49ee0001825839002b630067f4997129c6fcaea188d4535b1e69fa5860382ba1d2889c3ff3c5cf4a64da3d8d3ac295c3bcbe125961078cdb83080c2a722ef03b1b000000024ab36c59021a0004c829a1008182582064e1867f2c8e8da2e7f5bc06c2224dfdb51b9a40d895d556045ba696483c69685840525f47c570dcfee996eb41a726d1a25e19f46730dccc8e3c05b7dbcf98ceede1ce7931e3b7e0eee9f06b15351042c7285412ac8e4e624ee71805d1a926c65f02f5f6"
    )
    assert (
        transaction.transaction_body.outputs[0].amount.multi_asset
        == pycardano.MultiAsset()
    ), "Invalid deserialization of multi asset"
