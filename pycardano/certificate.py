from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, unique
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
    "StakeRegistrationConway",
    "StakeDeregistrationConway",
    "VoteDelegation",
    "StakeAndVoteDelegation",
    "StakeRegistrationAndDelegation",
    "StakeRegistrationAndVoteDelegation",
    "StakeRegistrationAndDelegationAndVoteDelegation",
    "DRep",
    "DRepKind",
    "AuthCommitteeHotCertificate",
    "ResignCommitteeColdCertificate",
    "Anchor",
    "DrepCredential",
    "UnregDrepCertificate",
    "UpdateDrepCertificate",
]

from pycardano.pool_params import PoolParams

unit_interval = Tuple[int, int]


@dataclass(repr=False)
class Anchor(ArrayCBORSerializable):
    url: str
    data_hash: bytes

    @classmethod
    @limit_primitive_type(list)
    def from_primitive(cls: Type[Anchor], values: Union[list, tuple]) -> Anchor:
        return cls(url=values[0], data_hash=values[1])


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
    @limit_primitive_type(list, tuple)
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
    @limit_primitive_type(list, tuple)
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
    @limit_primitive_type(list, tuple)
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
    @limit_primitive_type(list, tuple)
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
    @limit_primitive_type(list, tuple)
    def from_primitive(
        cls: Type[PoolRetirement], values: Union[list, tuple]
    ) -> PoolRetirement:
        if values[0] == 4:
            return cls(
                pool_keyhash=PoolKeyHash.from_primitive(values[1]), epoch=values[2]
            )
        else:
            raise DeserializeException(f"Invalid PoolRetirement type {values[0]}")


@dataclass(repr=False)
class StakeRegistrationConway(ArrayCBORSerializable):
    _CODE: int = field(init=False, default=7)

    stake_credential: StakeCredential
    coin: int

    def __post_init__(self):
        self._CODE = 7

    @classmethod
    @limit_primitive_type(list)
    def from_primitive(
        cls: Type[StakeRegistrationConway], values: Union[list, tuple]
    ) -> StakeRegistrationConway:
        if values[0] == 7:
            return cls(
                stake_credential=StakeCredential.from_primitive(values[1]),
                coin=values[2],
            )
        else:
            raise DeserializeException(
                f"Invalid StakeRegistrationConway type {values[0]}"
            )


@dataclass(repr=False)
class StakeDeregistrationConway(ArrayCBORSerializable):
    _CODE: int = field(init=False, default=8)

    stake_credential: StakeCredential
    coin: int

    def __post_init__(self):
        self._CODE = 8

    @classmethod
    @limit_primitive_type(list)
    def from_primitive(
        cls: Type[StakeDeregistrationConway], values: Union[list, tuple]
    ) -> StakeDeregistrationConway:
        if values[0] == 8:
            return cls(
                stake_credential=StakeCredential.from_primitive(values[1]),
                coin=values[2],
            )
        else:
            raise DeserializeException(
                f"Invalid StakeDeregistrationConway type {values[0]}"
            )


@dataclass(repr=False)
class VoteDelegation(ArrayCBORSerializable):
    _CODE: int = field(init=False, default=9)

    stake_credential: StakeCredential
    drep: DRep

    def __post_init__(self):
        self._CODE = 9

    @classmethod
    @limit_primitive_type(list)
    def from_primitive(
        cls: Type[VoteDelegation], values: Union[list, tuple]
    ) -> VoteDelegation:
        if values[0] == 9:
            return cls(
                stake_credential=StakeCredential.from_primitive(values[1]),
                drep=DRep.from_primitive(values[2]),
            )
        else:
            raise DeserializeException(f"Invalid VoteDelegation type {values[0]}")


@dataclass(repr=False)
class StakeAndVoteDelegation(ArrayCBORSerializable):
    _CODE: int = field(init=False, default=10)

    stake_credential: StakeCredential
    pool_keyhash: PoolKeyHash
    drep: DRep

    def __post_init__(self):
        self._CODE = 10

    @classmethod
    @limit_primitive_type(list)
    def from_primitive(
        cls: Type[StakeAndVoteDelegation], values: Union[list, tuple]
    ) -> StakeAndVoteDelegation:
        if values[0] == 10:
            return cls(
                stake_credential=StakeCredential.from_primitive(values[1]),
                pool_keyhash=PoolKeyHash.from_primitive(values[2]),
                drep=DRep.from_primitive(values[3]),
            )
        else:
            raise DeserializeException(
                f"Invalid StakeAndVoteDelegation type {values[0]}"
            )


