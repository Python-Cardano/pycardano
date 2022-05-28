import time

import cbor2
from retry import retry

from pycardano import *

from .base import TestBase


class TestPlutus(TestBase):
    @retry(tries=4, delay=6, backoff=2, jitter=(1, 3))
    def test_plutus(self):

        # ----------- Giver give ---------------

        with open("./plutus_scripts/fortytwo.plutus", "r") as f:
            script_hex = f.read()
            forty_two_script = cbor2.loads(bytes.fromhex(script_hex))

        script_hash = plutus_script_hash(forty_two_script)

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

        builder.add_script_input(utxo_to_spend, forty_two_script, datum, redeemer)
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
