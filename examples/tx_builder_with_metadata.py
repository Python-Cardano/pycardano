from blockfrost import ApiUrls

from pycardano import (
    Address,
    AlonzoMetadata,
    AuxiliaryData,
    BlockFrostChainContext,
    Metadata,
    Network,
    PaymentSigningKey,
    PaymentVerificationKey,
    TransactionBuilder,
    TransactionOutput,
)

# Use testnet
network = Network.TESTNET

# Read keys to memory
# Assume there is a payment.skey file sitting in current directory
payment_signing_key = PaymentSigningKey.load("payment.skey")
payment_verification_key = PaymentVerificationKey.from_signing_key(payment_signing_key)

from_address = Address(payment_verification_key.hash(), network=network)

# Create a BlockFrost chain context. In this example, we will use preprod network.
context = BlockFrostChainContext(
    "your_blockfrost_project_id", base_url=ApiUrls.preprod.value
)

# Metadata that follows the CIP-20 standard. More info here https://cips.cardano.org/cip/CIP-20/
metadata = {
    674: {
        "msg": [
            "Invoice-No: 1234567890",
            "Customer-No: 555-1234",
            "P.S.: i will shop again at your store :-)",
        ]
    }
}

# Place metadata in AuxiliaryData, the format acceptable by a transaction.
auxiliary_data = AuxiliaryData(AlonzoMetadata(metadata=Metadata(metadata)))
# Set transaction metadata
builder.auxiliary_data = auxiliary_data
# Create a transaction builder
builder = TransactionBuilder(context)
# Set your address
builder.add_input_address(from_address)
# Recipient address
to_address = "cardano_address_you_want_to_send_ada_to"
# Add output and sign transaction
builder.add_output(TransactionOutput.from_primitive([to_address, 100000000000]))
signed_tx = builder.build_and_sign([payment_signing_key], change_address=from_address)
# Send transaction
context.submit_tx(signed_tx)
