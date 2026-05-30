import os
import tempfile
from dataclasses import dataclass
from fractions import Fraction
from test.pycardano.util import check_two_way_cbor

import pytest
from typeguard import TypeCheckError

from pycardano import ParameterChangeAction
from pycardano.address import Address
from pycardano.exception import InvalidDataException, InvalidOperationException
from pycardano.hash import SCRIPT_HASH_SIZE, ScriptHash, TransactionId
from pycardano.key import PaymentKeyPair, PaymentSigningKey, VerificationKey
from pycardano.nativescript import ScriptPubkey
from pycardano.plutus import PlutusData, PlutusV1Script, PlutusV2Script, datum_hash
from pycardano.transaction import (
    Asset,
    AssetName,
    MultiAsset,
    Transaction,
    TransactionBody,
    TransactionInput,
    TransactionOutput,
    Value,
)
from pycardano.witness import TransactionWitnessSet, VerificationKeyWitness


def test_transaction_input():
    tx_id_hex = "732bfd67e66be8e8288349fcaaa2294973ef6271cc189a239bb431275401b8e5"
    tx_in = TransactionInput(TransactionId(bytes.fromhex(tx_id_hex)), 0)
    assert (
        tx_in.to_cbor_hex()
        == "825820732bfd67e66be8e8288349fcaaa2294973ef6271cc189a239bb431275401b8e500"
    )
    check_two_way_cbor(tx_in)


def test_hashable_transaction_input():
    my_inputs = {}
    tx_id_hex1 = "732bfd67e66be8e8288349fcaaa2294973ef6271cc189a239bb431275401b8e5"
    tx_id_hex2 = "732bfd67e66be8e8288349fcaaa2294973ef6271cc189a239bb431275401b8e5"
    tx_in1 = TransactionInput(TransactionId(bytes.fromhex(tx_id_hex1)), 0)
    tx_in2 = TransactionInput(TransactionId(bytes.fromhex(tx_id_hex2)), 0)
    assert tx_in1 == tx_in2
    my_inputs[tx_in1] = 1


def test_transaction_output():
    addr = Address.decode(
        "addr_test1vrm9x2zsux7va6w892g38tvchnzahvcd9tykqf3ygnmwtaqyfg52x"
    )
    output = TransactionOutput(addr, 100000000000)
    assert (
        output.to_cbor_hex()
        == "82581d60f6532850e1bccee9c72a9113ad98bcc5dbb30d2ac960262444f6e5f41b000000174876e800"
    )
    check_two_way_cbor(output)


def test_transaction_output_str_address():
    addr = "addr_test1vrm9x2zsux7va6w892g38tvchnzahvcd9tykqf3ygnmwtaqyfg52x"
    output = TransactionOutput(addr, 100000000000)
    assert (
        output.to_cbor_hex()
        == "82581d60f6532850e1bccee9c72a9113ad98bcc5dbb30d2ac960262444f6e5f41b000000174876e800"
    )
    check_two_way_cbor(output)


def test_transaction_output_inline_datum():
    addr = Address.decode(
        "addr_test1vrm9x2zsux7va6w892g38tvchnzahvcd9tykqf3ygnmwtaqyfg52x"
    )
    datum = 42
    output = TransactionOutput(addr, 100000000000, datum=datum)
    assert (
        output.to_cbor_hex()
        == "a300581d60f6532850e1bccee9c72a9113ad98bcc5dbb30d2ac960262444f6e5f4011b000000174876e800028201d81842182a"
    )
    check_two_way_cbor(output)


def test_transaction_output_datum_hash_inline_plutus_script():
    addr = Address.decode(
        "addr_test1vrm9x2zsux7va6w892g38tvchnzahvcd9tykqf3ygnmwtaqyfg52x"
    )
    datum = 42
    script = PlutusV1Script(b"magic script")
    output = TransactionOutput(
        addr, 100000000000, datum_hash=datum_hash(datum), script=script
    )
    assert (
        output.to_cbor_hex()
        == "a400581d60f6532850e1bccee9c72a9113ad98bcc5dbb30d2ac960262444f6e5f4011b000000174876"
        "e80002820058209e1199a988ba72ffd6e9c269cadb3b53b5f360ff99f112d9b2ee30c4d74ad88b03d8"
        "184f82014c6d6167696320736372697074"
    )
    check_two_way_cbor(output)


