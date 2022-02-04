import pathlib
import tempfile

from pycardano.key import PaymentVerificationKey, PaymentSigningKey, PaymentKeyPair

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


def test_payment_key():
    assert SK.payload == b"\t;\xe5\xcd9\x87\xd0\xc9\xfd\x88T\xef\x90\x8fwF\xb6\x9e-s2\r\xb6\xdc\x0fx\r\x81X[\x84\xc2"
    assert VK.payload == b"\x8b\xe83\x9e\x9f:\xdd\xfah\x10\xd5\x9e/\x07/\x85\xe6ML\x02L\x08~\r$\xf81|eD\xf6/"
    assert VK.hash().payload == b"\xd4\x13\xc1t]0`#\xe4\x95\x89\xe6X\xa7\xb7\xa4" \
                                b"\xb4\xdd\xa1e\xff\\\x97\xd8\xc8\xb9y\xbf"
    assert PaymentKeyPair.from_signing_key(SK).verification_key.payload == VK.payload


def test_key_pair():
    sk = PaymentSigningKey.generate()
    vk = PaymentVerificationKey.from_signing_key(sk)
    assert PaymentKeyPair(sk, vk) == PaymentKeyPair.from_signing_key(sk)


def test_key_load():
    sk = PaymentSigningKey.load(str(pathlib.Path(__file__).parent / "../resources/keys/payment.skey"))


def test_key_save():
    with tempfile.NamedTemporaryFile() as f:
        SK.save(f.name)
        sk = PaymentSigningKey.load(f.name)
        assert SK == sk
