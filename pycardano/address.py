"""A module that contains address-related classes.

Specifications and references could be found in:
    - CIP-0005: https://github.com/cardano-foundation/CIPs/tree/master/CIP-0005
    - CIP-0019: https://github.com/cardano-foundation/CIPs/tree/master/CIP-0019

"""

from __future__ import annotations

from enum import Enum
from typing import Type, Union

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
        self._address_type = self._infer_address_type()
        self._header_byte = self._compute_header_byte()
        self._hrp = self._compute_hrp()

    def _infer_address_type(self):
        """Guess address type from the combination of payment part and staking part."""
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
    def header_byte(self) -> bytes:
        """Header byte that identifies the type of address."""
        return self._header_byte

    @property
    def hrp(self) -> str:
        """Human-readable prefix for bech32 encoder."""
        return self._hrp

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
        payment = self.payment_part or bytes()
        if self.staking_part is None:
            staking = bytes()
        elif type(self.staking_part) == PointerAddress:
            staking = self.staking_part.encode()
        else:
            staking = self.staking_part
        return self.header_byte + bytes(payment) + bytes(staking)

    def encode(self) -> str:
        """Encode the address in Bech32 format.

        More info about Bech32 `here <https://github.com/bitcoin/bips/blob/master/bip-0173.mediawiki#Bech32>`_.

        Returns:
            str: Encoded address in Bech32.

        Examples:
            >>> payment_hash = VerificationKeyHash(
            ...     bytes.fromhex("cc30497f4ff962f4c1dca54cceefe39f86f1d7179668009f8eb71e59"))
            >>> print(Address(payment_hash).encode())
            addr1v8xrqjtlfluk9axpmjj5enh0uw0cduwhz7txsqyl36m3ukgqdsn8w
        """
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
        if isinstance(value, str):
            value = bytes(decode(value))
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

    def __eq__(self, other):
        if not isinstance(other, Address):
            return False
        else:
            return (
                other.payment_part == self.payment_part
                and other.staking_part == self.staking_part
                and other.network == self.network
            )

    def __repr__(self):
        return f"{self.encode()}"