def test_transaction_output_inline_plutus_script_v1():
    addr = Address.decode(
        "addr_test1vrm9x2zsux7va6w892g38tvchnzahvcd9tykqf3ygnmwtaqyfg52x"
    )
    script = PlutusV1Script(b"magic script")
    output = TransactionOutput(addr, 100000000000, script=script)
    assert (
        output.to_cbor_hex()
        == "a300581d60f6532850e1bccee9c72a9113ad98bcc5dbb30d2ac960262444f6e5f401"
        "1b000000174876e80003d8184f82014c6d6167696320736372697074"
    )
    check_two_way_cbor(output)


def test_transaction_output_inline_plutus_script_v2():
    addr = Address.decode(
        "addr_test1vrm9x2zsux7va6w892g38tvchnzahvcd9tykqf3ygnmwtaqyfg52x"
    )
    script = PlutusV2Script(b"magic script")
    output = TransactionOutput(addr, 100000000000, script=script)
    assert (
        output.to_cbor_hex()
        == "a300581d60f6532850e1bccee9c72a9113ad98bcc5dbb30d2ac960262444f6e5"
        "f4011b000000174876e80003d8184f82024c6d6167696320736372697074"
    )
    check_two_way_cbor(output)


def test_transaction_output_inline_native_script():
    addr = Address.decode(
        "addr_test1vrm9x2zsux7va6w892g38tvchnzahvcd9tykqf3ygnmwtaqyfg52x"
    )
    script = ScriptPubkey(addr.payment_part)
    output = TransactionOutput(addr, 100000000000, script=script)
    assert (
        output.to_cbor_hex()
        == "a300581d60f6532850e1bccee9c72a9113ad98bcc5dbb30d2ac960262444f6e5"
        "f4011b000000174876e80003d818582282008200581cf6532850e1bccee9c72a"
        "9113ad98bcc5dbb30d2ac960262444f6e5f4"
    )
    check_two_way_cbor(output)


def test_invalid_transaction_output():
    addr = Address.decode(
        "addr_test1vrm9x2zsux7va6w892g38tvchnzahvcd9tykqf3ygnmwtaqyfg52x"
    )
    output = TransactionOutput(addr, -1)
    with pytest.raises(InvalidDataException):
        output.to_cbor_hex()

    value = Value.from_primitive(
        [
            100,
            {
                b"1"
                * SCRIPT_HASH_SIZE: {b"TestToken1": -10000000, b"TestToken2": 20000000}
            },
        ]
    )
    output = TransactionOutput(addr, value)
    with pytest.raises(InvalidDataException):
        output.to_cbor_hex()


def make_transaction_body():
    tx_id_hex = "732bfd67e66be8e8288349fcaaa2294973ef6271cc189a239bb431275401b8e5"
    tx_in = TransactionInput(TransactionId(bytes.fromhex(tx_id_hex)), 0)
    addr = Address.decode(
        "addr_test1vrm9x2zsux7va6w892g38tvchnzahvcd9tykqf3ygnmwtaqyfg52x"
    )
    output1 = TransactionOutput(addr, 100000000000)
    output2 = TransactionOutput(addr, 799999834103)
    fee = 165897
    tx_body = TransactionBody(
        inputs=[tx_in],
        outputs=[output1, output2],
        fee=fee,
        collateral=[],
        required_signers=[],
    )
    return tx_body


def test_transaction_body():
    tx_body = make_transaction_body()
    assert (
        tx_body.to_cbor_hex()
        == "a50081825820732bfd67e66be8e8288349fcaaa2294973ef6271cc189a239bb431275401b8e"
        "500018282581d60f6532850e1bccee9c72a9113ad98bcc5dbb30d2ac960262444f6e5f41b00"
        "0000174876e80082581d60f6532850e1bccee9c72a9113ad98bcc5dbb30d2ac960262444f6e"
        "5f41b000000ba43b4b7f7021a000288090d800e80"
    )
    check_two_way_cbor(tx_body)


