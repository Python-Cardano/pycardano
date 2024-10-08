from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Tuple, Type, Union

from pycardano.exception import DeserializeException
from pycardano.hash import PoolKeyHash, ScriptHash, VerificationKeyHash
from pycardano.serialization import ArrayCBORSerializable, limit_primitive_type

__all__ = [
    "Certificate",
    "StakeCredential",
    "StakeRegistration",
    "StakeDeregistration",
    "StakeDelegation",
    "PoolRegistration",
    "PoolRetirement",
]

from pycardano.pool_params import PoolParams

unit_interval = Tuple[int, int]


@dataclass(repr=False)
class StakeCredential(ArrayCBORSerializable):
    _CODE: Optional[int] = field(init=False, default=None)

    credential: Union[VerificationKeyHash, ScriptHash]

    def __post_init__(self):
        if isinstance(self.credential, VerificationKeyHash):
            self._CODE = 0
        else:
            self._CODE = 1

    @classmethod
    @limit_primitive_type(list)
    def from_primitive(
        cls: Type[StakeCredential], values: Union[list, tuple]
    ) -> StakeCredential:
        if values[0] == 0:
            return cls(VerificationKeyHash(values[1]))
        elif values[0] == 1:
            return cls(ScriptHash(values[1]))
        else:
            raise DeserializeException(f"Invalid StakeCredential type {values[0]}")


@dataclass(repr=False)
class StakeRegistration(ArrayCBORSerializable):
    _CODE: int = field(init=False, default=0)

    stake_credential: StakeCredential

    def __post_init__(self):
        self._CODE = 0

    @classmethod
    @limit_primitive_type(list)
    def from_primitive(
        cls: Type[StakeRegistration], values: Union[list, tuple]
    ) -> StakeRegistration:
        if values[0] == 0:
            return cls(stake_credential=StakeCredential.from_primitive(values[1]))
        else:
            raise DeserializeException(f"Invalid StakeRegistration type {values[0]}")


@dataclass(repr=False)
class StakeDeregistration(ArrayCBORSerializable):
    _CODE: int = field(init=False, default=1)

    stake_credential: StakeCredential

    def __post_init__(self):
        self._CODE = 1

    @classmethod
    @limit_primitive_type(list)
    def from_primitive(
        cls: Type[StakeDeregistration], values: Union[list, tuple]
    ) -> StakeDeregistration:
        if values[0] == 1:
            return cls(StakeCredential.from_primitive(values[1]))
        else:
            raise DeserializeException(f"Invalid StakeDeregistration type {values[0]}")


@dataclass(repr=False)
class StakeDelegation(ArrayCBORSerializable):
    _CODE: int = field(init=False, default=2)

    stake_credential: StakeCredential

    pool_keyhash: PoolKeyHash

    def __post_init__(self):
        self._CODE = 2

    @classmethod
    @limit_primitive_type(list)
    def from_primitive(
        cls: Type[StakeDelegation], values: Union[list, tuple]
    ) -> StakeDelegation:
        if values[0] == 2:
            return cls(
                stake_credential=StakeCredential.from_primitive(values[1]),
                pool_keyhash=PoolKeyHash.from_primitive(values[2]),
            )
        else:
            raise DeserializeException(f"Invalid StakeDelegation type {values[0]}")


@dataclass(repr=False)
class PoolRegistration(ArrayCBORSerializable):
    _CODE: int = field(init=False, default=3)

    pool_params: PoolParams

    def __post_init__(self):
        self._CODE = 3

    def to_primitive(self):
        pool_params = self.pool_params.to_primitive()
        if isinstance(pool_params, list):
            return [self._CODE, *pool_params]
        return super().to_primitive()

    @classmethod
    @limit_primitive_type(list)
    def from_primitive(
        cls: Type[PoolRegistration], values: Union[list, tuple]
    ) -> PoolRegistration:
        if values[0] == 3:
            if isinstance(values[1], list):
                return cls(
                    pool_params=PoolParams.from_primitive(values[1]),
                )
            else:
                return cls(
                    pool_params=PoolParams.from_primitive(values[1:]),
                )
        else:
            raise DeserializeException(f"Invalid PoolRegistration type {values[0]}")


@dataclass(repr=False)
class PoolRetirement(ArrayCBORSerializable):
    _CODE: int = field(init=False, default=4)

    pool_keyhash: PoolKeyHash
    epoch: int

    def __post_init__(self):
        self._CODE = 4

    @classmethod
    @limit_primitive_type(list)
    def from_primitive(
        cls: Type[PoolRetirement], values: Union[list, tuple]
    ) -> PoolRetirement:
        if values[0] == 4:
            return cls(
                pool_keyhash=PoolKeyHash.from_primitive(values[1]), epoch=values[2]
            )
        else:
            raise DeserializeException(f"Invalid PoolRetirement type {values[0]}")


Certificate = Union[
    StakeRegistration,
    StakeDeregistration,
    StakeDelegation,
    PoolRegistration,
    PoolRetirement,
]
