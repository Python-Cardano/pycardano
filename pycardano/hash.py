from pycardano.serialization import CBORSerializable

ADDR_KEYHASH_SIZE = 28
SCRIPT_HASH_SIZE = 28
TRANSACTION_HASH_SIZE = 32
DATUM_HASH_SIZE = 32
AUXILIARY_DATA_HASH_SIZE = 32
SIGNATURE_SIZE = 32


class _FixedSizeBytes(CBORSerializable):
    """A wrapped class of bytes with fixed size.

    Args:
        payload (bytes): Hash in bytes.
    """

    SIZE = ADDR_KEYHASH_SIZE

    def __init__(self, payload: bytes):
        assert len(payload) == self.SIZE, f"Invalid byte size: {len(payload)}, expecting size: {self.SIZE}"
        self._payload = payload

    def __bytes__(self):
        return self.payload

    @property
    def payload(self) -> bytes:
        return self._payload

    def serialize(self) -> bytes:
        return self.payload

    @classmethod
    def deserialize(cls, value: bytes) -> CBORSerializable:
        return cls(value)

    def __eq__(self, other):
        if isinstance(other, _FixedSizeBytes):
            return self.payload == other.payload
        else:
            return False


class AddrKeyHash(_FixedSizeBytes):
    """Hash of a Cardano verification key."""
    SIZE = ADDR_KEYHASH_SIZE


class ScriptHash(_FixedSizeBytes):
    """Hash of a policy/plutus script."""
    SIZE = SCRIPT_HASH_SIZE


class TransactionHash(_FixedSizeBytes):
    """Hash of a transaction."""
    SIZE = TRANSACTION_HASH_SIZE


class DatumHash(_FixedSizeBytes):
    """Hash of a datum"""
    SIZE = DATUM_HASH_SIZE


class AuxiliaryDataHash(_FixedSizeBytes):
    """Hash of auxiliary data"""
    SIZE = AUXILIARY_DATA_HASH_SIZE