def test_full_tx():
    tx_cbor = (
        "84a70081825820b35a4ba9ef3ce21adcd6879d08553642224304704d206c74d3ffb3e6eed3ca28000d80018182581d60cc"
        "30497f4ff962f4c1dca54cceefe39f86f1d7179668009f8eb71e598200a1581cec8b7d1dd0b124e8333d3fa8d818f6eac0"
        "68231a287554e9ceae490ea24f5365636f6e6454657374746f6b656e1a009896804954657374746f6b656e1a0098968002"
        "1a000493e00e8009a1581cec8b7d1dd0b124e8333d3fa8d818f6eac068231a287554e9ceae490ea24f5365636f6e645465"
        "7374746f6b656e1a009896804954657374746f6b656e1a00989680075820592a2df0e091566969b3044626faa8023dabe6"
        "f39c78f33bed9e105e55159221a200828258206443a101bdb948366fc87369336224595d36d8b0eee5602cba8b81a024e5"
        "84735840846f408dee3b101fda0f0f7ca89e18b724b7ca6266eb29775d3967d6920cae7457accb91def9b77571e15dd2ed"
        "e38b12cf92496ce7382fa19eb90ab7f73e49008258205797dc2cc919dfec0bb849551ebdf30d96e5cbe0f33f734a87fe82"
        "6db30f7ef95840bdc771aa7b8c86a8ffcbe1b7a479c68503c8aa0ffde8059443055bf3e54b92f4fca5e0b9ca5bb11ab23b"
        "1390bb9ffce414fa398fc0b17f4dc76fe9f7e2c99c09018182018482051a075bcd1582041a075bcd0c8200581c9139e5c0"
        "a42f0f2389634c3dd18dc621f5594c5ba825d9a8883c66278200581c835600a2be276a18a4bebf0225d728f090f724f4c0"
        "acd591d066fa6ff5d90103a100a11902d1a16b7b706f6c6963795f69647da16d7b706f6c6963795f6e616d657da66b6465"
        "736372697074696f6e6a3c6f7074696f6e616c3e65696d6167656a3c72657175697265643e686c6f636174696f6ea36761"
        "7277656176656a3c6f7074696f6e616c3e6568747470736a3c6f7074696f6e616c3e64697066736a3c7265717569726564"
        "3e646e616d656a3c72657175697265643e667368613235366a3c72657175697265643e64747970656a3c72657175697265643e"
    )
    tx = Transaction.from_cbor(tx_cbor)
    tx.__repr__()
    check_two_way_cbor(tx)


def test_transaction():
    tx_body = make_transaction_body()
    sk = PaymentSigningKey.from_json("""{
        "type": "GenesisUTxOSigningKey_ed25519",
        "description": "Genesis Initial UTxO Signing Key",
        "cborHex": "5820093be5cd3987d0c9fd8854ef908f7746b69e2d73320db6dc0f780d81585b84c2"
    }""")
    vk = VerificationKey(PaymentKeyPair.from_signing_key(sk).verification_key.payload)
    signature = sk.sign(tx_body.hash())
    assert (
        signature
        == b"\xb6+-g\xba\x18TL\xe0\xa1\x975\xf9R\x8b\x89\x0b\x1a*\x7f\x8a\xf9\x03\xa3\xde\x92\x7f\x91"
        b"\xb8\x1f\xdbF\xbdy\xc9\x15\xc7\x05T\xdb\xa4i\xaa\xb8\xa39\x90\xa7\x1d\xe0\xb0$\x9fL~p"
        b"\x9d`)\xbb\xac\xe1P\x04"
    )
    vk_witness = [VerificationKeyWitness(vk, signature)]
    signed_tx = Transaction(tx_body, TransactionWitnessSet(vkey_witnesses=vk_witness))
    check_two_way_cbor(signed_tx)
    expected_tx_id = TransactionId.from_primitive(
        "4b5b9ed087b596150f8c95f14de821ab066ddb74f00919228acf33b85d9ca6ca"
    )
    assert expected_tx_id == tx_body.id
    assert expected_tx_id == signed_tx.id


def test_transaction_save_load():
    tx_cbor = (
        "84a70081825820b35a4ba9ef3ce21adcd6879d08553642224304704d206c74d3ffb3e6eed3ca28000d80018182581d60cc"
        "30497f4ff962f4c1dca54cceefe39f86f1d7179668009f8eb71e598200a1581cec8b7d1dd0b124e8333d3fa8d818f6eac0"
        "68231a287554e9ceae490ea24f5365636f6e6454657374746f6b656e1a009896804954657374746f6b656e1a0098968002"
        "1a000493e00e8009a1581cec8b7d1dd0b124e8333d3fa8d818f6eac068231a287554e9ceae490ea24f5365636f6e645465"
        "7374746f6b656e1a009896804954657374746f6b656e1a00989680075820592a2df0e091566969b3044626faa8023dabe6"
        "f39c78f33bed9e105e55159221a200828258206443a101bdb948366fc87369336224595d36d8b0eee5602cba8b81a024e5"
        "84735840846f408dee3b101fda0f0f7ca89e18b724b7ca6266eb29775d3967d6920cae7457accb91def9b77571e15dd2ed"
        "e38b12cf92496ce7382fa19eb90ab7f73e49008258205797dc2cc919dfec0bb849551ebdf30d96e5cbe0f33f734a87fe82"
        "6db30f7ef95840bdc771aa7b8c86a8ffcbe1b7a479c68503c8aa0ffde8059443055bf3e54b92f4fca5e0b9ca5bb11ab23b"
        "1390bb9ffce414fa398fc0b17f4dc76fe9f7e2c99c09018182018482051a075bcd1582041a075bcd0c8200581c9139e5c0"
        "a42f0f2389634c3dd18dc621f5594c5ba825d9a8883c66278200581c835600a2be276a18a4bebf0225d728f090f724f4c0"
        "acd591d066fa6ff5d90103a100a11902d1a16b7b706f6c6963795f69647da16d7b706f6c6963795f6e616d657da66b6465"
        "736372697074696f6e6a3c6f7074696f6e616c3e65696d6167656a3c72657175697265643e686c6f636174696f6ea36761"
        "7277656176656a3c6f7074696f6e616c3e6568747470736a3c6f7074696f6e616c3e64697066736a3c7265717569726564"
        "3e646e616d656a3c72657175697265643e667368613235366a3c72657175697265643e64747970656a3c72657175697265643e"
    )
    tx = Transaction.from_cbor(tx_cbor)

    with tempfile.NamedTemporaryFile(delete=False) as f:
        tmp_path = f.name
    try:
        tx.save(tmp_path)
        loaded_tx = Transaction.load(tmp_path)
        assert tx == loaded_tx
    finally:
        os.unlink(tmp_path)


