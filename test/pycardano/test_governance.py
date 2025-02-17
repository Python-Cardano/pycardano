from fractions import Fraction

import pytest

from pycardano.address import Address
from pycardano.certificate import Anchor, StakeCredential
from pycardano.exception import DeserializeException
from pycardano.governance import (
    CommitteeColdCredential,
    CommitteeColdCredentialEpochMap,
    ExUnitPrices,
    GovActionId,
    GovActionIdToVotingProcedure,
    HardForkInitiationAction,
    InfoAction,
    NewConstitution,
    NoConfidence,
    ParameterChangeAction,
    ProposalProcedure,
    TreasuryWithdrawal,
    TreasuryWithdrawalsAction,
    UpdateCommittee,
    Vote,
    Voter,
    VoterType,
    VotingProcedure,
    VotingProcedures,
)
from pycardano.hash import (
    ANCHOR_DATA_HASH_SIZE,
    SCRIPT_HASH_SIZE,
    TRANSACTION_HASH_SIZE,
    VERIFICATION_KEY_HASH_SIZE,
    AnchorDataHash,
    PolicyHash,
    ScriptHash,
    TransactionId,
    VerificationKeyHash,
)


class TestGovActionId:
    def test_gov_action_id_creation(self):
        tx_id = TransactionId(bytes.fromhex("00" * TRANSACTION_HASH_SIZE))
        gov_action_id = GovActionId(transaction_id=tx_id, gov_action_index=123)

        assert gov_action_id.transaction_id == tx_id
        assert gov_action_id.gov_action_index == 123

    def test_gov_action_id_invalid_index(self):
        tx_id = TransactionId(bytes.fromhex("00" * TRANSACTION_HASH_SIZE))

        with pytest.raises(
            ValueError, match="gov_action_index must be between 0 and 65535"
        ):
            GovActionId(transaction_id=tx_id, gov_action_index=70000)

        with pytest.raises(
            ValueError, match="gov_action_index must be between 0 and 65535"
        ):
            GovActionId(transaction_id=tx_id, gov_action_index=-1)

    def test_gov_action_id_serialization(self):
        tx_id = TransactionId(bytes.fromhex("00" * TRANSACTION_HASH_SIZE))
        gov_action_id = GovActionId(transaction_id=tx_id, gov_action_index=123)

        primitive = gov_action_id.to_primitive()
        deserialized = GovActionId.from_primitive(primitive)

        assert deserialized == gov_action_id


class TestVote:
    def test_vote_values(self):
        assert Vote.NO.value == 0
        assert Vote.YES.value == 1
        assert Vote.ABSTAIN.value == 2


class TestVotingProcedure:
    def test_voting_procedure_creation(self):
        anchor = Anchor(
            url="https://example.com",
            data_hash=AnchorDataHash(bytes.fromhex("00" * ANCHOR_DATA_HASH_SIZE)),
        )
        procedure = VotingProcedure(vote=Vote.YES, anchor=anchor)

        assert procedure.vote == Vote.YES
        assert procedure.anchor == anchor

    def test_voting_procedure_no_anchor(self):
        procedure = VotingProcedure(vote=Vote.NO, anchor=None)

        assert procedure.vote == Vote.NO
        assert procedure.anchor is None

    def test_voting_procedure_serialization(self):
        anchor = Anchor(
            url="https://example.com",
            data_hash=AnchorDataHash(bytes.fromhex("00" * ANCHOR_DATA_HASH_SIZE)),
        )
        procedure = VotingProcedure(vote=Vote.YES, anchor=anchor)

        primitive = procedure.to_primitive()
        deserialized = VotingProcedure.from_primitive(primitive)

        assert deserialized == procedure


class TestVoterType:
    def test_voter_type_values(self):
        assert VoterType.COMMITTEE_HOT.value == "committee_hot"
        assert VoterType.DREP.value == "drep"
        assert VoterType.STAKING_POOL.value == "staking_pool"


