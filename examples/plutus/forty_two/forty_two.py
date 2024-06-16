"""

Off-chain code of taker and giver in fortytwo.

"""

import os

import cbor2
from blockfrost import ApiUrls
from retry import retry

from pycardano import *

NETWORK = Network.TESTNET


def get_env_val(key):
    val = os.environ.get(key)
    if not val:
        raise Exception(f"Environment variable {key} is not set!")
    return val


payment_skey = PaymentSigningKey.load(get_env_val("PAYMENT_KEY_PATH"))
payment_vkey = PaymentVerificationKey.from_signing_key(payment_skey)

chain_context = BlockFrostChainContext(
    project_id=get_env_val("BLOCKFROST_ID"),
    base_url=ApiUrls.preprod.value,
)


@retry(delay=20)
def wait_for_tx(tx_id):
    chain_context.api.transaction(tx_id)
    print(f"Transaction {tx_id} has been successfully included in the blockchain.")


def submit_tx(tx):
    print("############### Transaction created ###############")
    print(tx)
    print(tx.to_cbor_hex())
    print("############### Submitting transaction ###############")
    chain_context.submit_tx(tx)
    wait_for_tx(str(tx.id))


with open("fortytwoV2.plutus", "r") as f:
    script_hex = f.read()
    forty_two_script = PlutusV2Script(cbor2.loads(bytes.fromhex(script_hex)))


script_hash = plutus_script_hash(forty_two_script)

script_address = Address(script_hash, network=NETWORK)

giver_address = Address(payment_vkey.hash(), network=NETWORK)

builder = TransactionBuilder(chain_context)
builder.add_input_address(giver_address)
builder.add_output(TransactionOutput(giver_address, 50000000, script=forty_two_script))

signed_tx = builder.build_and_sign([payment_skey], giver_address)

print("############### Transaction created ###############")
print(signed_tx)
print("############### Submitting transaction ###############")
submit_tx(signed_tx)


# ----------- Send ADA to the script address ---------------

builder = TransactionBuilder(chain_context)
builder.add_input_address(giver_address)
datum = 42
builder.add_output(TransactionOutput(script_address, 50000000, datum=datum))

signed_tx = builder.build_and_sign([payment_skey], giver_address)

print("############### Transaction created ###############")
print(signed_tx)
print("############### Submitting transaction ###############")
submit_tx(signed_tx)

# ----------- Taker take ---------------

redeemer = Redeemer(42)

utxo_to_spend = None

# Spend the utxo with datum 42 sitting at the script address
for utxo in chain_context.utxos(script_address):
    print(utxo)
    if utxo.output.datum:
        utxo_to_spend = utxo
        break

# Find the reference script utxo
reference_script_utxo = None
for utxo in chain_context.utxos(giver_address):
    if utxo.output.script and utxo.output.script == forty_two_script:
        reference_script_utxo = utxo
        break

taker_address = Address(payment_vkey.hash(), network=NETWORK)

builder = TransactionBuilder(chain_context)

builder.add_script_input(utxo_to_spend, script=reference_script_utxo, redeemer=redeemer)
take_output = TransactionOutput(taker_address, 25123456)
builder.add_output(take_output)

signed_tx = builder.build_and_sign([payment_skey], taker_address)

print("############### Transaction created ###############")
print(signed_tx)
print("############### Submitting transaction ###############")
submit_tx(signed_tx)
