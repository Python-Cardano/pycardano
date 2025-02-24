import os
import time

from retry import retry

from pycardano import *

from .base import TEST_RETRIES, TestBase


class TestDelegation(TestBase):
    @retry(tries=TEST_RETRIES, backoff=1.3, delay=2, jitter=(0, 10))
    def test_stake_delegation(self):
        address = Address(
            self.payment_key_pair.verification_key.hash(),
            self.stake_key_pair.verification_key.hash(),
            self.NETWORK,
        )

        utxos = self.chain_context.utxos(address)

        if not utxos:
            giver_address = Address(self.payment_vkey.hash(), network=self.NETWORK)

            builder = TransactionBuilder(self.chain_context)

            builder.add_input_address(giver_address)
            builder.add_output(TransactionOutput(address, 44000000000))

            signed_tx = builder.build_and_sign([self.payment_skey], giver_address)

            print("############### Transaction created ###############")
            print(signed_tx)
            print(signed_tx.to_cbor_hex())
            print("############### Submitting transaction ###############")
            self.chain_context.submit_tx(signed_tx)

            time.sleep(3)

            stake_credential = StakeCredential(
                self.stake_key_pair.verification_key.hash()
            )
            pool_hash = PoolKeyHash(bytes.fromhex(os.environ.get("POOL_ID").strip()))

            drep = DRep(
                DRepKind.VERIFICATION_KEY_HASH,
                self.stake_key_pair.verification_key.hash(),
            )

            drep_credential = DRepCredential(
                self.stake_key_pair.verification_key.hash()
            )

            anchor = Anchor(
                url="https://drep.com",
                data_hash=AnchorDataHash((bytes.fromhex("0" * 64))),
            )

            drep_registration = RegDRepCert(
                drep_credential=drep_credential, coin=500000000, anchor=anchor
            )

            all_in_one_cert = StakeRegistrationAndDelegationAndVoteDelegation(
                stake_credential, pool_hash, drep, 1000000
            )

            builder = TransactionBuilder(self.chain_context)

            builder.add_input_address(address)
            builder.add_output(TransactionOutput(address, 35000000))

            builder.certificates = [drep_registration, all_in_one_cert]

            signed_tx = builder.build_and_sign(
                [self.stake_key_pair.signing_key, self.payment_key_pair.signing_key],
                address,
            )

            print("############### Transaction created ###############")
            print(signed_tx)
            print(signed_tx.to_cbor_hex())
            print("############### Submitting transaction ###############")
            self.chain_context.submit_tx(signed_tx)

        time.sleep(120)

        builder = TransactionBuilder(self.chain_context)

        builder.add_input_address(address)

        stake_address = Address(
            staking_part=self.stake_key_pair.verification_key.hash(),
            network=self.NETWORK,
        )

        rewards = self.chain_context.query_account_reward_summaries(
            keys=[stake_address.encode()]
        )

        stake_address_reward = 0
        if stake_address.staking_part.payload.hex() in rewards:
            stake_address_reward = rewards[stake_address.staking_part.payload.hex()][
                "rewards"
            ]["ada"]["lovelace"]

        builder.withdrawals = Withdrawals({bytes(stake_address): stake_address_reward})

        builder.add_output(TransactionOutput(address, 1000000))

        signed_tx = builder.build_and_sign(
            [self.stake_key_pair.signing_key, self.payment_key_pair.signing_key],
            address,
        )

        print("############### Transaction created ###############")
        print(signed_tx)
        print(signed_tx.to_cbor_hex())
        print("############### Submitting transaction ###############")
        self.chain_context.submit_tx(signed_tx)
