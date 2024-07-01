import contextlib
import os
import pathlib
from datetime import datetime, timedelta
from fractions import Fraction
from unittest import mock

import pytest

from pycardano import (
    POOL_KEY_HASH_SIZE,
    POOL_METADATA_HASH_SIZE,
    REWARD_ACCOUNT_HASH_SIZE,
    VERIFICATION_KEY_HASH_SIZE,
    VRF_KEY_HASH_SIZE,
    PoolKeyHash,
    PoolMetadataHash,
    RewardAccountHash,
    VerificationKeyHash,
    VrfKeyHash,
    Address,
    ScriptPubkey,
    ScriptAll,
)
from pycardano.pool_params import (
    MultiHostName,
    PoolMetadata,
    PoolParams,
    SingleHostAddr,
    SingleHostName,
)
from pycardano.wallet import Wallet, Token, TokenPolicy
from test.pycardano.util import FixedChainContext


@pytest.fixture
def chain_context():
    return FixedChainContext()


@pytest.fixture
def address() -> Address:
    return Address.from_primitive(
        "addr_test1vr2p8st5t5cxqglyjky7vk98k7jtfhdpvhl4e97cezuhn0cqcexl7"
    )


@pytest.fixture
def stake_address() -> Address:
    return Address.from_primitive(
        "stake1u9ylzsgxaa6xctf4juup682ar3juj85n8tx3hthnljg47zctvm3rc"
    )


@pytest.fixture
def pool_id() -> Address:
    return "pool1pu5jlj4q9w9jlxeu370a3c9myx47md5j5m2str0naunn2q3lkdy"


@pytest.fixture
def wallet(chain_context) -> Wallet:
    test_wallet = Wallet(
        name="payment",
        keys_dir=str(pathlib.Path(__file__).parent / "./resources/keys"),
        context=chain_context,
    )
    test_wallet.sync()
    return test_wallet


@pytest.fixture
def token(wallet) -> Token:
    # script = ScriptAll([ScriptPubkey(wallet.verification_key.hash())])

    policy = TokenPolicy(name="Token1")

    with contextlib.suppress(FileExistsError):
        policy.generate_minting_policy(
            signers=wallet,
            expiration=datetime(2025, 5, 12, 12, 0, 0),
            context=wallet.context,
        )
    yield Token(policy=policy, name="Token1", amount=1, metadata={"key": "value"})

    script_filepath = pathlib.Path(policy.policy_dir) / f"{policy.name}.script"

    script_filepath.unlink(missing_ok=True)


@pytest.fixture
def pool_params():
    return PoolParams(
        operator=PoolKeyHash(b"1" * POOL_KEY_HASH_SIZE),
        vrf_keyhash=VrfKeyHash(b"1" * VRF_KEY_HASH_SIZE),
        pledge=100_000_000,
        cost=340_000_000,
        margin=Fraction(1, 50),
        reward_account=RewardAccountHash(b"1" * REWARD_ACCOUNT_HASH_SIZE),
        pool_owners=[VerificationKeyHash(b"1" * VERIFICATION_KEY_HASH_SIZE)],
        relays=[
            SingleHostAddr(port=3001, ipv4="192.168.0.1", ipv6="::1"),
            SingleHostName(port=3001, dns_name="relay1.example.com"),
            MultiHostName(dns_name="relay1.example.com"),
        ],
        pool_metadata=PoolMetadata(
            url="https://meta1.example.com",
            pool_metadata_hash=PoolMetadataHash(b"1" * POOL_METADATA_HASH_SIZE),
        ),
    )


@pytest.fixture(scope="session", autouse=True)
def mock_setting_env_vars():
    with mock.patch.dict(
        os.environ,
        {
            "BLOCKFROST_ID_MAINNET": "mainnet_fakeapikey",
            "BLOCKFROST_ID_PREPROD": "preprod_fakeapikey",
            "BLOCKFROST_ID_PREVIEW": "preview_fakeapikey",
        },
    ):
        yield
