from typing import Union

from pycardano.serialization import CBORSerializable

ADDR_KEYHASH_SIZE = 28
SCRIPT_HASH_SIZE = 28
TRANSACTION_HASH_SIZE = 32
DATUM_HASH_SIZE = 32
AUXILIARY_DATA_HASH_SIZE = 32
SIGNATURE_SIZE = 32


class ConstrainedBytes(CBORSerializable):
    """A wrapped class of bytes with constrained size.

    Args:
        payload (bytes): Hash in bytes.
    """

    __slots__ = "_payload"

    MAX_SIZE = 32
    MIN_SIZE = 0

    def __init__(self, payload: bytes):
        assert self.MIN_SIZE <= len(payload) <= self.MAX_SIZE, \
            f"Invalid byte size: {len(payload)}, expected size range: [{self.MIN_SIZE}, {self.MAX_SIZE}]"
        self._payload = payload

    def __bytes__(self):
        return self.payload

    def __hash__(self):
        return hash(self.payload)

    @property
    def payload(self) -> bytes:
        return self._payload

    def to_primitive(self) -> bytes:
        return self.payload

    @classmethod
    def from_primitive(cls, value: Union[bytes, str]) -> CBORSerializable:
        if isinstance(value, str):
            value = bytes.fromhex(value)
        return cls(value)

    def __eq__(self, other):
        if isinstance(other, ConstrainedBytes):
            return self.payload == other.payload
        else:
            return False


class AddrKeyHash(ConstrainedBytes):
    """Hash of a Cardano verification key."""
    MAX_SIZE = MIN_SIZE = ADDR_KEYHASH_SIZE


class ScriptHash(ConstrainedBytes):
    """Hash of a policy/plutus script."""
    MAX_SIZE = MIN_SIZE = SCRIPT_HASH_SIZE


class TransactionId(ConstrainedBytes):
    """Hash of a transaction."""
    MAX_SIZE = MIN_SIZE = TRANSACTION_HASH_SIZE


class DatumHash(ConstrainedBytes):
    """Hash of a datum"""
    MAX_SIZE = MIN_SIZE = DATUM_HASH_SIZE


class AuxiliaryDataHash(ConstrainedBytes):
    """Hash of auxiliary data"""
    MAX_SIZE = MIN_SIZE = AUXILIARY_DATA_HASH_SIZE
