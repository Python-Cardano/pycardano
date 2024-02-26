from fractions import Fraction
from test.pycardano.util import FixedChainContext

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
)
from pycardano.pool_params import (
    MultiHostName,
    PoolMetadata,
    PoolParams,
    SingleHostAddr,
    SingleHostName,
)


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
