from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, unique
from fractions import Fraction
from typing import Dict, Optional, Tuple, Type, Union

from pycardano.certificate import Anchor, GovernanceCredential, GovernanceKeyType
from pycardano.crypto.bech32 import bech32_decode, convertbits, encode
from pycardano.exception import (
    DecodingException,
    DeserializeException,
    InvalidDataException,
)
from pycardano.hash import PolicyHash, ScriptHash, TransactionId, VerificationKeyHash
from pycardano.plutus import ExecutionUnits
from pycardano.serialization import (
    ArrayCBORSerializable,
    CodedSerializable,
    DictCBORSerializable,
    MapCBORSerializable,
    OrderedSet,
    Primitive,
    limit_primitive_type,
)

__all__ = [
    "CommitteeColdCredential",
    "CommitteeHotCredential",
    "CommitteeColdCredentialEpochMap",
    "ParameterChangeAction",
    "HardForkInitiationAction",
    "TreasuryWithdrawalsAction",
    "NoConfidence",
    "UpdateCommittee",
    "NewConstitution",
    "InfoAction",
    "GovActionId",
    "VotingProcedure",
    "VotingProcedures",
    "VoterType",
    "Voter",
    "GovAction",
    "Vote",
    "Anchor",
    "GovActionIdToVotingProcedure",
    "ProposalProcedure",
    "ProtocolParamUpdate",
    "ExUnitPrices",
    "DRepVotingThresholds",
    "TreasuryWithdrawal",
    "PoolVotingThresholds",
]


class CommitteeColdCredential(GovernanceCredential):
    """Represents a cold credential for a committee member."""

    governance_key_type: GovernanceKeyType = GovernanceKeyType.CC_COLD


class CommitteeHotCredential(GovernanceCredential):
    """Represents a hot credential for a committee member."""

    governance_key_type: GovernanceKeyType = GovernanceKeyType.CC_HOT


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
    @limit_primitive_type(list, tuple)
    def from_primitive(
        cls: Type[GovActionId], values: Union[list, tuple]
    ) -> GovActionId:
        return cls(transaction_id=TransactionId(values[0]), gov_action_index=values[1])

    def __hash__(self):
        return hash((self.transaction_id, self.gov_action_index))

    def __repr__(self):
        return f"{self.encode()}"

    def __bytes__(self):
        # Convert index to hex (no prefix, lowercase)
        idx_hex = f"{self.gov_action_index:x}"

        # Pad to even-length hex
        if len(idx_hex) % 2 != 0:
            idx_hex = f"0{idx_hex}"

        try:
            idx_bytes = bytes.fromhex(idx_hex)
            return self.transaction_id.payload + idx_bytes
        except ValueError as e:
            raise InvalidDataException(f"Error encoding data: {idx_hex}") from e

    def encode(self) -> str:
        """Encode the governance action ID in Bech32 format.

        More info about Bech32 `here <https://github.com/bitcoin/bips/blob/master/bip-0173.mediawiki#Bech32>`_.

        Returns:
            str: Encoded pool key hash in Bech32.

        Examples:
            >>> transaction_id = TransactionId(bytes.fromhex("00" * 32))
            >>> gov_action_id = GovActionId(transaction_id=transaction_id, gov_action_index=17)
            >>> print(gov_action_id.encode())
            gov_action1qqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqpzklpgpf
        """
        return encode(
            "gov_action",
            bytes(self),
        )

    @classmethod
    def decode(cls, data: str) -> GovActionId:
        """Decode a bech32 string into a governance action ID object.

        Args:
            data (str): Bech32-encoded string.

        Returns:
            GovActionId: Decoded governance action ID.

        Raises:
            DecodingException: When the input string is not a valid governance action ID.

        Examples:
            >>> bech32_id = "gov_action1qqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqpzklpgpf"
            >>> gov_action_id = GovActionId.decode(bech32_id)
            >>> transaction_id = TransactionId(bytes.fromhex("00" * 32))
            >>> assert gov_action_id == GovActionId(transaction_id, 17)
        """
        hrp, checksum, _ = bech32_decode(data)
        value = bytes(convertbits(checksum, 5, 8, False))

        if hrp != "gov_action":
            raise DecodingException("Invalid GovActionId bech32 string")

        # Transaction ID is always 32 bytes, the rest is the index
        if len(value) < 33:
            raise DecodingException(
                f"Invalid GovActionId length: {len(value)}, expected at least 33 bytes"
            )

        tx_id = TransactionId(value[:32])
        index_bytes = value[32:]
        index = int.from_bytes(index_bytes, "big")
        return cls(transaction_id=tx_id, gov_action_index=index)


