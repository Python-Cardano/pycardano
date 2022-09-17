import os
import time

from retry import retry

from pycardano import *

from .base import TEST_RETRIES, TestBase


class TestDelegation(TestBase):
    @retry(tries=TEST_RETRIES, backoff=1.5, delay=6, jitter=(0, 4))
    def test_stake_delegation(self):

        address = Address(
            self.payment_key_pair.verification_key.hash(),
            self.stake_key_pair.verification_key.hash(),
            self.NETWORK,
        )

        utxos = self.chain_context.utxos(str(address))

        if not utxos:
            giver_address = Address(self.payment_vkey.hash(), network=self.NETWORK)

            builder = TransactionBuilder(self.chain_context)

            builder.add_input_address(giver_address)
            builder.add_output(TransactionOutput(address, 440000000000))

            signed_tx = builder.build_and_sign([self.payment_skey], giver_address)

            print("############### Transaction created ###############")
            print(signed_tx)
            print(signed_tx.to_cbor())
            print("############### Submitting transaction ###############")
            self.chain_context.submit_tx(signed_tx.to_cbor())

            time.sleep(3)

            stake_credential = StakeCredential(
                self.stake_key_pair.verification_key.hash()
            )
            stake_registration = StakeRegistration(stake_credential)
            pool_hash = PoolKeyHash(bytes.fromhex(os.environ.get("POOL_ID").strip()))
            stake_delegation = StakeDelegation(stake_credential, pool_keyhash=pool_hash)

            builder = TransactionBuilder(self.chain_context)

            builder.add_input_address(address)
            builder.add_output(TransactionOutput(address, 35000000))

            builder.certificates = [stake_registration, stake_delegation]

            signed_tx = builder.build_and_sign(
                [self.stake_key_pair.signing_key, self.payment_key_pair.signing_key],
                address,
            )

            print("############### Transaction created ###############")
            print(signed_tx)
            print(signed_tx.to_cbor())
            print("############### Submitting transaction ###############")
            self.chain_context.submit_tx(signed_tx.to_cbor())

        time.sleep(8)

        builder = TransactionBuilder(self.chain_context)

        builder.add_input_address(address)

        stake_address = Address(
            staking_part=self.stake_key_pair.verification_key.hash(),
            network=self.NETWORK,
        )

        builder.withdrawals = Withdrawals({bytes(stake_address): 0})

        builder.add_output(TransactionOutput(address, 1000000))

        signed_tx = builder.build_and_sign(
            [self.stake_key_pair.signing_key, self.payment_key_pair.signing_key],
            address,
        )

        print("############### Transaction created ###############")
        print(signed_tx)
        print(signed_tx.to_cbor())
        print("############### Submitting transaction ###############")
        self.chain_context.submit_tx(signed_tx.to_cbor())
