from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, unique
from typing import Optional, Tuple, Type, Union

from pycardano.crypto.bech32 import bech32_decode, convertbits, encode
from pycardano.exception import (
    DecodingException,
    DeserializeException,
    SerializeException,
)
from pycardano.hash import (
    CIP129_PAYLOAD_SIZE,
    VERIFICATION_KEY_HASH_SIZE,
    AnchorDataHash,
    PoolKeyHash,
    ScriptHash,
    VerificationKeyHash,
)
from pycardano.serialization import (
    ArrayCBORSerializable,
    CodedSerializable,
    limit_primitive_type,
)

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
    "DRepCredential",
    "RegDRepCert",
    "UnregDRepCertificate",
    "UpdateDRepCertificate",
    "GovernanceCredential",
    "GovernanceKeyType",
]

from pycardano.pool_params import PoolParams

unit_interval = Tuple[int, int]


@dataclass(repr=False)
class Anchor(ArrayCBORSerializable):
    """Represents an anchor in the Cardano blockchain that contains a URL and associated data hash.

    Anchors are used to provide additional metadata or reference external resources in certificates.
    """

    url: str
    """The URL pointing to the anchor's resource location"""

    data_hash: AnchorDataHash
    """The hash of the data associated with this anchor"""


@dataclass(repr=False)
class StakeCredential(ArrayCBORSerializable):
    """Represents a stake credential in the Cardano blockchain.

    A stake credential can either be a verification key hash or a script hash,
    used to identify stake rights and permissions.
    """

    _CODE: Optional[int] = field(init=False, default=None)

    credential: Union[VerificationKeyHash, ScriptHash]
    """The actual credential, either a verification key hash or script hash"""

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

    def __hash__(self):
        return hash(self.to_cbor())


class IdFormat(Enum):
    """
    Id format definition.
    """

    CIP129 = "cip129"
    CIP105 = "cip105"


class CredentialType(Enum):
    """
    Credential type definition.
    """

    KEY_HASH = 0b0010
    """Key hash"""

    SCRIPT_HASH = 0b0011
    """Script hash"""


class GovernanceKeyType(Enum):
    """
    Governance key type definition.
    """

    CC_HOT = 0b0000
    """Committee cold hot key"""

    CC_COLD = 0b0001
    """Committee cold key"""

    DREP = 0b0010
    """DRep key"""


