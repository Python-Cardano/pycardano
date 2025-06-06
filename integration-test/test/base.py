"""An example that demonstrates low-level construction of a transaction."""

import os
import time

import ogmios as python_ogmios
from retry import retry

from pycardano import *

TEST_RETRIES = 8


@retry(tries=10, delay=4)
def check_chain_context(chain_context):
    print(f"Current chain tip: {chain_context.last_block_slot}")


class TestBase:
    # Define chain context
    NETWORK = Network.TESTNET

    # TODO: Bring back kupo test
    KUPO_URL = "http://localhost:1442"

    chain_context = OgmiosV6ChainContext(
        host="localhost",
        port=1337,
        network=Network.TESTNET,
        refetch_chain_tip_interval=1,
    )

    check_chain_context(chain_context)

    payment_key_path = os.environ.get("PAYMENT_KEY")
    extended_key_path = os.environ.get("EXTENDED_PAYMENT_KEY")
    pool_cold_key_path = os.environ.get("POOL_COLD_KEY")
    pool_payment_key_path = os.environ.get("POOL_PAYMENT_KEY")
    pool_stake_key_path = os.environ.get("POOL_STAKE_KEY")
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
    pool_cold_skey = PaymentSigningKey.load(pool_cold_key_path)
    pool_cold_vkey = PaymentVerificationKey.from_signing_key(pool_cold_skey)
    pool_payment_skey = PaymentSigningKey.load(pool_payment_key_path)
    pool_payment_vkey = PaymentVerificationKey.from_signing_key(pool_payment_skey)
    pool_stake_skey = StakeSigningKey.load(pool_stake_key_path)
    pool_stake_vkey = StakeVerificationKey.from_signing_key(pool_stake_skey)

    payment_key_pair = PaymentKeyPair.generate()
    stake_key_pair = StakeKeyPair.generate()

    @retry(tries=10, delay=3)
    def assert_output(self, target_address, target):
        utxos = self.chain_context.utxos(target_address)
        found = False

        for utxo in utxos:
            if isinstance(target, UTxO):
                if utxo == target:
                    found = True
            if isinstance(target, TransactionOutput):
                if utxo.output == target:
                    found = True
            if isinstance(target, TransactionId):
                if utxo.input.transaction_id == target:
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
        print(signed_tx.to_cbor_hex())
        print("############### Submitting transaction ###############")
        self.chain_context.submit_tx(signed_tx)
        target_utxo = UTxO(TransactionInput(signed_tx.id, 0), output)
        self.assert_output(target_address, target_utxo)
