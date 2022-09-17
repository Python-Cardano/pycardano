from pycardano.address import Address
from pycardano.hdwallet import HDWallet
from pycardano.key import PaymentVerificationKey
from pycardano.network import Network


# Tests copied from: https://github.com/Emurgo/cardano-serialization-lib/blob/master/rust/src/address.rs

MNEMONIC_12 = "test walk nut penalty hip pave soap entry language right filter choice"
MNEMONIC_15 = "art forum devote street sure rather head chuckle guard poverty release quote oak craft enemy"

def test_mnemonic():
    wrong_mnemonic = "test walk nut penalty hip pave soap entry language right filter"
    hdwallet = HDWallet()
    assert not hdwallet.is_mnemonic(wrong_mnemonic)


def test_mnemonic_generation():
    hdwallet = HDWallet()
    mnemonic_words = hdwallet.generate_mnemonic(strength=128)
    assert hdwallet.is_mnemonic(mnemonic_words)


def test_payment_address_12_reward():
    hdwallet_stake = HDWallet()
    hdwallet_stake.from_mnemonic(MNEMONIC_12)
    hdwallet_stake.derive_from_path("m/1852'/1815'/0'/2/0")
    stake_public_key = hdwallet_stake.public_key
    stake_vk = PaymentVerificationKey.from_primitive(bytes.fromhex(stake_public_key))

    assert (
        Address(
            payment_part=None, staking_part=stake_vk.hash(), network=Network.TESTNET
        ).encode()
        == "stake_test1uqevw2xnsc0pvn9t9r9c7qryfqfeerchgrlm3ea2nefr9hqp8n5xl"
    )


def test_payment_address_12_base():
    hdwallet_spend = HDWallet().from_mnemonic(MNEMONIC_12)
    hdwallet_spend.derive_from_path("m/1852'/1815'/0'/0/0")
    spend_public_key = hdwallet_spend.public_key
    spend_vk = PaymentVerificationKey.from_primitive(bytes.fromhex(spend_public_key))

    hdwallet_stake = HDWallet().from_mnemonic(MNEMONIC_12)
    hdwallet_stake.derive_from_path("m/1852'/1815'/0'/2/0")
    stake_public_key = hdwallet_stake.public_key
    stake_vk = PaymentVerificationKey.from_primitive(bytes.fromhex(stake_public_key))

    assert (
        Address(spend_vk.hash(), stake_vk.hash(), network=Network.TESTNET).encode()
        == "addr_test1qz2fxv2umyhttkxyxp8x0dlpdt3k6cwng5pxj3jhsydzer3jcu5d8ps7zex2k2xt3uqxgjqnnj83ws8lhrn648jjxtwq2ytjqp"
    )


def test_payment_address_15_base():
    hdwallet_spend = HDWallet().from_mnemonic(MNEMONIC_15)
    hdwallet_spend.derive_from_path("m/1852'/1815'/0'/0/0")
    spend_public_key = hdwallet_spend.public_key
    spend_vk = PaymentVerificationKey.from_primitive(bytes.fromhex(spend_public_key))

    hdwallet_stake = HDWallet().from_mnemonic(MNEMONIC_15)
    hdwallet_stake.derive_from_path("m/1852'/1815'/0'/2/0")
    stake_public_key = hdwallet_stake.public_key
    stake_vk = PaymentVerificationKey.from_primitive(bytes.fromhex(stake_public_key))

    assert (
        Address(spend_vk.hash(), stake_vk.hash(), network=Network.MAINNET).encode()
        == "addr1q9u5vlrf4xkxv2qpwngf6cjhtw542ayty80v8dyr49rf5ewvxwdrt70qlcpeeagscasafhffqsxy36t90ldv06wqrk2qld6xc3"
    )