@dataclass(repr=False)
class StakeRegistrationAndDelegation(ArrayCBORSerializable):
    _CODE: int = field(init=False, default=11)

    stake_credential: StakeCredential
    pool_keyhash: PoolKeyHash
    coin: int

    def __post_init__(self):
        self._CODE = 11

    @classmethod
    @limit_primitive_type(list)
    def from_primitive(
        cls: Type[StakeRegistrationAndDelegation], values: Union[list, tuple]
    ) -> StakeRegistrationAndDelegation:
        if values[0] == 11:
            return cls(
                stake_credential=StakeCredential.from_primitive(values[1]),
                pool_keyhash=PoolKeyHash.from_primitive(values[2]),
                coin=values[3],
            )
        else:
            raise DeserializeException(f"Invalid {cls.__name__} type {values[0]}")


@dataclass(repr=False)
class StakeRegistrationAndVoteDelegation(ArrayCBORSerializable):
    _CODE: int = field(init=False, default=12)

    stake_credential: StakeCredential
    drep: DRep
    coin: int

    def __post_init__(self):
        self._CODE = 12

    @classmethod
    @limit_primitive_type(list)
    def from_primitive(
        cls: Type[StakeRegistrationAndVoteDelegation], values: Union[list, tuple]
    ) -> StakeRegistrationAndVoteDelegation:
        if values[0] == 12:
            return cls(
                stake_credential=StakeCredential.from_primitive(values[1]),
                drep=DRep.from_primitive(values[2]),
                coin=values[3],
            )
        else:
            raise DeserializeException(f"Invalid {cls.__name__} type {values[0]}")


@dataclass(repr=False)
class StakeRegistrationAndDelegationAndVoteDelegation(ArrayCBORSerializable):
    _CODE: int = field(init=False, default=13)

    stake_credential: StakeCredential
    pool_keyhash: PoolKeyHash
    drep: DRep
    coin: int

    def __post_init__(self):
        self._CODE = 13

    @classmethod
    @limit_primitive_type(list)
    def from_primitive(
        cls: Type[StakeRegistrationAndDelegationAndVoteDelegation],
        values: Union[list, tuple],
    ) -> StakeRegistrationAndDelegationAndVoteDelegation:
        if values[0] == 13:
            return cls(
                stake_credential=StakeCredential.from_primitive(values[1]),
                pool_keyhash=PoolKeyHash.from_primitive(values[2]),
                drep=DRep.from_primitive(values[3]),
                coin=values[4],
            )
        else:
            raise DeserializeException(f"Invalid {cls.__name__} type {values[0]}")


@unique
class DRepKind(Enum):
    VERIFICATION_KEY_HASH = 0
    SCRIPT_HASH = 1
    ALWAYS_ABSTAIN = 2
    ALWAYS_NO_CONFIDENCE = 3


@dataclass(repr=False)
class DRep(ArrayCBORSerializable):
    kind: DRepKind
    credential: Optional[Union[VerificationKeyHash, ScriptHash]] = field(
        default=None, metadata={"optional": True}
    )

    @classmethod
    @limit_primitive_type(list)
    def from_primitive(cls: Type[DRep], values: Union[list, tuple]) -> DRep:
        try:
            kind = DRepKind(values[0])
        except ValueError:
            raise DeserializeException(f"Invalid DRep type {values[0]}")

        if kind == DRepKind.VERIFICATION_KEY_HASH:
            return cls(kind=kind, credential=VerificationKeyHash(values[1]))
        elif kind == DRepKind.SCRIPT_HASH:
            return cls(kind=kind, credential=ScriptHash(values[1]))
        elif kind == DRepKind.ALWAYS_ABSTAIN:
            return cls(kind=kind)
        elif kind == DRepKind.ALWAYS_NO_CONFIDENCE:
            return cls(kind=kind)
        else:
            raise DeserializeException(f"Invalid DRep type {values[0]}")

    def to_primitive(self):
        if self.credential is not None:
            return [self.kind.value, self.credential.to_primitive()]
        return [self.kind.value]