def test_multi_asset():
    serialized_value = [
        100,
        {b"1" * SCRIPT_HASH_SIZE: {b"TestToken1": 10000000, b"TestToken2": 20000000}},
    ]
    value = Value.from_primitive(serialized_value)
    assert value == Value(
        100,
        MultiAsset(
            {
                ScriptHash(b"1" * SCRIPT_HASH_SIZE): Asset(
                    {
                        AssetName(b"TestToken1"): 10000000,
                        AssetName(b"TestToken2"): 20000000,
                    }
                )
            }
        ),
    )
    assert value.to_primitive() == serialized_value
    check_two_way_cbor(value)


def test_multi_asset_addition():
    a = MultiAsset.from_primitive(
        {b"1" * SCRIPT_HASH_SIZE: {b"Token1": 1, b"Token2": 2}}
    )

    b = MultiAsset.from_primitive(
        {
            b"1" * SCRIPT_HASH_SIZE: {b"Token1": 10, b"Token2": 20},
            b"2" * SCRIPT_HASH_SIZE: {b"Token1": 1, b"Token2": 2},
        }
    )

    result = a.union(b)

    assert a + b == MultiAsset.from_primitive(
        {
            b"1" * SCRIPT_HASH_SIZE: {b"Token1": 11, b"Token2": 22},
            b"2" * SCRIPT_HASH_SIZE: {b"Token1": 1, b"Token2": 2},
        }
    )

    assert result == MultiAsset.from_primitive(
        {
            b"1" * SCRIPT_HASH_SIZE: {b"Token1": 11, b"Token2": 22},
            b"2" * SCRIPT_HASH_SIZE: {b"Token1": 1, b"Token2": 2},
        }
    )

    assert a == MultiAsset.from_primitive(
        {b"1" * SCRIPT_HASH_SIZE: {b"Token1": 1, b"Token2": 2}}
    )

    assert b == MultiAsset.from_primitive(
        {
            b"1" * SCRIPT_HASH_SIZE: {b"Token1": 10, b"Token2": 20},
            b"2" * SCRIPT_HASH_SIZE: {b"Token1": 1, b"Token2": 2},
        }
    )


def test_multi_asset_subtraction():
    a = MultiAsset.from_primitive(
        {b"1" * SCRIPT_HASH_SIZE: {b"Token1": 1, b"Token2": 2}}
    )

    b = MultiAsset.from_primitive(
        {
            b"1" * SCRIPT_HASH_SIZE: {b"Token1": 10, b"Token2": 20},
            b"2" * SCRIPT_HASH_SIZE: {b"Token1": 1, b"Token2": 2},
        }
    )

    assert b - a == MultiAsset.from_primitive(
        {
            b"1" * SCRIPT_HASH_SIZE: {b"Token1": 9, b"Token2": 18},
            b"2" * SCRIPT_HASH_SIZE: {b"Token1": 1, b"Token2": 2},
        }
    )

    assert a == MultiAsset.from_primitive(
        {b"1" * SCRIPT_HASH_SIZE: {b"Token1": 1, b"Token2": 2}}
    )

    assert b == MultiAsset.from_primitive(
        {
            b"1" * SCRIPT_HASH_SIZE: {b"Token1": 10, b"Token2": 20},
            b"2" * SCRIPT_HASH_SIZE: {b"Token1": 1, b"Token2": 2},
        }
    )

    assert a - b == MultiAsset.from_primitive(
        {
            b"1" * SCRIPT_HASH_SIZE: {b"Token1": -9, b"Token2": -18},
            b"2" * SCRIPT_HASH_SIZE: {b"Token1": -1, b"Token2": -2},
        }
    )


