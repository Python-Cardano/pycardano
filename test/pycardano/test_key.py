import json
import os
import pathlib
import tempfile

import pytest
from mnemonic import Mnemonic

from pycardano import HDWallet, StakeKeyPair, StakeSigningKey, StakeVerificationKey
from pycardano.exception import InvalidKeyTypeException
from pycardano.key import (
    ExtendedSigningKey,
    ExtendedVerificationKey,
    Key,
    PaymentExtendedSigningKey,
    PaymentKeyPair,
    PaymentSigningKey,
    PaymentVerificationKey,
    StakeExtendedSigningKey,
    StakePoolKeyPair,
    StakePoolSigningKey,
    StakePoolVerificationKey,
)

SK = PaymentSigningKey.from_json("""{
        "type": "GenesisUTxOSigningKey_ed25519",
        "description": "Genesis Initial UTxO Signing Key",
        "cborHex": "5820093be5cd3987d0c9fd8854ef908f7746b69e2d73320db6dc0f780d81585b84c2"
    }""")

VK = PaymentVerificationKey.from_json("""{
        "type": "GenesisUTxOVerificationKey_ed25519",
        "description": "Genesis Initial UTxO Verification Key",
        "cborHex": "58208be8339e9f3addfa6810d59e2f072f85e64d4c024c087e0d24f8317c6544f62f"
    }""")

SPSK = StakePoolSigningKey.from_json("""{
        "type": "StakePoolSigningKey_ed25519", 
        "description": "StakePoolSigningKey_ed25519", 
        "cborHex": "582044181bd0e6be21cea5b0751b8c6d4f88a5cb2d5dfec31a271add617f7ce559a9"
    }""")

SPVK = StakePoolVerificationKey.from_json("""{
        "type": "StakePoolVerificationKey_ed25519",
        "description": "StakePoolVerificationKey_ed25519", 
        "cborHex": "5820354ce32da92e7116f6c70e9be99a3a601d33137d0685ab5b7e2ff5b656989299"
     }""")

EXTENDED_SK = ExtendedSigningKey.from_json("""{
        "type": "PaymentExtendedSigningKeyShelley_ed25519_bip32",
        "description": "Payment Signing Key",
        "cborHex": "5880e8428867ab9cc9304379a3ce0c238a592bd6d2349d2ebaf8a6ed2c6d2974a15ad59c74b6d8fa3edd032c6261a73998b7deafe983b6eeaff8b6fb3fab06bdf8019b693a62bce7a3cad1b9c02d22125767201c65db27484bb67d3cee7df7288d62c099ac0ce4a215355b149fd3114a2a7ef0438f01f8872c4487a61b469e26aae4"
    }""")

EXTENDED_VK = ExtendedVerificationKey.from_json("""{
        "type": "PaymentExtendedVerificationKeyShelley_ed25519_bip32",
        "description": "Payment Verification Key",
        "cborHex": "58409b693a62bce7a3cad1b9c02d22125767201c65db27484bb67d3cee7df7288d62c099ac0ce4a215355b149fd3114a2a7ef0438f01f8872c4487a61b469e26aae4"
    }""")


def test_invalid_key_type():
    data = json.dumps(
        {
            "type": "invalid_type",
            "payload": "example_payload",
            "description": "example_description",
        }
    )

    with pytest.raises(InvalidKeyTypeException):
        Key.from_json(data, validate_type=True)


def test_bytes_conversion():
    assert bytes(Key(b"1234")) == b"1234"


def test_eq_not_instance():
    assert Key(b"hello") != "1234"


def test_from_hdwallet_missing_xprivate_key():
    with pytest.raises(InvalidKeyTypeException):
        ExtendedSigningKey(b"1234").from_hdwallet(
            HDWallet(
                b"root_xprivate_key",
                b"root_public_key",
                b"root_chain_code",
                None,
                b"valid_public_key",
                chain_code=b"valid_chain_code",
            )
        )

    with pytest.raises(InvalidKeyTypeException):
        ExtendedSigningKey(b"1234").from_hdwallet(
            HDWallet(
                b"root_xprivate_key",
                b"root_public_key",
                b"root_chain_code",
                b"valid_xprivate_key",
                b"valid_public_key",
                None,
            )
        )


def test_payment_key():
    assert (
        SK.payload
        == b"\t;\xe5\xcd9\x87\xd0\xc9\xfd\x88T\xef\x90\x8fwF\xb6\x9e-s2\r\xb6\xdc\x0fx\r\x81X[\x84\xc2"
    )
    assert (
        VK.payload
        == b"\x8b\xe83\x9e\x9f:\xdd\xfah\x10\xd5\x9e/\x07/\x85\xe6ML\x02L\x08~\r$\xf81|eD\xf6/"
    )
    assert (
        VK.hash().payload == b"\xd4\x13\xc1t]0`#\xe4\x95\x89\xe6X\xa7\xb7\xa4"
        b"\xb4\xdd\xa1e\xff\\\x97\xd8\xc8\xb9y\xbf"
    )
    assert PaymentKeyPair.from_signing_key(SK).verification_key.payload == VK.payload


