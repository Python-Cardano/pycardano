"""PyCardano Beginner Example 3: Query Transaction Details

Look up and analyze transaction details using a transaction hash.

Author: stnltd - Cardano Builderthon 2024
"""

import os
from pycardano import BlockFrostChainContext
from blockfrost import ApiUrls, BlockFrostApi
from datetime import datetime

BLOCKFROST_PROJECT_ID = os.getenv("BLOCKFROST_PROJECT_ID", "preprodxxxxxxxxxxxxxxxxxxxxx")
TX_HASH = "e1b9d031f487c23e9b01fa2d67e3c454ab5c44c9e3b1bc3c4c8c7b6f5c3c6c6c"

print("=" * 70)
print("PyCardano Transaction Query - Beginner Example")
print("=" * 70)
print()

try:
    context = BlockFrostChainContext(project_id=BLOCKFROST_PROJECT_ID, base_url=ApiUrls.preprod.value)
    api = BlockFrostApi(project_id=BLOCKFROST_PROJECT_ID, base_url=ApiUrls.preprod.value)
    print("Connected to Cardano Preprod Testnet")
    print()
except Exception as e:
    print(f"Connection failed: {e}")
    exit(1)

print(f"Querying transaction: {TX_HASH[:20]}...{TX_HASH[-10:]}")
print()

try:
    tx_info = api.transaction(TX_HASH)
    print("Transaction found")
    print()
except Exception as e:
    print(f"Transaction not found: {e}")
    print("Get a valid hash from: https://preprod.cardanoscan.io/")
    exit(1)

print("=" * 70)
print("TRANSACTION INFORMATION")
print("=" * 70)
print()
print(f"Transaction Hash: {tx_info.hash}")
print(f"Block:            {tx_info.block}")
print(f"Block Height:     {tx_info.block_height:,}")

tx_time = datetime.fromtimestamp(tx_info.block_time)
print(f"Time:             {tx_time.strftime('%Y-%m-%d %H:%M:%S UTC')}")
print()

fee_ada = int(tx_info.fees) / 1_000_000
print(f"Transaction Fee:  {fee_ada:.6f} ADA")
print(f"Size:             {tx_info.size:,} bytes")
print()

print("=" * 70)
print(f"INPUTS ({len(tx_info.inputs)})")
print("=" * 70)
print()

total_input = 0
for i, inp in enumerate(tx_info.inputs, 1):
    amount = int(inp.amount[0].quantity) / 1_000_000
    total_input += amount
    print(f"Input #{i}: {amount:,.6f} ADA")

print(f"\nTotal Input: {total_input:,.6f} ADA")
print()

print("=" * 70)
print(f"OUTPUTS ({len(tx_info.outputs)})")
print("=" * 70)
print()

total_output = 0
for i, out in enumerate(tx_info.outputs, 1):
    amount = int(out.amount[0].quantity) / 1_000_000
    total_output += amount
    print(f"Output #{i}: {amount:,.6f} ADA")

print(f"\nTotal Output: {total_output:,.6f} ADA")
print()

print("=" * 70)
print("View on explorer:")
print(f"https://preprod.cardanoscan.io/transaction/{TX_HASH}")
print("=" * 70)
