from fractions import Fraction

import pytest

from pycardano import (
    POOL_KEY_HASH_SIZE,
    POOL_METADATA_HASH_SIZE,
    VERIFICATION_KEY_HASH_SIZE,
    VRF_KEY_HASH_SIZE,
    PoolMetadataHash,
)
from pycardano.hash import (
    REWARD_ACCOUNT_HASH_SIZE,
    PoolKeyHash,
    RewardAccountHash,
    VerificationKeyHash,
    VrfKeyHash,
)
from pycardano.pool_params import (  # Fraction,
    MultiHostName,
    PoolId,
    PoolMetadata,
    PoolParams,
    SingleHostAddr,
    SingleHostName,
    fraction_parser,
    is_bech32_cardano_pool_id,
)

TEST_POOL_ID = "pool1mt8sdg37f2h3rypyuc77k7vxrjshtvjw04zdjlae9vdzyt9uu34"


# Parametrized test for happy path cases
@pytest.mark.parametrize(
    "pool_id, expected",
    [
        (TEST_POOL_ID, True),
        ("pool1234567890abcdef", False),
        ("pool1abcdefghijklmnopqrstuvwxyz", False),
        ("pool1", False),
        ("pool11234567890abcdef", False),
        ("pool1abcdefghijklmnopqrstuvwxyz1234", False),
        ("pool1!@#$%^&*()-_+={}[]|\\:;\"'<>,.?/", False),
        (
            "pool1qqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq",
            False,
        ),  # One character short
        (
            "pool1qqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq",
            False,
        ),  # One character too long
        ("pool1!@#$%^&*()", False),  # Invalid characters
        ("pool1", False),  # Too short
        ("", False),  # Empty string
        (None, False),  # None input
        ("pool019", False),  # Invalid character '1'
        (
            "stake1uxtr5m6kygt77399zxqrykkluqr0grr4yrjtl5xplza6k8q5fghrp",
            False,
        ),  # Incorrect HRP
    ],
)
def test_is_bech32_cardano_pool_id(pool_id: str, expected: bool):
    assert is_bech32_cardano_pool_id(pool_id) == expected


def test_pool_id():
    # Act
    pool_id = PoolId(TEST_POOL_ID)

    # Assert
    assert str(pool_id) == TEST_POOL_ID
    assert pool_id.to_primitive() == TEST_POOL_ID
    assert str(PoolId.from_primitive(TEST_POOL_ID)) == TEST_POOL_ID


# Parametrized test cases for error cases
@pytest.mark.parametrize(
    "test_id, pool_id_str, expected_exception",
    [
        ("ERR-1", "", ValueError),  # Empty string
        ("ERR-2", "1234567890", ValueError),  # Not a bech32 format
        ("ERR-3", "pool123", ValueError),  # Too short to be valid
        # Add more error cases as needed
    ],
)
def test_pool_id_error_cases(test_id, pool_id_str, expected_exception):
    # Act & Assert
    with pytest.raises(expected_exception):
        PoolId(pool_id_str)


@pytest.mark.parametrize(
    "port, ipv4, ipv6",
    [
        (
            3001,
            b"\xC0\xA8\x00\x01",
            b" \x01\r\xb8\x85\xa3\x00\x00\x14-\x00\x00\x08\x01\r\xb8",
        ),  # IPv4 and IPv6
        (None, b"\xC0\xA8\x00\x01", None),  # Only IPv4
        (
            None,
            None,
            b" \x01\r\xb8\x85\xa3\x00\x00\x14-\x00\x00\x08\x01\r\xb8",
        ),  # Only IPv6
    ],
)
def test_single_host_addr(port, ipv4, ipv6):
    # Act
    single_host_addr = SingleHostAddr.from_primitive([0, port, ipv4, ipv6])

    # Assert
    assert single_host_addr.port == port
    assert single_host_addr.ipv4 == SingleHostAddr.bytes_to_ipv4(ipv4)
    assert single_host_addr.ipv6 == SingleHostAddr.bytes_to_ipv6(ipv6)
    assert single_host_addr.to_primitive() == [0, port, ipv4, ipv6]


