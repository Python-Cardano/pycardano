import pytest

from pycardano.address import Address
from pycardano.exception import InvalidOperationException
from pycardano.hash import TransactionId, SCRIPT_HASH_SIZE
from pycardano.key import PaymentKeyPair, PaymentSigningKey, AddressKey
from pycardano.transaction import (FullMultiAsset, MultiAsset, Transaction, TransactionBody, TransactionInput,
                                   TransactionOutput, TransactionWitnessSet)
from pycardano.witness import VerificationKeyWitness

from test.pycardano.util import check_two_way_cbor


def test_transaction_input():
    tx_id_hex = "732bfd67e66be8e8288349fcaaa2294973ef6271cc189a239bb431275401b8e5"
    tx_in = TransactionInput(TransactionId(bytes.fromhex(tx_id_hex)), 0)
    assert tx_in.to_cbor() == "825820732bfd67e66be8e8288349fcaaa2294973ef6271cc189a239bb431275401b8e500"
    check_two_way_cbor(tx_in)


def test_transaction_output():
    addr = Address.decode("addr_test1vrm9x2zsux7va6w892g38tvchnzahvcd9tykqf3ygnmwtaqyfg52x")
    output = TransactionOutput(addr, 100000000000)
    assert output.to_cbor() == "82581d60f6532850e1bccee9c72a9113ad98bcc5dbb30d2ac960262444f6e5f41b000000174876e800"
    check_two_way_cbor(output)


def make_transaction_body():
    tx_id_hex = "732bfd67e66be8e8288349fcaaa2294973ef6271cc189a239bb431275401b8e5"
    tx_in = TransactionInput(TransactionId(bytes.fromhex(tx_id_hex)), 0)
    addr = Address.decode("addr_test1vrm9x2zsux7va6w892g38tvchnzahvcd9tykqf3ygnmwtaqyfg52x")
    output1 = TransactionOutput(addr, 100000000000)
    output2 = TransactionOutput(addr, 799999834103)
    fee = 165897
    tx_body = TransactionBody(inputs=[tx_in],
                              outputs=[output1, output2],
                              fee=fee,
                              collateral=[],
                              required_signers=[])
    return tx_body


def test_transaction_body():
    tx_body = make_transaction_body()
    assert tx_body.to_cbor() == "a50081825820732bfd67e66be8e8288349fcaaa2294973ef6271cc189a239bb431275401b8e" \
                                "500018282581d60f6532850e1bccee9c72a9113ad98bcc5dbb30d2ac960262444f6e5f41b00" \
                                "0000174876e80082581d60f6532850e1bccee9c72a9113ad98bcc5dbb30d2ac960262444f6e" \
                                "5f41b000000ba43b4b7f7021a000288090d800e80"
    check_two_way_cbor(tx_body)


def test_transaction():
    tx_body = make_transaction_body()
    sk = PaymentSigningKey.from_json("""{
        "type": "GenesisUTxOSigningKey_ed25519",
        "description": "Genesis Initial UTxO Signing Key",
        "cborHex": "5820093be5cd3987d0c9fd8854ef908f7746b69e2d73320db6dc0f780d81585b84c2"
    }""")
    vk = AddressKey(PaymentKeyPair.from_signing_key(sk.payload).verification_key.payload)
    signature = sk.sign(tx_body.hash())
    assert signature == b"\xb6+-g\xba\x18TL\xe0\xa1\x975\xf9R\x8b\x89\x0b\x1a*\x7f\x8a\xf9\x03\xa3\xde\x92\x7f\x91" \
                        b"\xb8\x1f\xdbF\xbdy\xc9\x15\xc7\x05T\xdb\xa4i\xaa\xb8\xa39\x90\xa7\x1d\xe0\xb0$\x9fL~p" \
                        b"\x9d`)\xbb\xac\xe1P\x04"
    vk_witness = [VerificationKeyWitness(vk, signature)]
    signed_tx = Transaction(tx_body, TransactionWitnessSet(vkey_witnesses=vk_witness))
    check_two_way_cbor(signed_tx)


def test_multi_asset():
    serialized_full_multi_asset = [100,
                                   {b"1" * SCRIPT_HASH_SIZE: {
                                       b"TestToken1": 10000000,
                                       b"TestToken2": 20000000
                                   }}]
    full_multi_asset = FullMultiAsset.from_primitive(serialized_full_multi_asset)
    assert full_multi_asset.to_primitive() == serialized_full_multi_asset
    check_two_way_cbor(full_multi_asset)


def test_multi_asset_addition():
    a = MultiAsset.from_primitive({
        b"1" * SCRIPT_HASH_SIZE: {
            b"Token1": 1,
            b"Token2": 2
        }
    })

    b = MultiAsset.from_primitive({
        b"1" * SCRIPT_HASH_SIZE: {
            b"Token1": 10,
            b"Token2": 20
        },
        b"2" * SCRIPT_HASH_SIZE: {
            b"Token1": 1,
            b"Token2": 2
        }
    })

    assert a + b == MultiAsset.from_primitive({
        b"1" * SCRIPT_HASH_SIZE: {
            b"Token1": 11,
            b"Token2": 22
        },
        b"2" * SCRIPT_HASH_SIZE: {
            b"Token1": 1,
            b"Token2": 2
        }
    })


def test_multi_asset_subtraction():
    a = MultiAsset.from_primitive({
        b"1" * SCRIPT_HASH_SIZE: {
            b"Token1": 1,
            b"Token2": 2
        }
    })

    b = MultiAsset.from_primitive({
        b"1" * SCRIPT_HASH_SIZE: {
            b"Token1": 10,
            b"Token2": 20
        },
        b"2" * SCRIPT_HASH_SIZE: {
            b"Token1": 1,
            b"Token2": 2
        }
    })

    assert b - a == MultiAsset.from_primitive({
        b"1" * SCRIPT_HASH_SIZE: {
            b"Token1": 9,
            b"Token2": 18
        },
        b"2" * SCRIPT_HASH_SIZE: {
            b"Token1": 1,
            b"Token2": 2
        }
    })

    with pytest.raises(InvalidOperationException):
        a - b
