"""Cardano network types."""

from __future__ import annotations

from enum import Enum

from pycardano.serialization import CBORSerializable

__all__ = ["Network"]


class Network(CBORSerializable, Enum):
    """
    Network ID
    """

    TESTNET = 0
    MAINNET = 1
    PREVIEW = 2
    PREPROD = 3

    def to_primitive(self) -> int:
        return self.value

    @classmethod
    def from_primitive(cls, value: int) -> Network:
        return cls(value)


BLOCKFROST_URLS = {
    Network.MAINNET: "https://cardano-mainnet.blockfrost.io/api",
    Network.TESTNET: "https://cardano-testnet.blockfrost.io/api",
    Network.PREVIEW: "https://cardano-preview.blockfrost.io/api",
    Network.PREPROD: "https://cardano-preprod.blockfrost.io/api",
}
