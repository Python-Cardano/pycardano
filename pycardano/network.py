"""Cardano network types."""

from __future__ import annotations

from enum import Enum
from typing import Type

from pycardano.serialization import CBORSerializable, limit_primitive_type

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
    @limit_primitive_type(int)
    def from_primitive(cls: Type[Network], value: int) -> Network:
        return cls(value)
