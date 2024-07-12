"""
Pool parameters for stake pool registration certificate.
"""

from __future__ import annotations

import socket
from dataclasses import dataclass, field
from fractions import Fraction
from typing import List, Optional, Type, Union

from pycardano.crypto.bech32 import bech32_decode
from pycardano.exception import DeserializeException
from pycardano.hash import (
    PoolKeyHash,
    PoolMetadataHash,
    RewardAccountHash,
    VerificationKeyHash,
    VrfKeyHash,
)
from pycardano.serialization import (
    ArrayCBORSerializable,
    CBORSerializable,
    limit_primitive_type,
)

__all__ = [
    "PoolId",
    "PoolMetadata",
    "PoolParams",
    "Relay",
    "SingleHostAddr",
    "SingleHostName",
    "MultiHostName",
    "is_bech32_cardano_pool_id",
]


def is_bech32_cardano_pool_id(pool_id: str) -> bool:
    """Check if a string is a valid Cardano stake pool ID in bech32 format."""
    if pool_id is None or not pool_id.startswith("pool"):
        return False
    return bech32_decode(pool_id) != (None, None, None)


@dataclass(frozen=True)
class PoolId(CBORSerializable):
    value: str

    def __post_init__(self):
        if not is_bech32_cardano_pool_id(self.value):
            raise ValueError(
                "Invalid PoolId format. The PoolId should be a valid Cardano stake pool ID in bech32 format."
            )

    def __str__(self):
        return self.value

    def __repr__(self):
        return self.value

    def to_primitive(self) -> str:
        return self.value

    @classmethod
    @limit_primitive_type(str)
    def from_primitive(cls: Type[PoolId], value: str) -> PoolId:
        return cls(value)


@dataclass(repr=False)
class SingleHostAddr(ArrayCBORSerializable):
    _CODE: int = field(init=False, default=0)

    port: Optional[int]
    ipv4: Optional[Union[str, bytes]]
    ipv6: Optional[Union[str, bytes]]

    def __init__(
        self,
        port: Optional[int] = None,
        ipv4: Optional[Union[str, bytes]] = None,
        ipv6: Optional[Union[str, bytes]] = None,
    ):
        super().__init__()

        self._CODE = 0
        self.port = port

        self.ipv4 = self.bytes_to_ipv4(ipv4)
        self.ipv6 = self.bytes_to_ipv6(ipv6)

    @staticmethod
    def ipv4_to_bytes(ip_address: Optional[str | bytes] = None) -> bytes | None:
        """
        Convert IPv4 address to bytes format.
        Args:
            ip_address: The IPv4 address in human-readable format.

        Returns:
            bytes: IPv4 address in bytes format.
        """
        if isinstance(ip_address, str):
            return socket.inet_aton(ip_address)
        elif isinstance(ip_address, bytes):
            return ip_address
        else:
            return None

    @staticmethod
    def ipv6_to_bytes(ip_address: Optional[str | bytes] = None) -> bytes | None:
        """
        Convert IPv6 address to bytes format.
        Args:
            ip_address: The IPv6 address in human-readable format.

        Returns:
            The IPv6 address in bytes format.
        """
        if isinstance(ip_address, str):
            return socket.inet_pton(socket.AF_INET6, ip_address)
        elif isinstance(ip_address, bytes):
            return ip_address
        else:
            return None

    @staticmethod
    def bytes_to_ipv4(bytes_ip_address: Optional[str | bytes] = None) -> str | None:
        """
        Convert IPv4 address in bytes to human-readable format.
        Args:
            bytes_ip_address: The IPv4 address in bytes format.
        Returns:
            The IPv4 address in human-readable format.
        """
        if isinstance(bytes_ip_address, str):
            return bytes_ip_address
        elif isinstance(bytes_ip_address, bytes):
            return socket.inet_ntoa(bytes_ip_address)
        else:
            return None

    @staticmethod
    def bytes_to_ipv6(bytes_ip_address: Optional[str | bytes] = None) -> str | None:
        """
        Convert IPv6 address in bytes to human-readable format.
        Args:
            bytes_ip_address: The IPv6 address in bytes format.
        Returns:
            The IPv6 address in human-readable format.
        """
        if isinstance(bytes_ip_address, str):
            return bytes_ip_address
        elif isinstance(bytes_ip_address, bytes):
            return socket.inet_ntop(socket.AF_INET6, bytes_ip_address)
        else:
            return None

    def to_primitive(self) -> list:
        return [
            self._CODE,
            self.port,
            self.ipv4_to_bytes(self.ipv4),
            self.ipv6_to_bytes(self.ipv6),
        ]

    @classmethod
    @limit_primitive_type(list)
    def from_primitive(
        cls: Type[SingleHostAddr], values: Union[list, tuple]
    ) -> SingleHostAddr:
        if values[0] == 0:
            return cls(
                port=values[1],
                ipv4=values[2],
                ipv6=values[3],
            )
        else:
            raise DeserializeException(f"Invalid SingleHostAddr type {values[0]}")


@dataclass(repr=False)
class SingleHostName(ArrayCBORSerializable):
    _CODE: int = field(init=False, default=1)

    port: Optional[int]
    dns_name: Optional[str]

    def __post_init__(self):
        self._CODE = 1

    @classmethod
    @limit_primitive_type(list)
    def from_primitive(
        cls: Type[SingleHostName], values: Union[list, tuple]
    ) -> SingleHostName:
        if values[0] == 1:
            return cls(
                port=values[1],
                dns_name=values[2],
            )
        else:
            raise DeserializeException(f"Invalid SingleHostName type {values[0]}")


@dataclass(repr=False)
class MultiHostName(ArrayCBORSerializable):
    _CODE: int = field(init=False, default=2)

    dns_name: Optional[str]

    def __post_init__(self):
        self._CODE = 2

    @classmethod
    @limit_primitive_type(list)
    def from_primitive(
        cls: Type[MultiHostName], values: Union[list, tuple]
    ) -> MultiHostName:
        if values[0] == 2:
            return cls(
                dns_name=values[1],
            )
        else:
            raise DeserializeException(f"Invalid MultiHostName type {values[0]}")


Relay = Union[SingleHostAddr, SingleHostName, MultiHostName]


@dataclass(repr=False)
class PoolMetadata(ArrayCBORSerializable):
    url: str
    pool_metadata_hash: PoolMetadataHash


def fraction_parser(fraction: Union[Fraction, str, list]) -> Fraction:
    if isinstance(fraction, Fraction):
        return Fraction(int(fraction.numerator), int(fraction.denominator))
    elif isinstance(fraction, str):
        numerator, denominator = fraction.split("/")
        return Fraction(int(numerator), int(denominator))
    elif isinstance(fraction, list):
        numerator, denominator = fraction[1]
        return Fraction(int(numerator), int(denominator))
    else:
        raise ValueError(f"Invalid fraction type {fraction}")


@dataclass(repr=False)
class PoolParams(ArrayCBORSerializable):
    operator: PoolKeyHash
    vrf_keyhash: VrfKeyHash
    pledge: int
    cost: int
    margin: Fraction = field(metadata={"object_hook": fraction_parser})
    reward_account: RewardAccountHash
    pool_owners: List[VerificationKeyHash]
    relays: Optional[List[Relay]] = None
    pool_metadata: Optional[PoolMetadata] = None
    id: Optional[PoolId] = field(default=None, metadata={"optional": True})
