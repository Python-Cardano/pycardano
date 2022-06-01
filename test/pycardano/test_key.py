import pathlib
import tempfile

from pycardano.key import (
    ExtendedSigningKey,
    ExtendedVerificationKey,
    PaymentKeyPair,
    PaymentSigningKey,
    PaymentVerificationKey,
)

SK = PaymentSigningKey.from_json(
    """{
        "type": "GenesisUTxOSigningKey_ed25519",
        "description": "Genesis Initial UTxO Signing Key",
        "cborHex": "5820093be5cd3987d0c9fd8854ef908f7746b69e2d73320db6dc0f780d81585b84c2"
    }"""
)

VK = PaymentVerificationKey.from_json(
    """{
        "type": "GenesisUTxOVerificationKey_ed25519",
        "description": "Genesis Initial UTxO Verification Key",
        "cborHex": "58208be8339e9f3addfa6810d59e2f072f85e64d4c024c087e0d24f8317c6544f62f"
    }"""
)

EXTENDED_SK = ExtendedSigningKey.from_json(
    """{
        "type": "PaymentExtendedSigningKeyShelley_ed25519_bip32",
        "description": "Payment Signing Key",
        "cborHex": "5880e8428867ab9cc9304379a3ce0c238a592bd6d2349d2ebaf8a6ed2c6d2974a15ad59c74b6d8fa3edd032c6261a73998b7deafe983b6eeaff8b6fb3fab06bdf8019b693a62bce7a3cad1b9c02d22125767201c65db27484bb67d3cee7df7288d62c099ac0ce4a215355b149fd3114a2a7ef0438f01f8872c4487a61b469e26aae4"
    }"""
)

EXTENDED_VK = ExtendedVerificationKey.from_json(
    """{
        "type": "PaymentExtendedVerificationKeyShelley_ed25519_bip32",
        "description": "Payment Verification Key",
        "cborHex": "58409b693a62bce7a3cad1b9c02d22125767201c65db27484bb67d3cee7df7288d62c099ac0ce4a215355b149fd3114a2a7ef0438f01f8872c4487a61b469e26aae4"
    }"""
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
    sk = PaymentSigningKey.generate()
    vk = PaymentVerificationKey.from_signing_key(sk)
    assert PaymentKeyPair(sk, vk) == PaymentKeyPair.from_signing_key(sk)


def test_key_load():
    sk = PaymentSigningKey.load(
        str(pathlib.Path(__file__).parent / "../resources/keys/payment.skey")
    )


def test_key_save():
    with tempfile.NamedTemporaryFile() as f:
        SK.save(f.name)
        sk = PaymentSigningKey.load(f.name)
        assert SK == sk
