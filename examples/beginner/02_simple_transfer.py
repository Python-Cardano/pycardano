"""
PyCardano Beginner Example 2: Simple ADA Transfer

This script demonstrates how to send ADA from one wallet to another
using PyCardano and the Blockfrost API.

IMPORTANT: This script works on TESTNET only. It uses test ADA with no value.

What you'll learn:
- Building transactions
- Signing with payment keys
- Calculating fees
- Submitting transactions to blockchain

Requirements:
- pip install pycardano blockfrost-python
- Blockfrost API key
- Payment signing key (.skey file) for sender wallet
- Testnet ADA in sender wallet

Author: stnltd - Cardano Builderthon 2024
License: MIT
"""

import os
from pycardano import (
    Address,
    BlockFrostChainContext,
    PaymentSigningKey,
    PaymentVerificationKey,
    TransactionBuilder,
    TransactionOutput,
)
from blockfrost import ApiUrls

# Configuration
BLOCKFROST_PROJECT_ID = os.getenv("BLOCKFROST_PROJECT_ID", "preprodxxxxxxxxxxxxxxxxxxxxx")
SENDER_SKEY_PATH = "payment.skey"
RECIPIENT_ADDRESS = "addr_test1qz2fxv2umyhttkxyxp8x0dlpdt3k6cwng5pxj3jhsydzer3n0d3vllmyqwsx5wktcd8cc3sq835lu7drv2xwl2wywfgs68faae"
AMOUNT_TO_SEND_ADA = 10.0

def load_payment_keys(skey_path):
    """Load payment signing key from file."""
    try:
        with open(skey_path, 'r') as f:
            skey_data = f.read()
        payment_skey = PaymentSigningKey.from_json(skey_data)
        payment_vkey = PaymentVerificationKey.from_signing_key(payment_skey)
        return payment_skey, payment_vkey
    except FileNotFoundError:
        print(f"Key file not found: {skey_path}")
        print()
        print("Generate keys with cardano-cli:")
        print("  cardano-cli address key-gen \\")
        print("    --verification-key-file payment.vkey \\")
        print("    --signing-key-file payment.skey")
        exit(1)
    except Exception as e:
        print(f"Failed to load keys: {e}")
        exit(1)

print("=" * 70)
print("PyCardano Simple ADA Transfer - Beginner Example")
print("=" * 70)
print()

try:
    context = BlockFrostChainContext(
        project_id=BLOCKFROST_PROJECT_ID,
        base_url=ApiUrls.preprod.value
    )
    print("Connected to Cardano Preprod Testnet")
except Exception as e:
    print(f"Connection failed: {e}")
    exit(1)

print(f"Loading payment keys from: {SENDER_SKEY_PATH}")
payment_skey, payment_vkey = load_payment_keys(SENDER_SKEY_PATH)

sender_address = Address(payment_part=payment_vkey.hash())
print(f"Sender address: {sender_address}")
print()

try:
    recipient_address = Address.from_primitive(RECIPIENT_ADDRESS)
    print(f"Recipient address parsed")
    print(f"  Recipient: {RECIPIENT_ADDRESS[:20]}...{RECIPIENT_ADDRESS[-10:]}")
    print()
except Exception as e:
    print(f"Invalid recipient address: {e}")
    exit(1)

print("Checking sender balance...")
try:
    utxos = context.utxos(sender_address)
    
    if not utxos:
        print("No UTXOs found in sender wallet (zero balance)")
        print()
        print("Get testnet ADA:")
        print("  1. Visit: https://docs.cardano.org/cardano-testnet/tools/faucet/")
        print(f"  2. Enter address: {sender_address}")
        print("  3. Wait for confirmation (~20 seconds)")
        exit(1)
    
    total_lovelace = sum(utxo.output.amount.coin for utxo in utxos)
    total_ada = total_lovelace / 1_000_000
    
    print(f"Sender balance: {total_ada:,.6f} ADA ({len(utxos)} UTXOs)")
    print()
    
    if total_ada < (AMOUNT_TO_SEND_ADA + 2):
        print(f"Insufficient balance")
        print(f"  Required: ~{AMOUNT_TO_SEND_ADA + 2} ADA (including fees)")
        print(f"  Available: {total_ada} ADA")
        exit(1)

except Exception as e:
    print(f"Failed to check balance: {e}")
    exit(1)

print("Building transaction...")

amount_lovelace = int(AMOUNT_TO_SEND_ADA * 1_000_000)

try:
    builder = TransactionBuilder(context)
    builder.add_input_address(sender_address)
    
    output = TransactionOutput(
        address=recipient_address,
        amount=amount_lovelace
    )
    builder.add_output(output)
    
    signed_tx = builder.build_and_sign(
        signing_keys=[payment_skey],
        change_address=sender_address
    )
    
    print("Transaction built and signed")
    print()
    print("Transaction Details:")
    print(f"  Amount:      {AMOUNT_TO_SEND_ADA} ADA ({amount_lovelace:,} lovelace)")
    print(f"  Fee:         {signed_tx.transaction_body.fee / 1_000_000:.6f} ADA")
    print(f"  Inputs:      {len(signed_tx.transaction_body.inputs)} UTXO(s)")
    print(f"  Outputs:     {len(signed_tx.transaction_body.outputs)} output(s)")
    print()

except Exception as e:
    print(f"Failed to build transaction: {e}")
    exit(1)

print("Submitting transaction to blockchain...")
print("WARNING: This will actually send testnet ADA!")
print()

# Uncomment to actually submit
"""
try:
    tx_hash = context.submit_tx(signed_tx)
    
    print("=" * 70)
    print("TRANSACTION SUBMITTED SUCCESSFULLY!")
    print("=" * 70)
    print()
    print(f"Transaction Hash: {tx_hash}")
    print()
    print("View on explorer:")
    print(f"  https://preprod.cardanoscan.io/transaction/{tx_hash}")
    print()

except Exception as e:
    print(f"Failed to submit transaction: {e}")
    exit(1)
"""

print("=" * 70)
print("TRANSACTION READY (Not Submitted in Example)")
print("=" * 70)
print()
print("To actually send this transaction:")
print("  1. Uncomment the submission code in this script")
print("  2. Run the script again")
print()
print("Transaction Preview:")
print(f"  From:    {sender_address}")
print(f"  To:      {recipient_address}")
print(f"  Amount:  {AMOUNT_TO_SEND_ADA} ADA")
print(f"  Fee:     ~{signed_tx.transaction_body.fee / 1_000_000:.6f} ADA")
print()
print("=" * 70)
print()
print("HOW TRANSACTIONS WORK:")
print("  1. Input Selection: PyCardano selects UTXOs automatically")
print("  2. Fee Calculation: Based on transaction size")
print("  3. Change Output: Excess returns to sender")
print("  4. Signing: Proves you own the UTXOs")
print("  5. Submission: Sent to blockchain, confirms in ~20 seconds")
print()
print("=" * 70)