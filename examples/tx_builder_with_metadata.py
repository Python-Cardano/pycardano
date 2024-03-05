from blockfrost import ApiUrls
from pycardano import (
        PaymentSigningKey, 
        PaymentVerificationKey, 
        Address, 
        Network, 
        BlockFrostChainContext, 
        AuxiliaryData, 
        AlonzoMetadata, 
        Metadata, 
        TransactionBuilder, 
        TransactionOutput
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

metadata = 1337: {
                  "description": "example",
                  "name": "example",
                 }
        
# Place metadata in AuxiliaryData, the format acceptable by a transaction.
auxiliary_data = AuxiliaryData(AlonzoMetadata(metadata=Metadata(metadata)))
# Set transaction metadata
builder.auxiliary_data = auxiliary_data
# Create a transaction builder
builder = TransactionBuilder(chain_context)
# Set your address
builder.add_input_address(from_address)
# Recipient address
to_address = "cardano_address_you_want_to_send_ada_to"
# Add output and sign transaction
builder.add_output(TransactionOutput.from_primitive([to_address, 100000000000]))
signed_tx = builder.build_and_sign([sk], change_address=address)
# Send transaction
context.submit_tx(signed_tx)
