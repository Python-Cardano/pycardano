"""An example that demonstrates low-level construction of a transaction."""

import os
import pathlib
import tempfile
import time

import cbor2
from retry import retry

from pycardano import *


@retry(tries=10, delay=4)
def check_chain_context(chain_context):
    print(f"Current chain tip: {chain_context.last_block_slot}")


class TestAll:
    # Define chain context
    NETWORK = Network.TESTNET

    OGMIOS_WS = "ws://localhost:1337"

    KUPO_URL = "http://localhost:1442/v1/matches"

    chain_context = OgmiosChainContext(OGMIOS_WS, Network.TESTNET, kupo_url=KUPO_URL)

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

    @retry(tries=4, delay=1)
    def assert_output(self, target_address, target_output):
        time.sleep(1)
        utxos = self.chain_context.utxos(str(target_address))
        found = False

        for utxo in utxos:
            output = utxo.output
            if output == target_output:
                found = True

        assert found, f"Cannot find target UTxO in address: {target_address}"

    @retry(tries=4, delay=6, backoff=2, jitter=(1, 3))
    def test_mint(self):
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

        # A time policy that disallows token minting after 10000 seconds from last block
        must_before_slot = InvalidHereAfter(self.chain_context.last_block_slot + 10000)

        # Combine two policies using ScriptAll policy
        policy = ScriptAll([pub_key_policy_1, pub_key_policy_2, must_before_slot])

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
        builder = TransactionBuilder(self.chain_context)

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
        min_val = min_lovelace(Value(0, my_nft), self.chain_context)

        # Send the NFT to our own address
        nft_output = TransactionOutput(address, Value(min_val, my_nft))
        builder.add_output(nft_output)

        # Build and sign transaction
        signed_tx = builder.build_and_sign(
            [self.payment_skey, self.extended_payment_skey, policy_skey], address
        )

        print("############### Transaction created ###############")
        print(signed_tx)
        print(signed_tx.to_cbor())

        # Submit signed transaction to the network
        print("############### Submitting transaction ###############")
        self.chain_context.submit_tx(signed_tx.to_cbor())

        self.assert_output(address, nft_output)

        nft_to_send = TransactionOutput(
            address,
            Value(
                20000000,
                MultiAsset.from_primitive({policy_id.payload: {b"MY_NFT_1": 1}}),
            ),
        )

        builder = TransactionBuilder(self.chain_context)
        builder.add_input_address(address)

        builder.add_output(nft_to_send)

        # Create final signed transaction
        signed_tx = builder.build_and_sign([self.payment_skey], address)

        print("############### Transaction created ###############")
        print(signed_tx)
        print(signed_tx.to_cbor())

        # Submit signed transaction to the network
        print("############### Submitting transaction ###############")
        self.chain_context.submit_tx(signed_tx.to_cbor())

        self.assert_output(address, nft_to_send)

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

    @retry(tries=4, delay=6, backoff=2, jitter=(1, 3))
    def test_stake_delegation(self):

        address = Address(
            self.payment_key_pair.verification_key.hash(),
            self.stake_key_pair.verification_key.hash(),
            self.NETWORK,
        )

        utxos = self.chain_context.utxos(str(address))

        if not utxos:
            giver_address = Address(self.payment_vkey.hash(), network=self.NETWORK)

            builder = TransactionBuilder(self.chain_context)

            builder.add_input_address(giver_address)
            builder.add_output(TransactionOutput(address, 440000000000))

            signed_tx = builder.build_and_sign([self.payment_skey], giver_address)

            print("############### Transaction created ###############")
            print(signed_tx)
            print(signed_tx.to_cbor())
            print("############### Submitting transaction ###############")
            self.chain_context.submit_tx(signed_tx.to_cbor())

            time.sleep(3)

            stake_credential = StakeCredential(
                self.stake_key_pair.verification_key.hash()
            )
            stake_registration = StakeRegistration(stake_credential)
            pool_hash = PoolKeyHash(bytes.fromhex(os.environ.get("POOL_ID").strip()))
            stake_delegation = StakeDelegation(stake_credential, pool_keyhash=pool_hash)

            builder = TransactionBuilder(self.chain_context)

            builder.add_input_address(address)
            builder.add_output(TransactionOutput(address, 35000000))

            builder.certificates = [stake_registration, stake_delegation]

            signed_tx = builder.build_and_sign(
                [self.stake_key_pair.signing_key, self.payment_key_pair.signing_key],
                address,
            )

            print("############### Transaction created ###############")
            print(signed_tx)
            print(signed_tx.to_cbor())
            print("############### Submitting transaction ###############")
            self.chain_context.submit_tx(signed_tx.to_cbor())

        time.sleep(8)

        builder = TransactionBuilder(self.chain_context)

        builder.add_input_address(address)

        stake_address = Address(
            staking_part=self.stake_key_pair.verification_key.hash(),
            network=self.NETWORK,
        )

        builder.withdrawals = Withdrawals({bytes(stake_address): 0})

        builder.add_output(TransactionOutput(address, 1000000))

        signed_tx = builder.build_and_sign(
            [self.stake_key_pair.signing_key, self.payment_key_pair.signing_key],
            address,
        )

        print("############### Transaction created ###############")
        print(signed_tx)
        print(signed_tx.to_cbor())
        print("############### Submitting transaction ###############")
        self.chain_context.submit_tx(signed_tx.to_cbor())