@dataclass(repr=False)
class ExUnitPrices(ArrayCBORSerializable):
    """Represents execution unit prices for memory and CPU steps."""

    mem_price: Fraction
    """Memory price as a nonnegative interval (numerator, denominator)"""

    step_price: Fraction
    """Step price as a nonnegative interval (numerator, denominator)"""


@dataclass(repr=False)
class DRepVotingThresholds(ArrayCBORSerializable):
    """Represents DRep voting thresholds as an array of unit intervals."""

    motion_no_confidence: Fraction
    """Threshold for no confidence motions"""

    committee_normal: Fraction
    """Threshold for normal committee updates"""

    committee_no_confidence: Fraction
    """Threshold for committee updates during no confidence"""

    update_constitution: Fraction
    """Threshold for constitution updates"""

    hard_fork_initiation: Fraction
    """Threshold for hard fork initiation"""

    pp_network_group: Fraction
    """Threshold for network group protocol parameter updates"""

    pp_economic_group: Fraction
    """Threshold for economic group protocol parameter updates"""

    pp_technical_group: Fraction
    """Threshold for technical group protocol parameter updates"""

    pp_governance_group: Fraction
    """Threshold for governance group protocol parameter updates"""

    treasury_withdrawal: Fraction
    """Threshold for treasury withdrawals"""


@dataclass(repr=False)
class PoolVotingThresholds(ArrayCBORSerializable):
    """Represents pool voting thresholds as an array of unit intervals."""

    motion_no_confidence: Fraction
    """Threshold for no confidence motions"""

    committee_normal: Fraction
    """Threshold for normal committee updates"""

    committee_no_confidence: Fraction
    """Threshold for committee updates during no confidence"""

    hard_fork_initiation: Fraction
    """Threshold for hard fork initiation"""

    ppec_voting_threshold: Fraction
    """Threshold for protocol parameter and economic group voting"""


