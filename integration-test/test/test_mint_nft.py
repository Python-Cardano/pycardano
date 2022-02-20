"""An example that demonstrates low-level construction of a transaction."""

import os
import pathlib
import tempfile
import time

import websocket
from retry import retry

from pycardano import *


class TestMintNFT:
    # Define chain context
    NETWORK = Network.TESTNET

    OGMIOS_WS = "ws://localhost:1337"

    chain_context = OgmiosChainContext(OGMIOS_WS, Network.TESTNET)

    @retry(tries=10, delay=6)
    def check_ogmios(self):
        print(f"Current chain tip: {self.chain_context.last_block_slot}")

    def test_mint(self):
        self.check_ogmios()
        chain_context = OgmiosChainContext(self.OGMIOS_WS, Network.TESTNET)

        payment_key_path = os.environ.get("PAYMENT_KEY")
        if not payment_key_path:
            raise Exception(
                "Cannot find payment key. Please specify environment variable PAYMENT_KEY"
            )
        payment_skey = PaymentSigningKey.load(payment_key_path)
        payment_vkey = PaymentVerificationKey.from_signing_key(payment_skey)
        address = Address(payment_vkey.hash(), network=self.NETWORK)

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
        pub_key_policy = ScriptPubkey(policy_vkey.hash())

        # A time policy that disallows token minting after 10000 seconds from last block
        must_before_slot = InvalidHereAfter(chain_context.last_block_slot + 10000)

        # Combine two policies using ScriptAll policy
        policy = ScriptAll([pub_key_policy, must_before_slot])

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

        """Build transaction"""

        # Create a transaction builder
        builder = TransactionBuilder(chain_context)

        # Add our own address as the input address
        builder.add_input_address(address)

        # Since an InvalidHereAfter rule is included in the policy, we must specify time to live (ttl) for this transaction
        builder.ttl = must_before_slot.after

        # Set nft we want to mint
        builder.mint = my_nft

        # Set native script
        builder.native_scripts = native_scripts

        # Set transaction metadata
        builder.auxiliary_data = auxiliary_data

        # Calculate the minimum amount of lovelace that need to hold the NFT we are going to mint
        min_val = min_lovelace(Value(0, my_nft), chain_context)

        # Send the NFT to our own address
        nft_output = TransactionOutput(address, Value(min_val, my_nft))
        builder.add_output(nft_output)

        # Build a finalized transaction body with the change returning to our own address
        tx_body = builder.build(change_address=address)

        """Sign transaction and add witnesses"""
        # Sign the transaction body hash using the payment signing key
        payment_signature = payment_skey.sign(tx_body.hash())

        # Sign the transaction body hash using the policy signing key because we are minting new tokens
        policy_signature = policy_skey.sign(tx_body.hash())

        # Add verification keys and their signatures to the witness set
        vk_witnesses = [
            VerificationKeyWitness(payment_vkey, payment_signature),
            VerificationKeyWitness(policy_vkey, policy_signature),
        ]

        # Create final signed transaction
        signed_tx = Transaction(
            tx_body,
            # Beside vk witnesses, We also need to add the policy script to witness set when we are minting new tokens.
            TransactionWitnessSet(
                vkey_witnesses=vk_witnesses, native_scripts=native_scripts
            ),
            auxiliary_data=auxiliary_data,
        )

        print("############### Transaction created ###############")
        print(signed_tx)
        print(signed_tx.to_cbor())

        # Submit signed transaction to the network
        print("############### Submitting transaction ###############")
        chain_context.submit_tx(signed_tx.to_cbor())

        time.sleep(3)

        utxos = chain_context.utxos(str(address))
        found_nft = False

        for utxo in utxos:
            output = utxo.output
            if output == nft_output:
                found_nft = True

        assert found_nft, f"Cannot find target NFT in address: {address}"
