markdown# PyCardano Beginner Examples

Complete beginner-friendly examples for developers new to Cardano and PyCardano.

## Prerequisites

- Python 3.8 or higher
- pip installed
- Basic understanding of blockchain concepts
- Blockfrost API key (free at https://blockfrost.io)

## Setup

1. Install PyCardano:
```bash
pip install pycardano blockfrost-python
```

2. Get Blockfrost API Key:
   - Visit https://blockfrost.io
   - Sign up for free account
   - Create project for "Preprod Testnet"
   - Copy your project ID

3. Set your API key:
```bash
export BLOCKFROST_PROJECT_ID="your_project_id_here"
```

Or edit it directly in each script.

## Examples Overview

### 01_wallet_balance.py
Check the balance of any Cardano wallet address. Perfect first script to understand:
- Blockfrost API connection
- Address handling
- UTXO concept
- Lovelace to ADA conversion

**Run:**
```bash
python 01_wallet_balance.py
```

### 02_simple_transfer.py
Send ADA from one wallet to another. Learn about:
- Transaction building
- Signing transactions
- Fee calculation
- Submitting to blockchain

**Run:**
```bash
python 02_simple_transfer.py
```

### 03_query_transaction.py
Look up transaction details by hash. Understand:
- Transaction structure
- Inputs and outputs
- Metadata
- Confirmation status

**Run:**
```bash
python 03_query_transaction.py
```

## Getting Testnet ADA

To test transfers, you need testnet ADA (worthless test tokens):

1. Visit: https://docs.cardano.org/cardano-testnet/tools/faucet/
2. Enter your testnet address
3. Receive free test ADA

## Common Issues

### "Invalid API key"
- Check your Blockfrost project ID is correct
- Ensure you're using preprod testnet key, not mainnet
- Verify key is set in environment variable or script

### "Address not found"
- Ensure you're using testnet address (starts with `addr_test1`)
- Check address is properly formatted
- Verify address has received at least one transaction

### "Insufficient funds"
- Get testnet ADA from faucet (see above)
- Wait for faucet transaction to confirm (~20 seconds)
- Check balance before attempting transfer

## Learn More

- PyCardano Docs: https://pycardano.readthedocs.io/
- Cardano Docs: https://docs.cardano.org/
- Blockfrost Docs: https://docs.blockfrost.io/

## Contributing

Found an issue or want to improve these examples? Please open an issue or PR!

## License

MIT License - Same as PyCardano

---

**Created for Cardano Builderthon 2024**
**Author: stnltd (GitHub)**
```

---

### **Step 3: Paste into VS Code**

1. **Click** in the editor area (right side where the blank file opened)
2. **Paste:** `Ctrl+V`
3. **Save:** `Ctrl+S`

---

## ✅ CHECK

**Left sidebar should now show:**
```
BEGINNER
  📄 README.md

