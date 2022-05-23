from pycardano.address import Address
from pycardano.certificate import (
    StakeCredential,
    StakeDelegation,
    StakeDeregistration,
    StakeRegistration,
)
from pycardano.hash import POOL_KEY_HASH_SIZE

TEST_ADDR = Address.from_primitive(
    "stake_test1upyz3gk6mw5he20apnwfn96cn9rscgvmmsxc9r86dh0k66gswf59n"
)


def test_stake_credential():
    stake_credential = StakeCredential(TEST_ADDR.staking_part)

    assert (
        stake_credential.to_cbor()
        == "8200581c4828a2dadba97ca9fd0cdc99975899470c219bdc0d828cfa6ddf6d69"
    )


def test_stake_registration():
    stake_credential = StakeCredential(TEST_ADDR.staking_part)
    stake_registration = StakeRegistration(stake_credential)

    assert (
        stake_registration.to_cbor()
        == "82008200581c4828a2dadba97ca9fd0cdc99975899470c219bdc0d828cfa6ddf6d69"
    )


def test_stake_deregistration():
    stake_credential = StakeCredential(TEST_ADDR.staking_part)
    stake_deregistration = StakeDeregistration(stake_credential)

    assert (
        stake_deregistration.to_cbor()
        == "82018200581c4828a2dadba97ca9fd0cdc99975899470c219bdc0d828cfa6ddf6d69"
    )


def test_stake_delegation():
    stake_credential = StakeCredential(TEST_ADDR.staking_part)
    stake_delegation = StakeDelegation(stake_credential, b"1" * POOL_KEY_HASH_SIZE)

    assert (
        stake_delegation.to_cbor()
        == "83028200581c4828a2dadba97ca9fd0cdc99975899470c219bdc0d828cfa6ddf"
        "6d69581c31313131313131313131313131313131313131313131313131313131"
    )
