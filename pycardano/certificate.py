from dataclasses import dataclass, field
from typing import Union

from pycardano.hash import PoolKeyHash, ScriptHash, VerificationKeyHash
from pycardano.serialization import ArrayCBORSerializable

__all__ = [
    "Certificate",
    "StakeCredential",
    "StakeRegistration",
    "StakeDeregistration",
    "StakeDelegation",
]


@dataclass(repr=False)
class StakeCredential(ArrayCBORSerializable):

    _CODE: int = field(init=False, default=None)

    credential: Union[VerificationKeyHash, ScriptHash]

    def __post_init__(self):
        if isinstance(self.credential, VerificationKeyHash):
            self._CODE = 0
        else:
            self._CODE = 1


@dataclass(repr=False)
class StakeRegistration(ArrayCBORSerializable):

    _CODE: int = field(init=False, default=0)

    stake_credential: StakeCredential


@dataclass(repr=False)
class StakeDeregistration(ArrayCBORSerializable):

    _CODE: int = field(init=False, default=1)

    stake_credential: StakeCredential


@dataclass(repr=False)
class StakeDelegation(ArrayCBORSerializable):

    _CODE: int = field(init=False, default=2)

    stake_credential: StakeCredential

    pool_keyhash: PoolKeyHash


Certificate = Union[StakeRegistration, StakeDeregistration, StakeDelegation]