@dataclass(repr=False)
class GovernanceCredential(StakeCredential):
    """Represents a governance credential."""

    governance_key_type: GovernanceKeyType = field(init=False)
    """Governance key type."""

    id_format: IdFormat = field(default=IdFormat.CIP129, compare=False)
    """Id format."""

    def __repr__(self):
        return f"{self.encode()}"

    def __bytes__(self):
        if self.id_format == IdFormat.CIP129:
            return self._compute_header_byte() + bytes(self.credential.payload)
        else:
            return bytes(self.credential.payload)

    @property
    def credential_type(self) -> CredentialType:
        """Credential type."""
        if isinstance(self.credential, VerificationKeyHash):
            return CredentialType.KEY_HASH
        else:
            return CredentialType.SCRIPT_HASH

    def _compute_header_byte(self) -> bytes:
        """Compute the header byte."""
        return (
            self.governance_key_type.value << 4 | self.credential_type.value
        ).to_bytes(1, byteorder="big")

    def _compute_hrp(self, id_format: IdFormat = IdFormat.CIP129) -> str:
        """Compute human-readable prefix for bech32 encoder.

        Based on
        `miscellaneous section <https://github.com/cardano-foundation/CIPs/tree/master/CIP-0005#miscellaneous>`_
        in CIP-5.
        """
        prefix = ""
        if self.governance_key_type == GovernanceKeyType.CC_HOT:
            prefix = "cc_hot"
        elif self.governance_key_type == GovernanceKeyType.CC_COLD:
            prefix = "cc_cold"
        elif self.governance_key_type == GovernanceKeyType.DREP:
            prefix = "drep"

        suffix = ""
        if isinstance(self.credential, VerificationKeyHash):
            suffix = ""
        elif isinstance(self.credential, ScriptHash):
            suffix = "_script"

        return prefix + suffix if id_format == IdFormat.CIP105 else prefix

    def encode(self) -> str:
        """Encode the governance credential in Bech32 format.

        More info about Bech32 `here <https://github.com/bitcoin/bips/blob/master/bip-0173.mediawiki#Bech32>`_.

        Returns:
            str: Encoded governance credential in Bech32 format.
        """
        data = bytes(self)
        return encode(self._compute_hrp(self.id_format), data)

    @classmethod
    def decode(cls: Type[GovernanceCredential], data: str) -> GovernanceCredential:
        """Decode a bech32 string into a governance credential object.

        Args:
            data (str): Bech32-encoded string.

        Returns:
            GovernanceCredential: Decoded governance credential.

        Raises:
            DecodingException: When the input string is not a valid governance credential.
        """
        hrp, checksum, _ = bech32_decode(data)
        value = bytes(convertbits(checksum, 5, 8, False))
        if len(value) == VERIFICATION_KEY_HASH_SIZE:
            # CIP-105
            if "script" in hrp:
                return cls(credential=ScriptHash(value))
            else:
                return cls(credential=VerificationKeyHash(value))
        elif len(value) == CIP129_PAYLOAD_SIZE:
            header = value[0]
            payload = value[1:]

            key_type = GovernanceKeyType((header & 0xF0) >> 4)
            credential_type = CredentialType(header & 0x0F)

            if key_type != cls.governance_key_type:
                raise DecodingException(f"Invalid key type: {key_type}")

            if credential_type == CredentialType.KEY_HASH:
                return cls(credential=VerificationKeyHash(payload))
            elif credential_type == CredentialType.SCRIPT_HASH:
                return cls(credential=ScriptHash(payload))
            else:
                raise DecodingException(f"Invalid credential type: {credential_type}")
        else:
            raise DecodingException(f"Invalid data length: {len(value)}")

    def to_primitive(self):
        return [self._CODE, self.credential.to_primitive()]


@dataclass(repr=False)
class DRepCredential(GovernanceCredential):
    """Represents a Delegate Representative (DRep) credential.

    This credential type is specifically used for DReps in the governance system,
    inheriting from GovernanceCredential.
    """

    governance_key_type: GovernanceKeyType = GovernanceKeyType.DREP


@unique
class DRepKind(Enum):
    """Enumerates the different types of Delegate Representatives (DReps).

    Defines the possible kinds of DReps in the Cardano governance system:
    - VERIFICATION_KEY_HASH: A DRep identified by a verification key hash
    - SCRIPT_HASH: A DRep identified by a script hash
    - ALWAYS_ABSTAIN: A special DRep that always abstains from voting
    - ALWAYS_NO_CONFIDENCE: A special DRep that always votes no confidence
    """

    VERIFICATION_KEY_HASH = 0
    SCRIPT_HASH = 1
    ALWAYS_ABSTAIN = 2
    ALWAYS_NO_CONFIDENCE = 3


