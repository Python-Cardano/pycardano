import os
import sys
import time

import requests
from blockfrost import ApiError, ApiUrls, BlockFrostApi, BlockFrostIPFS
from dotenv import load_dotenv

from pycardano import *

load_dotenv()
network = os.getenv("network")
wallet_mnemonic = os.getenv("wallet_mnemonic")
blockfrost_api_key = os.getenv("blockfrost_api_key")

utxos = []


def reload_utxos(main_address):
    global utxos

    print("Reloading utxos from Blockfrost")

    api = BlockFrostApi(project_id=blockfrost_api_key, base_url=base_url)

    local_utxos = api.address_utxos(main_address)

    utxos = []

    for utxo in local_utxos:
        if len(utxo.amount) == 1:
            new_utxo = {
                "tx_hash": utxo.tx_hash,
                "tx_index": utxo.tx_index,
                "amount": utxo.amount[0].quantity,
            }

            utxos.append(new_utxo)


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
cardano = BlockFrostChainContext(project_id=blockfrost_api_key, base_url=base_url)

while True:

    if len(utxos) == 0:
        reload_utxos(main_address)

    inputs = []
    outputs = []

    if len(utxos) == 0:
        print("No utxos available. Waiting 10 seconds...")
        time.sleep(10)
        continue
    else:

        total_ada_used = 0
        for utxo in utxos:

            input = TransactionInput.from_primitive([utxo["tx_hash"], utxo["tx_index"]])

            inputs.append(input)
            total_ada_used += int(utxo["amount"])

        for i in range(10):
            output = TransactionOutput(main_address, Value(10000000))
            outputs.append(output)

        ada_leftovers = total_ada_used - (10 * 10000000)

        output = TransactionOutput(main_address, Value(ada_leftovers))
        outputs.append(output)

        tx_body_estimate = TransactionBody(
            inputs=inputs, outputs=outputs, fee=1000000, ttl=72303971
        )
        vk_witnesses = []
        signature = payment_skey.sign(tx_body_estimate.hash())
        vk_witnesses.append(
            VerificationKeyWitness(payment_skey.to_verification_key(), signature)
        )

        signed_tx = Transaction(
            tx_body_estimate, TransactionWitnessSet(vkey_witnesses=vk_witnesses)
        )

        estimated_fee = fee(cardano, len(signed_tx.to_cbor()))

        ada_leftovers = total_ada_used - (10 * 10000000) - estimated_fee

        outputs = []
        for i in range(10):
            output = TransactionOutput(main_address, Value(10000000))
            outputs.append(output)

        output = TransactionOutput(main_address, Value(ada_leftovers))
        outputs.append(output)

        tx_body_estimate = TransactionBody(
            inputs=inputs, outputs=outputs, fee=estimated_fee, ttl=72303971
        )
        vk_witnesses = []
        signature = payment_skey.sign(tx_body_estimate.hash())
        vk_witnesses.append(
            VerificationKeyWitness(payment_skey.to_verification_key(), signature)
        )

        signed_tx = Transaction(
            tx_body_estimate, TransactionWitnessSet(vkey_witnesses=vk_witnesses)
        )

        try:

            result = cardano.submit_tx(signed_tx)

            if len(result) > 64:
                print(signed_tx.to_cbor_hex())
            else:

                print(f"Number of inputs: \t {len(signed_tx.transaction_body.inputs)}")
                print(
                    f"Number of outputs: \t {len(signed_tx.transaction_body.outputs)}"
                )
                print(f"Fee: \t\t\t {signed_tx.transaction_body.fee/1000000} ADA")
                print(f"Transaction submitted! ID: {result}")

                utxos = []

                for i, output in enumerate(outputs):
                    new_utxo = {
                        "tx_hash": result,
                        "tx_index": i,
                        "amount": output.amount.coin,
                    }

                    utxos.append(new_utxo)

        except Exception as e:
            print(e)
            reload_utxos(main_address)
