import os

import pytest

from pycardano import AnchorDataHash, StakeSigningKey, TransactionBody
from pycardano.address import Address
from pycardano.certificate import (
    Anchor,
    AuthCommitteeHotCertificate,
    DRepCredential,
    PoolRegistration,
    PoolRetirement,
    ResignCommitteeColdCertificate,
    StakeCredential,
    StakeDelegation,
    StakeDeregistration,
    StakeRegistration,
    UnregDRepCertificate,
    UpdateDRepCertificate,
)
from pycardano.exception import DeserializeException, InvalidArgumentException
from pycardano.hash import (  # plutus_script_hash,
    POOL_KEY_HASH_SIZE,
    SCRIPT_HASH_SIZE,
    PoolKeyHash,
    ScriptHash,
)

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


def test_staking_certificate_serdes():
    staking_key = StakeSigningKey.generate()
    stake_pool_key_hash = os.urandom(28)

    transaction_body = TransactionBody(
        certificates=[
            StakeRegistration(
                stake_credential=StakeCredential(
                    staking_key.to_verification_key().hash()
                )
            ),
            StakeDelegation(
                stake_credential=StakeCredential(
                    staking_key.to_verification_key().hash()
                ),
                pool_keyhash=PoolKeyHash(stake_pool_key_hash),
            ),
        ]
    )

    primitives = transaction_body.to_validated_primitive()

    cbor_hex = transaction_body.to_cbor_hex()

    after_serdes = TransactionBody.from_cbor(cbor_hex)

    assert after_serdes == transaction_body


def test_anchor():
    url = "https://example.com"
    data_hash = AnchorDataHash(bytes.fromhex("0" * 64))  # 32 bytes
    anchor = Anchor(url=url, data_hash=data_hash)

    anchor_cbor_hex = anchor.to_cbor_hex()

    assert (
        anchor_cbor_hex
        == "827368747470733a2f2f6578616d706c652e636f6d58200000000000000000000000000000000000000000000000000000000000000000"
    )

    assert Anchor.from_cbor(anchor_cbor_hex) == anchor


def test_drep_credential():
    staking_key = StakeSigningKey.from_cbor(
        "5820ff3a330df8859e4e5f42a97fcaee73f6a00d0cf864f4bca902bd106d423f02c0"
    )
    drep_credential = DRepCredential(staking_key.to_verification_key().hash())
    drep_credential_cbor_hex = drep_credential.to_cbor_hex()
    assert (
        drep_credential_cbor_hex
        == "8200581c4828a2dadba97ca9fd0cdc99975899470c219bdc0d828cfa6ddf6d69"
    )
    assert DRepCredential.from_cbor(drep_credential_cbor_hex) == drep_credential


def test_unreg_drep_certificate():
    staking_key = StakeSigningKey.from_cbor(
        "5820ff3a330df8859e4e5f42a97fcaee73f6a00d0cf864f4bca902bd106d423f02c0"
    )
    drep_credential = DRepCredential(staking_key.to_verification_key().hash())
    coin = 1000000
    unreg_drep_cert = UnregDRepCertificate(drep_credential=drep_credential, coin=coin)

    unreg_drep_cert_cbor_hex = unreg_drep_cert.to_cbor_hex()

    assert (
        unreg_drep_cert_cbor_hex
        == "83118200581c4828a2dadba97ca9fd0cdc99975899470c219bdc0d828cfa6ddf6d691a000f4240"
    )

    assert UnregDRepCertificate.from_cbor(unreg_drep_cert_cbor_hex) == unreg_drep_cert


