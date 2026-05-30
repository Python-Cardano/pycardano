"""Unit tests for Byron address implementation in Address class."""

import binascii

import base58
import cbor2
import pytest
from cbor2 import CBORTag

from pycardano import Address, Network
from pycardano.exception import DecodingException, InvalidAddressInputException


class TestAddress:
    """Test cases for Byron address support in Address class."""

    # Known Byron mainnet address for testing
    BYRON_MAINNET_ADDR = "DdzFFzCqrhsxrgB6w6VhgfAqUZ69Va583murc21S4QFTJ6WUHAh4Gk8t1QHofpza5MZxG4dNVQWe8q78h4Utp9MGBQHBLD54rz6CTLsm"

    def test_decode_mainnet_address(self):
        """Test decoding a Byron mainnet address."""
        addr = Address.decode(self.BYRON_MAINNET_ADDR)

        assert addr.is_byron  # This is a Byron address
        assert addr.byron_type == 0  # Public key type
        assert addr.network == Network.MAINNET
        assert len(addr.payload_hash) == 28
        assert addr.crc32_checksum == 898818764

    def test_encode_round_trip(self):
        """Test encoding and decoding round trip."""
        addr = Address.decode(self.BYRON_MAINNET_ADDR)
        encoded = addr.encode()

        assert encoded == self.BYRON_MAINNET_ADDR

    def test_equality(self):
        """Test Byron address equality."""
        addr1 = Address.decode(self.BYRON_MAINNET_ADDR)
        addr2 = Address.decode(self.BYRON_MAINNET_ADDR)

        assert addr1 == addr2
        assert not (addr1 != addr2)

    def test_not_equal_to_other_types(self):
        """Test that Byron address is not equal to other types."""
        addr = Address.decode(self.BYRON_MAINNET_ADDR)

        assert addr != "not an address"
        assert addr != 123
        assert addr != None

    def test_bytes_interface(self):
        """Test conversion to and from bytes."""
        addr = Address.decode(self.BYRON_MAINNET_ADDR)
        addr_bytes = bytes(addr)

        # Should be able to decode from bytes
        addr_from_bytes = Address.from_primitive(addr_bytes)

        assert addr == addr_from_bytes

    def test_repr(self):
        """Test string representation."""
        addr = Address.decode(self.BYRON_MAINNET_ADDR)
        repr_str = repr(addr)

        # __repr__ returns the encoded address string
        assert self.BYRON_MAINNET_ADDR in repr_str

    # Note: Cannot test invalid construction since Byron addresses are read-only (decode only)

    def test_invalid_crc32_checksum(self):
        """Test that invalid CRC32 checksum is detected."""
        # Decode a valid address
        addr = Address.decode(self.BYRON_MAINNET_ADDR)

        # Create corrupted CBOR with wrong CRC32
        corrupted = cbor2.dumps(
            [
                CBORTag(
                    24,
                    cbor2.dumps(
                        [addr.payload_hash, addr.byron_attributes, addr.byron_type]
                    ),
                ),
                12345,  # Wrong CRC32
            ]
        )
        corrupted_b58 = base58.b58encode(corrupted).decode("ascii")

        # Should raise exception
        with pytest.raises(DecodingException, match="CRC32 checksum mismatch"):
            Address.decode(corrupted_b58)

    def test_invalid_base58_string(self):
        """Test that invalid Base58 string raises exception."""
        with pytest.raises(DecodingException):
            Address.decode("not a valid base58 string!!!")

    def test_invalid_cbor_structure(self):
        """Test that invalid CBOR structure raises exception."""
        # Create invalid CBOR (not a 2-element array)
        invalid_cbor = cbor2.dumps([1, 2, 3])
        invalid_b58 = base58.b58encode(invalid_cbor).decode("ascii")

        with pytest.raises(DecodingException):
            Address.decode(invalid_b58)

    def test_missing_cbor_tag(self):
        """Test that missing CBOR tag 24 raises exception."""
        addr = Address.decode(self.BYRON_MAINNET_ADDR)

        # Create CBOR without tag 24
        invalid = cbor2.dumps(
            [
                cbor2.dumps(
                    [addr.payload_hash, addr.byron_attributes, addr.byron_type]
                ),
                addr.crc32_checksum,
            ]
        )
        invalid_b58 = base58.b58encode(invalid).decode("ascii")

        with pytest.raises(DecodingException, match="CBOR tag 24"):
            Address.decode(invalid_b58)

    def test_to_primitive(self):
        """Test conversion to primitive types."""
        addr = Address.decode(self.BYRON_MAINNET_ADDR)
        primitive = addr.to_primitive()

        # For Byron addresses, to_primitive returns bytes
        assert isinstance(primitive, bytes)

    def test_byron_type_property(self):
        """Test Byron address type property."""
        addr = Address.decode(self.BYRON_MAINNET_ADDR)

        assert addr.byron_type in (0, 2)

    def test_network_property(self):
        """Test network property."""
        addr = Address.decode(self.BYRON_MAINNET_ADDR)

        assert isinstance(addr.network, Network)
        assert addr.network in (Network.MAINNET, Network.TESTNET)

    def test_byron_attributes_property(self):
        """Test Byron address attributes property."""
        addr = Address.decode(self.BYRON_MAINNET_ADDR)

        assert isinstance(addr.byron_attributes, dict)

    def test_save_and_load(self, tmp_path):
        """Test saving and loading Byron address to/from file."""
        addr = Address.decode(self.BYRON_MAINNET_ADDR)
        file_path = tmp_path / "byron_address.txt"

        # Save the address
        addr.save(str(file_path))

        # Load the address
        loaded_addr = Address.load(str(file_path))

        assert loaded_addr == addr

    def test_save_existing_file_raises_error(self, tmp_path):
        """Test that saving to existing file raises error."""
        addr = Address.decode(self.BYRON_MAINNET_ADDR)
        file_path = tmp_path / "byron_address.txt"

        # Save once
        addr.save(str(file_path))

        # Try to save again should raise error
        with pytest.raises(IOError):
            addr.save(str(file_path))

    def test_testnet_byron_address(self):
        """Test decoding a testnet Byron address."""
        # Create a Byron testnet address with network discriminant
        payload_hash = b"\x91\xd0\xa0Q\x8e>vN\x13\xf6\xef7X\nk\xe8\xab\x14\xdaO0f\xfd\x01\xaf\x01\xdaj"
        testnet_discriminant = cbor2.dumps(1097911063)  # 0x42659F17
        attributes = {2: testnet_discriminant}
        byron_type = 0

        payload = cbor2.dumps([payload_hash, attributes, byron_type])
        crc32 = binascii.crc32(payload) & 0xFFFFFFFF
        byron_cbor = cbor2.dumps([CBORTag(24, payload), crc32])

        addr = Address.from_primitive(byron_cbor)

        assert addr.is_byron
        assert addr.network == Network.TESTNET
        assert addr.byron_type == 0

    def test_decode_from_raw_cbor_bytes(self):
        """Test decoding Byron address directly from raw CBOR bytes."""
        # Decode a known address to get its CBOR representation
        addr = Address.decode(self.BYRON_MAINNET_ADDR)
        cbor_bytes = bytes(addr)

        # Decode from raw CBOR bytes
        addr_from_cbor = Address.from_primitive(cbor_bytes)

        assert addr == addr_from_cbor
        assert addr_from_cbor.is_byron

    def test_invalid_network_attribute_type(self):
        """Test Byron address with non-bytes network attribute."""
        payload_hash = b"\x00" * 28
        attributes = {2: "not bytes"}  # Invalid type for network discriminant
        byron_type = 0

        payload = cbor2.dumps([payload_hash, attributes, byron_type])
        crc32 = binascii.crc32(payload) & 0xFFFFFFFF
        byron_cbor = cbor2.dumps([CBORTag(24, payload), crc32])

        # Should still decode (defaults to mainnet)
        addr = Address.from_primitive(byron_cbor)
        assert addr.network == Network.MAINNET

    def test_invalid_network_discriminant_value(self):
        """Test Byron address with unknown network discriminant."""
        payload_hash = b"\x00" * 28
        unknown_discriminant = cbor2.dumps(99999)  # Unknown network
        attributes = {2: unknown_discriminant}
        byron_type = 0

        payload = cbor2.dumps([payload_hash, attributes, byron_type])
        crc32 = binascii.crc32(payload) & 0xFFFFFFFF
        byron_cbor = cbor2.dumps([CBORTag(24, payload), crc32])

        # Should default to mainnet
        addr = Address.from_primitive(byron_cbor)
        assert addr.network == Network.MAINNET

    def test_malformed_network_cbor(self):
        """Test Byron address with malformed network CBOR."""
        payload_hash = b"\x00" * 28
        attributes = {2: b"\xff\xff"}  # Invalid CBOR
        byron_type = 0

        payload = cbor2.dumps([payload_hash, attributes, byron_type])
        crc32 = binascii.crc32(payload) & 0xFFFFFFFF
        byron_cbor = cbor2.dumps([CBORTag(24, payload), crc32])

        # Should default to mainnet on CBOR decode error
        addr = Address.from_primitive(byron_cbor)
        assert addr.network == Network.MAINNET

    def test_redemption_address_type(self):
        """Test Byron redemption address (type 2)."""
        payload_hash = b"\x00" * 28
        attributes = {}
        byron_type = 2  # Redemption type

        payload = cbor2.dumps([payload_hash, attributes, byron_type])
        crc32 = binascii.crc32(payload) & 0xFFFFFFFF
        byron_cbor = cbor2.dumps([CBORTag(24, payload), crc32])

        addr = Address.from_primitive(byron_cbor)
        assert addr.byron_type == 2

    def test_invalid_payload_not_3_elements(self):
        """Test Byron address with wrong number of payload elements."""
        # Create invalid payload with 2 elements instead of 3
        invalid_payload = cbor2.dumps([b"\x00" * 28, {}])
        crc32 = binascii.crc32(invalid_payload) & 0xFFFFFFFF
        byron_cbor = cbor2.dumps([CBORTag(24, invalid_payload), crc32])

        with pytest.raises(DecodingException, match="3-element array"):
            Address.from_primitive(byron_cbor)

    def test_invalid_payload_hash_wrong_size(self):
        """Test Byron address with wrong payload hash size."""
        invalid_payload = cbor2.dumps([b"\x00" * 20, {}, 0])  # 20 bytes instead of 28
        crc32 = binascii.crc32(invalid_payload) & 0xFFFFFFFF
        byron_cbor = cbor2.dumps([CBORTag(24, invalid_payload), crc32])

        with pytest.raises(DecodingException, match="28 bytes"):
            Address.from_primitive(byron_cbor)

    def test_invalid_attributes_not_dict(self):
        """Test Byron address with non-dict attributes."""
        invalid_payload = cbor2.dumps([b"\x00" * 28, "not a dict", 0])
        crc32 = binascii.crc32(invalid_payload) & 0xFFFFFFFF
        byron_cbor = cbor2.dumps([CBORTag(24, invalid_payload), crc32])

        with pytest.raises(DecodingException, match="must be a dict"):
            Address.from_primitive(byron_cbor)

    def test_invalid_byron_type(self):
        """Test Byron address with invalid type (not 0 or 2)."""
        invalid_payload = cbor2.dumps([b"\x00" * 28, {}, 1])  # Type 1 is invalid
        crc32 = binascii.crc32(invalid_payload) & 0xFFFFFFFF
        byron_cbor = cbor2.dumps([CBORTag(24, invalid_payload), crc32])

        with pytest.raises(DecodingException, match="must be 0 or 2"):
            Address.from_primitive(byron_cbor)

    def test_shelley_and_byron_not_equal(self):
        """Test that Shelley and Byron addresses are never equal."""
        byron_addr = Address.decode(self.BYRON_MAINNET_ADDR)

        # Create a Shelley address
        from pycardano import VerificationKeyHash

        shelley_addr = Address(VerificationKeyHash(b"\x00" * 28), None, Network.MAINNET)

        assert byron_addr != shelley_addr
