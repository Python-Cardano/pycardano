from dataclasses import dataclass
from test.pycardano.util import check_two_way_cbor

import pytest
from typeguard import TypeCheckError

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
    assert (
            tx_in1
            == tx_in2
    )
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
    check_two_way_cbor(tx)


def test_transaction():
    tx_body = make_transaction_body()
    sk = PaymentSigningKey.from_json(
        """{
        "type": "GenesisUTxOSigningKey_ed25519",
        "description": "Genesis Initial UTxO Signing Key",
        "cborHex": "5820093be5cd3987d0c9fd8854ef908f7746b69e2d73320db6dc0f780d81585b84c2"
    }"""
    )
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

    assert result == Asset.from_primitive(
        {
            b"Token1": 2, b"Token2": 5
        }
    )

    assert a == a

    assert a <= b
    assert not b <= a
    assert a != b

    assert a <= c
    assert not c <= a
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
    assert not b <= a

    assert a != c
    assert a <= c
    assert not c <= a

    assert a != d
    assert not a <= d
    assert not d <= a

    assert not a == "abc"

    with pytest.raises(TypeCheckError):
        a <= 1


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

    assert a != b
    assert a <= b
    assert not b <= a

    assert a <= c
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
        [
            12,
            {
                b"1" * SCRIPT_HASH_SIZE: {b"Token1": 12, b"Token2": 24}
            }
        ]
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
