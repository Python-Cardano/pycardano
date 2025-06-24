#!/usr/bin/env python
"""
Example script to demonstrate PyCardano's governance capabilities.

This script performs the following steps:
1. Creates a DRep (Delegate Representative) voter.
2. Delegates voting power from a main account to the created DRep.
3. Creates an InfoAction governance proposal.
4. The DRep votes "Yes" on the InfoAction.

It assumes:
- A funded main payment key pair is available locally.
- Environment variables are set for network configuration and key paths.
- It uses Blockfrost as the chain context.
- Temporary files are used to store state between steps, making it resumable.
"""

import os
import time
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional

from blockfrost import ApiUrls

from pycardano import (
    # Core
    Network,
    ChainContext,
    BlockFrostChainContext,
    TransactionBuilder,
    TransactionOutput,
    TransactionId,
    UTxO,
    Value,
    # Keys & Addresses
    PaymentSigningKey,
    PaymentVerificationKey,
    StakeSigningKey,
    StakeVerificationKey,
    StakeKeyPair,
    Address,
    # Certificates
    RegDRepCert,
    StakeRegistrationAndVoteDelegation,
    DRepCredential,
    StakeCredential,
    DRep,
    DRepKind,
    # Governance
    GovActionId,
    InfoAction,
    Voter,
    VoterType,
    Vote,
    Anchor,
    AnchorDataHash,
    # Errors
    TransactionFailedException, VerificationKeyHash, AuxiliaryData, AlonzoMetadata, Metadata
)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Configuration from Environment Variables ---
NETWORK_NAME = os.environ.get("NETWORK_NAME", "preview")
ROOT_DIR = Path(os.environ.get("ROOT_DIR", Path.cwd()))
MAIN_PAYMENT_SKEY_FILE = Path(os.environ.get("MAIN_PAYMENT_SKEY_FILE", ROOT_DIR / "keys" / "main.skey"))
BLOCKFROST_PROJECT_ID = os.environ.get("BLOCKFROST_PROJECT_ID")

# Constants
ADA_TO_LOVELACE = 1_000_000
DREP_REGISTRATION_DEPOSIT = 500 * ADA_TO_LOVELACE  # Example: 500 ADA for DRep registration
STAKE_KEY_DEPOSIT = 2 * ADA_TO_LOVELACE       # Example: 2 ADA for stake key registration
PROPOSAL_DEPOSIT = 100_000 * ADA_TO_LOVELACE      # Example: 100 ADA for governance proposal
MIN_FUNDING_AMOUNT = 50 * ADA_TO_LOVELACE     # Minimum ADA to send when funding an address
TRANSACTION_WAIT_SLEEP = 15  # seconds to wait for transaction confirmation
RETRY_ATTEMPTS = 3
RETRY_DELAY = 10 # seconds

METADATA = AuxiliaryData(
    AlonzoMetadata(
        metadata=Metadata(
            {674: {"msg": ["Crafted by PyCardano Governance Demo."]}}
        )
    )
)

# --- Helper Functions ---

def get_network() -> Network:
    if NETWORK_NAME == "mainnet":
        return Network.MAINNET
    elif NETWORK_NAME == "preprod":
        return Network.TESTNET
    elif NETWORK_NAME == "preview":
        return Network.TESTNET
    else:
        logger.warning(f"Unknown network name '{NETWORK_NAME}', defaulting to Testnet.")
        return Network.TESTNET

def get_blockfrost_url(network: Network) -> str:
    if network == Network.MAINNET:
        return ApiUrls.mainnet.value
    # Default to preprod for testnets
    return ApiUrls.preview.value


def setup_directories():
    ROOT_DIR.mkdir(parents=True, exist_ok=True)
    (ROOT_DIR / "keys").mkdir(parents=True, exist_ok=True)
    (ROOT_DIR / "steps").mkdir(parents=True, exist_ok=True)

def step_file_path(step_name: str) -> Path:
    return ROOT_DIR / "steps" / f"{step_name}_completed.json"

def mark_step_done(step_name: str, data: Optional[Dict[str, Any]] = None):
    with open(step_file_path(step_name), "w") as f:
        if data:
            json.dump(data, f, indent=2)
        else:
            f.write("{}") # Empty JSON object
    logger.info(f"Step '{step_name}' marked as completed.")