class TestVoter:
    def test_committee_hot_voter_creation(self):
        vkey_hash = VerificationKeyHash(
            bytes.fromhex("00" * VERIFICATION_KEY_HASH_SIZE)
        )
        voter = Voter(credential=vkey_hash, voter_type=VoterType.COMMITTEE_HOT)

        assert voter._CODE == 0
        assert voter.credential == vkey_hash
        assert voter.voter_type == VoterType.COMMITTEE_HOT

    def test_committee_hot_script_voter_creation(self):
        script_hash = ScriptHash(bytes.fromhex("11" * SCRIPT_HASH_SIZE))
        voter = Voter(credential=script_hash, voter_type=VoterType.COMMITTEE_HOT)

        assert voter._CODE == 1
        assert voter.credential == script_hash
        assert voter.voter_type == VoterType.COMMITTEE_HOT

    def test_drep_key_voter_creation(self):
        vkey_hash = VerificationKeyHash(
            bytes.fromhex("22" * VERIFICATION_KEY_HASH_SIZE)
        )
        voter = Voter(credential=vkey_hash, voter_type=VoterType.DREP)

        assert voter._CODE == 2
        assert voter.credential == vkey_hash
        assert voter.voter_type == VoterType.DREP

    def test_drep_script_voter_creation(self):
        script_hash = ScriptHash(bytes.fromhex("33" * SCRIPT_HASH_SIZE))
        voter = Voter(credential=script_hash, voter_type=VoterType.DREP)

        assert voter._CODE == 3
        assert voter.credential == script_hash
        assert voter.voter_type == VoterType.DREP

    def test_staking_pool_voter_creation(self):
        vkey_hash = VerificationKeyHash(
            bytes.fromhex("44" * VERIFICATION_KEY_HASH_SIZE)
        )
        voter = Voter(credential=vkey_hash, voter_type=VoterType.STAKING_POOL)

        assert voter._CODE == 4
        assert voter.credential == vkey_hash
        assert voter.voter_type == VoterType.STAKING_POOL

    def test_invalid_voter_type(self):
        vkey_hash = VerificationKeyHash(
            bytes.fromhex("00" * VERIFICATION_KEY_HASH_SIZE)
        )
        with pytest.raises(ValueError, match="Invalid voter_type"):
            Voter(credential=vkey_hash, voter_type="invalid_type")

    def test_invalid_staking_pool_credential(self):
        script_hash = ScriptHash(bytes.fromhex("11" * SCRIPT_HASH_SIZE))
        with pytest.raises(
            ValueError, match="Staking pool voter must use key hash credential"
        ):
            Voter(credential=script_hash, voter_type=VoterType.STAKING_POOL)

    def test_voter_serialization_committee_hot_key(self):
        vkey_hash = VerificationKeyHash(
            bytes.fromhex("00" * VERIFICATION_KEY_HASH_SIZE)
        )
        voter = Voter(credential=vkey_hash, voter_type=VoterType.COMMITTEE_HOT)

        primitive = voter.to_primitive()
        deserialized = Voter.from_primitive(primitive)

        assert deserialized._CODE == voter._CODE
        assert deserialized.credential == voter.credential
        assert deserialized.voter_type == voter.voter_type

    def test_voter_serialization_committee_hot_script(self):
        script_hash = ScriptHash(bytes.fromhex("11" * SCRIPT_HASH_SIZE))
        voter = Voter(credential=script_hash, voter_type=VoterType.COMMITTEE_HOT)

        primitive = voter.to_primitive()
        deserialized = Voter.from_primitive(primitive)

        assert deserialized._CODE == voter._CODE
        assert deserialized.credential == voter.credential
        assert deserialized.voter_type == voter.voter_type

    def test_voter_serialization_drep_key(self):
        vkey_hash = VerificationKeyHash(
            bytes.fromhex("22" * VERIFICATION_KEY_HASH_SIZE)
        )
        voter = Voter(credential=vkey_hash, voter_type=VoterType.DREP)

        primitive = voter.to_primitive()
        deserialized = Voter.from_primitive(primitive)

        assert deserialized._CODE == voter._CODE
        assert deserialized.credential == voter.credential
        assert deserialized.voter_type == voter.voter_type

    def test_voter_serialization_drep_script(self):
        script_hash = ScriptHash(bytes.fromhex("33" * SCRIPT_HASH_SIZE))
        voter = Voter(credential=script_hash, voter_type=VoterType.DREP)

        primitive = voter.to_primitive()
        deserialized = Voter.from_primitive(primitive)

        assert deserialized._CODE == voter._CODE
        assert deserialized.credential == voter.credential
        assert deserialized.voter_type == voter.voter_type

    def test_voter_serialization_staking_pool(self):
        vkey_hash = VerificationKeyHash(
            bytes.fromhex("44" * VERIFICATION_KEY_HASH_SIZE)
        )
        voter = Voter(credential=vkey_hash, voter_type=VoterType.STAKING_POOL)

        primitive = voter.to_primitive()
        deserialized = Voter.from_primitive(primitive)

        assert deserialized._CODE == voter._CODE
        assert deserialized.credential == voter.credential
        assert deserialized.voter_type == voter.voter_type

    def test_voter_invalid_deserialization_code(self):
        invalid_primitive = [5, bytes.fromhex("00" * VERIFICATION_KEY_HASH_SIZE)]
        with pytest.raises(DeserializeException, match="Invalid Voter type 5"):
            Voter.from_primitive(invalid_primitive)

    def test_voter_invalid_primitive_format(self):
        with pytest.raises(
            Exception
        ):  # Specific exception type depends on implementation
            Voter.from_primitive([])  # Empty list

        with pytest.raises(Exception):
            Voter.from_primitive([0])  # Missing credential

        with pytest.raises(Exception):
            Voter.from_primitive([0, "invalid"])  # Invalid credential format


