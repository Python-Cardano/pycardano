import pathlib
import tempfile

from pycardano.key import (
    ExtendedSigningKey,
    ExtendedVerificationKey,
    Message,
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


def test_verify_message():

    signed_message = "845869a3012704582060545b786d3a6f903158e35aae9b86548a99bc47d4b0a6f503ab5e78c1a9bbfc6761646472657373583900ddba3ad76313825f4f646f5aa6d323706653bda40ec1ae55582986a463e661768b92deba45b5ada4ab9e7ffd17ed3051b2e03500e0542e9aa166686173686564f452507963617264616e6f20697320636f6f6c2e58403b09cbae8d272ff94befd28cc04b152aea3c1633caffb4924a8a8c45be3ba6332a76d9f2aba833df53803286d32a5ee700990b79a0e86fab3cccdbfd37ce250f"

    message = Message(signed_message=signed_message)

    assert message.verify(cose_key_separate=False) is True
    assert message.message == "Pycardano is cool."
    assert (
        str(message.signing_address)
        == "addr_test1qrwm5wkhvvfcyh60v3h44fknydcxv5aa5s8vrtj4tq5cdfrrueshdzujm6aytddd5j4eullazlknq5djuq6spcz596dqjvm8nu"
    )


def test_verify_message_cose_key_separate():

    signed_message = {
        "signature": "845846a201276761646472657373583900ddba3ad76313825f4f646f5aa6d323706653bda40ec1ae55582986a463e661768b92deba45b5ada4ab9e7ffd17ed3051b2e03500e0542e9aa166686173686564f452507963617264616e6f20697320636f6f6c2e584040b65c973ba6e123f1e7f738205b10c709fe214a27d21b1c382e6dfa5772aaeeb6222943fd56b1dd6bfa5abfa4a4992d2abde110cbd0c8651fdfa679ba462605",
        "key": "a401010327200621582060545b786d3a6f903158e35aae9b86548a99bc47d4b0a6f503ab5e78c1a9bbfc",
    }

    message = Message(signed_message=signed_message)

    assert message.verify(cose_key_separate=True) is True
    assert message.message == "Pycardano is cool."
    assert (
        str(message.signing_address)
        == "addr_test1qrwm5wkhvvfcyh60v3h44fknydcxv5aa5s8vrtj4tq5cdfrrueshdzujm6aytddd5j4eullazlknq5djuq6spcz596dqjvm8nu"
    )


def test_sign_message():

    message = Message(message="Pycardano is cool.")
    signed_message = message.sign(
        signing_key=SK, verification_key=VK, cose_key_separate=False
    )
    assert (
        signed_message
        == "84582da20127676164647265737358208be8339e9f3addfa6810d59e2f072f85e64d4c024c087e0d24f8317c6544f62fa166686173686564f452507963617264616e6f20697320636f6f6c2e584045009400ef415f5635a363e5a6cb06c08dd2e9b677cd5317463018f2a5430d9faed85e773ade91e65d7579ccdd4934aefac64e48722d50dd492931784332a30b"
    )


def test_sign_message_cosy_key_separate():

    message = Message(message="Pycardano is cool.")
    signed_message = message.sign(
        signing_key=SK, verification_key=VK, cose_key_separate=True
    )
    assert signed_message == {
        "signature": "845850a30127676164647265737358208be8339e9f3addfa6810d59e2f072f85e64d4c024c087e0d24f8317c6544f62f0458208be8339e9f3addfa6810d59e2f072f85e64d4c024c087e0d24f8317c6544f62fa166686173686564f452507963617264616e6f20697320636f6f6c2e5840b530b779ab8c78c445d91dd859878bdc94e7900865a920d6bc85a98b7b74c794eb4ef22a2712aa0d29840ab14a884aca32609001594bdde5368515d981b2fd0f",
        "key": b"a40101032720062158208be8339e9f3addfa6810d59e2f072f85e64d4c024c087e0d24f8317c6544f62f",
    }