@dataclass(repr=False)
class ProtocolParamUpdate(MapCBORSerializable):
    """Represents a protocol parameter update."""

    min_fee_a: Optional[int] = field(
        default=None, metadata={"key": 0, "optional": True}
    )
    """The 'a' parameter to calculate the minimum fee"""

    min_fee_b: Optional[int] = field(
        default=None, metadata={"key": 1, "optional": True}
    )
    """The 'b' parameter to calculate the minimum fee"""

    max_block_body_size: Optional[int] = field(
        default=None, metadata={"key": 2, "optional": True}
    )
    """Maximum block body size"""

    max_transaction_size: Optional[int] = field(
        default=None, metadata={"key": 3, "optional": True}
    )
    """Maximum transaction size"""

    max_block_header_size: Optional[int] = field(
        default=None, metadata={"key": 4, "optional": True}
    )
    """Maximum block header size"""

    key_deposit: Optional[int] = field(
        default=None, metadata={"key": 5, "optional": True}
    )
    """The deposit required for registering a stake key"""

    pool_deposit: Optional[int] = field(
        default=None, metadata={"key": 6, "optional": True}
    )
    """The deposit required for registering a stake pool"""

    maximum_epoch: Optional[int] = field(
        default=None, metadata={"key": 7, "optional": True}
    )
    """Maximum epoch interval (uint32)"""

    n_opt: Optional[int] = field(default=None, metadata={"key": 8, "optional": True})
    """Desired number of stake pools"""

    pool_pledge_influence: Optional[Fraction] = field(
        default=None, metadata={"key": 9, "optional": True}
    )
    """Pool pledge influence as a nonnegative interval (numerator, denominator)"""

    expansion_rate: Optional[Fraction] = field(
        default=None, metadata={"key": 10, "optional": True}
    )
    """Monetary expansion rate as a unit interval (numerator, denominator)"""

    treasury_growth_rate: Optional[Fraction] = field(
        default=None, metadata={"key": 11, "optional": True}
    )
    """Treasury growth rate as a unit interval (numerator, denominator)"""

    min_pool_cost: Optional[int] = field(
        default=None, metadata={"key": 16, "optional": True}
    )
    """Minimum pool cost"""

    ada_per_utxo_byte: Optional[int] = field(
        default=None, metadata={"key": 17, "optional": True}
    )
    """Ada per UTxO byte"""

    cost_models: Optional[Dict] = field(
        default=None, metadata={"key": 18, "optional": True}
    )
    """Cost models for script languages"""

    execution_costs: Optional[ExUnitPrices] = field(
        default=None, metadata={"key": 19, "optional": True}
    )
    """Execution costs (prices) for ex units"""

    max_tx_ex_units: Optional[ExecutionUnits] = field(
        default=None, metadata={"key": 20, "optional": True}
    )
    """Maximum execution units per transaction"""

    max_block_ex_units: Optional[ExecutionUnits] = field(
        default=None, metadata={"key": 21, "optional": True}
    )
    """Maximum execution units per block"""

    max_value_size: Optional[int] = field(
        default=None, metadata={"key": 22, "optional": True}
    )
    """Maximum value size"""

    collateral_percentage: Optional[int] = field(
        default=None, metadata={"key": 23, "optional": True}
    )
    """Collateral percentage"""

    max_collateral_inputs: Optional[int] = field(
        default=None, metadata={"key": 24, "optional": True}
    )
    """Maximum number of collateral inputs"""

    pool_voting_thresholds: Optional[PoolVotingThresholds] = field(
        default=None, metadata={"key": 25, "optional": True}
    )
    """Pool voting thresholds"""

    drep_voting_thresholds: Optional[DRepVotingThresholds] = field(
        default=None, metadata={"key": 26, "optional": True}
    )
    """DRep voting thresholds"""

    min_committee_size: Optional[int] = field(
        default=None, metadata={"key": 27, "optional": True}
    )
    """Minimum committee size"""

    committee_term_limit: Optional[int] = field(
        default=None, metadata={"key": 28, "optional": True}
    )
    """Committee term limit in epochs (uint32)"""

    governance_action_validity_period: Optional[int] = field(
        default=None, metadata={"key": 29, "optional": True}
    )
    """Governance action validity period in epochs (uint32)"""

    governance_action_deposit: Optional[int] = field(
        default=None, metadata={"key": 30, "optional": True}
    )
    """Deposit required for governance actions"""

    drep_deposit: Optional[int] = field(
        default=None, metadata={"key": 31, "optional": True}
    )
    """Deposit required for DRep registration"""

    drep_inactivity_period: Optional[int] = field(
        default=None, metadata={"key": 32, "optional": True}
    )
    """DRep inactivity period in epochs (uint32)"""

    min_fee_ref_script_cost: Optional[Fraction] = field(
        default=None, metadata={"key": 33, "optional": True}
    )
    """Minimum fee for reference scripts as a nonnegative interval (numerator, denominator)"""


@dataclass(repr=False)
class ParameterChangeAction(CodedSerializable):
    """Represents a governance action to change protocol parameters."""

    _CODE: int = field(init=False, default=0)
    gov_action_id: Optional[GovActionId]
    """Optional reference to a previous governance action"""

    protocol_param_update: ProtocolParamUpdate
    """Dictionary containing the protocol parameters to be updated"""

    policy_hash: Optional[PolicyHash]
    """Optional policy hash associated with this parameter change"""


@dataclass(repr=False)
class HardForkInitiationAction(CodedSerializable):
    """Represents a governance action to initiate a hard fork."""

    _CODE: int = field(init=False, default=1)
    gov_action_id: Optional[GovActionId]
    """Optional reference to a previous governance action"""

    protocol_version: Fraction
    """The target protocol version as (major, minor) version numbers"""

    def __post_init__(self):
        major, minor = self.protocol_version
        if not 1 <= major <= 10:
            raise ValueError("Major protocol version must be between 1 and 10")


class TreasuryWithdrawal(DictCBORSerializable):
    """Represents a treasury withdrawal amount and destination."""

    KEY_TYPE = bytes

    VALUE_TYPE = int