def is_step_done(step_name: str) -> bool:
    return step_file_path(step_name).exists()

def load_step_data(step_name: str) -> Optional[Dict[str, Any]]:
    if is_step_done(step_name):
        with open(step_file_path(step_name), "r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                logger.error(f"Could not decode JSON from {step_file_path(step_name)}")
                return None
    return None

def save_key_pair(key_pair: StakeKeyPair, base_name: str):
    skey_path = ROOT_DIR / "keys" / f"{base_name}.skey"
    vkey_path = ROOT_DIR / "keys" / f"{base_name}.vkey"

    # Ensure keys directory exists
    skey_path.parent.mkdir(parents=True, exist_ok=True)
    
    key_pair.signing_key.save(str(skey_path))
    key_pair.verification_key.save(str(vkey_path))
    logger.info(f"Saved stake key pair '{base_name}'")

def load_or_generate_stake_key_pair(base_name: str) -> StakeKeyPair:
    skey_path = ROOT_DIR / "keys" / f"{base_name}.skey"
    vkey_path = ROOT_DIR / "keys" / f"{base_name}.vkey"

    if skey_path.exists() and vkey_path.exists():
        try:
            skey = StakeSigningKey.load(str(skey_path))
            vkey = StakeVerificationKey.load(str(vkey_path))
            # Basic check: does the loaded skey correspond to the loaded vkey?
            if skey.to_verification_key() != vkey:
                logger.warning(
                    f"Verification key loaded from {vkey_path} does not match "
                    f"signing key from {skey_path} for base name '{base_name}'. "
                    f"Will regenerate keys."
                )
                # Fall through to generate new keys
            else:
                logger.info(f"Loaded existing stake key pair for '{base_name}' from {skey_path.parent}")
                return StakeKeyPair(skey, vkey)
        except Exception as e:
            logger.warning(f"Failed to load existing key pair for '{base_name}': {e}. Will attempt to regenerate.")
            # Fall through to generate new keys if loading fails for any reason
    
    logger.info(f"Stake key pair for '{base_name}' not found or failed to load. Generating new ones.")
    key_pair = StakeKeyPair.generate()
    save_key_pair(key_pair, base_name) # save_key_pair now handles saving
    return key_pair

def load_stake_skey(base_name: str) -> StakeSigningKey:
    return StakeSigningKey.load(str(ROOT_DIR / "keys" / f"{base_name}.skey"))

def load_stake_vkey(base_name: str) -> StakeVerificationKey:
    return StakeVerificationKey.load(str(ROOT_DIR / "keys" / f"{base_name}.vkey"))

def fund_address_if_needed(
    context: BlockFrostChainContext,
    target_address: Address,
    min_amount: int,
    funder_address: Address,
    funder_skey: PaymentSigningKey,
):
    logger.info(f"Checking funds for address: {target_address}")
    utxos = context.utxos(str(target_address))
    total_balance = sum(utxo.output.amount.coin for utxo in utxos)

    if not utxos or total_balance < min_amount:
        amount_to_send = max(min_amount, MIN_FUNDING_AMOUNT) # Ensure we send at least MIN_FUNDING_AMOUNT
        logger.info(
            f"Address {target_address} has insufficient funds ({total_balance / ADA_TO_LOVELACE} ADA). "
            f"Funding with {amount_to_send / ADA_TO_LOVELACE} ADA from {funder_address}."
        )
        builder = TransactionBuilder(context)
        builder.add_input_address(funder_address)
        builder.add_output(TransactionOutput(target_address, amount_to_send))
        builder.auxiliary_data = METADATA
        signed_tx = builder.build_and_sign([funder_skey], funder_address)

        for attempt in range(RETRY_ATTEMPTS):
            try:
                logger.info(f"Submitting funding transaction: {signed_tx}")
                context.submit_tx(signed_tx.to_cbor())
                logger.info(f"Funding transaction submitted: {signed_tx.id}")
                wait_for_tx(context, signed_tx.id)
                return
            except TransactionFailedException as e:
                logger.error(f"Funding transaction failed (attempt {attempt + 1}/{RETRY_ATTEMPTS}): {e}")
                if attempt < RETRY_ATTEMPTS - 1:
                    time.sleep(RETRY_DELAY * (attempt + 1)) # Exponential backoff
                else:
                    raise
    else:
        logger.info(f"Address {target_address} has sufficient funds ({total_balance / ADA_TO_LOVELACE} ADA).")


def wait_for_tx(context: BlockFrostChainContext, tx_id: TransactionId, patience: int = 5):
    """Waits for a transaction to appear on-chain with a timeout."""
    logger.info(f"Waiting for transaction {tx_id} to be confirmed...")
    for i in range(patience * (60 // TRANSACTION_WAIT_SLEEP) ): # Wait for `patience` minutes
        try:
            # A bit of a hack: Check if any UTxO from the tx exists.
            # Blockfrost API doesn't have a direct tx confirmation status that's quick.
            # We'll try to get utxos from one of its potential outputs.
            # A more robust way would be to check if one of the input UTxOs is spent.
            # For now, just sleep, as Blockfrost can take time to index.
            # This is not a reliable way to check confirmation with Blockfrost.
            # Consider checking specific UTxO states if possible.
            # context.api.transaction_utxos(str(tx_id)) # This might work but can be slow to update
            time.sleep(TRANSACTION_WAIT_SLEEP)
            logger.info(f"Still waiting for {tx_id} ({i * TRANSACTION_WAIT_SLEEP}s elapsed)...")
            # Attempt to fetch utxos for an address we expect to change, or just rely on time.
            # This is a simplification. In production, you'd need a more robust check.
            if i > 1 : # After minimum wait, check if tx is found (may still not be confirmed)
                 tx_details = context.api.transaction(str(tx_id))
                 if tx_details:
                     logger.info(f"Transaction {tx_id} found on chain.")
                     time.sleep(TRANSACTION_WAIT_SLEEP * 2) # Extra sleep after finding
                     return
        except Exception: # ApiError if not found
            pass # Tx not found yet
    logger.warning(f"Timed out waiting for transaction {tx_id} after {patience} minutes.")
    # Not raising an error, allowing script to proceed, but this indicates potential issues.

# --- Main Script Steps ---

def step_1_create_drep(
    context: BlockFrostChainContext,
    network: Network,
    main_address: Address,
    main_payment_skey: PaymentSigningKey,
    main_payment_vkey: PaymentVerificationKey,
):
    logger.info("--- Step 1: Create DRep Voter ---")
    step_name = "1_create_drep"
    if is_step_done(step_name):
        logger.info(f"Step '{step_name}' already completed. Loading data.")
        return load_step_data(step_name)

    # 1.1 Generate or load DRep stake key pair
    drep_stake_key_pair = load_or_generate_stake_key_pair("drep_stake")
    logger.info("Ensured DRep stake key pair is available.")

    # 1.2 Create DRep address (payment part from main account, staking part from DRep stake key)
    drep_address = Address(
        payment_part=main_payment_vkey.hash(),
        staking_part=drep_stake_key_pair.verification_key.hash(),
        network=network,
    )
    logger.info(f"DRep address: {drep_address}")

    # 1.3 Fund DRep address (needs ADA for deposit and transaction fees)
    fund_address_if_needed(
        context,
        drep_address,
        DREP_REGISTRATION_DEPOSIT + 2 * ADA_TO_LOVELACE, # Deposit + buffer for fees
        main_address,
        main_payment_skey,
    )

    # 1.4 Create DRep registration certificate
    drep_credential = DRepCredential(drep_stake_key_pair.verification_key.hash())
    # Anchor can be optional, but good practice to include if DRep has off-chain presence
    anchor = Anchor(
        url="https://pycardano.drep.example.com/info",
        data_hash=AnchorDataHash(bytes.fromhex("00" * 32)), # Placeholder hash
    )
    drep_registration_cert = RegDRepCert(
        drep_credential=drep_credential,
        coin=DREP_REGISTRATION_DEPOSIT, # Deposit amount
        anchor=anchor,
    )
    logger.info("Created DRep registration certificate.")

    # 1.5 Build and submit transaction
    builder = TransactionBuilder(context)
    builder.add_input_address(str(drep_address)) # DRep address pays for its registration
    builder.certificates = [drep_registration_cert]
    builder.required_signers = [main_payment_vkey.hash(), drep_stake_key_pair.verification_key.hash()]
    builder.auxiliary_data = METADATA


    # Signatures: payment key for UTxOs, DRep stake key for the certificate
    signed_tx = builder.build_and_sign(
        signing_keys=[main_payment_skey, drep_stake_key_pair.signing_key],
        change_address=drep_address,
    )
    logger.info(f"DRep Registration TX ({signed_tx.id}):{signed_tx.transaction_body}")

    for attempt in range(RETRY_ATTEMPTS):
        try:
            context.submit_tx(signed_tx.to_cbor())
            logger.info(f"DRep registration transaction submitted: {signed_tx.id}")
            wait_for_tx(context, signed_tx.id)
            drep_data = {
                "drep_address": str(drep_address),
                "drep_stake_vkey_hash": drep_stake_key_pair.verification_key.hash().payload.hex(),
            }
            mark_step_done(step_name, drep_data)
            return drep_data
        except TransactionFailedException as e:
            logger.error(f"DRep registration transaction failed (attempt {attempt + 1}/{RETRY_ATTEMPTS}): {e}")
            if attempt < RETRY_ATTEMPTS - 1:
                time.sleep(RETRY_DELAY * (attempt + 1))
            else:
                raise

def step_2_delegate_to_drep(
    context: BlockFrostChainContext,
    network: Network,
    main_address: Address,
    main_payment_skey: PaymentSigningKey,
    main_payment_vkey: PaymentVerificationKey,
    drep_stake_vkey_hash_hex: str,
):
    logger.info("--- Step 2: Delegate Voting Power to DRep ---")
    step_name = "2_delegate_to_drep"
    if is_step_done(step_name):
        logger.info(f"Step '{step_name}' already completed. Loading data.")
        return load_step_data(step_name)

    # 2.1 Generate or load a new stake key pair for the main account's voting delegation
    main_voting_stake_key_pair = load_or_generate_stake_key_pair("main_voting_stake")
    logger.info("Ensured main account's voting stake key pair is available.")

    # 2.2 Create the main account's full address (payment + new voting stake)
    # This address will hold the deposit for the stake registration
    main_full_address = Address(
        payment_part=main_payment_vkey.hash(),
        staking_part=main_voting_stake_key_pair.verification_key.hash(),
        network=network,
    )
    logger.info(f"Main account's full address for delegation: {main_full_address}")

    # 2.3 Fund this full address
    fund_address_if_needed(
        context,
        main_full_address,
        STAKE_KEY_DEPOSIT + 1 * ADA_TO_LOVELACE, # Deposit + buffer
        main_address,
        main_payment_skey,
    )

    # 2.4 Create StakeRegistrationAndVoteDelegation certificate
    stake_credential = StakeCredential(main_voting_stake_key_pair.verification_key.hash())
    drep_credential_hash = VerificationKeyHash.from_primitive(drep_stake_vkey_hash_hex)
    drep_for_delegation = DRep(
        kind=DRepKind.VERIFICATION_KEY_HASH,
        credential=drep_credential_hash
    )

    delegation_cert = StakeRegistrationAndVoteDelegation(
        stake_credential=stake_credential,
        drep=drep_for_delegation,
        coin=STAKE_KEY_DEPOSIT, # Stake key registration deposit
    )
    logger.info("Created StakeRegistrationAndVoteDelegation certificate.")

    # 2.5 Build and submit transaction
    builder = TransactionBuilder(context)
    # The main_full_address (which includes the new stake key) pays for this
    builder.add_input_address(str(main_full_address))
    builder.certificates = [delegation_cert]
    builder.required_signers = [main_payment_vkey.hash(), main_voting_stake_key_pair.verification_key.hash()]
    builder.auxiliary_data = METADATA


    # Signatures: main payment key for UTxOs, main voting stake key for the certificate
    signed_tx = builder.build_and_sign(
        signing_keys=[main_payment_skey, main_voting_stake_key_pair.signing_key],
        change_address=main_full_address,
    )
    logger.info(f"Delegation TX ({signed_tx.id}):{signed_tx.transaction_body}")

    for attempt in range(RETRY_ATTEMPTS):
        try:
            context.submit_tx(signed_tx.to_cbor())
            logger.info(f"Delegation transaction submitted: {signed_tx.id}")
            wait_for_tx(context, signed_tx.id)
            delegation_data = {
                "main_voting_stake_vkey_hash": main_voting_stake_key_pair.verification_key.hash().payload.hex(),
                "delegated_to_drep_hash": drep_stake_vkey_hash_hex,
            }
            mark_step_done(step_name, delegation_data)
            return delegation_data
        except TransactionFailedException as e:
            logger.error(f"Delegation transaction failed (attempt {attempt + 1}/{RETRY_ATTEMPTS}): {e}")
            if attempt < RETRY_ATTEMPTS - 1:
                time.sleep(RETRY_DELAY * (attempt + 1))
            else:
                raise


def step_3_create_info_action(
    context: BlockFrostChainContext,
    drep_address_str: str, # The address that will propose the action
    drep_stake_skey: StakeSigningKey, # DRep stake key for signing (as proposer)
    main_payment_skey: PaymentSigningKey, # Main payment key for UTxOs
):
    logger.info("--- Step 3: Create an Info Action ---")
    step_name = "3_create_info_action"
    if is_step_done(step_name):
        logger.info(f"Step '{step_name}' already completed. Loading data.")
        return load_step_data(step_name)

    proposer_address = Address.from_primitive(drep_address_str)

    # 3.1 Ensure proposer_address (DRep's address) has funds for proposal deposit
    fund_address_if_needed(
        context,
        proposer_address,
        PROPOSAL_DEPOSIT + 1 * ADA_TO_LOVELACE, # Deposit + buffer
        Address(main_payment_skey.to_verification_key().hash(), network=context.network), # funder is main
        main_payment_skey,
    )

    # 3.2 Create InfoAction
    info_action = InfoAction() # Simplest action, no specific parameters
    logger.info("Created InfoAction.")

    # 3.3 Define anchor for the proposal
    proposal_anchor = Anchor(
        url="https://pycardano.infoaction.example.com/details",
        data_hash=AnchorDataHash(bytes.fromhex("11" * 32)), # Placeholder hash
    )

    # 3.4 The reward account for the proposal deposit refund.
    # This should be an address controlled by the proposer. Here, DRep's own staking part.
    reward_account_address = Address(
        staking_part=drep_stake_skey.to_verification_key().hash(),
        network=context.network
    )
    logger.info(f"Proposal reward account (for deposit refund): {reward_account_address}")


    # 3.5 Build and submit transaction for proposing the InfoAction
    builder = TransactionBuilder(context)
    builder.add_input_address(str(proposer_address)) # DRep address pays for proposal
    builder.add_proposal(
        deposit=PROPOSAL_DEPOSIT,
        # reward_account is bytes of the Shelley reward address
        reward_account=bytes(reward_account_address),
        gov_action=info_action,
        anchor=proposal_anchor,
    )
    builder.auxiliary_data = METADATA
    # builder.add_output(TransactionOutput(proposer_address, Value(MIN_FUNDING_AMOUNT))) # Example change

    # Signatures: payment key from proposer_address for UTxOs,
    # and the DRep's stake key because they are proposing.
    # The payment part of proposer_address is assumed to be main_payment_vkey.hash() from step 1.
    signed_tx = builder.build_and_sign(
        signing_keys=[main_payment_skey, drep_stake_skey],
        change_address=proposer_address,
    )
    logger.info(f"InfoAction Proposal TX ({signed_tx.id}):{signed_tx.transaction_body}")

    for attempt in range(RETRY_ATTEMPTS):
        try:
            context.submit_tx(signed_tx.to_cbor())
            logger.info(f"InfoAction proposal transaction submitted: {signed_tx.id}")
            wait_for_tx(context, signed_tx.id)

            # 3.6 Extract GovActionId
            # Assuming the InfoAction is the first (and only) proposal in this transaction
            gov_action_id = GovActionId(
                transaction_id=signed_tx.id,
                gov_action_index=0,
            )
            logger.info(f"Created GovActionId: {gov_action_id.transaction_id.payload.hex()}:{gov_action_id.gov_action_index}")

            action_data = {
                "gov_action_tx_id": gov_action_id.transaction_id.payload.hex(),
                "gov_action_index": gov_action_id.gov_action_index,
            }
            mark_step_done(step_name, action_data)
            return action_data
        except TransactionFailedException as e:
            logger.error(f"InfoAction proposal transaction failed (attempt {attempt + 1}/{RETRY_ATTEMPTS}): {e}")
            if attempt < RETRY_ATTEMPTS - 1:
                time.sleep(RETRY_DELAY * (attempt + 1))
            else:
                raise

def step_4_drep_vote_yes(
    context: BlockFrostChainContext,
    drep_address_str: str,
    drep_stake_skey: StakeSigningKey, # DRep's stake key for voting
    main_payment_skey: PaymentSigningKey, # For UTxOs from DRep's address
    gov_action_tx_id_hex: str,
    gov_action_index: int,
):
    logger.info("--- Step 4: DRep Votes 'Yes' on the Info Action ---")
    step_name = "4_drep_vote_yes"
    if is_step_done(step_name):
        logger.info(f"Step '{step_name}' already completed.")
        return load_step_data(step_name)

    voter_address = Address.from_primitive(drep_address_str)

    # 4.1 Ensure voter_address (DRep's address) has funds for transaction fee
    fund_address_if_needed(
        context,
        voter_address,
        1 * ADA_TO_LOVELACE, # Buffer for fee
        Address(main_payment_skey.to_verification_key().hash(), network=context.network),
        main_payment_skey,
    )

    # 4.2 Create Voter object for the DRep
    drep_voter = Voter(
        credential=drep_stake_skey.to_verification_key().hash(),
        voter_type=VoterType.DREP,
    )
    logger.info(f"DRep voter: {drep_voter.credential.payload.hex()} ({drep_voter.voter_type.value})")

    # 4.3 Reconstruct GovActionId
    gov_action_id = GovActionId(
        transaction_id=TransactionId.from_primitive(gov_action_tx_id_hex),
        gov_action_index=gov_action_index,
    )

    # 4.4 Define anchor for the vote
    vote_anchor = Anchor(
        url="https://pycardano.drepvote.example.com/rationale",
        data_hash=AnchorDataHash(bytes.fromhex("22" * 32)), # Placeholder hash
    )

    # 4.5 Build transaction with the vote
    builder = TransactionBuilder(context)
    builder.add_input_address(str(voter_address)) # DRep address pays for vote tx
    builder.add_vote(
        voter=drep_voter,
        gov_action_id=gov_action_id,
        vote=Vote.YES,
        anchor=vote_anchor,
    )
    builder.auxiliary_data = METADATA
    # builder.add_output(TransactionOutput(voter_address, Value(MIN_FUNDING_AMOUNT))) # Example change

    # Signatures: payment key from voter_address for UTxOs, and DRep's stake key for the vote
    signed_tx = builder.build_and_sign(
        signing_keys=[main_payment_skey, drep_stake_skey],
        change_address=voter_address,
    )
    logger.info(f"DRep Vote TX ({signed_tx.id}):{signed_tx.transaction_body}")

    for attempt in range(RETRY_ATTEMPTS):
        try:
            context.submit_tx(signed_tx.to_cbor())
            logger.info(f"DRep vote transaction submitted: {signed_tx.id}")
            wait_for_tx(context, signed_tx.id)

            vote_data = {
                "voted_on_action_tx_id": gov_action_tx_id_hex,
                "vote_tx_id": signed_tx.id.payload.hex(),
            }
            mark_step_done(step_name, vote_data)
            logger.info("DRep successfully voted 'Yes'.")
            return vote_data
        except TransactionFailedException as e:
            logger.error(f"DRep vote transaction failed (attempt {attempt + 1}/{RETRY_ATTEMPTS}): {e}")
            if attempt < RETRY_ATTEMPTS - 1:
                time.sleep(RETRY_DELAY * (attempt + 1))
            else:
                raise


# --- Main Execution ---
def main():
    logger.info("Starting PyCardano Governance Demo Script...")
    setup_directories()

    if not BLOCKFROST_PROJECT_ID:
        logger.error("BLOCKFROST_PROJECT_ID environment variable not set.")
        return

    network = get_network()
    blockfrost_url = get_blockfrost_url(network)
    context = BlockFrostChainContext(project_id=BLOCKFROST_PROJECT_ID, base_url=blockfrost_url)
    logger.info(f"Initialized BlockFrostChainContext for network: {network.name} ({blockfrost_url})")
    logger.info(f"Epoch: {context.epoch}")


    # Load main payment keys
    if not MAIN_PAYMENT_SKEY_FILE.exists():
        logger.error(
            f"Main payment key files not found: {MAIN_PAYMENT_SKEY_FILE}"
        )
        logger.error("Please generate them or update MAIN_PAYMENT_SKEY_FILE env vars.")
        return

    main_payment_skey = PaymentSigningKey.load(str(MAIN_PAYMENT_SKEY_FILE))
    main_payment_vkey = main_payment_skey.to_verification_key()
    main_address = Address(main_payment_vkey.hash(), network=network)
    logger.info(f"Loaded main payment address: {main_address}")

    # --- Execute Steps ---
    try:
        # Step 1: Create DRep
        drep_data = step_1_create_drep(
            context, network, main_address, main_payment_skey, main_payment_vkey
        )
        if not drep_data: return logger.error("Failed to complete Step 1 or load its data.")
        logger.info(f"Step 1 Result: DRep Address: {drep_data['drep_address']}, DRep Stake VKey Hash: {drep_data['drep_stake_vkey_hash']}")

        time.sleep(TRANSACTION_WAIT_SLEEP) # Allow time for DRep registration to propagate

        # Step 2: Delegate to DRep
        delegation_data = step_2_delegate_to_drep(
            context,
            network,
            main_address,
            main_payment_skey,
            main_payment_vkey,
            drep_data["drep_stake_vkey_hash"],
        )
        if not delegation_data: return logger.error("Failed to complete Step 2 or load its data.")
        logger.info(f"Step 2 Result: Main voting stake VKey Hash: {delegation_data['main_voting_stake_vkey_hash']}, Delegated to: {delegation_data['delegated_to_drep_hash']}")

        time.sleep(TRANSACTION_WAIT_SLEEP) # Allow time for delegation to propagate

        # Step 3: Create Info Action
        # DRep's stake signing key is needed to propose the action
        drep_stake_skey = load_stake_skey("drep_stake")
        # action_data = step_3_create_info_action(
        #     context,
        #     drep_data["drep_address"], # DRep's address proposes the action
        #     drep_stake_skey,
        #     main_payment_skey, # Main payment key funds the DRep's address if needed
        # )

        # For testing, we can load the action data from an existing governance action, because a governance action
        # proposal costs 100k ADA, and we don't want to spend that for this demo.
        # https://preview.cexplorer.io/tx/8b12e1d96880d2ce3dc1d57e9144f72c5ad9bda77720ac95a8a61ee46543f4cb/governance#data
        action_data = {
            "gov_action_tx_id": "8b12e1d96880d2ce3dc1d57e9144f72c5ad9bda77720ac95a8a61ee46543f4cb",
            "gov_action_index": 0,
        }

        # Step 4: DRep Votes Yes
        vote_result = step_4_drep_vote_yes(
            context,
            drep_data["drep_address"], # DRep's address submits the vote
            drep_stake_skey,
            main_payment_skey, # Main payment key for UTxOs from DRep's address
            action_data["gov_action_tx_id"],
            action_data["gov_action_index"],
        )
        if not vote_result: return logger.error("Failed to complete Step 4 or load its data.")
        logger.info(f"Step 4 Result: Vote TxID: {vote_result['vote_tx_id']}")

        logger.info("--- Governance Demo Script Completed Successfully! ---")

    except TransactionFailedException as e:
        logger.error(f"A transaction failed: {e}", exc_info=True)
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}", exc_info=True)
    finally:
        logger.info(f"Script execution finished. Check {ROOT_DIR} for logs and state files.")


if __name__ == "__main__":
    main()
