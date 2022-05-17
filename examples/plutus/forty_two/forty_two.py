"""

Off-chain code of taker and giver in fortytwo.

"""


import os

import cbor2
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
    project_id=get_env_val("BLOCKFROST_ID"), network=NETWORK
)


@retry(delay=20)
def wait_for_tx(tx_id):
    chain_context.api.transaction(tx_id)
    print(f"Transaction {tx_id} has been successfully included in the blockchain.")


def submit_tx(tx):
    print("############### Transaction created ###############")
    print(tx)
    print(tx.to_cbor())
    print("############### Submitting transaction ###############")
    chain_context.submit_tx(tx.to_cbor())
    wait_for_tx(str(tx.id))


def find_collateral(target_address):
    for utxo in chain_context.utxos(str(target_address)):
        if isinstance(utxo.output.amount, int):
            return utxo
    return None


def create_collateral(target_address, skey):
    collateral_builder = TransactionBuilder(chain_context)

    collateral_builder.add_input_address(target_address)
    collateral_builder.add_output(TransactionOutput(target_address, 5000000))

    submit_tx(collateral_builder.build_and_sign([skey], target_address))


# ----------- Giver sends 10 ADA to a script address ---------------
with open("fortytwo.plutus", "r") as f:
    script_hex = f.read()
    forty_two_script = cbor2.loads(bytes.fromhex(script_hex))

script_hash = plutus_script_hash(forty_two_script)

script_address = Address(script_hash, network=NETWORK)

giver_address = Address(payment_vkey.hash(), network=NETWORK)

builder = TransactionBuilder(chain_context)
builder.add_input_address(giver_address)
datum = PlutusData()  # A Unit type "()" in Haskell
builder.add_output(
    TransactionOutput(script_address, 10000000, datum_hash=datum_hash(datum))
)

signed_tx = builder.build_and_sign([payment_skey], giver_address)

submit_tx(signed_tx)

# ----------- Taker takes 10 ADA from the script address ---------------

# taker_address could be any address. In this example, we will use the same address as giver.
taker_address = giver_address

# Notice that transaction builder will automatically estimate execution units (num steps & memory) for a redeemer if
# no execution units are provided in the constructor of Redeemer.
# Put integer 42 (the secret that unlocks the fund) in the redeemer.
redeemer = Redeemer(RedeemerTag.SPEND, 42)

utxo_to_spend = chain_context.utxos(str(script_address))[0]

builder = TransactionBuilder(chain_context)

builder.add_script_input(utxo_to_spend, forty_two_script, datum, redeemer)

# Send 5 ADA to taker address. The remaining ADA (~4.7) will be sent as change.
take_output = TransactionOutput(taker_address, 5000000)
builder.add_output(take_output)

non_nft_utxo = find_collateral(taker_address)

if non_nft_utxo is None:
    create_collateral(taker_address, payment_skey)
    non_nft_utxo = find_collateral(taker_address)

builder.collaterals.append(non_nft_utxo)

signed_tx = builder.build_and_sign([payment_skey], taker_address)

submit_tx(signed_tx)
