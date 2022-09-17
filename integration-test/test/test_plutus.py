import time

import cbor2
import pytest
from retry import retry

from pycardano import *

from .base import TEST_RETRIES, TestBase


class TestPlutus(TestBase):
    @retry(tries=TEST_RETRIES, backoff=1.5, delay=6, jitter=(0, 4))
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
        datum = PlutusData()  # A Unit type "()" in Haskell
        builder.add_output(
            TransactionOutput(script_address, 50000000, datum_hash=datum_hash(datum))
        )

        signed_tx = builder.build_and_sign([self.payment_skey], giver_address)

        print("############### Transaction created ###############")
        print(signed_tx)
        print(signed_tx.to_cbor())
        print("############### Submitting transaction ###############")
        self.chain_context.submit_tx(signed_tx.to_cbor())
        time.sleep(3)

        # ----------- Fund taker a collateral UTxO ---------------

        taker_address = Address(self.extended_payment_vkey.hash(), network=self.NETWORK)

        builder = TransactionBuilder(self.chain_context)

        builder.add_input_address(giver_address)
        builder.add_output(TransactionOutput(taker_address, 5000000))

        signed_tx = builder.build_and_sign([self.payment_skey], giver_address)

        print("############### Transaction created ###############")
        print(signed_tx)
        print(signed_tx.to_cbor())
        print("############### Submitting transaction ###############")
        self.chain_context.submit_tx(signed_tx.to_cbor())
        time.sleep(3)

        # ----------- Taker take ---------------

        redeemer = Redeemer(RedeemerTag.SPEND, 42)

        utxo_to_spend = self.chain_context.utxos(str(script_address))[0]

        taker_address = Address(self.extended_payment_vkey.hash(), network=self.NETWORK)

        builder = TransactionBuilder(self.chain_context)

        builder.add_script_input(
            utxo_to_spend, PlutusV1Script(forty_two_script), datum, redeemer
        )
        take_output = TransactionOutput(taker_address, 25123456)
        builder.add_output(take_output)

        non_nft_utxo = None
        for utxo in self.chain_context.utxos(str(taker_address)):
            # multi_asset should be empty for collateral utxo
            if not utxo.output.amount.multi_asset:
                non_nft_utxo = utxo
                break

        builder.collaterals.append(non_nft_utxo)

        signed_tx = builder.build_and_sign([self.extended_payment_skey], taker_address)

        print("############### Transaction created ###############")
        print(signed_tx)
        print(signed_tx.to_cbor())
        print("############### Submitting transaction ###############")
        self.chain_context.submit_tx(signed_tx.to_cbor())

        self.assert_output(taker_address, take_output)

    @retry(tries=TEST_RETRIES, backoff=1.5, delay=6, jitter=(0, 4))
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
        print(signed_tx.to_cbor())
        print("############### Submitting transaction ###############")
        self.chain_context.submit_tx(signed_tx.to_cbor())
        time.sleep(3)

        # ----------- Taker take ---------------

        redeemer = Redeemer(RedeemerTag.SPEND, 42)

        utxo_to_spend = None

        # Speed the utxo that doesn't have datum/datum_hash or script attached
        for utxo in self.chain_context.utxos(str(script_address)):
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
        for utxo in self.chain_context.utxos(str(taker_address)):
            # multi_asset should be empty for collateral utxo
            if not utxo.output.amount.multi_asset:
                non_nft_utxo = utxo
                break

        builder.collaterals.append(non_nft_utxo)

        signed_tx = builder.build_and_sign([self.extended_payment_skey], taker_address)

        print("############### Transaction created ###############")
        print(signed_tx)
        print(signed_tx.to_cbor())
        print("############### Submitting transaction ###############")
        self.chain_context.submit_tx(signed_tx.to_cbor())

        self.assert_output(taker_address, take_output)

    @retry(tries=TEST_RETRIES, backoff=1.5, delay=6, jitter=(0, 4))
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
        print(signed_tx.to_cbor())
        print("############### Submitting transaction ###############")
        self.chain_context.submit_tx(signed_tx.to_cbor())
        time.sleep(3)

        # ----------- Taker take ---------------

        redeemer = Redeemer(RedeemerTag.SPEND, 42)

        utxo_to_spend = None

        # Speed the utxo that has both inline script and inline datum
        for utxo in self.chain_context.utxos(str(script_address)):
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
        print(signed_tx.to_cbor())
        print("############### Submitting transaction ###############")
        self.chain_context.submit_tx(signed_tx.to_cbor())

        self.assert_output(taker_address, take_output)

    @retry(tries=TEST_RETRIES, backoff=1.5, delay=6, jitter=(0, 4))
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
        print(signed_tx.to_cbor())
        print("############### Submitting transaction ###############")
        self.chain_context.submit_tx(signed_tx.to_cbor())
        time.sleep(3)

        # ----------- Send ADA to the same script address without datum or script ---------------

        builder = TransactionBuilder(self.chain_context)
        builder.add_input_address(giver_address)
        builder.add_output(
            TransactionOutput(script_address, 50000000, datum_hash=datum_hash(datum))
        )

        signed_tx = builder.build_and_sign([self.payment_skey], giver_address)

        print("############### Transaction created ###############")
        print(signed_tx)
        print(signed_tx.to_cbor())
        print("############### Submitting transaction ###############")
        self.chain_context.submit_tx(signed_tx.to_cbor())
        time.sleep(3)

        # ----------- Taker take ---------------

        redeemer = Redeemer(RedeemerTag.SPEND, 42)

        utxo_to_spend = None

        # Spend the utxo that doesn't have datum/datum_hash or script attached
        for utxo in self.chain_context.utxos(str(script_address)):
            if not utxo.output.script and (
                utxo.output.datum_hash == datum_hash(datum)
                or utxo.output.datum == datum
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
        print(signed_tx.to_cbor())
        print("############### Submitting transaction ###############")
        self.chain_context.submit_tx(signed_tx.to_cbor())

        self.assert_output(taker_address, take_output)