@pytest.mark.parametrize(
    "port, dns_name",
    [
        (80, "example.com"),
        (443, "secure.example.com"),
        (None, "noport.example.com"),
    ],
)
def test_single_host_name(port, dns_name):
    # Arrange
    primitive_values = [1, port, dns_name]

    # Act
    single_host_name = SingleHostName.from_primitive(primitive_values)

    # Assert
    assert single_host_name.port == port
    assert single_host_name.dns_name == dns_name
    assert single_host_name._CODE == 1
    assert single_host_name.to_primitive() == [1, port, dns_name]


@pytest.mark.parametrize(
    "dns_name",
    [
        "example.com",
        "secure.example.com",
        "noport.example.com",
    ],
)
def test_multi_host_name(dns_name):
    # Arrange
    primitive_values = [2, dns_name]

    # Act
    multi_host_name = MultiHostName.from_primitive(primitive_values)

    # Assert
    assert multi_host_name.dns_name == dns_name
    assert multi_host_name._CODE == 2
    assert multi_host_name.to_primitive() == [2, dns_name]


@pytest.mark.parametrize(
    "url, pool_metadata_hash",
    [
        (
            "https://example.com/metadata.json",
            b"1" * POOL_METADATA_HASH_SIZE,
        ),
        (
            "https://pooldata.info/api/metadata",
            b"2" * POOL_METADATA_HASH_SIZE,
        ),
        (
            "http://metadata.pool/endpoint",
            b"3" * POOL_METADATA_HASH_SIZE,
        ),
    ],
)
def test_pool_metadata(url, pool_metadata_hash):
    # Arrange
    primitive_values = [url, pool_metadata_hash]

    # Act
    pool_metadata = PoolMetadata.from_primitive(primitive_values)

    # Assert
    assert pool_metadata.url == url
    assert pool_metadata.pool_metadata_hash == PoolMetadataHash(pool_metadata_hash)
    assert isinstance(pool_metadata, PoolMetadata)
    assert pool_metadata.to_primitive() == primitive_values


@pytest.mark.parametrize(
    "input_value",
    [
        [30, [1, 2]],
        "1/2",
        "3/4",
        "0/1",
        "1/1",
        Fraction(123456, 1),
        Fraction(5, 6),
        Fraction(7, 8),
        Fraction(5, 6),
    ],
)
def test_fraction_serializer(input_value):
    # Act
    result = fraction_parser(input_value)

    # Assert
    assert isinstance(result, Fraction)


@pytest.mark.parametrize(
    "operator, vrf_keyhash, pledge, cost, margin, reward_account, pool_owners, relays, pool_metadata",
    [
        # Test case ID: HP-1
        (
            b"1" * POOL_KEY_HASH_SIZE,
            b"1" * VRF_KEY_HASH_SIZE,
            10_000_000,
            340_000_000,
            "1/10",
            b"1" * REWARD_ACCOUNT_HASH_SIZE,
            [b"1" * VERIFICATION_KEY_HASH_SIZE],
            [
                [0, 3001, SingleHostAddr.ipv4_to_bytes("10.20.30.40"), None],
                [1, 3001, "example.com"],
                [2, "example.com"],
            ],
            [
                "https://example.com/metadata.json",
                b"1" * POOL_METADATA_HASH_SIZE,
            ],
        ),
        # Add more test cases with different realistic values
    ],
    ids=["test_pool_params-1"],
)  # Add more IDs for each test case
def test_pool_params(
    operator,
    vrf_keyhash,
    pledge,
    cost,
    margin,
    reward_account,
    pool_owners,
    relays,
    pool_metadata,
):
    # Arrange
    primitive_values = [
        operator,
        vrf_keyhash,
        pledge,
        cost,
        margin,
        reward_account,
        pool_owners,
        relays,
        pool_metadata,
    ]
    primitive_out = [
        operator,
        vrf_keyhash,
        pledge,
        cost,
        fraction_parser(margin),
        reward_account,
        pool_owners,
        relays,
        pool_metadata,
    ]

    assert PoolParams.from_primitive(primitive_values).to_primitive() == primitive_out
