import pathlib
import tempfile
from dataclasses import dataclass

import cbor2
import pytest
from retry import retry

from pycardano import *

from .base import TEST_RETRIES, TestBase


class TestMint(TestBase):
    @retry(tries=TEST_RETRIES, backoff=1.3, delay=2, jitter=(0, 10))
    @pytest.mark.post_alonzo
    def test_min_utxo(self):
        address = Address(self.payment_vkey.hash(), network=self.NETWORK)

        with open("./plutus_scripts/always_succeeds.plutus", "r") as f:
            script_hex = f.read()
            anymint_script = PlutusV1Script(cbor2.loads(bytes.fromhex(script_hex)))

        policy_id = plutus_script_hash(anymint_script)

        my_nft = MultiAsset.from_primitive(
            {
                policy_id.payload: {
                    b"MY_SCRIPT_NFT_1": 1,  # Name of our NFT1  # Quantity of this NFT
                    b"MY_SCRIPT_NFT_2": 1,  # Name of our NFT2  # Quantity of this NFT
                }
            }
        )

        metadata = {
            721: {
                policy_id.payload.hex(): {
                    "MY_SCRIPT_NFT_1": {
                        "description": "This is my first NFT thanks to PyCardano",
                        "name": "PyCardano NFT example token 1",
                        "id": 1,
                        "image": "ipfs://QmRhTTbUrPYEw3mJGGhQqQST9k86v1DPBiTTWJGKDJsVFw",
                    },
                    "MY_SCRIPT_NFT_2": {
                        "description": "This is my second NFT thanks to PyCardano",
                        "name": "PyCardano NFT example token 2",
                        "id": 2,
                        "image": "ipfs://QmRhTTbUrPYEw3mJGGhQqQST9k86v1DPBiTTWJGKDJsVFw",
                    },
                }
            }
        }

        # Place metadata in AuxiliaryData, the format acceptable by a transaction.
        auxiliary_data = AuxiliaryData(AlonzoMetadata(metadata=Metadata(metadata)))

        # Create a transaction builder
        builder = TransactionBuilder(self.chain_context)

        # Add our own address as the input address
        builder.add_input_address(address)

        @dataclass
        class MyPlutusData(PlutusData):
            a: int

        # Add minting script with an empty datum and a minting redeemer
        builder.add_minting_script(
            anymint_script, redeemer=Redeemer(MyPlutusData(a=42))
        )

        # Set nft we want to mint
        builder.mint = my_nft

        # Set transaction metadata
        builder.auxiliary_data = auxiliary_data

        # Calculate the minimum amount of lovelace that need to hold the NFT we are going to mint
        min_val = min_lovelace(
            output=TransactionOutput(address, Value(0, my_nft)),
            context=self.chain_context,
        )

        # Send the NFT to our own address
        nft_output = TransactionOutput(address, Value(min_val, my_nft))
        pure_ada_output = TransactionOutput(
            address,
            min_lovelace(
                context=self.chain_context, output=TransactionOutput(address, 0)
            ),
        )
        builder.add_output(nft_output)
        builder.add_output(pure_ada_output)

        # Build and sign transaction
        signed_tx = builder.build_and_sign([self.payment_skey], address)
        # signed_tx.transaction_witness_set.plutus_data

        print("############### Transaction created ###############")
        print(signed_tx)
        print(signed_tx.to_cbor_hex())

        # Submit signed transaction to the network
        print("############### Submitting transaction ###############")
        self.chain_context.submit_tx(signed_tx)

        self.assert_output(address, nft_output)
