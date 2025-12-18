"""A module that contains address-related classes.

Specifications and references could be found in:
    - CIP-0005: https://github.com/cardano-foundation/CIPs/tree/master/CIP-0005
    - CIP-0019: https://github.com/cardano-foundation/CIPs/tree/master/CIP-0019

"""

from __future__ import annotations

import binascii
import os
from enum import Enum
from typing import Optional, Type, Union

import base58
from cbor2 import CBORTag
from typing_extensions import override

from pycardano.cbor import cbor2
from pycardano.crypto.bech32 import decode, encode
from pycardano.exception import (
    DecodingException,
    DeserializeException,
    InvalidAddressInputException,
)
from pycardano.hash import VERIFICATION_KEY_HASH_SIZE, ScriptHash, VerificationKeyHash
from pycardano.network import Network
from pycardano.serialization import CBORSerializable, limit_primitive_type

__all__ = ["AddressType", "PointerAddress", "Address"]


class AddressType(Enum):
    """
    Address type definition.
    """

    BYRON = 0b1000
    """Byron address"""

    KEY_KEY = 0b0000
    """Payment key hash + Stake key hash"""

    SCRIPT_KEY = 0b0001
    """Script hash + Stake key hash"""

    KEY_SCRIPT = 0b0010
    """Payment key hash + Script hash"""

    SCRIPT_SCRIPT = 0b0011
    """Script hash + Script hash"""

    KEY_POINTER = 0b0100
    """Payment key hash + Pointer address"""

    SCRIPT_POINTER = 0b0101
    """Script hash + Pointer address"""

    KEY_NONE = 0b0110
    """Payment key hash only"""

    SCRIPT_NONE = 0b0111
    """Script hash for payment part only"""

    NONE_KEY = 0b1110
    """Stake key hash for stake part only"""

    NONE_SCRIPT = 0b1111
    """Script hash for stake part only"""


class PointerAddress(CBORSerializable):
    """Pointer address.

    It refers to a point of the chain containing a stake key registration certificate.

    Args:
        slot (int): Slot in which the staking certificate was posted.
        tx_index (int): The transaction index (within that slot).
        cert_index (int): A (delegation) certificate index (within that transaction).
    """

    def __init__(self, slot: int, tx_index: int, cert_index: int):
        self._slot = slot
        self._tx_index = tx_index
        self._cert_index = cert_index

    @property
    def slot(self) -> int:
        return self._slot

    @property
    def tx_index(self) -> int:
        return self._tx_index

    @property
    def cert_index(self) -> int:
        return self._cert_index

    def encode(self) -> bytes:
        """Encode the pointer address to bytes.

        The encoding follows
        `CIP-0019#Pointers <https://github.com/cardano-foundation/CIPs/tree/master/CIP-0019#pointers>`_.

        Returns:
            bytes: Encoded bytes.

        Examples:
            >>> PointerAddress(1, 2, 3).encode()
            b'\\x01\\x02\\x03'
            >>> PointerAddress(123456789, 2, 3).encode()
            b'\\xba\\xef\\x9a\\x15\\x02\\x03'
        """

        def _encode_int(n):
            output = bytearray()
            output.append(n & 0x7F)
            n >>= 7
            while n > 0:
                output.append(0x80 | (n & 0x7F))
                n >>= 7
            output.reverse()
            return bytes(output)

        return (
            _encode_int(self.slot)
            + _encode_int(self.tx_index)
            + _encode_int(self.cert_index)
        )

    @classmethod
    def decode(cls, data: bytes) -> PointerAddress:
        """Decode bytes into a PointerAddress.

        Args:
            data (bytes): The data to be decoded.

        Returns:
            PointerAddress: Decoded pointer address.

        Examples:
            >>> PointerAddress.decode(b'\\x01\\x02\\x03')
            PointerAddress(1, 2, 3)
            >>> PointerAddress.decode(b'\\xba\\xef\\x9a\\x15\\x02\\x03')
            PointerAddress(123456789, 2, 3)
        """
        ints = []
        cur_int = 0
        for i in data:
            cur_int |= i & 0x7F
            if not (i & 0x80):
                ints.append(cur_int)
                cur_int = 0
            else:
                cur_int <<= 7

        if len(ints) != 3:
            raise DecodingException(
                f"Error in decoding data {data} into a PointerAddress"
            )

        return cls(*ints)

    def to_primitive(self) -> bytes:
        return self.encode()

    @classmethod
    @limit_primitive_type(bytes)
    def from_primitive(cls: Type[PointerAddress], value: bytes) -> PointerAddress:
        return cls.decode(value)

    def __eq__(self, other):
        if not isinstance(other, PointerAddress):
            return False
        else:
            return (
                other.slot == self.slot
                and other.tx_index == self.tx_index
                and other.cert_index == self.cert_index
            )

    def __repr__(self):
        return f"PointerAddress({self.slot}, {self.tx_index}, {self.cert_index})"