@dataclass(repr=False)
class TreasuryWithdrawalsAction(CodedSerializable):
    """Represents a governance action to withdraw funds from the treasury."""

    _CODE: int = field(init=False, default=2)
    withdrawals: TreasuryWithdrawal
    """The withdrawal amounts and their destinations"""

    policy_hash: Optional[PolicyHash]
    """Optional policy hash associated with these withdrawals"""


@dataclass(repr=False)
class NoConfidence(CodedSerializable):
    """Represents a governance action expressing no confidence."""

    _CODE: int = field(init=False, default=3)
    gov_action_id: Optional[GovActionId]
    """Optional reference to a previous governance action"""


class CommitteeColdCredentialEpochMap(DictCBORSerializable):
    """Represents a mapping of committee members to their expiration epochs."""

    KEY_TYPE = CommitteeColdCredential
    VALUE_TYPE = int


@dataclass(repr=False)
class UpdateCommittee(CodedSerializable):
    """Represents a governance action to update the constitutional committee."""

    _CODE: int = field(init=False, default=4)
    gov_action_id: Optional[GovActionId]
    """Optional reference to a previous governance action"""

    committee_cold_credentials: OrderedSet[CommitteeColdCredential]
    """Set of cold credentials for committee members"""

    committee_expiration: CommitteeColdCredentialEpochMap
    """Mapping of committee members to their expiration epochs"""

    quorum: Fraction  # unit_interval
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

    def to_shallow_primitive(self) -> Primitive:
        return [self.vote.value, self.anchor]


@unique
class VoterType(Enum):
    """Represents the possible types of voters in the governance system."""

    COMMITTEE_HOT = "committee_hot"
    DREP = "drep"
    STAKING_POOL = "staking_pool"


@dataclass(repr=False)
class Voter(ArrayCBORSerializable):
    """Represents a voter in the governance system.

    Voters can be committee members, DReps, or stake pool operators.
    """

    _CODE: Optional[int] = field(init=False, default=None)

    credential: Union[VerificationKeyHash, ScriptHash]
    """The credential identifying the voter"""

    voter_type: VoterType
    """The type of voter (COMMITTEE_HOT, DREP, or STAKING_POOL)"""

    def __post_init__(self):
        if self.voter_type == VoterType.COMMITTEE_HOT:
            if isinstance(self.credential, VerificationKeyHash):
                self._CODE = 0
            else:
                self._CODE = 1
        elif self.voter_type == VoterType.DREP:
            if isinstance(self.credential, VerificationKeyHash):
                self._CODE = 2
            else:
                self._CODE = 3
        elif self.voter_type == VoterType.STAKING_POOL:
            if not isinstance(self.credential, VerificationKeyHash):
                raise ValueError("Staking pool voter must use key hash credential")
            self._CODE = 4
        else:
            raise ValueError("Invalid voter_type")

    def to_shallow_primitive(self) -> Primitive:
        return self._CODE, self.credential

    @classmethod
    @limit_primitive_type(list, tuple)
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
            0: VoterType.COMMITTEE_HOT,
            1: VoterType.COMMITTEE_HOT,
            2: VoterType.DREP,
            3: VoterType.DREP,
            4: VoterType.STAKING_POOL,
        }[code]

        return cls(credential=credential, voter_type=voter_type)

    def __hash__(self):
        return hash((self._CODE, self.credential))


class GovActionIdToVotingProcedure(DictCBORSerializable):
    """Represents a mapping of governance action IDs to their voting procedures."""

    KEY_TYPE = GovActionId
    VALUE_TYPE = VotingProcedure


class VotingProcedures(DictCBORSerializable):
    """Represents a mapping of voters to their voting procedures."""

    KEY_TYPE = Voter
    VALUE_TYPE = GovActionIdToVotingProcedure


GovAction = Union[
    ParameterChangeAction,
    HardForkInitiationAction,
    TreasuryWithdrawalsAction,
    NoConfidence,
    UpdateCommittee,
    NewConstitution,
    InfoAction,
]


@dataclass(repr=False)
class ProposalProcedure(ArrayCBORSerializable):
    """Represents a proposal procedure for governance actions."""

    deposit: int
    """The deposit required to submit a proposal"""

    reward_account: bytes
    """The reward account for the proposal"""

    gov_action: GovAction
    """The governance actions to be proposed"""

    anchor: Anchor
    """The metadata anchor for the proposal"""
