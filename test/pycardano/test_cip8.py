from pycardano.cip.cip8 import sign, verify
from pycardano.key import PaymentSigningKey, PaymentVerificationKey
from pycardano.network import Network

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


def test_verify_message():

    signed_message = "845869a3012704582060545b786d3a6f903158e35aae9b86548a99bc47d4b0a6f503ab5e78c1a9bbfc6761646472657373583900ddba3ad76313825f4f646f5aa6d323706653bda40ec1ae55582986a463e661768b92deba45b5ada4ab9e7ffd17ed3051b2e03500e0542e9aa166686173686564f452507963617264616e6f20697320636f6f6c2e58403b09cbae8d272ff94befd28cc04b152aea3c1633caffb4924a8a8c45be3ba6332a76d9f2aba833df53803286d32a5ee700990b79a0e86fab3cccdbfd37ce250f"

    verification = verify(signed_message)
    assert verification["verified"]
    assert verification["message"] == "Pycardano is cool."
    assert (
        str(verification["signing_address"])
        == "addr_test1qrwm5wkhvvfcyh60v3h44fknydcxv5aa5s8vrtj4tq5cdfrrueshdzujm6aytddd5j4eullazlknq5djuq6spcz596dqjvm8nu"
    )


def test_verify_message_cose_key_attached():

    signed_message = {
        "signature": "845846a201276761646472657373583900ddba3ad76313825f4f646f5aa6d323706653bda40ec1ae55582986a463e661768b92deba45b5ada4ab9e7ffd17ed3051b2e03500e0542e9aa166686173686564f452507963617264616e6f20697320636f6f6c2e584040b65c973ba6e123f1e7f738205b10c709fe214a27d21b1c382e6dfa5772aaeeb6222943fd56b1dd6bfa5abfa4a4992d2abde110cbd0c8651fdfa679ba462605",
        "key": "a401010327200621582060545b786d3a6f903158e35aae9b86548a99bc47d4b0a6f503ab5e78c1a9bbfc",
    }

    verification = verify(signed_message, attach_cose_key=True)
    assert verification["verified"]
    assert verification["message"] == "Pycardano is cool."
    assert (
        str(verification["signing_address"])
        == "addr_test1qrwm5wkhvvfcyh60v3h44fknydcxv5aa5s8vrtj4tq5cdfrrueshdzujm6aytddd5j4eullazlknq5djuq6spcz596dqjvm8nu"
    )


def test_sign_message():

    message = "Pycardano is cool."
    signed_message = sign(
        message, signing_key=SK, attach_cose_key=False, network=Network.TESTNET
    )
    assert (
        signed_message
        == "84584da301276761646472657373581d60d413c1745d306023e49589e658a7b7a4b4dda165ff5c97d8c8b979bf0458208be8339e9f3addfa6810d59e2f072f85e64d4c024c087e0d24f8317c6544f62fa166686173686564f452507963617264616e6f20697320636f6f6c2e5840278d36ecc026cb94d2674d66d020b4b99ccb5e905825f4f35d8ff601b22c563d694b41acdf46766c4bc7feeb8c73273a8be3cd81b5913f550db67a64bcb72b0a"
    )


def test_sign_message_cosy_key_separate():

    message = "Pycardano is cool."
    signed_message = sign(
        message, signing_key=SK, attach_cose_key=True, network=Network.TESTNET
    )
    assert signed_message == {
        "signature": "84582aa201276761646472657373581d60d413c1745d306023e49589e658a7b7a4b4dda165ff5c97d8c8b979bfa166686173686564f452507963617264616e6f20697320636f6f6c2e58407dc07e9304488c128a2cb82c48fb6224476b6d0bd2a44e3719bf8d09c8b15d540ca4f7730d13cd7894caf27a48e4ac3e9008e39c85b90b11fd4961b1b1622701",
        "key": "a40101032720062158208be8339e9f3addfa6810d59e2f072f85e64d4c024c087e0d24f8317c6544f62f",
    }


def test_sign_and_verify():

    # try first with no cose key attached
    message = "Pycardano is cool."
    signed_message = sign(
        message, signing_key=SK, attach_cose_key=False, network=Network.TESTNET
    )

    verification = verify(signed_message)
    assert verification["verified"]
    assert verification["message"] == "Pycardano is cool."
    assert verification["signing_address"].payment_part == VK.hash()

    # try again but attach cose key
    signed_message = sign(
        message, signing_key=SK, attach_cose_key=True, network=Network.TESTNET
    )

    verification = verify(signed_message)
    assert verification["verified"]
    assert verification["message"] == "Pycardano is cool."
    assert verification["signing_address"].payment_part == VK.hash()