def test_update_drep_certificate_with_anchor():
    staking_key = StakeSigningKey.from_cbor(
        "5820ff3a330df8859e4e5f42a97fcaee73f6a00d0cf864f4bca902bd106d423f02c0"
    )
    drep_credential = DRepCredential(staking_key.to_verification_key().hash())
    url = "https://pycardano.com"
    data_hash = AnchorDataHash(bytes.fromhex("0" * 64))  # 32 bytes
    anchor = Anchor(url=url, data_hash=data_hash)
    update_drep_cert = UpdateDRepCertificate(
        drep_credential=drep_credential, anchor=anchor
    )

    update_drep_cert_cbor_hex = update_drep_cert.to_cbor_hex()

    assert (
        update_drep_cert_cbor_hex
        == "83128200581c4828a2dadba97ca9fd0cdc99975899470c219bdc0d828cfa6ddf6d69827568747470733a2f2f707963617264616e6f2e636f6d58200000000000000000000000000000000000000000000000000000000000000000"
    )

    assert (
        UpdateDRepCertificate.from_cbor(update_drep_cert_cbor_hex) == update_drep_cert
    )


def test_update_drep_certificate_without_anchor():
    staking_key = StakeSigningKey.from_cbor(
        "5820ff3a330df8859e4e5f42a97fcaee73f6a00d0cf864f4bca902bd106d423f02c0"
    )
    drep_credential = DRepCredential(staking_key.to_verification_key().hash())
    update_drep_cert = UpdateDRepCertificate(
        drep_credential=drep_credential, anchor=None
    )
    update_drep_cert_cbor_hex = update_drep_cert.to_cbor_hex()

    assert (
        update_drep_cert_cbor_hex
        == "83128200581c4828a2dadba97ca9fd0cdc99975899470c219bdc0d828cfa6ddf6d69f6"
    )

    assert (
        UpdateDRepCertificate.from_cbor(update_drep_cert_cbor_hex) == update_drep_cert
    )


def test_auth_committee_hot_certificate():
    committee_cold_credential = StakeCredential(TEST_ADDR.staking_part)
    committee_hot_credential = StakeCredential(ScriptHash(b"1" * SCRIPT_HASH_SIZE))
    auth_committee_hot_cert = AuthCommitteeHotCertificate(
        committee_cold_credential=committee_cold_credential,
        committee_hot_credential=committee_hot_credential,
    )

    auth_committee_hot_cert_cbor_hex = auth_committee_hot_cert.to_cbor_hex()

    assert (
        auth_committee_hot_cert_cbor_hex
        == "830e8200581c4828a2dadba97ca9fd0cdc99975899470c219bdc0d828cfa6ddf6d698201581c31313131313131313131313131313131313131313131313131313131"
    )

    assert (
        AuthCommitteeHotCertificate.from_cbor(auth_committee_hot_cert_cbor_hex)
        == auth_committee_hot_cert
    )


def test_resign_committee_cold_certificate_with_anchor():
    committee_cold_credential = StakeCredential(TEST_ADDR.staking_part)
    url = "https://pycardano.com"
    data_hash = AnchorDataHash(bytes.fromhex("0" * 64))
    anchor = Anchor(url=url, data_hash=data_hash)
    resign_committee_cold_cert = ResignCommitteeColdCertificate(
        committee_cold_credential=committee_cold_credential,
        anchor=anchor,
    )

    resign_committee_cold_cert_cbor_hex = resign_committee_cold_cert.to_cbor_hex()

    assert (
        resign_committee_cold_cert_cbor_hex
        == "830f8200581c4828a2dadba97ca9fd0cdc99975899470c219bdc0d828cfa6ddf6d69827568747470733a2f2f707963617264616e6f2e636f6d58200000000000000000000000000000000000000000000000000000000000000000"
    )

    assert (
        ResignCommitteeColdCertificate.from_cbor(resign_committee_cold_cert_cbor_hex)
        == resign_committee_cold_cert
    )


def test_resign_committee_cold_certificate_without_anchor():
    committee_cold_credential = StakeCredential(TEST_ADDR.staking_part)
    resign_committee_cold_cert = ResignCommitteeColdCertificate(
        committee_cold_credential=committee_cold_credential,
        anchor=None,
    )
    resign_committee_cold_cert_cbor_hex = resign_committee_cold_cert.to_cbor_hex()

    assert (
        resign_committee_cold_cert_cbor_hex
        == "830f8200581c4828a2dadba97ca9fd0cdc99975899470c219bdc0d828cfa6ddf6d69f6"
    )

    assert (
        ResignCommitteeColdCertificate.from_cbor(resign_committee_cold_cert_cbor_hex)
        == resign_committee_cold_cert
    )


