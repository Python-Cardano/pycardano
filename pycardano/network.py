from __future__ import annotations

from enum import Enum

from pycardano.serialization import CBORSerializable


class Network(CBORSerializable, Enum):
    """
    Network ID
    """
    TESTNET = 0
    MAINNET = 1

    def serialize(self) -> int:
        return self.value

    @classmethod
    def deserialize(cls, value: int) -> Network:
        return cls(value)
