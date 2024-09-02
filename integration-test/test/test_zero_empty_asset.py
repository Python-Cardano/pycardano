import pathlib
import tempfile
from dataclasses import dataclass

import cbor2
import pytest
from retry import retry

from pycardano import *

from .base import TEST_RETRIES, TestBase


class TestZeroEmptyAsset(TestBase):
    @retry(tries=TEST_RETRIES, backoff=1.5, delay=6, jitter=(0, 4))
    def test_submit_zero_and_empty(self):
        address = Address(self.payment_vkey.hash(), network=self.NETWORK)

        # Load payment keys or create them if they don't exist
        def load_or_create_key_pair(base_dir, base_name):
            skey_path = base_dir / f"{base_name}.skey"
            vkey_path = base_dir / f"{base_name}.vkey"

            if skey_path.exists():
                skey = PaymentSigningKey.load(str(skey_path))
                vkey = PaymentVerificationKey.from_signing_key(skey)
            else:
                key_pair = PaymentKeyPair.generate()
                key_pair.signing_key.save(str(skey_path))
                key_pair.verification_key.save(str(vkey_path))
                skey = key_pair.signing_key
                vkey = key_pair.verification_key
            return skey, vkey

        tempdir = tempfile.TemporaryDirectory()
        PROJECT_ROOT = tempdir.name

        root = pathlib.Path(PROJECT_ROOT)
        # Create the directory if it doesn't exist
        root.mkdir(parents=True, exist_ok=True)
        """Generate keys"""
        key_dir = root / "keys"
        key_dir.mkdir(exist_ok=True)

        # Generate policy keys, which will be used when minting NFT
        policy_skey, policy_vkey = load_or_create_key_pair(key_dir, "policy")

        """Build transaction"""

        # Create a transaction builder
        builder = TransactionBuilder(self.chain_context)

        # Add our own address as the input address
        builder.add_input_address(address)

        # Calculate the minimum amount of lovelace that need to hold the NFT we are going to mint
        min_val = min_lovelace_pre_alonzo(Value(0), self.chain_context)

        # Send the NFT to our own address
        nft_output = TransactionOutput(
            address,
            Value(
                min_val,
                MultiAsset.from_primitive({policy_skey.hash(): {b"MY_NFT_1": 0}}),
            ),
        )
        builder.add_output(nft_output)

        # Build and sign transaction
        signed_tx = builder.build_and_sign(
            [self.payment_skey, self.extended_payment_skey, policy_skey], address
        )

        print("############### Transaction created ###############")
        print(signed_tx)
        print(signed_tx.to_cbor_hex())

        # Submit signed transaction to the network
        print("############### Submitting transaction ###############")
        self.chain_context.submit_tx(signed_tx)

        self.assert_output(address, nft_output)

        """Build transaction"""

        # Create a transaction builder
        builder = TransactionBuilder(self.chain_context)

        # Add our own address as the input address
        builder.add_input_address(address)

        # Calculate the minimum amount of lovelace that need to hold the NFT we are going to mint
        min_val = min_lovelace_pre_alonzo(Value(0), self.chain_context)

        # Send the NFT to our own address
        nft_output = TransactionOutput(
            address, Value(min_val, MultiAsset.from_primitive({policy_skey.hash(): {}}))
        )
        builder.add_output(nft_output)

        # Build and sign transaction
        signed_tx = builder.build_and_sign(
            [self.payment_skey, self.extended_payment_skey, policy_skey], address
        )

        print("############### Transaction created ###############")
        print(signed_tx)
        print(signed_tx.to_cbor_hex())

        # Submit signed transaction to the network
        print("############### Submitting transaction ###############")
        self.chain_context.submit_tx(signed_tx)

        self.assert_output(address, nft_output)