def test_asset_comparison():
    a = Asset.from_primitive({b"Token1": 1, b"Token2": 2})

    b = Asset.from_primitive({b"Token1": 1, b"Token2": 3})

    c = Asset.from_primitive({b"Token1": 1, b"Token2": 2, b"Token3": 3})

    d = Asset.from_primitive({b"Token3": 1, b"Token4": 2})

    result = a.union(b)

    assert result == Asset.from_primitive({b"Token1": 2, b"Token2": 5})

    assert a == a
    assert a < b
    assert a <= b
    assert not b <= a
    assert b > a
    assert b >= a
    assert a != b

    assert a < c
    assert a <= c
    assert not c <= a
    assert c > a
    assert c >= a
    assert a != c

    assert not any([a == d, a <= d, d <= a])

    assert not a == "abc"

    with pytest.raises(TypeCheckError):
        a <= 1


def test_multi_asset_comparison():
    a = MultiAsset.from_primitive(
        {b"1" * SCRIPT_HASH_SIZE: {b"Token1": 1, b"Token2": 2}}
    )

    b = MultiAsset.from_primitive(
        {
            b"1" * SCRIPT_HASH_SIZE: {b"Token1": 1, b"Token2": 2, b"Token3": 3},
        }
    )

    c = MultiAsset.from_primitive(
        {
            b"1" * SCRIPT_HASH_SIZE: {b"Token1": 1, b"Token2": 3},
            b"2" * SCRIPT_HASH_SIZE: {b"Token1": 1, b"Token2": 2},
        }
    )

    d = MultiAsset.from_primitive(
        {
            b"2" * SCRIPT_HASH_SIZE: {b"Token1": 1, b"Token2": 2},
        }
    )

    assert a != b
    assert a <= b
    assert a < c
    assert b > a
    assert b >= a
    assert not b <= a

    assert a != c
    assert a <= c
    assert c > a
    assert c >= a
    assert not c <= a

    assert a != d
    assert not a <= d
    assert not d <= a

    assert not a == "abc"

    with pytest.raises(TypeCheckError):
        a <= 1


def test_datum_witness():
    @dataclass
    class TestDatum(PlutusData):
        CONSTR_ID = 0
        a: int
        b: bytes

    tx_body = make_transaction_body()
    signed_tx = Transaction(
        tx_body,
        TransactionWitnessSet(vkey_witnesses=None, plutus_data=[TestDatum(1, b"test")]),
    )
    restored_tx = Transaction.from_cbor(signed_tx.to_cbor())

    assert signed_tx.to_cbor_hex() == restored_tx.to_cbor_hex()


def test_values():
    a = Value.from_primitive(
        [1, {b"1" * SCRIPT_HASH_SIZE: {b"Token1": 1, b"Token2": 2}}]
    )

    b = Value.from_primitive(
        [11, {b"1" * SCRIPT_HASH_SIZE: {b"Token1": 11, b"Token2": 22}}]
    )

    c = Value.from_primitive(
        [
            11,
            {
                b"1" * SCRIPT_HASH_SIZE: {b"Token1": 11, b"Token2": 22},
                b"2" * SCRIPT_HASH_SIZE: {b"Token1": 11, b"Token2": 22},
            },
        ]
    )
    e = Value.from_primitive([1000])
    d = 1000
    assert e >= d

    assert a != b
    assert a <= b
    assert a < b
    assert b > a
    assert b >= a
    assert not b <= a

    assert a <= c
    assert c > a
    assert c >= a
    assert not c <= a

    assert b <= c
    assert not c <= b

    assert not a == "abc"

    assert b - a == Value.from_primitive(
        [10, {b"1" * SCRIPT_HASH_SIZE: {b"Token1": 10, b"Token2": 20}}]
    )

    assert c - a == Value.from_primitive(
        [
            10,
            {
                b"1" * SCRIPT_HASH_SIZE: {b"Token1": 10, b"Token2": 20},
                b"2" * SCRIPT_HASH_SIZE: {b"Token1": 11, b"Token2": 22},
            },
        ]
    )

    assert a + 100 == Value.from_primitive(
        [101, {b"1" * SCRIPT_HASH_SIZE: {b"Token1": 1, b"Token2": 2}}]
    )

    assert a - c == Value.from_primitive(
        [
            -10,
            {
                b"1" * SCRIPT_HASH_SIZE: {b"Token1": -10, b"Token2": -20},
                b"2" * SCRIPT_HASH_SIZE: {b"Token1": -11, b"Token2": -22},
            },
        ]
    )

    assert b - c == Value.from_primitive(
        [
            0,
            {
                b"1" * SCRIPT_HASH_SIZE: {b"Token1": 0, b"Token2": 0},
                b"2" * SCRIPT_HASH_SIZE: {b"Token1": -11, b"Token2": -22},
            },
        ]
    )

    result = a.union(b)

    assert result == Value.from_primitive(
        [12, {b"1" * SCRIPT_HASH_SIZE: {b"Token1": 12, b"Token2": 24}}]
    )

    d = 10000000

    f = Value(1)

    assert f <= d