def test_invalid_certificate_types():
    with pytest.raises(DeserializeException) as excinfo:
        StakeRegistration.from_primitive([1, [0, b"1" * 28]])
    assert "Invalid StakeRegistration type 1" in str(excinfo.value)

    with pytest.raises(DeserializeException) as excinfo:
        StakeDeregistration.from_primitive([0, [0, b"1" * 28]])
    assert "Invalid StakeDeregistration type 0" in str(excinfo.value)

    with pytest.raises(DeserializeException) as excinfo:
        StakeDelegation.from_primitive([1, [0, b"1" * 28], b"1" * 28])
    assert "Invalid StakeDelegation type 1" in str(excinfo.value)

    with pytest.raises(DeserializeException) as excinfo:
        PoolRegistration.from_primitive([4, b"1" * 28])
    assert "Invalid PoolRegistration type 4" in str(excinfo.value)

    with pytest.raises(DeserializeException) as excinfo:
        PoolRetirement.from_primitive([3, b"1" * 28, 100])
    assert "Invalid PoolRetirement type 3" in str(excinfo.value)

    staking_key = StakeSigningKey.generate()
    committee_cold_credential = StakeCredential(
        staking_key.to_verification_key().hash()
    )
    committee_hot_credential = StakeCredential(ScriptHash(b"1" * SCRIPT_HASH_SIZE))

    with pytest.raises(DeserializeException) as excinfo:
        AuthCommitteeHotCertificate.from_primitive(
            [15, committee_cold_credential, committee_hot_credential]
        )
    assert "Invalid AuthCommitteeHotCertificate type 15" in str(excinfo.value)

    with pytest.raises(DeserializeException) as excinfo:
        ResignCommitteeColdCertificate.from_primitive(
            [14, committee_cold_credential, None]
        )
    assert "Invalid ResignCommitteeColdCertificate type 14" in str(excinfo.value)

    staking_key = StakeSigningKey.generate()
    drep_credential = DRepCredential(staking_key.to_verification_key().hash())

    with pytest.raises(DeserializeException) as excinfo:
        UnregDRepCertificate.from_primitive([18, drep_credential, 1000000])
    assert "Invalid UnregDRepCertificate type 18" in str(excinfo.value)

    with pytest.raises(DeserializeException) as excinfo:
        UpdateDRepCertificate.from_primitive([17, drep_credential, None])
    assert "Invalid UpdateDRepCertificate type 17" in str(excinfo.value)


def test_certificate_in_transaction():
    staking_key = StakeSigningKey.generate()
    committee_cold_credential = StakeCredential(
        staking_key.to_verification_key().hash()
    )
    committee_hot_credential = StakeCredential(ScriptHash(b"1" * SCRIPT_HASH_SIZE))

    auth_committee_hot_cert = AuthCommitteeHotCertificate(
        committee_cold_credential=committee_cold_credential,
        committee_hot_credential=committee_hot_credential,
    )

    url = "https://example.com"
    data_hash = AnchorDataHash(bytes.fromhex("0" * 64))  # 32 bytes
    anchor = Anchor(url=url, data_hash=data_hash)
    resign_committee_cold_cert = ResignCommitteeColdCertificate(
        committee_cold_credential=committee_cold_credential,
        anchor=anchor,
    )

    # Create transaction with certificates
    transaction_body = TransactionBody(
        certificates=[
            auth_committee_hot_cert,
            resign_committee_cold_cert,
        ]
    )

    # Test serialization/deserialization
    after_serdes = TransactionBody.from_cbor(transaction_body.to_cbor())
    assert after_serdes == transaction_body

    # Verify certificates in deserialized transaction
    assert len(after_serdes.certificates) == 2
    assert isinstance(after_serdes.certificates[0], AuthCommitteeHotCertificate)
    assert isinstance(after_serdes.certificates[1], ResignCommitteeColdCertificate)
    assert after_serdes.certificates[0] == auth_committee_hot_cert
    assert after_serdes.certificates[1] == resign_committee_cold_cert
