"""All type of hashes in Cardano ledger spec."""

from typing import Type, TypeVar, Union

from pycardano.serialization import CBORSerializable, limit_primitive_type

__all__ = [
    "VERIFICATION_KEY_HASH_SIZE",
    "SCRIPT_HASH_SIZE",
    "TRANSACTION_HASH_SIZE",
    "DATUM_HASH_SIZE",
    "AUXILIARY_DATA_HASH_SIZE",
    "POOL_KEY_HASH_SIZE",
    "SCRIPT_DATA_HASH_SIZE",
    "ConstrainedBytes",
    "VerificationKeyHash",
    "ScriptHash",
    "ScriptDataHash",
    "TransactionId",
    "DatumHash",
    "AuxiliaryDataHash",
    "PoolKeyHash",
]

VERIFICATION_KEY_HASH_SIZE = 28
SCRIPT_HASH_SIZE = 28
SCRIPT_DATA_HASH_SIZE = 32
TRANSACTION_HASH_SIZE = 32
DATUM_HASH_SIZE = 32
AUXILIARY_DATA_HASH_SIZE = 32
POOL_KEY_HASH_SIZE = 28


T = TypeVar("T", bound="ConstrainedBytes")


class ConstrainedBytes(CBORSerializable):
    """A wrapped class of bytes with constrained size.

    Args:
        payload (bytes): Hash in bytes.
    """

    __slots__ = "_payload"

    MAX_SIZE = 32
    MIN_SIZE = 0

    def __init__(self, payload: bytes):
        assert self.MIN_SIZE <= len(payload) <= self.MAX_SIZE, (
            f"Invalid byte size: {len(payload)} for class {self.__class__}, "
            f"expected size range: [{self.MIN_SIZE}, {self.MAX_SIZE}]"
        )
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
    @limit_primitive_type(bytes, str)
    def from_primitive(cls: Type[T], value: Union[bytes, str]) -> T:
        if isinstance(value, str):
            value = bytes.fromhex(value)
        return cls(value)

    def __eq__(self, other):
        if isinstance(other, ConstrainedBytes):
            return self.payload == other.payload
        else:
            return False

    def __repr__(self):
        return f"{self.__class__.__name__}(hex='{self.payload.hex()}')"

    def __str__(self):
        return self.payload.hex()


class VerificationKeyHash(ConstrainedBytes):
    """Hash of a Cardano verification key."""

    MAX_SIZE = MIN_SIZE = VERIFICATION_KEY_HASH_SIZE


class ScriptHash(ConstrainedBytes):
    """Hash of a policy/plutus script."""

    MAX_SIZE = MIN_SIZE = SCRIPT_HASH_SIZE


class ScriptDataHash(ConstrainedBytes):
    """Hash of script data. See
    https://github.com/input-output-hk/cardano-ledger/blob/525844be05adae151e82069dcd0000f3301ca0d0/eras/alonzo/
    test-suite/cddl-files/alonzo.cddl#L79-L86"""

    MAX_SIZE = MIN_SIZE = SCRIPT_DATA_HASH_SIZE


class TransactionId(ConstrainedBytes):
    """Hash of a transaction."""

    MAX_SIZE = MIN_SIZE = TRANSACTION_HASH_SIZE


class DatumHash(ConstrainedBytes):
    """Hash of a datum"""

    MAX_SIZE = MIN_SIZE = DATUM_HASH_SIZE


class AuxiliaryDataHash(ConstrainedBytes):
    """Hash of auxiliary data"""

    MAX_SIZE = MIN_SIZE = AUXILIARY_DATA_HASH_SIZE


class PoolKeyHash(ConstrainedBytes):
    """Hash of a stake pool"""

    MAX_SIZE = MIN_SIZE = POOL_KEY_HASH_SIZE