@dataclass(repr=False)
class AuthCommitteeHotCertificate(ArrayCBORSerializable):
    _CODE: int = field(init=False, default=14)

    committee_cold_credential: StakeCredential
    committee_hot_credential: StakeCredential

    def __post_init__(self):
        self._CODE = 14

    @classmethod
    @limit_primitive_type(list)
    def from_primitive(
        cls: Type[AuthCommitteeHotCertificate], values: Union[list, tuple]
    ) -> AuthCommitteeHotCertificate:
        if values[0] == 14:
            return cls(
                committee_cold_credential=StakeCredential.from_primitive(values[1]),
                committee_hot_credential=StakeCredential.from_primitive(values[2]),
            )
        else:
            raise DeserializeException(
                f"Invalid AuthCommitteeHotCertificate type {values[0]}"
            )


@dataclass(repr=False)
class ResignCommitteeColdCertificate(ArrayCBORSerializable):
    _CODE: int = field(init=False, default=15)

    committee_cold_credential: StakeCredential
    anchor: Optional[Anchor]

    def __post_init__(self):
        self._CODE = 15

    @classmethod
    @limit_primitive_type(list)
    def from_primitive(
        cls: Type[ResignCommitteeColdCertificate], values: Union[list, tuple]
    ) -> ResignCommitteeColdCertificate:
        if values[0] == 15:
            return cls(
                committee_cold_credential=StakeCredential.from_primitive(values[1]),
                anchor=(
                    Anchor.from_primitive(values[2]) if values[2] is not None else None
                ),
            )
        else:
            raise DeserializeException(
                f"Invalid ResignCommitteeColdCertificate type {values[0]}"
            )


@dataclass(repr=False)
class DrepCredential(ArrayCBORSerializable):
    """DRep credential is identical to StakeCredential in structure."""

    _CODE: int = field(init=False, default=16)

    drep_credential: StakeCredential
    coin: int
    anchor: Optional[Anchor] = field(default=None)

    def __post_init__(self):
        self._CODE = 16

    @classmethod
    @limit_primitive_type(list)
    def from_primitive(
        cls: Type[DrepCredential], values: Union[list, tuple]
    ) -> DrepCredential:
        if values[0] == 16:
            return cls(
                drep_credential=StakeCredential.from_primitive(values[1]),
                coin=values[2],
                anchor=(
                    Anchor.from_primitive(values[3]) if values[3] is not None else None
                ),
            )
        else:
            raise DeserializeException(f"Invalid DrepCredential type {values[0]}")


@dataclass(repr=False)
class UnregDrepCertificate(ArrayCBORSerializable):
    _CODE: int = field(init=False, default=17)

    drep_credential: DrepCredential
    coin: int

    def __post_init__(self):
        self._CODE = 17

    @classmethod
    @limit_primitive_type(list)
    def from_primitive(
        cls: Type[UnregDrepCertificate], values: Union[list, tuple]
    ) -> UnregDrepCertificate:
        if values[0] == 17:
            return cls(
                drep_credential=DrepCredential.from_primitive(values[1]),
                coin=values[2],
            )
        else:
            raise DeserializeException(f"Invalid UnregDrepCertificate type {values[0]}")


@dataclass(repr=False)
class UpdateDrepCertificate(ArrayCBORSerializable):
    _CODE: int = field(init=False, default=18)

    drep_credential: DrepCredential
    anchor: Optional[Anchor]

    def __post_init__(self):
        self._CODE = 18

    @classmethod
    @limit_primitive_type(list)
    def from_primitive(
        cls: Type[UpdateDrepCertificate], values: Union[list, tuple]
    ) -> UpdateDrepCertificate:
        if values[0] == 18:
            return cls(
                drep_credential=DrepCredential.from_primitive(values[1]),
                anchor=(
                    Anchor.from_primitive(values[2]) if values[2] is not None else None
                ),
            )
        else:
            raise DeserializeException(
                f"Invalid UpdateDrepCertificate type {values[0]}"
            )


Certificate = Union[
    StakeRegistration,
    StakeDeregistration,
    StakeDelegation,
    PoolRegistration,
    PoolRetirement,
    StakeRegistrationConway,
    StakeDeregistrationConway,
    VoteDelegation,
    StakeAndVoteDelegation,
    StakeRegistrationAndDelegation,
    StakeRegistrationAndVoteDelegation,
    StakeRegistrationAndDelegationAndVoteDelegation,
    AuthCommitteeHotCertificate,
    ResignCommitteeColdCertificate,
    UnregDrepCertificate,
    UpdateDrepCertificate,
]
