from dataclasses import dataclass, field
from typing import Optional, Union, Type

from pycardano.exception import DeserializeException
from pycardano.hash import PoolKeyHash, ScriptHash, VerificationKeyHash
from pycardano.serialization import (
    ArrayCBORSerializable,
    ArrayBase,
    limit_primitive_type,
)

__all__ = [
    "Certificate",
    "StakeCredential",
    "StakeRegistration",
    "StakeDeregistration",
    "StakeDelegation",
]


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
    @limit_primitive_type(list, tuple)
    def from_primitive(
        cls: Type[ArrayBase], values: Union[list, tuple]
    ) -> "StakeCredential":
        if len(values) != 2:
            raise ValueError(f"Expected 2 values, got {len(values)}")
        if values[0] == 0:
            return StakeCredential(VerificationKeyHash.from_primitive(values[1]))
        elif values[0] == 1:
            return StakeCredential(ScriptHash.from_primitive(values[1]))
        else:
            raise ValueError(f"Unknown code: {values[0]}")


@dataclass(repr=False)
class StakeRegistration(ArrayCBORSerializable):
    _CODE: int = field(init=False, default=0)

    stake_credential: StakeCredential

    @classmethod
    @limit_primitive_type(list, tuple)
    def from_primitive(
        cls: Type[ArrayBase], values: Union[list, tuple]
    ) -> "StakeRegistration":
        if len(values) != 2:
            raise DeserializeException(f"Expected 2 values, got {len(values)}")
        if values[0] != 0:
            raise DeserializeException(f"Expected 0, got {values[0]}")
        return StakeRegistration(StakeCredential.from_primitive(values[1]))


@dataclass(repr=False)
class StakeDeregistration(ArrayCBORSerializable):
    _CODE: int = field(init=False, default=1)

    stake_credential: StakeCredential

    @classmethod
    @limit_primitive_type(list, tuple)
    def from_primitive(
        cls: Type[ArrayBase], values: Union[list, tuple]
    ) -> "StakeDeregistration":
        if len(values) != 2:
            raise DeserializeException(f"Expected 2 values, got {len(values)}")
        if values[0] != 1:
            raise DeserializeException(f"Expected 1, got {values[0]}")
        return StakeDeregistration(StakeCredential.from_primitive(values[1]))


@dataclass(repr=False)
class StakeDelegation(ArrayCBORSerializable):
    _CODE: int = field(init=False, default=2)

    stake_credential: StakeCredential

    pool_keyhash: PoolKeyHash

    @classmethod
    @limit_primitive_type(list, tuple)
    def from_primitive(
        cls: Type[ArrayBase], values: Union[list, tuple]
    ) -> "StakeDelegation":
        if len(values) != 3:
            raise DeserializeException(f"Expected 3 values, got {len(values)}")
        if values[0] != 2:
            raise DeserializeException(f"Expected 2, got {values[0]}")
        return StakeDelegation(
            StakeCredential.from_primitive(values[1]),
            PoolKeyHash.from_primitive(values[2]),
        )


Certificate = Union[StakeRegistration, StakeDeregistration, StakeDelegation]
