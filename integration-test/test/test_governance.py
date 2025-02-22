import os
import time

from retry import retry

from pycardano import *

from .base import TEST_RETRIES, TestBase


class TestGovernanceAction(TestBase):
    @retry(tries=TEST_RETRIES, backoff=1.3, delay=2, jitter=(0, 10))
    def test_governance_action_and_voting(self):
        # Create new stake key pair
        stake_key_pair = StakeKeyPair.generate()

        # Create addresses for testing
        address = Address(
            self.payment_vkey.hash(),
            stake_key_pair.verification_key.hash(),
            self.NETWORK,
        )

        # Load pool cold key for signing
        # pool_cold_skey = PaymentSigningKey.load(self.pool_cold_key_path)

        # First, ensure we have enough funds
        utxos = self.chain_context.utxos(address)

        if not utxos:
            giver_address = Address(self.payment_vkey.hash(), network=self.NETWORK)

            builder = TransactionBuilder(self.chain_context)
            builder.add_input_address(giver_address)
            builder.add_output(TransactionOutput(address, 110000000000))

            signed_tx = builder.build_and_sign([self.payment_skey], giver_address)
            print("############### Funding Transaction created ###############")
            print(signed_tx)
            print(signed_tx.to_cbor_hex())
            print("############### Submitting funding transaction ###############")
            self.chain_context.submit_tx(signed_tx)
            time.sleep(5)

        # Step 1: Register as a DRep first
        drep_credential = DRepCredential(stake_key_pair.verification_key.hash())
        anchor = Anchor(
            url="https://test-drep.com",
            data_hash=AnchorDataHash(bytes.fromhex("0" * 64)),
        )

        drep_registration = RegDRepCert(
            drep_credential=drep_credential,
            coin=500000000,
            anchor=anchor,
        )

        stake_credential = StakeCredential(stake_key_pair.verification_key.hash())
        pool_hash = PoolKeyHash(bytes.fromhex(os.environ.get("POOL_ID").strip()))

        drep = DRep(
            DRepKind.VERIFICATION_KEY_HASH,
            stake_key_pair.verification_key.hash(),
        )

        all_in_one_cert = StakeRegistrationAndDelegationAndVoteDelegation(
            stake_credential, pool_hash, drep, 1000000
        )

        # Create transaction for DRep registration
        builder = TransactionBuilder(self.chain_context)
        builder.add_input_address(address)
        builder.add_output(TransactionOutput(address, 35000000))
        builder.certificates = [drep_registration, all_in_one_cert]

        signed_tx = builder.build_and_sign(
            [stake_key_pair.signing_key, self.payment_skey],
            address,
        )
        print("############### DRep Registration Transaction created ###############")
        print(signed_tx)
        print(signed_tx.to_cbor_hex())
        print("############### Submitting DRep registration ###############")
        self.chain_context.submit_tx(signed_tx)
        time.sleep(5)

        # Step 2: Create and submit parameter change action
        param_update = ProtocolParamUpdate(
            max_block_body_size=75536,
            max_transaction_size=26384,
        )

        parameter_change_action = ParameterChangeAction(None, param_update, None)

        # Create transaction for parameter change
        builder = TransactionBuilder(self.chain_context)
        builder.add_input_address(address)
        builder.add_output(TransactionOutput(address, 35000000))
        reward_account = Address(
            staking_part=stake_key_pair.verification_key.hash(), network=self.NETWORK
        )
        builder.add_proposal(
            100000000000,
            bytes(reward_account),
            parameter_change_action,
            Anchor(
                url="https://test-param-update.com",
                data_hash=AnchorDataHash(bytes.fromhex("0" * 64)),
            ),
        )

        # Sign with both payment key and pool cold key for governance action
        signed_tx = builder.build_and_sign(
            [self.payment_skey, stake_key_pair.signing_key],
            address,
        )
        print("############### Gov Action Transaction created ###############")
        print(signed_tx)
        print(signed_tx.to_cbor_hex())
        print("############### Submitting gov action transaction ###############")
        self.chain_context.submit_tx(signed_tx)
        time.sleep(5)

        # Get the governance action ID from the transaction
        gov_action_id = GovActionId(
            transaction_id=signed_tx.id,
            gov_action_index=0,  # First governance action in the transaction
        )

        # Step 3: Vote for the action as a DRep
        drep_voter = Voter(
            credential=stake_key_pair.verification_key.hash(),
            voter_type=VoterType.DREP,
        )

        # Step 4: Vote for the action as a stake pool
        pool_id = os.environ.get("POOL_ID").strip()

        # Create transaction for voting
        builder = TransactionBuilder(self.chain_context)
        builder.add_input_address(address)
        builder.add_output(TransactionOutput(address, 35000000))

        # Add DRep vote using the helper method
        builder.add_vote(
            voter=drep_voter,
            gov_action_id=gov_action_id,
            vote=Vote.YES,
            anchor=Anchor(
                url="https://test-drep.com",
                data_hash=AnchorDataHash(bytes.fromhex("0" * 64)),
            ),
        )

        # Add pool vote using the helper method
        pool_voter = Voter(
            credential=VerificationKeyHash(bytes.fromhex(pool_id)),
            voter_type=VoterType.STAKING_POOL,
        )
        builder.add_vote(
            voter=pool_voter,
            gov_action_id=gov_action_id,
            vote=Vote.YES,
            anchor=Anchor(
                url="https://test-pool.com",
                data_hash=AnchorDataHash(bytes.fromhex("0" * 64)),
            ),
        )

        # Sign with all required keys
        signed_tx = builder.build_and_sign(
            [
                stake_key_pair.signing_key,
                self.payment_skey,
                self.pool_cold_skey,
            ],
            address,
        )
        print("############### Voting Transaction created ###############")
        print(signed_tx)
        print(signed_tx.to_cbor_hex())
        print("############### Submitting voting transaction ###############")
        self.chain_context.submit_tx(signed_tx)

        print("############### Test completed successfully ###############")
