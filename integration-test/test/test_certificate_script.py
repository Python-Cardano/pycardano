import os
import time

import cbor2
from retry import retry

from pycardano import *

from .base import TEST_RETRIES, TestBase


class TestDelegation(TestBase):
    @retry(tries=TEST_RETRIES, backoff=1.3, delay=2, jitter=(0, 10))
    def test_stake_delegation(self):
        with open("./plutus_scripts/pass_certifying_and_rewarding.plutus", "r") as f:
            script_hex = f.read()
            stake_script = PlutusV2Script(bytes.fromhex(script_hex))
        cert_script_hash = plutus_script_hash(stake_script)
        address = Address(
            self.payment_key_pair.verification_key.hash(),
            cert_script_hash,
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

            stake_credential = StakeCredential(cert_script_hash)
            stake_registration = StakeRegistration(stake_credential)
            pool_hash = PoolKeyHash(bytes.fromhex(os.environ.get("POOL_ID").strip()))
            stake_delegation = StakeDelegation(stake_credential, pool_keyhash=pool_hash)

            builder = TransactionBuilder(self.chain_context)

            builder.add_input_address(address)
            builder.add_output(TransactionOutput(address, 35000000))
            builder.certificates = [stake_registration, stake_delegation]
            redeemer = Redeemer(0)
            builder.add_certificate_script(stake_script, redeemer=redeemer)

            signed_tx = builder.build_and_sign(
                [self.payment_key_pair.signing_key],
                address,
            )

            print("############### Transaction created ###############")
            print(signed_tx)
            print(signed_tx.to_cbor_hex())
            print("############### Submitting transaction ###############")
            self.chain_context.submit_tx(signed_tx)


#        time.sleep(8)
#
#        builder = TransactionBuilder(self.chain_context)
#
#        builder.add_input_address(address)
#
#        stake_address = Address(
#            staking_part=cert_script_hash,
#            network=self.NETWORK,
#        )
#
#        builder.withdrawals = Withdrawals({bytes(stake_address): 0})
#
#        builder.add_output(TransactionOutput(address, 1000000))
#        redeemer = Redeemer(0)
#        builder.add_withdrawal_script(stake_script, redeemer=redeemer)
#
#        signed_tx = builder.build_and_sign(
#            [self.payment_key_pair.signing_key],
#            address,
#        )
#
#        print("############### Transaction created ###############")
#        print(signed_tx)
#        print(signed_tx.to_cbor_hex())
#        print("############### Submitting transaction ###############")
#        self.chain_context.submit_tx(signed_tx)
#
