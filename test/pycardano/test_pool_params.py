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
    PoolOperator,
    PoolParams,
    SingleHostAddr,
    SingleHostName,
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
            b"\xc0\xa8\x00\x01",
            b" \x01\r\xb8\x85\xa3\x00\x00\x14-\x00\x00\x08\x01\r\xb8",
        ),  # IPv4 and IPv6
        (None, b"\xc0\xa8\x00\x01", None),  # Only IPv4
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
    "operator, vrf_keyhash, pledge, cost, margin, reward_account, pool_owners, relays, pool_metadata",
    [
        # Test case ID: HP-1
        (
            b"1" * POOL_KEY_HASH_SIZE,
            b"1" * VRF_KEY_HASH_SIZE,
            10_000_000,
            340_000_000,
            Fraction(1, 10),
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
        margin,
        reward_account,
        pool_owners,
        relays,
        pool_metadata,
    ]

    assert PoolParams.from_primitive(primitive_values).to_primitive() == primitive_out


# PoolOperator Tests
def test_pool_operator_initialization():
    """Test PoolOperator can be initialized with a PoolKeyHash."""
    # Arrange
    pool_key_hash = PoolKeyHash(b"1" * POOL_KEY_HASH_SIZE)

    # Act
    pool_operator = PoolOperator(pool_key_hash)

    # Assert
    assert pool_operator.pool_key_hash == pool_key_hash


def test_pool_operator_encode():
    """Test PoolOperator can encode to bech32 format."""
    # Arrange
    pool_key_hash_hex = "dacf06a23e4aaf119024e63deb79861ca175b24e7d44d97fb92b1a22"
    pool_key_hash = PoolKeyHash(bytes.fromhex(pool_key_hash_hex))
    pool_operator = PoolOperator(pool_key_hash)

    # Act
    encoded = pool_operator.encode()

    # Assert
    assert encoded.startswith("pool")
    assert isinstance(encoded, str)
    assert encoded == TEST_POOL_ID


def test_pool_operator_decode():
    """Test PoolOperator can decode from bech32 format."""
    # Act
    pool_operator = PoolOperator.decode(TEST_POOL_ID)

    # Assert
    assert isinstance(pool_operator, PoolOperator)
    assert pool_operator.encode() == TEST_POOL_ID


def test_pool_operator_id_property():
    """Test PoolOperator.id property returns a PoolId."""
    # Arrange
    pool_key_hash_hex = "dacf06a23e4aaf119024e63deb79861ca175b24e7d44d97fb92b1a22"
    pool_key_hash = PoolKeyHash(bytes.fromhex(pool_key_hash_hex))
    pool_operator = PoolOperator(pool_key_hash)

    # Act
    pool_id = str(pool_operator)

    # Assert
    assert pool_id == TEST_POOL_ID


def test_pool_operator_id_hex_property():
    """Test PoolOperator.id_hex property returns hex string."""
    # Arrange
    pool_key_hash_hex = "dacf06a23e4aaf119024e63deb79861ca175b24e7d44d97fb92b1a22"
    pool_key_hash = PoolKeyHash(bytes.fromhex(pool_key_hash_hex))
    pool_operator = PoolOperator(pool_key_hash)

    # Act
    id_hex = bytes(pool_operator).hex()

    # Assert
    assert id_hex == pool_key_hash_hex


def test_pool_operator_repr():
    """Test PoolOperator __repr__ returns encoded string."""
    # Arrange
    pool_key_hash_hex = "dacf06a23e4aaf119024e63deb79861ca175b24e7d44d97fb92b1a22"
    pool_key_hash = PoolKeyHash(bytes.fromhex(pool_key_hash_hex))
    pool_operator = PoolOperator(pool_key_hash)

    # Act
    repr_str = repr(pool_operator)

    # Assert
    assert repr_str == TEST_POOL_ID


def test_pool_operator_bytes():
    """Test PoolOperator __bytes__ returns pool key hash payload."""
    # Arrange
    pool_key_hash_hex = "dacf06a23e4aaf119024e63deb79861ca175b24e7d44d97fb92b1a22"
    pool_key_hash = PoolKeyHash(bytes.fromhex(pool_key_hash_hex))
    pool_operator = PoolOperator(pool_key_hash)

    # Act
    bytes_result = bytes(pool_operator)

    # Assert
    assert isinstance(bytes_result, bytes)
    assert bytes_result == bytes.fromhex(pool_key_hash_hex)


def test_pool_operator_to_primitive():
    """Test PoolOperator.to_primitive returns bytes."""
    # Arrange
    pool_key_hash_hex = "dacf06a23e4aaf119024e63deb79861ca175b24e7d44d97fb92b1a22"
    pool_key_hash = PoolKeyHash(bytes.fromhex(pool_key_hash_hex))
    pool_operator = PoolOperator(pool_key_hash)

    # Act
    primitive = pool_operator.to_primitive()

    # Assert
    assert isinstance(primitive, bytes)
    assert primitive == bytes.fromhex(pool_key_hash_hex)


@pytest.mark.parametrize(
    "input_value, description",
    [
        (TEST_POOL_ID, "bech32 pool id"),
        ("dacf06a23e4aaf119024e63deb79861ca175b24e7d44d97fb92b1a22", "hex string"),
        (
            bytes.fromhex("dacf06a23e4aaf119024e63deb79861ca175b24e7d44d97fb92b1a22"),
            "bytes",
        ),
    ],
)
def test_pool_operator_from_primitive(input_value, description):
    """Test PoolOperator.from_primitive handles different input formats."""
    # Act
    pool_operator = PoolOperator.from_primitive(input_value)

    # Assert
    assert isinstance(pool_operator, PoolOperator)
    assert (
        bytes(pool_operator).hex()
        == "dacf06a23e4aaf119024e63deb79861ca175b24e7d44d97fb92b1a22"
    )


def test_pool_operator_roundtrip_bech32():
    """Test PoolOperator can encode and decode maintaining consistency."""
    # Arrange
    pool_key_hash = PoolKeyHash(b"1" * POOL_KEY_HASH_SIZE)
    original_operator = PoolOperator(pool_key_hash)

    # Act
    encoded = original_operator.encode()
    decoded_operator = PoolOperator.decode(encoded)

    # Assert
    assert decoded_operator.pool_key_hash == original_operator.pool_key_hash
    assert decoded_operator.encode() == encoded


def test_pool_operator_roundtrip_primitive():
    """Test PoolOperator serialization roundtrip."""
    # Arrange
    pool_key_hash = PoolKeyHash(b"2" * POOL_KEY_HASH_SIZE)
    original_operator = PoolOperator(pool_key_hash)

    # Act
    primitive = original_operator.to_primitive()
    restored_operator = PoolOperator.from_primitive(primitive)

    # Assert
    assert restored_operator.pool_key_hash == original_operator.pool_key_hash
    assert restored_operator.to_primitive() == primitive


@pytest.mark.parametrize(
    "invalid_input, expected_exception",
    [
        ("invalid_pool_id", Exception),  # Invalid hex string
        (
            "stake1uxtr5m6kygt77399zxqrykkluqr0grr4yrjtl5xplza6k8q5fghrp",
            Exception,
        ),  # Wrong prefix
        ("", Exception),  # Empty string
    ],
)
def test_pool_operator_from_primitive_errors(invalid_input, expected_exception):
    """Test PoolOperator.from_primitive raises errors for invalid inputs."""
    # Act & Assert
    with pytest.raises(expected_exception):
        PoolOperator.from_primitive(invalid_input)