def test_inline_datum_serdes():
    @dataclass
    class TestDatum(PlutusData):
        a: int
        b: bytes

    output = TransactionOutput(
        Address.from_primitive(
            "addr_test1vrm9x2zsux7va6w892g38tvchnzahvcd9tykqf3ygnmwtaqyfg52x"
        ),
        1000000,
        datum=TestDatum(1, b"test"),
    )

    cbor = output.to_cbor_hex()

    assert cbor == TransactionOutput.from_cbor(cbor).to_cbor_hex()


def test_out_of_bound_asset():
    a = Asset({AssetName(b"abc"): 1 << 64})

    a.to_cbor_hex()  # okay to have out of bound asset

    tx = TransactionBody(mint=MultiAsset({ScriptHash(b"1" * SCRIPT_HASH_SIZE): a}))

    # Not okay only when minting
    with pytest.raises(InvalidDataException):
        tx.to_cbor_hex()


def test_zero_value():
    nft_output = Value(
        10000000,
        MultiAsset.from_primitive(
            {
                bytes.fromhex(
                    "a39a5998f2822dfc9111e447038c3cfffa883ed1b9e357be9cd60dfe"
                ): {b"MY_NFT_1": 0}
            }
        ),
    )
    assert len(nft_output.multi_asset) == 0


def test_empty_multiasset():
    nft_output = Value(
        10000000,
        MultiAsset.from_primitive(
            {
                bytes.fromhex(
                    "a39a5998f2822dfc9111e447038c3cfffa883ed1b9e357be9cd60dfe"
                ): {}
            }
        ),
    )
    assert len(nft_output.multi_asset) == 0


def test_add_empty():
    nft_output = Value(
        10000000,
        MultiAsset.from_primitive(
            {
                bytes.fromhex(
                    "a39a5998f2822dfc9111e447038c3cfffa883ed1b9e357be9cd60dfe"
                ): {b"MY_NFT_1": 100}
            }
        ),
    ) - Value(
        5,
        MultiAsset.from_primitive(
            {
                bytes.fromhex(
                    "a39a5998f2822dfc9111e447038c3cfffa883ed1b9e357be9cd60dfe"
                ): {b"MY_NFT_1": 100}
            }
        ),
    )
    assert len(nft_output.multi_asset) == 0


def test_zero_value_pop():
    policy = bytes.fromhex("a39a5998f2822dfc9111e447038c3cfffa883ed1b9e357be9cd60dfe")
    nft_output = Value(
        10000000,
        MultiAsset.from_primitive({policy: {b"MY_NFT_1": 0, b"MY_NFT_2": 1}}),
    )
    assert len(nft_output.multi_asset) == 1
    assert len(nft_output.multi_asset[ScriptHash(policy)]) == 1


def test_empty_multiasset_pop():
    nft_output = Value(
        10000000,
        MultiAsset.from_primitive(
            {
                bytes.fromhex(
                    "a39a5998f2822dfc9111e447038c3cfffa883ed1b9e357be9cd60dfe"
                ): {},
                bytes.fromhex(
                    "b39a5998f2822dfc9111e447038c3cfffa883ed1b9e357be9cd60dfe"
                ): {b"MY_NFT_1": 1},
            }
        ),
    )
    assert len(nft_output.multi_asset) == 1


def test_add_empty_pop():
    policy = bytes.fromhex("a39a5998f2822dfc9111e447038c3cfffa883ed1b9e357be9cd60dfe")
    nft_output = Value(
        10000000,
        MultiAsset.from_primitive({policy: {b"MY_NFT_1": 100, b"MY_NFT_2": 100}}),
    ) - Value(
        5,
        MultiAsset.from_primitive({policy: {b"MY_NFT_1": 100}}),
    )
    assert len(nft_output.multi_asset) == 1
    assert len(nft_output.multi_asset[ScriptHash(policy)]) == 1


