from __future__ import annotations

import fractions
import re
from dataclasses import dataclass, field
from typing import Optional, Union, List, Type

from pycardano.hash import (
    PoolKeyHash,
    VerificationKeyHash,
    VrfKeyHash,
    PoolMetadataHash,
    RewardAccountHash,
)
from pycardano.serialization import (
    CBORSerializable,
    ArrayCBORSerializable,
    limit_primitive_type,
    list_hook,
)


def is_bech32_cardano_pool_id(s: str) -> bool:
    """Check if a string is a valid Cardano stake pool ID in bech32 format."""
    # Regex for Cardano bech32 stake pool ID format with the correct HRP "pool1"
    # pattern = r'^pool1[02-9ac-hj-np-z]{57}$'
    pattern = r"^pool1[02-9ac-hj-np-z]+$"
    return re.match(pattern, s) is not None


@dataclass(frozen=True)
class PoolId(CBORSerializable):
    value: str

    def __post_init__(self):
        if not is_bech32_cardano_pool_id(self.value):
            raise ValueError(
                "Invalid PoolId format. The PoolId should be a valid Cardano stake pool ID in bech32 format."
            )

        if not self.value.startswith("pool1") and len(self.value) != 56:
            raise ValueError("The pool id bech32 is not valid!")

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
class Fraction(CBORSerializable):
    numerator: int
    denominator: int

    def __str__(self):
        return f"{self.numerator}/{self.denominator}"

    def __repr__(self):
        return f"Fraction({self.numerator}, {self.denominator})"

    def to_primitive(self) -> str:
        return f"{self.numerator}/{self.denominator}"

    @classmethod
    @limit_primitive_type(fractions.Fraction, str)
    def from_primitive(
        cls: Type[Fraction], fraction: Union[fractions.Fraction, str]
    ) -> Fraction:
        if isinstance(fraction, fractions.Fraction):
            return cls(int(fraction.numerator), int(fraction.denominator))
        elif isinstance(fraction, str):
            numerator, denominator = fraction.split("/")
            return cls(int(numerator), int(denominator))


@dataclass(repr=False)
class SingleHostAddr(ArrayCBORSerializable):
    _CODE: int = field(init=False, default=0)

    port: Optional[int]
    ipv4: Optional[bytes]
    ipv6: Optional[bytes]

    def __post_init__(self):
        self._CODE = 0

    @classmethod
    @limit_primitive_type(list)
    def from_primitive(
        cls: Type[SingleHostAddr], values: Union[list, tuple]
    ) -> SingleHostAddr:
        return cls(
            port=values[1],
            ipv4=values[2],
            ipv6=values[3],
        )


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
        return cls(
            port=values[1],
            dns_name=values[2],
        )


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
        return cls(
            dns_name=values[1],
        )


Relay = Union[SingleHostAddr, SingleHostName, MultiHostName]


@dataclass(repr=False)
class PoolMetadata(ArrayCBORSerializable):
    url: str
    pool_metadata_hash: PoolMetadataHash


@dataclass(repr=False)
class RelayCBORSerializer(ArrayCBORSerializable):
    # relay: Relay

    @classmethod
    @limit_primitive_type(list)
    def from_primitive(cls: Type[Relay], values: Union[list, tuple]) -> Relay:
        if values[0] == 0:
            return SingleHostAddr.from_primitive(values)
        elif values[0] == 1:
            return SingleHostName.from_primitive(values)
        elif values[0] == 2:
            return MultiHostName.from_primitive(values)


@dataclass(repr=False)
class PoolParams(ArrayCBORSerializable):
    operator: PoolKeyHash
    vrf_keyhash: VrfKeyHash
    pledge: int
    cost: int
    margin: Fraction
    reward_account: RewardAccountHash
    pool_owners: List[VerificationKeyHash]
    relays: Optional[List[Relay]] = field(
        default=None,
        metadata={"optional": True, "object_hook": list_hook(RelayCBORSerializer)},
    )
    pool_metadata: Optional[PoolMetadata] = None
    id: Optional[PoolId] = field(default=None, metadata={"optional": True})

    # @classmethod
    # @limit_primitive_type(list)
    # def from_primitive(cls: Type[PoolParams], values: Union[list, tuple]) -> PoolParams:
    #     return cls(
    #         operator=PoolKeyHash.from_primitive(values[1]),
    #         vrf_keyhash=VrfKeyHash.from_primitive(values[2]),
    #         pledge=values[3],
    #         cost=values[4],
    #         margin=Fraction.from_primitive(fractions.Fraction(values[5][0], values[5][1])),
    #         reward_account=RewardAccountHash.from_primitive(values[6]),
    #         pool_owners=[VerificationKeyHash.from_primitive(value) for value in values[7]],
    #         relays=[RelayCBORSerializer.from_primitive(value) for value in values[8]],
    #         pool_metadata=PoolMetadata.from_primitive(values[9]),
    #         id=PoolId.from_primitive(values[10]),
    #     )
