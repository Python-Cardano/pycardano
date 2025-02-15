import pytest

from pycardano.address import Address
from pycardano.exception import DeserializeException
from pycardano.governance import TreasuryWithdrawalsAction
from pycardano.hash import PolicyHash
from pycardano.key import VerificationKeyHash
from pycardano.transaction import Withdrawals


class TestTreasuryWithdrawalsAction:
    @pytest.fixture
    def sample_reward_address(self):
        # Create a sample reward address using a verification key hash
        vkey_hash = VerificationKeyHash(bytes.fromhex("00" * 28))
        return bytes(Address(staking_part=vkey_hash))

    @pytest.fixture
    def sample_withdrawals(self, sample_reward_address):
        # Create a sample withdrawals dictionary
        return Withdrawals({sample_reward_address: 1000000})

    @pytest.fixture
    def sample_policy_hash(self):
        # Create a sample policy hash
        return PolicyHash(bytes.fromhex("11" * 28))

    def test_treasury_withdrawals_action_creation(
        self, sample_withdrawals, sample_policy_hash
    ):
        # Test creating a TreasuryWithdrawalsAction with all fields
        action = TreasuryWithdrawalsAction(
            withdrawals=sample_withdrawals, policy_hash=sample_policy_hash
        )
        assert action._CODE == 2
        assert action.withdrawals == sample_withdrawals
        assert action.policy_hash == sample_policy_hash

        # Test creating without optional policy_hash
        action_no_policy = TreasuryWithdrawalsAction(
            withdrawals=sample_withdrawals, policy_hash=None
        )
        assert action_no_policy._CODE == 2
        assert action_no_policy.withdrawals == sample_withdrawals
        assert action_no_policy.policy_hash is None

    def test_treasury_withdrawals_action_serialization(
        self, sample_withdrawals, sample_policy_hash
    ):
        action = TreasuryWithdrawalsAction(
            withdrawals=sample_withdrawals, policy_hash=sample_policy_hash
        )

        # Serialize to primitive
        primitive = action.to_primitive()

        # Check the structure of the primitive
        assert isinstance(primitive, list)
        assert primitive[0] == 2  # Check the _CODE
        assert len(primitive) == 3  # [code, withdrawals, policy_hash]

        # Deserialize back and compare
        deserialized = TreasuryWithdrawalsAction.from_primitive(primitive)
        assert deserialized._CODE == action._CODE
        assert deserialized.withdrawals == action.withdrawals
        assert deserialized.policy_hash == action.policy_hash

    def test_treasury_withdrawals_action_invalid_deserialization(
        self, sample_withdrawals
    ):
        # Test with invalid code
        with pytest.raises(DeserializeException):
            TreasuryWithdrawalsAction.from_primitive([3, sample_withdrawals, None])

    def test_treasury_withdrawals_action_equality(
        self, sample_withdrawals, sample_policy_hash
    ):
        action1 = TreasuryWithdrawalsAction(
            withdrawals=sample_withdrawals, policy_hash=sample_policy_hash
        )
        action2 = TreasuryWithdrawalsAction(
            withdrawals=sample_withdrawals, policy_hash=sample_policy_hash
        )
        action3 = TreasuryWithdrawalsAction(
            withdrawals=sample_withdrawals, policy_hash=None
        )

        assert action1 == action2
        assert action1 != action3