def test_decode_param_update_proposal_tx():
    # The proposal of decreasing treasury tax from 20% to 10% on mainnet
    # https://cardanoscan.io/transaction/941502b0aa104c850d197923259444d2b57cab7af18b63143775465aaacc84f5
    tx_cbor_hex = """84a700d90102868258202f980a7d47a6195c975c266335211afd3b9cabb5db5165e6e6d9cb18418415ab008258202f980a7d47a6195c975c266335211afd3b9cabb5db5165e6e6d9cb18418415ab018258202f980a7d47a6195c975c266335211afd3b9cabb5db5165e6e6d9cb18418415ab028258202f980a7d47a6195c975c266335211afd3b9cabb5db5165e6e6d9cb18418415ab0382582040aba0069d0dce7f801a9d16c26d469ec8ce16e1eb68379ae2774e5d28f33d5b008258206ba686304126196267200c6502df4b42af898ad2fb1621561fdb0a457fd8b68b000dd90102818258202f980a7d47a6195c975c266335211afd3b9cabb5db5165e6e6d9cb18418415ab040181825839013c55ef61a7fac4c7f94dc65052586f31dd659acddffc69f13d2c4364646c9e5f7484e8aeceba94566b73b8b50394eb6bfb54f67ac5885d591ab25dc1bf021a0004ee04031a08d0f5dc0b58204a080e29d89a598d6a3c000c9f15f4ab74a10ffdaa320f256fc7f69b75ff8a5914d9010281841b000000174876e800581de1646c9e5f7484e8aeceba94566b73b8b50394eb6bfb54f67ac5885d598400825820b2a591ac219ce6dcca5847e0248015209c7cb0436aa6bd6863d0c1f152a60bc500a10bd81e82010a581cfa24fb305126805cf2164c161d852a0e7330cf988f1fe558cf7d4a64827835697066733a2f2f516d634b51676763706f757568414176555947447a6f4b674d77625a536b57716945654536633637534a336b457158209b2438f0032a0c24ed62d12d6bdb79b47e2bd0c4d2dd4f4936c055ead7109cafa300d90102818258205d58313597871a1823742d172d738fcd1fee4800ba41859db790f981d4dae74e584089b07924734e5b9d813b43638c3e2e6f4ac1e473e454d2d5b404b7bee939d8b5046b6a5c4ba0b51096d5538feb933e802a5944442b046ef11b2381ffce70f70e07d90102815908545908510101003232323232323232323232323232323232323232323232323232323232323232323232323232323232259323255333573466e1d20000011180098111bab357426ae88d55cf00104554ccd5cd19b87480100044600422c6aae74004dd51aba1357446ae88d55cf1baa3255333573466e1d200a35573a002226ae84d5d11aab9e00111637546ae84d5d11aba235573c6ea800642b26006003149a2c8a4c301f801c0052000c00e0070018016006901e4070c00e003000c00d20d00fc000c0003003800a4005801c00e003002c00d20c09a0c80e1801c006001801a4101b5881380018000600700148013003801c006005801a410100078001801c006001801a4101001f8001800060070014801b0038018096007001800600690404002600060001801c0052008c00e006025801c006001801a41209d8001800060070014802b003801c006005801a410112f501c3003800c00300348202b7881300030000c00e00290066007003800c00b003482032ad7b806038403060070014803b00380180960003003800a4021801c00e003002c00d20f40380e1801c006001801a41403f800100a0c00e0029009600f0030078040c00e002900a600f003800c00b003301a483403e01a600700180060066034904801e00060001801c0052016c01e00600f801c006001801980c2402900e30000c00e002901060070030128060c00e00290116007003800c00b003483c0ba03860070018006006906432e00040283003800a40498003003800a404d802c00e00f003800c00b003301a480cb0003003800c003003301a4802b00030001801c01e0070018016006603490605c0160006007001800600660349048276000600030000c00e0029014600b003801c00c04b003800c00300348203a2489b00030001801c00e006025801c006001801a4101b11dc2df80018000c0003003800a4055802c00e007003012c00e003000c00d2080b8b872c000c0006007003801809600700180060069040607e4155016000600030000c00e00290166007003012c00e003000c00d2080c001c000c0003003800a405d801c00e003002c00d20c80180e1801c006001801a412007800100a0c00e00290186007003013c0006007001480cb005801801e006003801800e00600500403003800a4069802c00c00f003001c00c007003803c00e003002c00c05300333023480692028c0004014c00c00b003003c00c00f003003c00e00f003800c00b00301480590052008003003800a406d801c00e003002c00d2000c00d2006c00060070018006006900a600060001801c0052038c00e007001801600690006006901260003003800c003003483281300020141801c005203ac00e006027801c006001801a403d800180006007001480f3003801804e00700180060069040404af3c4e302600060001801c005203ec00e006013801c006001801a4101416f0fd20b80018000600700148103003801c006005801a403501c3003800c0030034812b00030000c00e0029021600f003800c00a01ac00e003000c00ccc08d20d00f4800b00030000c0000000000803c00c016008401e006009801c006001801807e0060298000c000401e006007801c0060018018074020c000400e00f003800c00b003010c000802180020070018006006019801805e0003000400600580180760060138000800c00b00330134805200c400e00300080330004006005801a4001801a410112f58000801c00600901260008019806a40118002007001800600690404a75ee01e00060008018046000801801e000300c4832004c025201430094800a0030028052003002c00d2002c000300648010c0092002300748028c0312000300b48018c0292012300948008c0212066801a40018000c0192008300a2233335573e00250002801994004d55ce800cd55cf0008d5d08014c00cd5d10011263009222532900389800a4d2219002912c80344c01526910c80148964cc04cdd68010034564cc03801400626601800e0071801226601800e01518010096400a3000910c008600444002600244004a664600200244246466004460044460040064600444600200646a660080080066a00600224446600644b20051800484ccc02600244666ae68cdc3801000c00200500a91199ab9a33710004003000801488ccd5cd19b89002001800400a44666ae68cdc4801000c00a00122333573466e20008006005000912a999ab9a3371200400222002220052255333573466e2400800444008440040026eb400a42660080026eb000a4264666015001229002914801c8954ccd5cd19b8700400211333573466e1c00c006001002118011229002914801c88cc044cdc100200099b82002003245200522900391199ab9a3371066e08010004cdc1001001c002004403245200522900391199ab9a3371266e08010004cdc1001001c00a00048a400a45200722333573466e20cdc100200099b820020038014000912c99807001000c40062004912c99807001000c400a2002001199919ab9a357466ae880048cc028dd69aba1003375a6ae84008d5d1000934000dd60010a40064666ae68d5d1800c0020052225933006003357420031330050023574400318010600a444aa666ae68cdc3a400000222c22aa666ae68cdc4000a4000226600666e05200000233702900000088994004cdc2001800ccdc20010008cc010008004c01088954ccd5cd19b87480000044400844cc00c004cdc300100091119803112c800c60012219002911919806912c800c4c02401a442b26600a004019130040018c008002590028c804c8888888800d1900991111111002a244b267201722222222008001000c600518000001112a999ab9a3370e004002230001155333573466e240080044600823002229002914801c88ccd5cd19b893370400800266e0800800e00100208c8c0040048c0088cc00800800505a182050082a0821a0007c6d41a06a71df2f5f6"""
    tx = Transaction.from_cbor(tx_cbor_hex)
    assert len(tx.transaction_body.proposal_procedures) == 1
    assert isinstance(
        tx.transaction_body.proposal_procedures[0].gov_action, ParameterChangeAction
    )
    assert tx.transaction_body.proposal_procedures[
        0
    ].gov_action.protocol_param_update.treasury_growth_rate == Fraction(1, 10)