class TestParameterChangeAction:
    def test_parameter_change_action_creation(self):
        tx_id = TransactionId(bytes.fromhex("00" * TRANSACTION_HASH_SIZE))
        gov_action_id = GovActionId(transaction_id=tx_id, gov_action_index=1)
        protocol_params = {"key": "value"}
        policy_hash = PolicyHash(bytes.fromhex("33" * SCRIPT_HASH_SIZE))

        action = ParameterChangeAction(
            gov_action_id=gov_action_id,
            protocol_param_update=protocol_params,
            policy_hash=policy_hash,
        )

        assert action._CODE == 0
        assert action.gov_action_id == gov_action_id
        assert action.protocol_param_update == protocol_params
        assert action.policy_hash == policy_hash


class TestHardForkInitiationAction:
    def test_hard_fork_action_creation(self):
        tx_id = TransactionId(bytes.fromhex("00" * TRANSACTION_HASH_SIZE))
        gov_action_id = GovActionId(transaction_id=tx_id, gov_action_index=1)

        action = HardForkInitiationAction(
            gov_action_id=gov_action_id, protocol_version=(8, 0)
        )

        assert action._CODE == 1
        assert action.gov_action_id == gov_action_id
        assert action.protocol_version == (8, 0)

    def test_invalid_protocol_version(self):
        tx_id = TransactionId(bytes.fromhex("00" * TRANSACTION_HASH_SIZE))
        gov_action_id = GovActionId(transaction_id=tx_id, gov_action_index=1)

        with pytest.raises(
            ValueError, match="Major protocol version must be between 1 and 10"
        ):
            HardForkInitiationAction(
                gov_action_id=gov_action_id, protocol_version=(11, 0)
            )


class TestUpdateCommittee:
    def test_update_committee_creation(self):
        tx_id = TransactionId(bytes.fromhex("00" * TRANSACTION_HASH_SIZE))
        gov_action_id = GovActionId(transaction_id=tx_id, gov_action_index=1)

        credential1 = StakeCredential(
            VerificationKeyHash(bytes.fromhex("44" * VERIFICATION_KEY_HASH_SIZE))
        )
        credential2 = StakeCredential(
            VerificationKeyHash(bytes.fromhex("55" * VERIFICATION_KEY_HASH_SIZE))
        )

        committee_credentials = {credential1, credential2}
        committee_expiration = {credential1: 100, credential2: 200}

        action = UpdateCommittee(
            gov_action_id=gov_action_id,
            committee_cold_credentials=committee_credentials,
            committee_expiration=committee_expiration,
            quorum=(2, 3),
        )

        assert action._CODE == 4
        assert action.gov_action_id == gov_action_id
        assert action.committee_cold_credentials == committee_credentials
        assert action.committee_expiration == committee_expiration
        assert action.quorum == (2, 3)


