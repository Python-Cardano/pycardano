from pycardano.address import Address
from pycardano.crypto.bip32 import HDWallet
from pycardano.key import PaymentVerificationKey
from pycardano.network import Network

# Tests copied from: https://github.com/Emurgo/cardano-serialization-lib/blob/master/rust/src/address.rs

MNEMONIC_12 = "test walk nut penalty hip pave soap entry language right filter choice"
MNEMONIC_15 = "art forum devote street sure rather head chuckle guard poverty release quote oak craft enemy"
MNEMONIC_24 = "excess behave track soul table wear ocean cash stay nature item turtle palm soccer lunch horror start stumble month panic right must lock dress"

MNEMONIC_12_ENTROPY = "df9ed25ed146bf43336a5d7cf7395994"
MNEMONIC_15_ENTROPY = "0ccb74f36b7da1649a8144675522d4d8097c6412"
MNEMONIC_24_ENTROPY = "4e828f9a67ddcff0e6391ad4f26ddb7579f59ba14b6dd4baf63dcfdb9d2420da"


def test_mnemonic():
    wrong_mnemonic = "test walk nut penalty hip pave soap entry language right filter"
    assert not HDWallet.is_mnemonic(wrong_mnemonic)


def test_mnemonic_generation():
    mnemonic_words = HDWallet.generate_mnemonic(strength=128)
    assert HDWallet.is_mnemonic(mnemonic_words)


def test_payment_address_12_reward():
    hdwallet = HDWallet.from_mnemonic(MNEMONIC_12)
    hdwallet_stake = hdwallet.derive_from_path("m/1852'/1815'/0'/2/0")
    stake_public_key = hdwallet_stake.public_key
    stake_vk = PaymentVerificationKey.from_primitive(stake_public_key)

    assert (
        Address(
            payment_part=None, staking_part=stake_vk.hash(), network=Network.TESTNET
        ).encode()
        == "stake_test1uqevw2xnsc0pvn9t9r9c7qryfqfeerchgrlm3ea2nefr9hqp8n5xl"
    )

    assert (
        Address(
            payment_part=None, staking_part=stake_vk.hash(), network=Network.MAINNET
        ).encode()
        == "stake1uyevw2xnsc0pvn9t9r9c7qryfqfeerchgrlm3ea2nefr9hqxdekzz"
    )


def test_payment_address_12_reward2():
    hdwallet = HDWallet.from_mnemonic(MNEMONIC_12)
    hdwalletl_l1 = hdwallet.derive_from_index(
        hdwallet, 1852, private=True, hardened=True
    )
    hdwalletl_l2 = hdwallet.derive_from_index(
        hdwalletl_l1, 1815, private=True, hardened=True
    )
    hdwalletl_l3 = hdwallet.derive_from_index(
        hdwalletl_l2, 0, private=True, hardened=True
    )
    hdwalletl_l4 = hdwallet.derive_from_index(
        hdwalletl_l3, 2, private=False, hardened=False
    )
    hdwallet_stake = hdwallet.derive_from_index(
        hdwalletl_l4, 0, private=False, hardened=False
    )
    stake_public_key = hdwallet_stake.public_key
    stake_vk = PaymentVerificationKey.from_primitive(stake_public_key)

    assert (
        Address(
            payment_part=None, staking_part=stake_vk.hash(), network=Network.TESTNET
        ).encode()
        == "stake_test1uqevw2xnsc0pvn9t9r9c7qryfqfeerchgrlm3ea2nefr9hqp8n5xl"
    )

    assert (
        Address(
            payment_part=None, staking_part=stake_vk.hash(), network=Network.MAINNET
        ).encode()
        == "stake1uyevw2xnsc0pvn9t9r9c7qryfqfeerchgrlm3ea2nefr9hqxdekzz"
    )


def test_payment_address_12_base():
    hdwallet = HDWallet.from_mnemonic(MNEMONIC_12)
    hdwallet_spend = hdwallet.derive_from_path("m/1852'/1815'/0'/0/0")
    spend_public_key = hdwallet_spend.public_key
    spend_vk = PaymentVerificationKey.from_primitive(spend_public_key)

    hdwallet_stake = hdwallet.derive_from_path("m/1852'/1815'/0'/2/0")
    stake_public_key = hdwallet_stake.public_key
    stake_vk = PaymentVerificationKey.from_primitive(stake_public_key)

    assert (
        Address(spend_vk.hash(), stake_vk.hash(), network=Network.TESTNET).encode()
        == "addr_test1qz2fxv2umyhttkxyxp8x0dlpdt3k6cwng5pxj3jhsydzer3jcu5d8ps7zex2k2xt3uqxgjqnnj83ws8lhrn648jjxtwq2ytjqp"
    )

    assert (
        Address(spend_vk.hash(), stake_vk.hash(), network=Network.MAINNET).encode()
        == "addr1qx2fxv2umyhttkxyxp8x0dlpdt3k6cwng5pxj3jhsydzer3jcu5d8ps7zex2k2xt3uqxgjqnnj83ws8lhrn648jjxtwqfjkjv7"
    )


