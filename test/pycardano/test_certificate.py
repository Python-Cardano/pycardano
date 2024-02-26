from pycardano.address import Address
from pycardano.certificate import (
    PoolRegistration,
    PoolRetirement,
    StakeCredential,
    StakeDelegation,
    StakeDeregistration,
    StakeRegistration,
)
from pycardano.hash import POOL_KEY_HASH_SIZE, SCRIPT_HASH_SIZE, PoolKeyHash, ScriptHash

TEST_ADDR = Address.from_primitive(
    "stake_test1upyz3gk6mw5he20apnwfn96cn9rscgvmmsxc9r86dh0k66gswf59n"
)


def test_stake_credential_verification_key_hash():
    stake_credential = StakeCredential(TEST_ADDR.staking_part)

    stake_credential_cbor_hex = stake_credential.to_cbor_hex()

    assert (
        stake_credential_cbor_hex
        == "8200581c4828a2dadba97ca9fd0cdc99975899470c219bdc0d828cfa6ddf6d69"
    )

    assert StakeCredential.from_cbor(stake_credential_cbor_hex) == stake_credential


def test_stake_credential_script_hash():
    stake_credential = StakeCredential(ScriptHash(b"1" * SCRIPT_HASH_SIZE))

    stake_credential_cbor_hex = stake_credential.to_cbor_hex()

    assert (
        stake_credential_cbor_hex
        == "8201581c31313131313131313131313131313131313131313131313131313131"
    )

    assert StakeCredential.from_cbor(stake_credential_cbor_hex) == stake_credential


def test_stake_registration():
    stake_credential = StakeCredential(TEST_ADDR.staking_part)
    stake_registration = StakeRegistration(stake_credential)

    stake_registration_cbor_hex = stake_registration.to_cbor_hex()

    assert (
        stake_registration_cbor_hex
        == "82008200581c4828a2dadba97ca9fd0cdc99975899470c219bdc0d828cfa6ddf6d69"
    )

    assert (
        StakeRegistration.from_cbor(stake_registration_cbor_hex) == stake_registration
    )


def test_stake_deregistration():
    stake_credential = StakeCredential(TEST_ADDR.staking_part)
    stake_deregistration = StakeDeregistration(stake_credential)

    stake_deregistration_cbor_hex = stake_deregistration.to_cbor_hex()

    assert (
        stake_deregistration_cbor_hex
        == "82018200581c4828a2dadba97ca9fd0cdc99975899470c219bdc0d828cfa6ddf6d69"
    )

    assert (
        StakeDeregistration.from_cbor(stake_deregistration_cbor_hex)
        == stake_deregistration
    )


def test_stake_delegation():
    stake_credential = StakeCredential(TEST_ADDR.staking_part)
    stake_delegation = StakeDelegation(
        stake_credential, PoolKeyHash(b"1" * POOL_KEY_HASH_SIZE)
    )

    stake_delegation_cbor_hex = stake_delegation.to_cbor_hex()

    assert (
        stake_delegation_cbor_hex
        == "83028200581c4828a2dadba97ca9fd0cdc99975899470c219bdc0d828cfa6ddf"
        "6d69581c31313131313131313131313131313131313131313131313131313131"
    )

    assert StakeDelegation.from_cbor(stake_delegation_cbor_hex) == stake_delegation


def test_pool_registration(pool_params):
    pool_registration = PoolRegistration(pool_params)

    pool_registration_cbor_hex = pool_registration.to_cbor_hex()

    assert (
        pool_registration_cbor_hex
        == "8a03581c31313131313131313131313131313131313131313131313131313131582031313131313131313131313131313131313131"
        "313131313131313131313131311a05f5e1001a1443fd00d81e82011832581d31313131313131313131313131313131313131313131"
        "3131313131313181581c31313131313131313131313131313131313131313131313131313131838400190bb944c0a8000150000000"
        "000000000000000000000000018301190bb97272656c6179312e6578616d706c652e636f6d82027272656c6179312e6578616d706c"
        "652e636f6d82781968747470733a2f2f6d657461312e6578616d706c652e636f6d5820313131313131313131313131313131313131"
        "3131313131313131313131313131"
    )

    assert PoolRegistration.from_cbor(pool_registration_cbor_hex) == pool_registration


def test_pool_retirement():
    pool_keyhash = PoolKeyHash(b"1" * POOL_KEY_HASH_SIZE)
    epoch = 700
    pool_retirement = PoolRetirement(pool_keyhash, epoch)

    pool_retirement_cbor_hex = pool_retirement.to_cbor_hex()

    assert (
        pool_retirement_cbor_hex
        == "8304581c313131313131313131313131313131313131313131313131313131311902bc"
    )

    assert PoolRetirement.from_cbor(pool_retirement_cbor_hex) == pool_retirement