def test_decode_byron_transaction():
    tx_cbor_hex = """83a400818258205d5f5c04aaa2367c5a700cf6ba9e9da76e214a0a1485a174618cb38b292bf0d9000182825839016a2fcce35ec3795b9418ae49b69074a17cdd0a7c60ae6ba63fc85eff17eabf85728a590b7785f27d60dea7d4bcb356b438b9d577a45547fe1b0000001e3001052482584c82d818584283581c91d0a0518e3e764e13f6ef37580a6be8ab14da4f3066fd01af01da6aa101581e581cabbf051bdee353839fbb21a6d4e6c584138a6a33896bb96d4124a330001a3592e2cc1a0a6526b0021a0002964d031a012f6296a10081825820e8fe69f9fd8afcb4792e3ca0f08b49e6eece1788c2d7b026096cfdbd1344a9bc5840dcef77b73af0922005f4b60d21333628348864c405ff52efd3f72523bf2c790e662650ad9951d306b40ce5beddf5b8eebb6731156b8b7617f6614b9ffdf2fb05f6"""
    tx = Transaction.from_cbor(tx_cbor_hex)
    check_two_way_cbor(tx)
    assert tx.id == TransactionId.from_primitive(
        "52e274237caceb4e0916587d2b4ba19d89fb40e8e85338f9bb4f75fcec1256a2"
    )
