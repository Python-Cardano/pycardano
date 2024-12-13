import pathlib
import tempfile

import pytest
from retry import retry

from pycardano import *

from .base import TEST_RETRIES, TestBase


class TestZeroEmptyAsset(TestBase):
    @retry(tries=TEST_RETRIES, backoff=1.3, delay=2, jitter=(0, 10))
    @pytest.mark.post_chang
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

        """Create policy"""
        # A policy that requires a signature from the policy key we generated above
        pub_key_policy_1 = ScriptPubkey(policy_vkey.hash())

        # A policy that requires a signature from the extended payment key
        pub_key_policy_2 = ScriptPubkey(self.extended_payment_vkey.hash())

        # Combine two policies using ScriptAll policy
        policy = ScriptAll([pub_key_policy_1, pub_key_policy_2])

        # Calculate policy ID, which is the hash of the policy
        policy_id = policy.hash()

        """Define NFT"""
        my_nft = MultiAsset.from_primitive(
            {
                policy_id.payload: {
                    b"MY_NFT_1": 1,  # Name of our NFT1  # Quantity of this NFT
                    b"MY_NFT_2": 1,  # Name of our NFT2  # Quantity of this NFT
                }
            }
        )

        native_scripts = [policy]

        """Create metadata"""
        # We need to create a metadata for our NFTs, so they could be displayed correctly by blockchain explorer
        metadata = {
            721: {  # 721 refers to the metadata label registered for NFT standard here:
                # https://github.com/cardano-foundation/CIPs/blob/master/CIP-0010/registry.json#L14-L17
                policy_id.payload.hex(): {
                    "MY_NFT_1": {
                        "description": "This is my first NFT thanks to PyCardano",
                        "name": "PyCardano NFT example token 1",
                        "id": 1,
                        "image": "ipfs://QmRhTTbUrPYEw3mJGGhQqQST9k86v1DPBiTTWJGKDJsVFw",
                    },
                    "MY_NFT_2": {
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

        """Build mint transaction"""

        # Create a transaction builder
        builder = TransactionBuilder(self.chain_context)

        # Add our own address as the input address
        builder.add_input_address(address)

        # Set nft we want to mint
        builder.mint = my_nft

        # Set native script
        builder.native_scripts = native_scripts

        # Set transaction metadata
        builder.auxiliary_data = auxiliary_data

        # Calculate the minimum amount of lovelace that need to hold the NFT we are going to mint
        min_val = min_lovelace_pre_alonzo(Value(0, my_nft), self.chain_context)

        # Send the NFT to our own address
        nft_output = TransactionOutput(address, Value(min_val, my_nft))
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

        """Build transaction with 0 nft"""

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
                MultiAsset.from_primitive(
                    {policy_vkey.hash().payload: {b"MY_NFT_1": 0}}
                ),
            ),
        )
        builder.add_output(nft_output)

        # Build and sign transaction
        signed_tx = builder.build_and_sign(
            [self.payment_skey, self.extended_payment_skey], address
        )

        print("############### Transaction created ###############")
        print(signed_tx)
        print(signed_tx.to_cbor_hex())

        # Submit signed transaction to the network
        print("############### Submitting transaction ###############")
        self.chain_context.submit_tx(signed_tx)

        self.assert_output(address, nft_output)

        """Build transaction with empty multi-asset"""

        # Create a transaction builder
        builder = TransactionBuilder(self.chain_context)

        # Add our own address as the input address
        builder.add_input_address(address)

        # Calculate the minimum amount of lovelace that need to hold the NFT we are going to mint
        min_val = min_lovelace_pre_alonzo(Value(0), self.chain_context)

        # Send the NFT to our own address
        nft_output = TransactionOutput(
            address,
            Value(min_val, MultiAsset.from_primitive({policy_vkey.hash().payload: {}})),
        )
        builder.add_output(nft_output)

        # Build and sign transaction
        signed_tx = builder.build_and_sign(
            [self.payment_skey, self.extended_payment_skey], address
        )

        print("############### Transaction created ###############")
        print(signed_tx)
        print(signed_tx.to_cbor_hex())

        # Submit signed transaction to the network
        print("############### Submitting transaction ###############")
        self.chain_context.submit_tx(signed_tx)

        self.assert_output(address, nft_output)
