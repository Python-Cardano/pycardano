"""An example that demonstrates low-level construction of a transaction that involves multi-asset."""

from pycardano import (
    Address,
    PaymentSigningKey,
    PaymentVerificationKey,
    Transaction,
    TransactionBody,
    TransactionInput,
    TransactionOutput,
    TransactionWitnessSet,
    Value,
    VerificationKeyWitness,
)

# Define a transaction input
tx_id_hex = "732bfd67e66be8e8288349fcaaa2294973ef6271cc189a239bb431275401b8e5"
tx_in = TransactionInput.from_primitive([tx_id_hex, 0])

# Define an output address
addr = Address.decode("addr_test1vrm9x2zsux7va6w892g38tvchnzahvcd9tykqf3ygnmwtaqyfg52x")

# Define two transaction outputs, both to the same address, but one with multi-assets.
output1 = TransactionOutput(addr, 100000000000)

# Output2 will send ADA along with multi-assets
policy_id = b"1" * 28  # A dummy policy ID
multi_asset = Value.from_primitive(
    [
        2,  # Amount of ADA (in lovelace) to send
        {
            policy_id: {
                b"Token1": 100,  # Send 100 Token1 under `policy_id`
                b"Token2": 200,  # Send 200 Token2 under `policy_id`
            }
        },
    ]
)
output2 = TransactionOutput(addr, multi_asset)

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