def test_stake_pool_key():
    assert (
        SPSK.payload
        == b"D\x18\x1b\xd0\xe6\xbe!\xce\xa5\xb0u\x1b\x8cmO\x88\xa5\xcb-]\xfe\xc3\x1a'\x1a\xdda\x7f|\xe5Y\xa9"
    )
    assert (
        SPVK.payload
        == b"5L\xe3-\xa9.q\x16\xf6\xc7\x0e\x9b\xe9\x9a:`\x1d3\x13}\x06\x85\xab[~/\xf5\xb6V\x98\x92\x99"
    )
    assert (
        SPVK.hash().payload
        == b'3/\x13v\xecJi\xe3\x93\xe1\x88`1\x80\xa6\r"\n\x10\xf0<1\xb6)|\xa4c\xb5'
    )
    assert (
        StakePoolKeyPair.from_signing_key(SPSK).verification_key.payload == SPVK.payload
    )


def test_extended_payment_key():
    assert EXTENDED_VK == ExtendedVerificationKey.from_signing_key(EXTENDED_SK)


def test_extended_payment_key_hash():
    assert (
        str(EXTENDED_VK.hash())
        == "c15a362df1b521e2f664cc66db77aad41311dc5ba0998c29862c2a93"
    )


def test_extended_payment_key_sign():
    message = bytes.fromhex(
        "1bf8beed1677524b44903f09a7bb596ffb9d48e368b19293ca834df19ddbb566"
    )
    assert (
        EXTENDED_SK.sign(message).hex()
        == "f09d56ad9163f42bd4b37b1eeb4d2325e8b6c7e85919ff0e2770ba0e438fc065"
        "d057a3bc929fb474d1d056345bec39392973e0d4446d7b8e197aae5bd6e3400a"
    )


def test_key_pair():
    PaymentSigningKey.generate()


def test_payment_key_pair():
    PaymentKeyPair.generate()
    sk = PaymentSigningKey.generate()
    vk = PaymentVerificationKey.from_signing_key(sk)
    assert PaymentKeyPair(sk, vk) == PaymentKeyPair.from_signing_key(sk)


def test_stake_key_pair():
    StakeKeyPair.generate()
    sk = StakeSigningKey.generate()
    vk = StakeVerificationKey.from_signing_key(sk)
    assert StakeKeyPair(sk, vk) == StakeKeyPair.from_signing_key(sk)


def test_stake_pool_key_pair():
    StakePoolKeyPair.generate()
    sk = StakePoolSigningKey.generate()
    vk = StakePoolVerificationKey.from_signing_key(sk)
    assert StakePoolKeyPair(sk, vk) == StakePoolKeyPair.from_signing_key(sk)


def test_key_load():
    PaymentSigningKey.load(
        str(pathlib.Path(__file__).parent / "../resources/keys/payment.skey")
    )


def test_stake_pool_key_load():
    sk = StakePoolSigningKey.load(
        str(pathlib.Path(__file__).parent / "../resources/keys/cold.skey")
    )
    vk = StakePoolVerificationKey.load(
        str(pathlib.Path(__file__).parent / "../resources/keys/cold.vkey")
    )
    assert sk == StakePoolSigningKey.from_json(sk.to_json())
    assert vk == StakePoolVerificationKey.from_json(vk.to_json())


def test_key_save():
    # On Windows, NamedTemporaryFile keeps the file locked while open.
    # Use delete=False and close the handle first, then clean up manually.
    with tempfile.NamedTemporaryFile(delete=False) as f:
        tmp_path = f.name
    try:
        SK.save(tmp_path)
        sk = PaymentSigningKey.load(tmp_path)
        assert SK == sk
    finally:
        os.unlink(tmp_path)


def test_key_save_invalid_address():
    with tempfile.NamedTemporaryFile(delete=False) as f:
        tmp_path = f.name
    try:
        SK.save(tmp_path)
        with pytest.raises(IOError):
            VK.save(tmp_path)
    finally:
        os.unlink(tmp_path)


def test_stake_pool_key_save():
    with tempfile.NamedTemporaryFile(delete=False) as skf:
        sk_path = skf.name
    with tempfile.NamedTemporaryFile(delete=False) as vkf:
        vk_path = vkf.name
    try:
        SPSK.save(sk_path)
        sk = StakePoolSigningKey.load(sk_path)
        SPVK.save(vk_path)
        vk = StakePoolSigningKey.load(vk_path)
    finally:
        os.unlink(sk_path)
        os.unlink(vk_path)
    assert SPSK == sk
    assert SPVK == vk


def test_key_hash():
    sk = PaymentSigningKey.generate()
    vk = PaymentVerificationKey.from_signing_key(sk)

    sk_set = set()
    vk_set = set()

    for _ in range(2):
        sk_set.add(sk)
        vk_set.add(vk)

    assert len(sk_set) == 1
    assert len(vk_set) == 1


def test_stake_pool_key_hash():
    sk = StakePoolSigningKey.generate()
    vk = StakePoolVerificationKey.from_signing_key(sk)

    sk_set = set()
    vk_set = set()

    for _ in range(2):
        sk_set.add(sk)
        vk_set.add(vk)

    assert len(sk_set) == 1
    assert len(vk_set) == 1


def test_extended_signing_key_from_hd_wallet_uses_type_and_description_from_class():
    hd_wallet = HDWallet.from_mnemonic(Mnemonic().generate())

    extended_payment_key = PaymentExtendedSigningKey.from_hdwallet(hd_wallet)
    assert extended_payment_key.key_type == PaymentExtendedSigningKey.KEY_TYPE
    assert extended_payment_key.description == PaymentExtendedSigningKey.DESCRIPTION

    extended_stake_key = StakeExtendedSigningKey.from_hdwallet(hd_wallet)
    assert extended_stake_key.key_type == StakeExtendedSigningKey.KEY_TYPE
    assert extended_stake_key.description == StakeExtendedSigningKey.DESCRIPTION
