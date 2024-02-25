from fractions import Fraction

import pytest

from pycardano import (
    PoolKeyHash,
    POOL_KEY_HASH_SIZE,
    VRF_KEY_HASH_SIZE,
    VrfKeyHash,
    VerificationKeyHash,
    RewardAccountHash,
    REWARD_ACCOUNT_HASH_SIZE,
    VERIFICATION_KEY_HASH_SIZE,
    PoolMetadataHash,
    POOL_METADATA_HASH_SIZE,
)
from pycardano.pool_params import (
    PoolParams,
    SingleHostAddr,
    SingleHostName,
    MultiHostName,
    PoolMetadata,
)
from test.pycardano.util import FixedChainContext


@pytest.fixture
def chain_context():
    return FixedChainContext()


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
