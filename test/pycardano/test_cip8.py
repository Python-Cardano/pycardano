from pycardano.cip.cip8 import sign, verify
from pycardano.crypto.bip32 import BIP32ED25519PrivateKey, HDWallet
from pycardano.key import (
    ExtendedSigningKey,
    ExtendedVerificationKey,
    PaymentSigningKey,
    PaymentVerificationKey,
    StakeSigningKey,
    StakeVerificationKey,
)
from pycardano.network import Network

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

STAKE_SK = StakeSigningKey.from_json("""{
        "type": "StakeSigningKeyShelley_ed25519",
        "description": "Stake Signing Key",
        "cborHex": "5820ff3a330df8859e4e5f42a97fcaee73f6a00d0cf864f4bca902bd106d423f02c0"
    }""")

STAKE_VK = StakeVerificationKey.from_json("""{
        "type": "StakeVerificationKeyShelley_ed25519",
        "description": "Stake Verification Key",
        "cborHex": "58205edaa384c658c2bd8945ae389edac0a5bd452d0cfd5d1245e3ecd540030d1e3c"
    }""")


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


def test_verify_message_stake_address():
    signed_message = {
        "signature": "84582aa201276761646472657373581de0219f8e3ffefc82395df0bfcfe4e576f8f824bae0c731be35321c01d7a166686173686564f452507963617264616e6f20697320636f6f6c2e58402f2b75301a20876beba03ec68b30c5fbaebc99cb1d038b679340eb2299c2b75cd9c6c884c198e89f690548ee94a87168f5db34acf024d5788e58d119bcba630d",
        "key": "a40101032720062158200d8e03b5673bf8dabc567dd6150ebcd56179a91a6c0b245f477033dcab7dc780",
    }

    verification = verify(signed_message, attach_cose_key=True)
    assert verification["verified"]
    assert verification["message"] == "Pycardano is cool."
    assert (
        str(verification["signing_address"])
        == "stake_test1uqselr3llm7gyw2a7zlule89wmu0sf96urrnr034xgwqr4csd30df"
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


def test_sign_message_with_stake():
    message = "Pycardano is cool."
    signed_message = sign(
        message, signing_key=STAKE_SK, attach_cose_key=False, network=Network.TESTNET
    )
    assert (
        signed_message
        == "84584da301276761646472657373581de04828a2dadba97ca9fd0cdc99975899470c219bdc0d828cfa6ddf6d690458205edaa384c658c2bd8945ae389edac0a5bd452d0cfd5d1245e3ecd540030d1e3ca166686173686564f452507963617264616e6f20697320636f6f6c2e5840ba1dd643f0d2e844f0509b1a7161ae4a3650f1d553fcc6e517020c5703acb70dfeea1014f2a1513baefaa2279cb151e8ff2dada6b51269cf33127d3c05829502"
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


def test_extended_sign_and_verify():
    # try first with no cose key attached

    message = "Pycardano is cool."
    signed_message = sign(
        message,
        signing_key=EXTENDED_SK,
        attach_cose_key=False,
        network=Network.TESTNET,
    )

    verification = verify(signed_message)
    assert verification["verified"]
    assert verification["message"] == "Pycardano is cool."
    assert verification["signing_address"].payment_part == EXTENDED_VK.hash()

    # try again but attach cose key
    signed_message = sign(
        message, signing_key=EXTENDED_SK, attach_cose_key=True, network=Network.TESTNET
    )

    verification = verify(signed_message)
    assert verification["verified"]
    assert verification["message"] == "Pycardano is cool."
    assert verification["signing_address"].payment_part == EXTENDED_VK.hash()


def test_sign_and_verify_stake():
    # try first with no cose key attached
    message = "Pycardano is cool."
    signed_message = sign(
        message, signing_key=STAKE_SK, attach_cose_key=False, network=Network.TESTNET
    )

    verification = verify(signed_message)
    assert verification["verified"]
    assert verification["message"] == "Pycardano is cool."
    assert verification["signing_address"].payment_part == None
    assert verification["signing_address"].staking_part == STAKE_VK.hash()

    # try again but attach cose key
    signed_message = sign(
        message, signing_key=STAKE_SK, attach_cose_key=True, network=Network.TESTNET
    )

    verification = verify(signed_message)
    assert verification["verified"]
    assert verification["message"] == "Pycardano is cool."
    assert verification["signing_address"].payment_part == None
    assert verification["signing_address"].staking_part == STAKE_VK.hash()