def test_payment_address_15_base():
    hdwallet = HDWallet.from_mnemonic(MNEMONIC_15)
    hdwallet_spend = hdwallet.derive_from_path("m/1852'/1815'/0'/0/0")
    spend_public_key = hdwallet_spend.public_key
    spend_vk = PaymentVerificationKey.from_primitive(spend_public_key)

    hdwallet_stake = hdwallet.derive_from_path("m/1852'/1815'/0'/2/0")
    stake_public_key = hdwallet_stake.public_key
    stake_vk = PaymentVerificationKey.from_primitive(stake_public_key)

    assert (
        Address(spend_vk.hash(), stake_vk.hash(), network=Network.TESTNET).encode()
        == "addr_test1qpu5vlrf4xkxv2qpwngf6cjhtw542ayty80v8dyr49rf5ewvxwdrt70qlcpeeagscasafhffqsxy36t90ldv06wqrk2qum8x5w"
    )

    assert (
        Address(spend_vk.hash(), stake_vk.hash(), network=Network.MAINNET).encode()
        == "addr1q9u5vlrf4xkxv2qpwngf6cjhtw542ayty80v8dyr49rf5ewvxwdrt70qlcpeeagscasafhffqsxy36t90ldv06wqrk2qld6xc3"
    )


def test_payment_address_24_base():
    hdwallet = HDWallet.from_mnemonic(MNEMONIC_24)
    hdwallet_spend = hdwallet.derive_from_path("m/1852'/1815'/0'/0/0")
    spend_public_key = hdwallet_spend.public_key
    spend_vk = PaymentVerificationKey.from_primitive(spend_public_key)

    hdwallet_stake = hdwallet.derive_from_path("m/1852'/1815'/0'/2/0")
    stake_public_key = hdwallet_stake.public_key
    stake_vk = PaymentVerificationKey.from_primitive(stake_public_key)

    assert (
        Address(spend_vk.hash(), stake_vk.hash(), network=Network.TESTNET).encode()
        == "addr_test1qqy6nhfyks7wdu3dudslys37v252w2nwhv0fw2nfawemmn8k8ttq8f3gag0h89aepvx3xf69g0l9pf80tqv7cve0l33sw96paj"
    )

    assert (
        Address(spend_vk.hash(), stake_vk.hash(), network=Network.MAINNET).encode()
        == "addr1qyy6nhfyks7wdu3dudslys37v252w2nwhv0fw2nfawemmn8k8ttq8f3gag0h89aepvx3xf69g0l9pf80tqv7cve0l33sdn8p3d"
    )


def test_payment_address_12_reward_from_entropy():
    hdwallet = HDWallet.from_entropy(MNEMONIC_12_ENTROPY)
    hdwallet_stake = hdwallet.derive_from_path("m/1852'/1815'/0'/2/0")
    stake_public_key = hdwallet_stake.public_key
    stake_vk = PaymentVerificationKey.from_primitive(stake_public_key)

    assert (
        Address(
            payment_part=None, staking_part=stake_vk.hash(), network=Network.TESTNET
        ).encode()
        == "stake_test1uqevw2xnsc0pvn9t9r9c7qryfqfeerchgrlm3ea2nefr9hqp8n5xl"
    )

    assert (
        Address(
            payment_part=None, staking_part=stake_vk.hash(), network=Network.MAINNET
        ).encode()
        == "stake1uyevw2xnsc0pvn9t9r9c7qryfqfeerchgrlm3ea2nefr9hqxdekzz"
    )


def test_is_entropy():
    is_entropy = HDWallet.is_entropy(MNEMONIC_12_ENTROPY)
    assert is_entropy


def test_is_entropy_wrong_input():
    wrong_entropy = "df9ed25ed146bf43336a5d7cf73959"
    is_entropy = HDWallet.is_entropy(wrong_entropy)
    assert not is_entropy