class TestNewConstitution:
    def test_new_constitution_creation(self):
        tx_id = TransactionId(bytes.fromhex("00" * TRANSACTION_HASH_SIZE))
        gov_action_id = GovActionId(transaction_id=tx_id, gov_action_index=1)

        anchor = Anchor(
            url="https://example.com/constitution",
            data_hash=AnchorDataHash(bytes.fromhex("66" * ANCHOR_DATA_HASH_SIZE)),
        )
        script_hash = ScriptHash(bytes.fromhex("77" * SCRIPT_HASH_SIZE))

        action = NewConstitution(
            gov_action_id=gov_action_id, constitution=(anchor, script_hash)
        )

        assert action._CODE == 5
        assert action.gov_action_id == gov_action_id
        assert action.constitution == (anchor, script_hash)


class TestInfoAction:
    def test_info_action_creation(self):
        action = InfoAction()
        assert action._CODE == 6


class TestExUnitPrices:
    def test_ex_unit_prices_creation(self):
        prices = ExUnitPrices(mem_price=Fraction(1, 2), step_price=Fraction(3, 4))
        assert prices.mem_price == Fraction(1, 2)
        assert prices.step_price == Fraction(3, 4)

    def test_ex_unit_prices_serialization(self):
        prices = ExUnitPrices(mem_price=Fraction(1, 2), step_price=Fraction(3, 4))
        primitive = prices.to_primitive()
        # The primitive should be a list of two tuples
        assert isinstance(primitive, list)
        assert len(primitive) == 2
        assert primitive[0] == Fraction(1, 2)  # Tuples are serialized as lists
        assert primitive[1] == Fraction(3, 4)

        deserialized = ExUnitPrices.from_cbor(prices.to_cbor())
        assert deserialized.mem_price == prices.mem_price
        assert deserialized.step_price == prices.step_price


class TestTreasuryWithdrawal:
    def test_treasury_withdrawal_creation(self):
        withdrawals = TreasuryWithdrawal()
        withdrawals[b"addr1"] = 1000
        withdrawals[b"addr2"] = 2000

        assert withdrawals[b"addr1"] == 1000
        assert withdrawals[b"addr2"] == 2000

    def test_treasury_withdrawal_serialization(self):
        withdrawals = TreasuryWithdrawal()
        withdrawals[b"addr1"] = 1000
        withdrawals[b"addr2"] = 2000

        primitive = withdrawals.to_primitive()
        deserialized = TreasuryWithdrawal.from_primitive(primitive)
        assert deserialized == withdrawals


class TestTreasuryWithdrawalsAction:
    def test_treasury_withdrawals_action_creation(self):
        withdrawals = TreasuryWithdrawal()
        withdrawals[b"addr1"] = 1000
        policy_hash = PolicyHash(bytes.fromhex("00" * SCRIPT_HASH_SIZE))

        action = TreasuryWithdrawalsAction(
            withdrawals=withdrawals, policy_hash=policy_hash
        )

        assert action._CODE == 2
        assert action.withdrawals == withdrawals
        assert action.policy_hash == policy_hash

    def test_treasury_withdrawals_action_no_policy(self):
        withdrawals = TreasuryWithdrawal()
        withdrawals[b"addr1"] = 1000

        action = TreasuryWithdrawalsAction(withdrawals=withdrawals, policy_hash=None)

        assert action._CODE == 2
        assert action.withdrawals == withdrawals
        assert action.policy_hash is None


