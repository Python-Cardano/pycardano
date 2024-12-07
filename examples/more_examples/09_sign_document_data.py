from pycardano import *
from dotenv import load_dotenv
import os
from os.path import exists
from blockfrost import BlockFrostApi, ApiError, ApiUrls,BlockFrostIPFS
import sys
import random
from hashlib import sha256
import urllib.request 
import json

def split_into_64chars(string):
    return [string[i:i+64] for i in range(0, len(string), 64)]

load_dotenv()
network = os.getenv('network')
wallet_mnemonic = os.getenv('wallet_mnemonic')
blockfrost_api_key = os.getenv('blockfrost_api_key')

file_url = "https://archive.podaac.earthdata.nasa.gov/podaac-ops-cumulus-docs/web-misc/opera/atbd/D-108763_Rev_A_OPERA_DSWx_S1_NI_ATBD_20240530_SIGNED.pdf"
filename = "tempfile.pdf"

urllib.request.urlretrieve(file_url, filename)


h256 = sha256()
h256.update(open(filename,'rb').read())
document_hash = h256.hexdigest()


if network=="testnet":
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


main_address=Address(payment_part=payment_skey.to_verification_key().hash(), staking_part=staking_skey.to_verification_key().hash(),network=cardano_network)


print(" ")
print(f"Derived address: {main_address}")
print(" ")

payload = {
    "document_hash": document_hash
}

payload=str(payload)

result = cip8.sign(message= payload, signing_key= payment_skey, network=cardano_network, attach_cose_key=True)



metadata = {
            1787: {  
                document_hash: {
                    "signature": split_into_64chars(result['signature']),
                }
            }
        }



api = BlockFrostApi(project_id=blockfrost_api_key, base_url=base_url)

try:
    utxos = api.address_utxos(main_address)
except Exception as e:
    if e.status_code == 404:
        print("Address does not have any UTXOs. ")
        if network=="testnet":
            print("Request tADA from the faucet: https://docs.cardano.org/cardano-testnets/tools/faucet/")
    else:
        print(e.message)
    sys.exit(1)


cardano = BlockFrostChainContext(project_id=blockfrost_api_key, base_url=base_url)

builder = TransactionBuilder(cardano)


auxiliary_data = AuxiliaryData(AlonzoMetadata(metadata=Metadata(metadata)))
builder.auxiliary_data = auxiliary_data


builder.add_input_address(main_address)
signed_tx = builder.build_and_sign([payment_skey], change_address=main_address)
result = cardano.submit_tx(signed_tx.to_cbor())

print(f"Number of inputs: \t {len(signed_tx.transaction_body.inputs)}") 
print(f"Number of outputs: \t {len(signed_tx.transaction_body.outputs)}") 
print(f"Fee: \t\t\t {signed_tx.transaction_body.fee/1000000} ADA") 
print(f"Transaction submitted! ID: {result}")