@dataclass(repr=False)
class DRep(ArrayCBORSerializable):
    """Represents a Delegate Representative (DRep) in the Cardano governance system.

    DReps are entities that can represent stake holders in governance decisions.
    """

    kind: DRepKind
    """The type of DRep (verification key, script hash, always abstain, or always no confidence)"""

    credential: Optional[Union[VerificationKeyHash, ScriptHash]] = field(
        default=None, metadata={"optional": True}
    )
    """The credential associated with this DRep, if applicable"""

    id_format: IdFormat = field(default=IdFormat.CIP129, compare=False)

    def __repr__(self):
        return f"{self.encode()}"

    def __bytes__(self):
        if self.credential is not None:
            drep_credential = DRepCredential(
                credential=self.credential, id_format=self.id_format
            )
            return bytes(drep_credential)
        return b""

    @classmethod
    @limit_primitive_type(list)
    def from_primitive(cls: Type[DRep], values: Union[list, tuple]) -> DRep:
        try:
            kind = DRepKind(values[0])
        except ValueError as e:
            raise DeserializeException(f"Invalid DRep type {values[0]}") from e

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

    def encode(self) -> str:
        """Encode the DRep in Bech32 format.

        More info about Bech32 `here <https://github.com/bitcoin/bips/blob/master/bip-0173.mediawiki#Bech32>`_.

        Returns:
            str: Encoded DRep in Bech32 format.

        Examples:
            >>> vkey_bytes = bytes.fromhex("00000000000000000000000000000000000000000000000000000000")
            >>> credential = VerificationKeyHash(vkey_bytes)
            >>> print(DRep(kind=DRepKind.VERIFICATION_KEY_HASH, credential=credential).encode())
            drep1ygqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq7vlc9n
        """
        if self.kind == DRepKind.ALWAYS_ABSTAIN:
            return "drep_always_abstain"
        elif self.kind == DRepKind.ALWAYS_NO_CONFIDENCE:
            return "drep_always_no_confidence"
        elif self.credential is not None:
            drep_credential = DRepCredential(
                credential=self.credential, id_format=self.id_format
            )
            return drep_credential.encode()
        else:
            raise SerializeException("DRep credential is None")

    @classmethod
    def decode(cls: Type[DRep], data: str) -> DRep:
        """Decode a bech32 string into a DRep object.

        Args:
            data (str): Bech32-encoded string.

        Returns:
            DRep: Decoded DRep.

        Raises:
            DecodingException: When the input string is not a valid DRep.

        Examples:
            >>> credential = DRep.decode("drep1ygqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq7vlc9n")
            >>> khash = VerificationKeyHash(bytes.fromhex("00000000000000000000000000000000000000000000000000000000"))
            >>> assert credential == DRep(DRepKind.VERIFICATION_KEY_HASH, khash)
        """
        if data == "drep_always_abstain":
            return cls(kind=DRepKind.ALWAYS_ABSTAIN)
        elif data == "drep_always_no_confidence":
            return cls(kind=DRepKind.ALWAYS_NO_CONFIDENCE)
        else:
            drep_credential = DRepCredential.decode(data)
            return cls(
                kind=(
                    DRepKind.VERIFICATION_KEY_HASH
                    if isinstance(drep_credential.credential, VerificationKeyHash)
                    else DRepKind.SCRIPT_HASH
                ),
                credential=drep_credential.credential,
            )


@dataclass(repr=False)
class StakeRegistration(CodedSerializable):
    """Certificate for registering a stake credential."""

    _CODE: int = field(init=False, default=0)
    stake_credential: StakeCredential
    """The stake credential being registered"""


@dataclass(repr=False)
class StakeDeregistration(CodedSerializable):
    """Certificate for deregistering a stake credential."""

    _CODE: int = field(init=False, default=1)
    stake_credential: StakeCredential
    """The stake credential being deregistered"""


@dataclass(repr=False)
class StakeDelegation(CodedSerializable):
    """Certificate for delegating stake to a stake pool."""

    _CODE: int = field(init=False, default=2)
    stake_credential: StakeCredential
    """The stake credential being delegated"""

    pool_keyhash: PoolKeyHash
    """The hash of the pool's key to delegate to"""


@dataclass(repr=False)
class PoolRegistration(CodedSerializable):
    """Certificate for registering a stake pool."""

    _CODE: int = field(init=False, default=3)
    pool_params: PoolParams
    """The parameters defining the stake pool's configuration"""

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
class PoolRetirement(CodedSerializable):
    """Certificate for retiring a stake pool."""

    _CODE: int = field(init=False, default=4)
    pool_keyhash: PoolKeyHash
    """The hash of the pool's key that is being retired"""

    epoch: int
    """The epoch number when the pool will retire"""


@dataclass(repr=False)
class StakeRegistrationConway(CodedSerializable):
    """Certificate for registering a stake credential in the Conway era."""

    _CODE: int = field(init=False, default=7)
    stake_credential: StakeCredential
    """The stake credential being registered"""

    coin: int
    """The amount of coins associated with this registration"""


@dataclass(repr=False)
class StakeDeregistrationConway(CodedSerializable):
    """Certificate for deregistering a stake credential in the Conway era."""

    _CODE: int = field(init=False, default=8)
    stake_credential: StakeCredential
    """The stake credential being deregistered"""

    coin: int
    """The amount of coins associated with this deregistration"""


