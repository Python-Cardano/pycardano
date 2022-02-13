"""An example that demonstrates low-level construction of a transaction."""

from pycardano import (
    PaymentSigningKey,
    PaymentVerificationKey,
    Transaction,
    TransactionBody,
    TransactionInput,
    TransactionOutput,
    TransactionWitnessSet,
    VerificationKeyWitness,
)

# Define a transaction input
tx_id = "732bfd67e66be8e8288349fcaaa2294973ef6271cc189a239bb431275401b8e5"
tx_in = TransactionInput.from_primitive([tx_id, 0])

# Define an output address
addr = "addr_test1vrm9x2zsux7va6w892g38tvchnzahvcd9tykqf3ygnmwtaqyfg52x"

# Define two transaction outputs, both to the same address, but with different amount.
output1 = TransactionOutput.from_primitive([addr, 100000000000])
output2 = TransactionOutput.from_primitive([addr, 799999834103])

# Create a transaction body from inputs and outputs
tx_body = TransactionBody(inputs=[tx_in], outputs=[output1, output2], fee=165897)

# Create signing key from a secret json file
sk = PaymentSigningKey.from_json(
    """{
        "type": "GenesisUTxOSigningKey_ed25519",
        "description": "Genesis Initial UTxO Signing Key",
        "cborHex": "5820093be5cd3987d0c9fd8854ef908f7746b69e2d73320db6dc0f780d81585b84c2"
    }"""
)

# Derive a verification key from the signing key
vk = PaymentVerificationKey.from_signing_key(sk)

# Sign the transaction body hash
signature = sk.sign(tx_body.hash())

# Add verification key and the signature to the witness set
vk_witnesses = [VerificationKeyWitness(vk, signature)]

# Create final signed transaction
signed_tx = Transaction(tx_body, TransactionWitnessSet(vkey_witnesses=vk_witnesses))
