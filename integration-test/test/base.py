"""An example that demonstrates low-level construction of a transaction."""

import os
import time

from retry import retry

from pycardano import *

TEST_RETRIES = 6


@retry(tries=10, delay=4)
def check_chain_context(chain_context):
    print(f"Current chain tip: {chain_context.last_block_slot}")


class TestBase:
    # Define chain context
    NETWORK = Network.TESTNET

    OGMIOS_WS = "ws://localhost:1337"

    KUPO_URL = "http://localhost:1442/v1/matches"

    chain_context = OgmiosChainContext(OGMIOS_WS, Network.TESTNET)

    check_chain_context(chain_context)

    payment_key_path = os.environ.get("PAYMENT_KEY")
    extended_key_path = os.environ.get("EXTENDED_PAYMENT_KEY")
    if not payment_key_path or not extended_key_path:
        raise Exception(
            "Cannot find payment key. Please specify environment variable PAYMENT_KEY and extended_key_path"
        )
    payment_skey = PaymentSigningKey.load(payment_key_path)
    payment_vkey = PaymentVerificationKey.from_signing_key(payment_skey)
    extended_payment_skey = PaymentExtendedSigningKey.load(extended_key_path)
    extended_payment_vkey = PaymentExtendedVerificationKey.from_signing_key(
        extended_payment_skey
    )

    payment_key_pair = PaymentKeyPair.generate()
    stake_key_pair = StakeKeyPair.generate()

    @retry(tries=TEST_RETRIES, delay=3)
    def assert_output(self, target_address, target_output):
        utxos = self.chain_context.utxos(str(target_address))
        found = False

        for utxo in utxos:
            output = utxo.output
            if output == target_output:
                found = True

        assert found, f"Cannot find target UTxO in address: {target_address}"

    @retry(tries=TEST_RETRIES, delay=6, backoff=2, jitter=(1, 3))
    def fund(self, source_address, source_key, target_address, amount=5000000):
        builder = TransactionBuilder(self.chain_context)

        builder.add_input_address(source_address)
        output = TransactionOutput(target_address, amount)
        builder.add_output(output)

        signed_tx = builder.build_and_sign([source_key], source_address)

        print("############### Transaction created ###############")
        print(signed_tx)
        print(signed_tx.to_cbor())
        print("############### Submitting transaction ###############")
        self.chain_context.submit_tx(signed_tx.to_cbor())
        self.assert_output(target_address, target_output=output)
