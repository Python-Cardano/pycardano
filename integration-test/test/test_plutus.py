import collections
import time
from dataclasses import dataclass
from typing import Dict, Union

import cbor2
import pytest
from retry import retry

from pycardano import *
from pycardano.backend.kupo import KupoChainContextExtension

from .base import TEST_RETRIES, TestBase
from .test_cardano_cli import TestCardanoCli


@dataclass
class HelloWorldDatum(PlutusData):
    CONSTR_ID = 0
    owner: bytes


@dataclass
class HelloWorldRedeemer(PlutusData):
    CONSTR_ID = 0
    msg: bytes


class TestPlutus(TestBase):
    @retry(tries=TEST_RETRIES, backoff=1.3, delay=2, jitter=(0, 10))
    def test_plutus_v1(self):
        # ----------- Giver give ---------------

        with open("./plutus_scripts/fortytwo.plutus", "r") as f:
            script_hex = f.read()
            forty_two_script = cbor2.loads(bytes.fromhex(script_hex))

        script_hash = plutus_script_hash(PlutusV1Script(forty_two_script))

        script_address = Address(script_hash, network=self.NETWORK)

        giver_address = Address(self.payment_vkey.hash(), network=self.NETWORK)

        builder = TransactionBuilder(self.chain_context)
        builder.add_input_address(giver_address)
        datum = Unit()  # A Unit type "()" in Haskell
        builder.add_output(
            TransactionOutput(script_address, 50000000, datum_hash=datum_hash(datum))
        )

        signed_tx = builder.build_and_sign([self.payment_skey], giver_address)

        print("############### Transaction created ###############")
        print(signed_tx)
        print(signed_tx.to_cbor_hex())
        print("############### Submitting transaction ###############")
        self.chain_context.submit_tx(signed_tx)
        time.sleep(3)

        # ----------- Fund taker a collateral UTxO ---------------

        taker_address = Address(self.extended_payment_vkey.hash(), network=self.NETWORK)

        builder = TransactionBuilder(self.chain_context)

        builder.add_input_address(giver_address)
        builder.add_output(TransactionOutput(taker_address, 5000000))

        signed_tx = builder.build_and_sign([self.payment_skey], giver_address)

        print("############### Transaction created ###############")
        print(signed_tx)
        print(signed_tx.to_cbor_hex())
        print("############### Submitting transaction ###############")
        self.chain_context.submit_tx(signed_tx)
        time.sleep(3)

        # ----------- Taker take ---------------

        redeemer = Redeemer(42)

        utxo_to_spend = self.chain_context.utxos(script_address)[0]

        taker_address = Address(self.extended_payment_vkey.hash(), network=self.NETWORK)

        builder = TransactionBuilder(self.chain_context)

        builder.add_script_input(
            utxo_to_spend, PlutusV1Script(forty_two_script), datum, redeemer
        )
        take_output = TransactionOutput(taker_address, 25123456)
        builder.add_output(take_output)

        non_nft_utxo = None
        for utxo in self.chain_context.utxos(taker_address):
            # multi_asset should be empty for collateral utxo
            if not utxo.output.amount.multi_asset:
                non_nft_utxo = utxo
                break

        builder.collaterals.append(non_nft_utxo)

        signed_tx = builder.build_and_sign([self.extended_payment_skey], taker_address)

        print("############### Transaction created ###############")
        print(signed_tx)
        print(signed_tx.to_cbor_hex())
        print("############### Submitting transaction ###############")
        self.chain_context.submit_tx(signed_tx)

        self.assert_output(taker_address, take_output)

    @retry(tries=TEST_RETRIES, backoff=1.3, delay=2, jitter=(0, 10))
    @pytest.mark.post_alonzo
    def test_plutus_v2_datum_hash(self):
        # ----------- Giver give ---------------

        with open("./plutus_scripts/fortytwoV2.plutus", "r") as f:
            script_hex = f.read()
            forty_two_script = cbor2.loads(bytes.fromhex(script_hex))

        script_hash = plutus_script_hash(PlutusV2Script(forty_two_script))

        script_address = Address(script_hash, network=self.NETWORK)

        giver_address = Address(self.payment_vkey.hash(), network=self.NETWORK)

        builder = TransactionBuilder(self.chain_context)
        builder.add_input_address(giver_address)
        datum = 42
        builder.add_output(
            TransactionOutput(script_address, 50000000, datum_hash=datum_hash(datum))
        )

        signed_tx = builder.build_and_sign([self.payment_skey], giver_address)

        print("############### Transaction created ###############")
        print(signed_tx)
        print(signed_tx.to_cbor_hex())
        print("############### Submitting transaction ###############")
        self.chain_context.submit_tx(signed_tx)
        time.sleep(3)

        # ----------- Taker take ---------------

        redeemer = Redeemer(42)

        utxo_to_spend = None

        # Speed the utxo that doesn't have datum/datum_hash or script attached
        for utxo in self.chain_context.utxos(script_address):
            if not utxo.output.script and (
                utxo.output.datum_hash == datum_hash(datum)
                or utxo.output.datum == datum
            ):
                utxo_to_spend = utxo
                break

        taker_address = Address(self.extended_payment_vkey.hash(), network=self.NETWORK)

        builder = TransactionBuilder(self.chain_context)

        builder.add_script_input(
            utxo_to_spend, PlutusV2Script(forty_two_script), datum, redeemer
        )
        take_output = TransactionOutput(taker_address, 25123456)
        builder.add_output(take_output)

        non_nft_utxo = None
        for utxo in self.chain_context.utxos(taker_address):
            # multi_asset should be empty for collateral utxo
            if not utxo.output.amount.multi_asset:
                non_nft_utxo = utxo
                break

        builder.collaterals.append(non_nft_utxo)

        signed_tx = builder.build_and_sign([self.extended_payment_skey], taker_address)

        print("############### Transaction created ###############")
        print(signed_tx)
        print(signed_tx.to_cbor_hex())
        print("############### Submitting transaction ###############")
        self.chain_context.submit_tx(signed_tx)

        self.assert_output(taker_address, take_output)

    @retry(tries=TEST_RETRIES, backoff=1.3, delay=2, jitter=(0, 10))
    @pytest.mark.post_alonzo
    def test_plutus_v2_inline_script_inline_datum(self):
        # ----------- Giver give ---------------

        with open("./plutus_scripts/fortytwoV2.plutus", "r") as f:
            script_hex = f.read()
            forty_two_script = PlutusV2Script(cbor2.loads(bytes.fromhex(script_hex)))

        script_hash = plutus_script_hash(forty_two_script)

        script_address = Address(script_hash, network=self.NETWORK)

        giver_address = Address(self.payment_vkey.hash(), network=self.NETWORK)

        builder = TransactionBuilder(self.chain_context)
        builder.add_input_address(giver_address)
        datum = 42
        builder.add_output(
            TransactionOutput(
                script_address, 50000000, datum=datum, script=forty_two_script
            )
        )

        signed_tx = builder.build_and_sign([self.payment_skey], giver_address)

        print("############### Transaction created ###############")
        print(signed_tx)
        print(signed_tx.to_cbor_hex())
        print("############### Submitting transaction ###############")
        self.chain_context.submit_tx(signed_tx)
        time.sleep(3)

        # ----------- Taker take ---------------

        redeemer = Redeemer(42)

        utxo_to_spend = None

        # Speed the utxo that has both inline script and inline datum
        for utxo in self.chain_context.utxos(script_address):
            if utxo.output.datum and utxo.output.script:
                utxo_to_spend = utxo
                break

        taker_address = Address(self.extended_payment_vkey.hash(), network=self.NETWORK)

        builder = TransactionBuilder(self.chain_context)

        builder.add_script_input(utxo_to_spend, redeemer=redeemer)
        take_output = TransactionOutput(taker_address, 25123456)
        builder.add_output(take_output)

        signed_tx = builder.build_and_sign([self.extended_payment_skey], taker_address)

        print("############### Transaction created ###############")
        print(signed_tx)
        print(signed_tx)
        print("############### Submitting transaction ###############")
        self.chain_context.submit_tx(signed_tx)

        self.assert_output(taker_address, take_output)

    @retry(tries=TEST_RETRIES, backoff=1.3, delay=2, jitter=(0, 10))
    @pytest.mark.post_alonzo
    def test_plutus_v2_ref_script(self):
        # ----------- Create a reference script ---------------

        with open("./plutus_scripts/fortytwoV2.plutus", "r") as f:
            script_hex = f.read()
            forty_two_script = PlutusV2Script(cbor2.loads(bytes.fromhex(script_hex)))

        script_hash = plutus_script_hash(forty_two_script)

        script_address = Address(script_hash, network=self.NETWORK)

        giver_address = Address(self.payment_vkey.hash(), network=self.NETWORK)

        builder = TransactionBuilder(self.chain_context)
        builder.add_input_address(giver_address)
        datum = 42
        builder.add_output(
            TransactionOutput(script_address, 50000000, script=forty_two_script)
        )

        signed_tx = builder.build_and_sign([self.payment_skey], giver_address)

        print("############### Transaction created ###############")
        print(signed_tx)
        print(signed_tx.to_cbor_hex())
        print("############### Submitting transaction ###############")
        self.chain_context.submit_tx(signed_tx)
        time.sleep(6)

        # ----------- Send ADA to the same script address without datum or script ---------------

        builder = TransactionBuilder(self.chain_context)
        builder.add_input_address(giver_address)
        builder.add_output(
            TransactionOutput(script_address, 50000000, datum_hash=datum_hash(datum))
        )

        signed_tx = builder.build_and_sign([self.payment_skey], giver_address)

        print("############### Transaction created ###############")
        print(signed_tx)
        print(signed_tx.to_cbor_hex())
        print("############### Submitting transaction ###############")
        self.chain_context.submit_tx(signed_tx)
        time.sleep(6)

        # ----------- Taker take ---------------

        redeemer = Redeemer(42)

        utxo_to_spend = None

        # Spend the utxo that doesn't have datum/datum_hash or script attached
        for utxo in self.chain_context.utxos(script_address):
            if not utxo.output.script and (
                utxo.output.datum_hash == datum_hash(datum)
                or datum_hash(utxo.output.datum) == datum_hash(datum)
            ):
                utxo_to_spend = utxo
                break

        taker_address = Address(self.extended_payment_vkey.hash(), network=self.NETWORK)

        builder = TransactionBuilder(self.chain_context)

        builder.add_script_input(utxo_to_spend, redeemer=redeemer, datum=datum)
        take_output = TransactionOutput(taker_address, 25123456)
        builder.add_output(take_output)

        signed_tx = builder.build_and_sign([self.extended_payment_skey], taker_address)

        print("############### Transaction created ###############")
        print(signed_tx)
        print(signed_tx.to_cbor_hex())
        print("############### Submitting transaction ###############")
        self.chain_context.submit_tx(signed_tx)

        self.assert_output(taker_address, take_output)

    @retry(tries=TEST_RETRIES, backoff=1.3, delay=2, jitter=(0, 10))
    @pytest.mark.post_alonzo
    def test_transaction_chaining(self):
        giver_address = Address(self.payment_vkey.hash(), network=self.NETWORK)
        builder = TransactionBuilder(self.chain_context)
        builder.add_input_address(giver_address)
        builder.add_output(TransactionOutput(giver_address, 50000000))
        tx1 = builder.build_and_sign([self.payment_skey], giver_address)

        utxo_to_spend = UTxO(
            TransactionInput(tx1.id, 0), tx1.transaction_body.outputs[0]
        )

        builder = TransactionBuilder(self.chain_context)
        builder.add_input(utxo_to_spend)
        builder.add_output(TransactionOutput(giver_address, 25000000))
        tx2 = builder.build_and_sign([self.payment_skey], giver_address)

        self.chain_context.submit_tx(tx1)
        self.chain_context.submit_tx(tx2)

    @retry(tries=TEST_RETRIES, backoff=1.3, delay=2, jitter=(0, 10))
    @pytest.mark.post_alonzo
    def test_get_plutus_script(self):
        # ----------- Giver give ---------------
        with open("./plutus_scripts/fortytwoV2.plutus", "r") as f:
            script_hex = f.read()
            forty_two_script = PlutusV2Script(cbor2.loads(bytes.fromhex(script_hex)))

        script_hash = plutus_script_hash(forty_two_script)

        script_address = Address(script_hash, network=self.NETWORK)

        giver_address = Address(self.payment_vkey.hash(), network=self.NETWORK)

        builder = TransactionBuilder(self.chain_context)
        builder.add_input_address(giver_address)
        builder.add_output(
            TransactionOutput(script_address, 50000000, script=forty_two_script)
        )

        signed_tx = builder.build_and_sign([self.payment_skey], giver_address)

        print("############### Transaction created ###############")
        print(signed_tx)
        print(signed_tx.to_cbor_hex())
        print("############### Submitting transaction ###############")
        self.chain_context.submit_tx(signed_tx)
        time.sleep(3)

        utxos = self.chain_context.utxos(script_address)

        assert utxos[0].output.script == forty_two_script

    @retry(tries=TEST_RETRIES, backoff=1.3, delay=2, jitter=(0, 10))
    @pytest.mark.post_chang
    def test_plutus_v3(self):
        # ----------- Giver give ---------------

        with open("./plutus_scripts/helloworldV3.plutus", "r") as f:
            script_hex = f.read()
            hello_world_script = bytes.fromhex(script_hex)

        script_hash = plutus_script_hash(PlutusV3Script(hello_world_script))

        print("script_hash: ", script_hash)

        script_address = Address(script_hash, network=self.NETWORK)

        giver_address = Address(self.payment_vkey.hash(), network=self.NETWORK)

        builder = TransactionBuilder(self.chain_context)
        builder.add_input_address(giver_address)
        datum = HelloWorldDatum(owner=self.payment_vkey.hash().to_primitive())
        builder.add_output(TransactionOutput(script_address, 50000000, datum=datum))

        signed_tx = builder.build_and_sign([self.payment_skey], giver_address)

        print("############### Transaction created ###############")
        print(signed_tx)
        print(signed_tx.to_cbor_hex())
        print("############### Submitting transaction ###############")
        self.chain_context.submit_tx(signed_tx)
        time.sleep(3)

        # ----------- Taker take ---------------

        redeemer = Redeemer(data=HelloWorldRedeemer(msg=b"Hello, World!"))

        utxo_to_spend = self.chain_context.utxos(script_address)[0]

        taker_address = Address(self.payment_vkey.hash(), network=self.NETWORK)

        builder = TransactionBuilder(self.chain_context)

        builder.add_script_input(
            utxo_to_spend, PlutusV3Script(hello_world_script), redeemer=redeemer
        )
        take_output = TransactionOutput(taker_address, 25123456)
        builder.add_output(take_output)

        builder.required_signers = [self.payment_vkey.hash()]

        signed_tx = builder.build_and_sign([self.payment_skey], taker_address)

        print("############### Transaction created ###############")
        print(signed_tx)
        print(signed_tx.to_cbor_hex())
        print("############### Submitting transaction ###############")
        self.chain_context.submit_tx(signed_tx)

        time.sleep(3)

        self.assert_output(taker_address, take_output)


class TestPlutusKupoOgmios(TestPlutus):
    @classmethod
    def setup_class(cls):
        cls.chain_context = KupoChainContextExtension(cls.chain_context, cls.KUPO_URL)


def evaluate_tx(tx: Transaction) -> Dict[str, ExecutionUnits]:
    redeemers = tx.transaction_witness_set.redeemer
    execution_units = {}

    if redeemers:
        for r in redeemers:
            k = f"{r.tag.name.lower()}:{r.index}"
            execution_units[k] = ExecutionUnits(1000000, 1000000000)

    return execution_units


@pytest.mark.CardanoCLI
class TestPlutusCardanoCLI(TestPlutus):
    @classmethod
    def setup_class(cls):
        cls.chain_context = TestCardanoCli.chain_context
        cls.chain_context.evaluate_tx = evaluate_tx
