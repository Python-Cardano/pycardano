"""Cardano network types."""

from __future__ import annotations

from enum import Enum
from typing import Type

from pycardano.exception import DeserializeException
from pycardano.serialization import CBORSerializable, Primitive

__all__ = ["Network"]


class Network(CBORSerializable, Enum):
    """
    Network ID
    """

    TESTNET = 0
    MAINNET = 1

    def to_primitive(self) -> int:
        return self.value

    @classmethod
    def from_primitive(cls: Type[Network], value: Primitive) -> Network:
        if not isinstance(value, int):
            raise DeserializeException(
                f"An integer value is required for deserialization: {str(value)}"
            )
        return cls(value)
