import os
import sys

from blockfrost import ApiError, ApiUrls, BlockFrostApi, BlockFrostIPFS
from dotenv import load_dotenv

from pycardano import *

load_dotenv()
network = os.getenv("network")
wallet_mnemonic = os.getenv("wallet_mnemonic")
blockfrost_api_key = os.getenv("blockfrost_api_key")


if network == "testnet":
    base_url = ApiUrls.preprod.value
    cardano_network = Network.TESTNET
else:
    base_url = ApiUrls.mainnet.value
    cardano_network = Network.MAINNET


new_wallet = crypto.bip32.HDWallet.from_mnemonic(wallet_mnemonic)
payment_key = new_wallet.derive_from_path(f"m/1852'/1815'/0'/0/0")
staking_key = new_wallet.derive_from_path(f"m/1852'/1815'/0'/2/0")
payment_skey = ExtendedSigningKey.from_hdwallet(payment_key)
staking_skey = ExtendedSigningKey.from_hdwallet(staking_key)


main_address = Address(
    payment_part=payment_skey.to_verification_key().hash(),
    staking_part=staking_skey.to_verification_key().hash(),
    network=cardano_network,
)

print(" ")
print(f"Derived address: {main_address}")
print(" ")

api = BlockFrostApi(project_id=blockfrost_api_key, base_url=base_url)

try:
    utxos = api.address_utxos(main_address)
except Exception as e:
    if e.status_code == 404:
        print("Address does not have any UTXOs. ")
        if network == "testnet":
            print(
                "Request tADA from the faucet: https://docs.cardano.org/cardano-testnets/tools/faucet/"
            )
    else:
        print(e.message)
    sys.exit(1)


cardano = BlockFrostChainContext(project_id=blockfrost_api_key, base_url=base_url)

builder = TransactionBuilder(cardano)

inputs = []

total_ada_used = 0

for utxo in utxos:
    input = TransactionInput.from_primitive([utxo.tx_hash, utxo.tx_index])
    inputs.append(input)
    builder.add_input(input)
    total_ada_used += int(utxo.amount[0].quantity)

output = TransactionOutput(main_address, Value(total_ada_used))

tx_body = TransactionBody(inputs=inputs, outputs=[output], fee=100000)

signature = payment_skey.sign(tx_body.hash())
vk = PaymentVerificationKey.from_signing_key(payment_skey)
vk_witnesses = [VerificationKeyWitness(vk, signature)]
signed_tx = Transaction(tx_body, TransactionWitnessSet(vkey_witnesses=vk_witnesses))

calculated_fee = fee(cardano, len(signed_tx.to_cbor()))


total_ada_available = total_ada_used - calculated_fee
output = TransactionOutput(main_address, Value(total_ada_available))

tx_body = TransactionBody(inputs=inputs, outputs=[output], fee=calculated_fee)

signature = payment_skey.sign(tx_body.hash())
vk = PaymentVerificationKey.from_signing_key(payment_skey)
vk_witnesses = [VerificationKeyWitness(vk, signature)]
signed_tx = Transaction(tx_body, TransactionWitnessSet(vkey_witnesses=vk_witnesses))

try:
    result = cardano.submit_tx(signed_tx.to_cbor())
    print(f"Number of inputs: \t {len(signed_tx.transaction_body.inputs)}")
    print(f"Number of outputs: \t {len(signed_tx.transaction_body.outputs)}")
    print(f"Fee: \t\t\t {signed_tx.transaction_body.fee/1000000} ADA")
    print(f"Transaction submitted! ID: {result}")
except Exception as e:
    if "BadInputsUTxO" in str(e):
        print("Trying to spend an input that doesn't exist (or no longer exist).")
    elif "ValueNotConservedUTxO" in str(e):
        print(
            "Transaction not correctly balanced. Inputs and outputs (+fee) don't match."
        )
    else:
        print(e)