class Address(CBORSerializable):
    """A shelley address. It consists of two parts: payment part and staking part.
        Either of the parts could be None, but they cannot be None at the same time.

    Args:
        payment_part (Union[VerificationKeyHash, ScriptHash, None]): Payment part of the address.
        staking_part (Union[KeyHash, ScriptHash, PointerAddress, None]): Staking part of the address.
        network (Network): Type of network the address belongs to.
    """

    def __init__(
        self,
        payment_part: Union[VerificationKeyHash, ScriptHash, None] = None,
        staking_part: Union[
            VerificationKeyHash, ScriptHash, PointerAddress, None
        ] = None,
        network: Network = Network.MAINNET,
    ):
        self._payment_part = payment_part
        self._staking_part = staking_part
        self._network = network

        # Byron address fields (only populated when decoding Byron addresses)
        self._byron_payload_hash: Optional[bytes] = None
        self._byron_attributes: Optional[dict] = None
        self._byron_type: Optional[int] = None
        self._byron_crc32: Optional[int] = None

        self._address_type = self._infer_address_type()
        self._header_byte = self._compute_header_byte() if not self.is_byron else None
        self._hrp = self._compute_hrp() if not self.is_byron else None

    @property
    def is_byron(self) -> bool:
        """Check if this is a Byron-era address.

        Returns:
            bool: True if this is a Byron address, False if Shelley/later.
        """
        return self._byron_payload_hash is not None

    def _infer_address_type(self):
        """Guess address type from the combination of payment part and staking part."""
        # Check if this is a Byron address
        if self.is_byron:
            return AddressType.BYRON

        payment_type = type(self.payment_part)
        staking_type = type(self.staking_part)
        if payment_type == VerificationKeyHash:
            if staking_type == VerificationKeyHash:
                return AddressType.KEY_KEY
            elif staking_type == ScriptHash:
                return AddressType.KEY_SCRIPT
            elif staking_type == PointerAddress:
                return AddressType.KEY_POINTER
            elif self.staking_part is None:
                return AddressType.KEY_NONE
        elif payment_type == ScriptHash:
            if staking_type == VerificationKeyHash:
                return AddressType.SCRIPT_KEY
            elif staking_type == ScriptHash:
                return AddressType.SCRIPT_SCRIPT
            elif staking_type == PointerAddress:
                return AddressType.SCRIPT_POINTER
            elif self.staking_part is None:
                return AddressType.SCRIPT_NONE
        elif self.payment_part is None:
            if staking_type == VerificationKeyHash:
                return AddressType.NONE_KEY
            elif staking_type == ScriptHash:
                return AddressType.NONE_SCRIPT

        raise InvalidAddressInputException(
            f"Cannot construct a shelley address from a combination of "
            f"payment part: {self.payment_part} and "
            f"stake part: {self.staking_part}"
        )

    @property
    def payment_part(self) -> Union[VerificationKeyHash, ScriptHash, None]:
        """Payment part of the address."""
        return self._payment_part

    @property
    def staking_part(
        self,
    ) -> Union[VerificationKeyHash, ScriptHash, PointerAddress, None]:
        """Staking part of the address."""
        return self._staking_part

    @property
    def network(self) -> Network:
        """Network this address belongs to."""
        return self._network

    @property
    def address_type(self) -> AddressType:
        """Address type."""
        return self._address_type

    @property
    def header_byte(self) -> Optional[bytes]:
        """Header byte that identifies the type of address. None for Byron addresses."""
        return self._header_byte

    @property
    def hrp(self) -> Optional[str]:
        """Human-readable prefix for bech32 encoder. None for Byron addresses."""
        return self._hrp

    @property
    def payload_hash(self) -> Optional[bytes]:
        """Byron address payload hash (28 bytes). None for Shelley addresses."""
        return self._byron_payload_hash if self.is_byron else None

    @property
    def byron_attributes(self) -> Optional[dict]:
        """Byron address attributes. None for Shelley addresses."""
        return self._byron_attributes if self.is_byron else None

    @property
    def byron_type(self) -> Optional[int]:
        """Byron address type (0=Public Key, 2=Redemption). None for Shelley addresses."""
        return self._byron_type if self.is_byron else None

    @property
    def crc32_checksum(self) -> Optional[int]:
        """Byron address CRC32 checksum. None for Shelley addresses."""
        return self._byron_crc32 if self.is_byron else None

    def _compute_header_byte(self) -> bytes:
        """Compute the header byte."""
        return (self.address_type.value << 4 | self.network.value).to_bytes(
            1, byteorder="big"
        )

    def _compute_hrp(self) -> str:
        """Compute human-readable prefix for bech32 encoder.

        Based on
        `miscellaneous section <https://github.com/cardano-foundation/CIPs/tree/master/CIP-0005#miscellaneous>`_
        in CIP-5.
        """
        prefix = (
            "stake"
            if self.address_type in (AddressType.NONE_KEY, AddressType.NONE_SCRIPT)
            else "addr"
        )
        suffix = "" if self.network == Network.MAINNET else "_test"
        return prefix + suffix

    def __bytes__(self):
        if self.is_byron:
            payload = cbor2.dumps(
                [
                    self._byron_payload_hash,
                    self._byron_attributes,
                    self._byron_type,
                ]
            )
            return cbor2.dumps([CBORTag(24, payload), self._byron_crc32])

        payment = self.payment_part or bytes()
        if self.staking_part is None:
            staking = bytes()
        elif type(self.staking_part) is PointerAddress:
            staking = self.staking_part.encode()
        else:
            staking = self.staking_part
        return self.header_byte + bytes(payment) + bytes(staking)

    def encode(self) -> str:
        """Encode the address in Bech32 format (Shelley) or Base58 format (Byron).

        More info about Bech32 `here <https://github.com/bitcoin/bips/blob/master/bip-0173.mediawiki#Bech32>`_.

        Returns:
            str: Encoded address in Bech32 (Shelley) or Base58 (Byron).

        Examples:
            >>> payment_hash = VerificationKeyHash(
            ...     bytes.fromhex("cc30497f4ff962f4c1dca54cceefe39f86f1d7179668009f8eb71e59"))
            >>> print(Address(payment_hash).encode())
            addr1v8xrqjtlfluk9axpmjj5enh0uw0cduwhz7txsqyl36m3ukgqdsn8w
        """
        if self.is_byron:
            return base58.b58encode(bytes(self)).decode("ascii")
        return encode(self.hrp, bytes(self))

    @classmethod
    def decode(cls, data: str) -> Address:
        """Decode a bech32 string into an address object.

        Args:
            data (str): Bech32-encoded string.

        Returns:
            Address: Decoded address.

        Raises:
            DecodingException: When the input string is not a valid Shelley address.

        Examples:
            >>> addr = Address.decode("addr1v8xrqjtlfluk9axpmjj5enh0uw0cduwhz7txsqyl36m3ukgqdsn8w")
            >>> khash = VerificationKeyHash(bytes.fromhex("cc30497f4ff962f4c1dca54cceefe39f86f1d7179668009f8eb71e59"))
            >>> assert addr == Address(khash)
        """
        return cls.from_primitive(data)

    def to_primitive(self) -> bytes:
        return bytes(self)

    @classmethod
    @limit_primitive_type(bytes, str)
    def from_primitive(cls: Type[Address], value: Union[bytes, str]) -> Address:
        # Convert string to bytes
        if isinstance(value, str):
            # Check for Byron Base58 prefixes (common Byron patterns)
            if value.startswith(("Ae2td", "Ddz")):
                return cls._from_byron_base58(value)

            # Try Bech32 decode for Shelley addresses
            original_str = value
            try:
                value = bytes(decode(value))
            except Exception:
                try:
                    return cls._from_byron_base58(original_str)
                except Exception as e:
                    raise DecodingException(f"Failed to decode address string: {e}")

        # At this point, value is always bytes
        # Check if it's a Byron address (CBOR with tag 24)
        try:
            decoded = cbor2.loads(value)
            if isinstance(decoded, (tuple, list)) and len(decoded) == 2:
                if isinstance(decoded[0], CBORTag) and decoded[0].tag == 24:
                    # This is definitely a Byron address - validate and decode it
                    return cls._from_byron_cbor(value)
        except DecodingException:
            # Byron decoding failed with validation error - re-raise it
            raise
        except Exception:
            # Not Byron CBOR (general CBOR decode error), continue with Shelley decoding
            pass

        # Shelley address decoding (existing logic)
        header = value[0]
        payload = value[1:]
        addr_type = AddressType((header & 0xF0) >> 4)
        network = Network(header & 0x0F)
        if addr_type == AddressType.KEY_KEY:
            return cls(
                VerificationKeyHash(payload[:VERIFICATION_KEY_HASH_SIZE]),
                VerificationKeyHash(payload[VERIFICATION_KEY_HASH_SIZE:]),
                network,
            )
        elif addr_type == AddressType.KEY_SCRIPT:
            return cls(
                VerificationKeyHash(payload[:VERIFICATION_KEY_HASH_SIZE]),
                ScriptHash(payload[VERIFICATION_KEY_HASH_SIZE:]),
                network,
            )
        elif addr_type == AddressType.KEY_POINTER:
            pointer_addr = PointerAddress.decode(payload[VERIFICATION_KEY_HASH_SIZE:])
            return cls(
                VerificationKeyHash(payload[:VERIFICATION_KEY_HASH_SIZE]),
                pointer_addr,
                network,
            )
        elif addr_type == AddressType.KEY_NONE:
            return cls(VerificationKeyHash(payload), None, network)
        elif addr_type == AddressType.SCRIPT_KEY:
            return cls(
                ScriptHash(payload[:VERIFICATION_KEY_HASH_SIZE]),
                VerificationKeyHash(payload[VERIFICATION_KEY_HASH_SIZE:]),
                network,
            )
        elif addr_type == AddressType.SCRIPT_SCRIPT:
            return cls(
                ScriptHash(payload[:VERIFICATION_KEY_HASH_SIZE]),
                ScriptHash(payload[VERIFICATION_KEY_HASH_SIZE:]),
                network,
            )
        elif addr_type == AddressType.SCRIPT_POINTER:
            pointer_addr = PointerAddress.decode(payload[VERIFICATION_KEY_HASH_SIZE:])
            return cls(
                ScriptHash(payload[:VERIFICATION_KEY_HASH_SIZE]), pointer_addr, network
            )
        elif addr_type == AddressType.SCRIPT_NONE:
            return cls(ScriptHash(payload), None, network)
        elif addr_type == AddressType.NONE_KEY:
            return cls(None, VerificationKeyHash(payload), network)
        elif addr_type == AddressType.NONE_SCRIPT:
            return cls(None, ScriptHash(payload), network)
        raise DeserializeException(f"Error in deserializing bytes: {value}")

    @classmethod
    def _from_byron_base58(cls: Type[Address], base58_str: str) -> Address:
        """Decode a Byron address from Base58 string.

        Args:
            base58_str: Base58-encoded Byron address string.

        Returns:
            Address: Decoded Byron address instance.

        Raises:
            DecodingException: When decoding fails.
        """
        try:
            cbor_bytes = base58.b58decode(base58_str)
        except Exception as e:
            raise DecodingException(f"Failed to decode Base58 string: {e}")

        return cls._from_byron_cbor(cbor_bytes)

    @classmethod
    def _from_byron_cbor(cls: Type[Address], cbor_bytes: bytes) -> Address:
        """Decode a Byron address from CBOR bytes.

        Args:
            cbor_bytes: CBOR-encoded Byron address bytes.

        Returns:
            Address: Decoded Byron address instance.

        Raises:
            DecodingException: When decoding fails.
        """
        try:
            decoded = cbor2.loads(cbor_bytes)
        except Exception as e:
            raise DecodingException(f"Failed to decode CBOR bytes: {e}")

        # Byron address structure: [CBORTag(24, payload), crc32]
        if not isinstance(decoded, (tuple, list)) or len(decoded) != 2:
            raise DecodingException(
                f"Byron address must be a 2-element array, got {type(decoded)}"
            )

        tagged_payload, crc32_checksum = decoded

        if not isinstance(tagged_payload, CBORTag) or tagged_payload.tag != 24:
            raise DecodingException(
                f"Byron address must use CBOR tag 24, got {tagged_payload}"
            )

        payload_cbor = tagged_payload.value
        if not isinstance(payload_cbor, bytes):
            raise DecodingException(
                f"Tag 24 must contain bytes, got {type(payload_cbor)}"
            )

        computed_crc32 = binascii.crc32(payload_cbor) & 0xFFFFFFFF
        if computed_crc32 != crc32_checksum:
            raise DecodingException(
                f"CRC32 checksum mismatch: expected {crc32_checksum}, got {computed_crc32}"
            )

        try:
            payload = cbor2.loads(payload_cbor)
        except Exception as e:
            raise DecodingException(f"Failed to decode Byron address payload: {e}")

        if not isinstance(payload, (tuple, list)) or len(payload) != 3:
            raise DecodingException(
                f"Byron address payload must be a 3-element array, got {payload}"
            )

        payload_hash, attributes, byron_type = payload

        if not isinstance(payload_hash, bytes) or len(payload_hash) != 28:
            size = (
                len(payload_hash)
                if isinstance(payload_hash, bytes)
                else f"type {type(payload_hash).__name__}"
            )
            raise DecodingException(f"Payload hash must be 28 bytes, got {size}")

        if not isinstance(attributes, dict):
            raise DecodingException(
                f"Attributes must be a dict, got {type(attributes)}"
            )

        if byron_type not in (0, 2):
            raise DecodingException(f"Byron type must be 0 or 2, got {byron_type}")

        # Create Address instance with Byron fields
        addr = cls.__new__(cls)
        addr._payment_part = None
        addr._staking_part = None
        addr._byron_payload_hash = payload_hash
        addr._byron_attributes = attributes
        addr._byron_type = byron_type
        addr._byron_crc32 = crc32_checksum
        addr._network = addr._infer_byron_network()
        addr._address_type = AddressType.BYRON
        addr._header_byte = None
        addr._hrp = None
        return addr

    def _infer_byron_network(self) -> Network:
        """Infer network from Byron address attributes.

        Returns:
            Network: MAINNET or TESTNET (defaults to MAINNET).
        """
        if self._byron_attributes and 2 in self._byron_attributes:
            network_bytes = self._byron_attributes[2]
            if isinstance(network_bytes, bytes):
                try:
                    network_discriminant = cbor2.loads(network_bytes)
                    # Mainnet: 764824073 (0x2D964A09), Testnet: 1097911063 (0x42659F17)
                    if network_discriminant == 1097911063:
                        return Network.TESTNET
                except Exception:
                    pass
        return Network.MAINNET

    def __eq__(self, other):
        if not isinstance(other, Address):
            return False

        if self.is_byron != other.is_byron:
            return False

        if self.is_byron:
            return (
                self._byron_payload_hash == other._byron_payload_hash
                and self._byron_attributes == other._byron_attributes
                and self._byron_type == other._byron_type
                and self._byron_crc32 == other._byron_crc32
            )

        return (
            self.payment_part == other.payment_part
            and self.staking_part == other.staking_part
            and self.network == other.network
        )

    def __repr__(self):
        return f"{self.encode()}"

    @override
    def save(
        self,
        path: str,
        key_type: Optional[str] = None,
        description: Optional[str] = None,
        **kwargs,
    ):
        """
        Save the Address object to a file.

        This method writes the object's JSON representation to the specified file path.
         It raises an error if the file already exists and is not empty.

        Args:
            path (str): The file path to save the object to.
            key_type (str, optional): Not used in this context, but can be included for consistency.
            description (str, optional): Not used in this context, but can be included for consistency.
            **kwargs: Additional keyword arguments (not used here).

        Raises:
            IOError: If the file already exists and is not empty.
        """
        if os.path.isfile(path) and os.stat(path).st_size > 0:
            raise IOError(f"File {path} already exists!")
        with open(path, "w") as f:
            f.write(self.encode())

    @classmethod
    def load(cls, path: str) -> Address:
        """
        Load an Address object from a file.

        Args:
            path (str): The file path to load the object from.

        Returns:
            Address: The loaded Address object.
        """
        with open(path) as f:
            return cls.decode(f.read())
