"""Build a transaction using transaction builder"""

from pycardano import *

# Use testnet
network = Network.TESTNET

# Read keys to memory
# Assume there is a payment.skey file sitting in current directory
psk = PaymentSigningKey.load("payment.skey")
# Assume there is a stake.skey file sitting in current directory
ssk = StakeSigningKey.load("stake.skey")

pvk = PaymentVerificationKey.from_signing_key(psk)
svk = StakeVerificationKey.from_signing_key(ssk)

# Derive an address from payment verification key and stake verification key
address = Address(pvk.hash(), svk.hash(), network)

# Create a BlockFrost chain context
context = BlockFrostChainContext("your_blockfrost_project_id", network)

# Create a transaction builder
builder = TransactionBuilder(context)

# Tell the builder that transaction input will come from a specific address, assuming that there are some ADA and native
# assets sitting at this address. "add_input_address" could be called multiple times with different address.
builder.add_input_address(address)

# Get all UTxOs currently sitting at this address
utxos = context.utxos(str(address))

# We can also tell the builder to include a specific UTxO in the transaction.
# Similarly, "add_input" could be called multiple times.
builder.add_input(utxos[0])

# Send 1.5 ADA and a native asset (CHOC) in quantity of 2000 to an address.
builder.add_output(
    TransactionOutput(
        Address.from_primitive(
            "addr_test1vrm9x2zsux7va6w892g38tvchnzahvcd9tykqf3ygnmwtaqyfg52x"
        ),
        Value.from_primitive(
            [
                1500000,
                {
                    bytes.fromhex(
                        "57fca08abbaddee36da742a839f7d83a7e1d2419f1507fcbf3916522"  # Policy ID
                    ): {
                        b"CHOC": 2000  # Asset name and amount
                    }
                },
            ]
        ),
    )
)

# We can add multiple outputs, similar to what we can do with inputs.
# Send 2 ADA and a native asset (CHOC) in quantity of 200 to ourselves
builder.add_output(
    TransactionOutput(
        address,
        Value.from_primitive(
            [
                2000000,
                {
                    bytes.fromhex(
                        "57fca08abbaddee36da742a839f7d83a7e1d2419f1507fcbf3916522"  # Policy ID
                    ): {
                        b"CHOC": 200  # Asset name and amount
                    }
                },
            ]
        ),
    )
)

# Create final signed transaction
signed_tx = builder.build_and_sign([psk], change_address=address)

# Submit signed transaction to the network
context.submit_tx(signed_tx.to_cbor())