@dataclass(repr=False)
class VoteDelegation(CodedSerializable):
    """Certificate for delegating voting power to a DRep."""

    _CODE: int = field(init=False, default=9)
    stake_credential: StakeCredential
    """The stake credential delegating its voting power"""

    drep: DRep
    """The DRep receiving the voting power delegation"""


@dataclass(repr=False)
class StakeAndVoteDelegation(CodedSerializable):
    """Certificate for delegating both stake and voting power."""

    _CODE: int = field(init=False, default=10)
    stake_credential: StakeCredential
    """The stake credential being delegated"""

    pool_keyhash: PoolKeyHash
    """The hash of the pool's key receiving the stake delegation"""

    drep: DRep
    """The DRep receiving the voting power delegation"""


@dataclass(repr=False)
class StakeRegistrationAndDelegation(CodedSerializable):
    """Certificate for registering stake and delegating to a pool."""

    _CODE: int = field(init=False, default=11)
    stake_credential: StakeCredential
    """The stake credential being registered and delegated"""

    pool_keyhash: PoolKeyHash
    """The hash of the pool's key receiving the delegation"""

    coin: int
    """The amount of coins associated with this registration"""


@dataclass(repr=False)
class StakeRegistrationAndVoteDelegation(CodedSerializable):
    """Certificate for registering stake and delegating voting power."""

    _CODE: int = field(init=False, default=12)
    stake_credential: StakeCredential
    """The stake credential being registered"""

    drep: DRep
    """The DRep receiving the voting power delegation"""

    coin: int
    """The amount of coins associated with this registration"""


@dataclass(repr=False)
class StakeRegistrationAndDelegationAndVoteDelegation(CodedSerializable):
    """Certificate for registering stake and delegating both stake and voting power."""

    _CODE: int = field(init=False, default=13)
    stake_credential: StakeCredential
    """The stake credential being registered and delegated"""

    pool_keyhash: PoolKeyHash
    """The hash of the pool's key receiving the stake delegation"""

    drep: DRep
    """The DRep receiving the voting power delegation"""

    coin: int
    """The amount of coins associated with this registration"""


@dataclass(repr=False)
class AuthCommitteeHotCertificate(CodedSerializable):
    """Certificate for authorizing a committee hot key."""

    _CODE: int = field(init=False, default=14)
    committee_cold_credential: StakeCredential
    """The cold credential of the committee member"""

    committee_hot_credential: StakeCredential
    """The hot credential being authorized"""


@dataclass(repr=False)
class ResignCommitteeColdCertificate(CodedSerializable):
    """Certificate for resigning from the constitutional committee."""

    _CODE: int = field(init=False, default=15)
    committee_cold_credential: StakeCredential
    """The cold credential of the resigning committee member"""

    anchor: Optional[Anchor]
    """Optional anchor containing additional metadata about the resignation"""


@dataclass(repr=False)
class RegDRepCert(CodedSerializable):
    """Certificate for registering as a delegate representative (DRep)."""

    _CODE: int = field(init=False, default=16)
    drep_credential: DRepCredential
    """The credential of the DRep being registered"""

    coin: int
    """The amount of coins associated with this registration"""

    anchor: Optional[Anchor] = field(default=None)
    """Optional anchor containing additional metadata about the DRep"""


@dataclass(repr=False)
class UnregDRepCertificate(CodedSerializable):
    """Certificate for unregistering as a delegate representative (DRep)."""

    _CODE: int = field(init=False, default=17)
    drep_credential: DRepCredential
    """The credential of the DRep being unregistered"""

    coin: int
    """The amount of coins associated with this unregistration"""


@dataclass(repr=False)
class UpdateDRepCertificate(CodedSerializable):
    """Certificate for updating delegate representative (DRep) metadata."""

    _CODE: int = field(init=False, default=18)
    drep_credential: DRepCredential
    """The credential of the DRep being updated"""

    anchor: Optional[Anchor]
    """Optional anchor containing the updated metadata"""


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
    UnregDRepCertificate,
    UpdateDRepCertificate,
]
