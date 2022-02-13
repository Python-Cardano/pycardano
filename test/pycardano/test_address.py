from pycardano.address import Address
from pycardano.key import PaymentVerificationKey
from pycardano.network import Network


def test_payment_addr():
    vk = PaymentVerificationKey.from_json(
        """{
        "type": "GenesisUTxOVerificationKey_ed25519",
        "description": "Genesis Initial UTxO Verification Key",
        "cborHex": "58208be8339e9f3addfa6810d59e2f072f85e64d4c024c087e0d24f8317c6544f62f"
    }"""
    )
    assert (
        Address(vk.hash(), network=Network.TESTNET).encode()
        == "addr_test1vr2p8st5t5cxqglyjky7vk98k7jtfhdpvhl4e97cezuhn0cqcexl7"
    )
