from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, unique
from typing import Dict, Optional, Set, Tuple, Type, Union

from pycardano.certificate import Anchor, StakeCredential
from pycardano.exception import DeserializeException
from pycardano.hash import PolicyHash, ScriptHash, TransactionId, VerificationKeyHash
from pycardano.serialization import (
    ArrayCBORSerializable,
    CodedSerializable,
    limit_primitive_type,
)
from pycardano.transaction import Withdrawals

__all__ = [
    "ParameterChangeAction",
    "HardForkInitiationAction",
    "TreasuryWithdrawalsAction",
    "NoConfidence",
    "UpdateCommittee",
    "NewConstitution",
    "InfoAction",
    "GovActionId",
    "VotingProcedure",
    "Voter",
    "GovAction",
    "Vote",
]


@unique
class Vote(Enum):
    """Represents possible voting choices in the governance system."""

    NO = 0
    YES = 1
    ABSTAIN = 2


@dataclass(repr=False)
class GovActionId(ArrayCBORSerializable):
    """Represents a unique identifier for a governance action.

    This identifier consists of a transaction ID and an index within that transaction.
    """

    transaction_id: TransactionId
    """The transaction ID where this governance action was submitted"""

    gov_action_index: int
    """The index of this governance action within the transaction (0-65535)"""

    def __post_init__(self):
        if not 0 <= self.gov_action_index <= 65535:  # uint .size 2
            raise ValueError("gov_action_index must be between 0 and 65535")

    @classmethod
    @limit_primitive_type(list)
    def from_primitive(
        cls: Type[GovActionId], values: Union[list, tuple]
    ) -> GovActionId:
        return cls(transaction_id=TransactionId(values[0]), gov_action_index=values[1])


@dataclass(repr=False)
class ParameterChangeAction(CodedSerializable):
    """Represents a governance action to change protocol parameters."""

    _CODE: int = field(init=False, default=0)
    gov_action_id: Optional[GovActionId]
    """Optional reference to a previous governance action"""

    protocol_param_update: Dict
    """Dictionary containing the protocol parameters to be updated"""

    policy_hash: Optional[PolicyHash]
    """Optional policy hash associated with this parameter change"""


@dataclass(repr=False)
class HardForkInitiationAction(CodedSerializable):
    """Represents a governance action to initiate a hard fork."""

    _CODE: int = field(init=False, default=1)
    gov_action_id: Optional[GovActionId]
    """Optional reference to a previous governance action"""

    protocol_version: Tuple[int, int]
    """The target protocol version as (major, minor) version numbers"""

    def __post_init__(self):
        major, minor = self.protocol_version
        if not 1 <= major <= 10:
            raise ValueError("Major protocol version must be between 1 and 10")


@dataclass(repr=False)
class TreasuryWithdrawalsAction(CodedSerializable):
    """Represents a governance action to withdraw funds from the treasury."""

    _CODE: int = field(init=False, default=2)
    withdrawals: Withdrawals
    """The withdrawal amounts and their destinations"""

    policy_hash: Optional[PolicyHash]
    """Optional policy hash associated with these withdrawals"""


@dataclass(repr=False)
class NoConfidence(CodedSerializable):
    """Represents a governance action expressing no confidence."""

    _CODE: int = field(init=False, default=3)
    gov_action_id: Optional[GovActionId]
    """Optional reference to a previous governance action"""


@dataclass(repr=False)
class UpdateCommittee(CodedSerializable):
    """Represents a governance action to update the constitutional committee."""

    _CODE: int = field(init=False, default=4)
    gov_action_id: Optional[GovActionId]
    """Optional reference to a previous governance action"""

    committee_cold_credentials: Set[
        StakeCredential
    ]  # TODO: Define CommitteeColdCredential
    """Set of cold credentials for committee members"""

    committee_expiration: Dict[StakeCredential, int]  # credential -> epoch_no
    """Mapping of committee members to their expiration epochs"""

    quorum: Tuple[int, int]  # unit_interval
    """The quorum threshold as a unit interval (numerator, denominator)"""


@dataclass(repr=False)
class NewConstitution(CodedSerializable):
    """Represents a governance action to establish a new constitution."""

    _CODE: int = field(init=False, default=5)
    gov_action_id: Optional[GovActionId]
    """Optional reference to a previous governance action"""

    constitution: Tuple[Anchor, Optional[ScriptHash]]
    """The constitution data as (anchor, optional script hash)"""


@dataclass(repr=False)
class InfoAction(CodedSerializable):
    """Represents an informational governance action with no direct effect."""

    _CODE: int = field(init=False, default=6)


@dataclass(repr=False)
class VotingProcedure(ArrayCBORSerializable):
    """Represents a voting procedure for governance actions.

    This defines how voting is conducted for a specific governance action.
    """

    vote: Vote
    """The vote cast (YES, NO, or ABSTAIN)"""

    anchor: Optional[Anchor]
    """Optional metadata associated with this vote"""

    @classmethod
    @limit_primitive_type(list)
    def from_primitive(
        cls: Type[VotingProcedure], values: Union[list, tuple]
    ) -> VotingProcedure:
        return cls(
            vote=Vote(values[0]),
            anchor=Anchor.from_primitive(values[1]) if values[1] is not None else None,
        )


@dataclass(repr=False)
class Voter(ArrayCBORSerializable):
    """Represents a voter in the governance system.

    Voters can be committee members, DReps, or stake pool operators.
    """

    _CODE: Optional[int] = field(init=False, default=None)

    credential: Union[VerificationKeyHash, ScriptHash]
    """The credential identifying the voter"""

    voter_type: str
    """The type of voter ('committee_hot', 'drep', or 'staking_pool')"""

    def __post_init__(self):
        if self.voter_type == "committee_hot":
            if isinstance(self.credential, VerificationKeyHash):
                self._CODE = 0
            else:
                self._CODE = 1
        elif self.voter_type == "drep":
            if isinstance(self.credential, VerificationKeyHash):
                self._CODE = 2
            else:
                self._CODE = 3
        elif self.voter_type == "staking_pool":
            if not isinstance(self.credential, VerificationKeyHash):
                raise ValueError("Staking pool voter must use key hash credential")
            self._CODE = 4
        else:
            raise ValueError("Invalid voter_type")

    @classmethod
    @limit_primitive_type(list)
    def from_primitive(cls: Type[Voter], values: Union[list, tuple]) -> Voter:
        code = values[0]
        credential: Union[VerificationKeyHash, ScriptHash]
        if code in (0, 2, 4):
            credential = VerificationKeyHash(values[1])
        elif code in (1, 3):
            credential = ScriptHash(values[1])
        else:
            raise DeserializeException(f"Invalid Voter type {code}")

        voter_type = {
            0: "committee_hot",
            1: "committee_hot",
            2: "drep",
            3: "drep",
            4: "staking_pool",
        }[code]

        return cls(credential=credential, voter_type=voter_type)


# Define the GovAction type union
GovAction = Union[
    ParameterChangeAction,
    HardForkInitiationAction,
    TreasuryWithdrawalsAction,
    NoConfidence,
    UpdateCommittee,
    NewConstitution,
    InfoAction,
]