class TestVotingProcedures:
    def test_voting_procedures_creation(self):
        # Create a voter
        vkey_hash = VerificationKeyHash(
            bytes.fromhex("00" * VERIFICATION_KEY_HASH_SIZE)
        )
        voter = Voter(credential=vkey_hash, voter_type=VoterType.COMMITTEE_HOT)

        # Create a GovActionId
        tx_id = TransactionId(bytes.fromhex("00" * TRANSACTION_HASH_SIZE))
        gov_action_id = GovActionId(transaction_id=tx_id, gov_action_index=1)

        # Create a VotingProcedure
        anchor = Anchor(
            url="https://example.com",
            data_hash=AnchorDataHash(bytes.fromhex("00" * ANCHOR_DATA_HASH_SIZE)),
        )
        procedure = VotingProcedure(vote=Vote.YES, anchor=anchor)

        # Create GovActionIdToVotingProcedure
        gov_to_voting = GovActionIdToVotingProcedure()
        gov_to_voting[gov_action_id] = procedure

        # Create VotingProcedures
        procedures = VotingProcedures()
        procedures[voter] = gov_to_voting

        assert procedures[voter][gov_action_id] == procedure

    def test_voting_procedures_serialization(self):
        # Create test data
        vkey_hash = VerificationKeyHash(
            bytes.fromhex("00" * VERIFICATION_KEY_HASH_SIZE)
        )
        voter = Voter(credential=vkey_hash, voter_type=VoterType.COMMITTEE_HOT)

        tx_id = TransactionId(bytes.fromhex("00" * TRANSACTION_HASH_SIZE))
        gov_action_id = GovActionId(transaction_id=tx_id, gov_action_index=1)

        procedure = VotingProcedure(vote=Vote.YES, anchor=None)

        voting_procedures = VotingProcedures()
        voting_procedures[voter] = GovActionIdToVotingProcedure(
            {gov_action_id: procedure}
        )

        # Test deserialization
        deserialized = VotingProcedures.from_cbor(voting_procedures.to_cbor())

        # Verify the structure was preserved
        assert isinstance(deserialized, VotingProcedures)
        assert len(deserialized) == 1

        # Get the first (and only) key-value pair
        deserialized_voter = next(iter(deserialized.keys()))
        deserialized_gov_to_voting = deserialized[deserialized_voter]

        assert isinstance(deserialized_gov_to_voting, GovActionIdToVotingProcedure)
        assert len(deserialized_gov_to_voting) == 1

        # Get the first (and only) key-value pair from the nested map
        deserialized_gov_action_id = next(iter(deserialized_gov_to_voting.keys()))
        deserialized_procedure = deserialized_gov_to_voting[deserialized_gov_action_id]

        # Verify the contents
        assert deserialized_voter == voter
        assert deserialized_gov_action_id == gov_action_id
        assert deserialized_procedure == procedure


class TestProposalProcedure:
    def test_proposal_procedure_creation(self):
        # Create an InfoAction as it's the simplest GovAction
        gov_action = InfoAction()

        anchor = Anchor(
            url="https://example.com",
            data_hash=AnchorDataHash(bytes.fromhex("00" * ANCHOR_DATA_HASH_SIZE)),
        )

        procedure = ProposalProcedure(
            deposit=1000000,
            reward_account=b"reward_account",
            gov_action=gov_action,
            anchor=anchor,
        )

        assert procedure.deposit == 1000000
        assert procedure.reward_account == b"reward_account"
        assert procedure.gov_action == gov_action
        assert procedure.anchor == anchor

    def test_proposal_procedure_serialization(self):
        gov_action = InfoAction()
        anchor = Anchor(
            url="https://example.com",
            data_hash=AnchorDataHash(bytes.fromhex("00" * ANCHOR_DATA_HASH_SIZE)),
        )

        procedure = ProposalProcedure(
            deposit=1000000,
            reward_account=b"reward_account",
            gov_action=gov_action,
            anchor=anchor,
        )

        primitive = procedure.to_primitive()
        deserialized = ProposalProcedure.from_primitive(primitive)

        assert deserialized.deposit == procedure.deposit
        assert deserialized.reward_account == procedure.reward_account
        assert deserialized.anchor == procedure.anchor
