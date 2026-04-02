"""
PyCardano Beginner Example 1: Wallet Balance Checker

This script demonstrates how to check the balance of any Cardano wallet
using PyCardano and the Blockfrost API.

What you'll learn:
- Connecting to Cardano blockchain via Blockfrost
- Working with Cardano addresses
- Understanding UTXOs (Unspent Transaction Outputs)
- Converting between lovelace and ADA

Requirements:
- pip install pycardano blockfrost-python
- Blockfrost API key from https://blockfrost.io (free)

Author: stnltd - Cardano Builderthon 2024
License: MIT
"""

import os
from pycardano import Address, BlockFrostChainContext
from blockfrost import ApiUrls

# ==============================================================================
# CONFIGURATION
# ==============================================================================

# Get your FREE Blockfrost API key at: https://blockfrost.io
# Create a project for "Preprod Testnet"
BLOCKFROST_PROJECT_ID = os.getenv(
    "BLOCKFROST_PROJECT_ID", 
    "preprodxxxxxxxxxxxxxxxxxxxxx"  # Replace with your key
)

# Example testnet address to check (you can replace with any testnet address)
# This address format starts with 'addr_test1' for testnet
WALLET_ADDRESS = "addr_test1qz2fxv2umyhttkxyxp8x0dlpdt3k6cwng5pxj3jhsydzer3n0d3vllmyqwsx5wktcd8cc3sq835lu7drv2xwl2wywfgs68faae"

# ==============================================================================
# STEP 1: Setup Blockchain Connection
# ==============================================================================

print("="*70)
print("PyCardano Wallet Balance Checker - Beginner Example")
print("="*70)
print()

try:
    # Create a connection to Cardano blockchain using Blockfrost
    # Blockfrost is a hosted API service that handles blockchain queries
    # We're using 'preprod' testnet - safe for testing without real money
    context = BlockFrostChainContext(
        project_id=BLOCKFROST_PROJECT_ID,
        base_url=ApiUrls.preprod.value  # Testnet URL
    )
    print("✓ Connected to Cardano Preprod Testnet via Blockfrost")
    print()

except Exception as e:
    print("✗ Failed to connect to Blockfrost")
    print(f"  Error: {e}")
    print()
    print("Common fixes:")
    print("  1. Check your BLOCKFROST_PROJECT_ID is correct")
    print("  2. Ensure you created a PREPROD testnet project (not mainnet)")
    print("  3. Visit https://blockfrost.io to get/verify your API key")
    exit(1)

# ==============================================================================
# STEP 2: Parse the Wallet Address
# ==============================================================================

try:
    # Convert the string address into a PyCardano Address object
    # This validates the address format and extracts its components
    address = Address.from_primitive(WALLET_ADDRESS)
    print(f"✓ Address parsed successfully")
    print(f"  Address: {WALLET_ADDRESS[:20]}...{WALLET_ADDRESS[-10:]}")
    print()

except Exception as e:
    print("✗ Invalid address format")
    print(f"  Error: {e}")
    print()
    print("Common fixes:")
    print("  1. Ensure address starts with 'addr_test1' for testnet")
    print("  2. Check for typos in the address")
    print("  3. Verify address is properly formatted (no spaces)")
    exit(1)

# ==============================================================================
# STEP 3: Query UTXOs (Unspent Transaction Outputs)
# ==============================================================================

try:
    # In Cardano, wallet balance is stored as UTXOs
    # UTXO = Unspent Transaction Output (like receiving a check)
    # Each UTXO represents some amount of ADA you can spend
    utxos = context.utxos(address)
    
    print(f"✓ Found {len(utxos)} UTXO(s) at this address")
    print()

except Exception as e:
    print("✗ Failed to query UTXOs")
    print(f"  Error: {e}")
    print()
    print("Common fixes:")
    print("  1. Check if address has ever received a transaction")
    print("  2. Verify Blockfrost API key has correct permissions")
    print("  3. Wait a moment and try again (network issue)")
    exit(1)

# ==============================================================================
# STEP 4: Calculate Total Balance
# ==============================================================================

# Initialize counters
total_lovelace = 0  # 1 ADA = 1,000,000 lovelace (smallest unit)

# Loop through each UTXO and sum up the amounts
for utxo in utxos:
    # Each UTXO has an output that contains the amount
    # The amount is in 'lovelace' (Cardano's smallest unit)
    total_lovelace += utxo.output.amount.coin

# Convert lovelace to ADA for human-readable format
# 1 ADA = 1,000,000 lovelace
total_ada = total_lovelace / 1_000_000

# ==============================================================================
# STEP 5: Display Results
# ==============================================================================

print("="*70)
print("WALLET BALANCE")
print("="*70)
print(f"Address:        {WALLET_ADDRESS}")
print(f"Total UTXOs:    {len(utxos)}")
print(f"Total Balance:  {total_ada:,.6f} ADA")
print(f"                ({total_lovelace:,} lovelace)")
print("="*70)
print()

# ==============================================================================
# STEP 6: Show Detailed UTXO Information (Optional)
# ==============================================================================

if len(utxos) > 0:
    print("UTXO DETAILS:")
    print("-" * 70)
    
    for i, utxo in enumerate(utxos, 1):
        # Convert this UTXO's lovelace to ADA
        utxo_ada = utxo.output.amount.coin / 1_000_000
        
        # Get transaction hash and output index
        tx_hash = utxo.input.transaction_id
        output_index = utxo.input.index
        
        print(f"UTXO #{i}:")
        print(f"  Amount:     {utxo_ada:,.6f} ADA ({utxo.output.amount.coin:,} lovelace)")
        print(f"  Tx Hash:    {str(tx_hash)[:20]}...{str(tx_hash)[-10:]}")
        print(f"  Output #:   {output_index}")
        print()

else:
    print("ℹ This address has no UTXOs (zero balance)")
    print()
    print("To receive testnet ADA:")
    print("  1. Visit: https://docs.cardano.org/cardano-testnet/tools/faucet/")
    print("  2. Enter your address")
    print("  3. Wait ~20 seconds for transaction to confirm")
    print("  4. Run this script again")
    print()

# ==============================================================================
# UNDERSTANDING THE OUTPUT
# ==============================================================================

print("="*70)
print("UNDERSTANDING THE RESULTS")
print("="*70)
print()
print("UTXOs (Unspent Transaction Outputs):")
print("  - Think of them like separate checks in your wallet")
print("  - Each UTXO is from a previous transaction")
print("  - When you spend, you use entire UTXOs (not partial amounts)")
print()
print("Lovelace vs ADA:")
print("  - Lovelace is the smallest unit (like cents)")
print("  - 1 ADA = 1,000,000 lovelace")
print("  - Blockchain stores amounts in lovelace")
print()
print("Next Steps:")
print("  - Try checking your own wallet address")
print("  - Run 02_simple_transfer.py to send ADA")
print("  - Learn about transactions with 03_query_transaction.py")
print()
print("=" * 70)
