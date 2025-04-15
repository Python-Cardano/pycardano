import os
import sys
from os.path import exists

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

receive_key = new_wallet.derive_from_path(f"m/1852'/1815'/0'/0/1")
reeive_skey = ExtendedSigningKey.from_hdwallet(receive_key)
receive_address = Address(
    payment_part=reeive_skey.to_verification_key().hash(),
    staking_part=staking_skey.to_verification_key().hash(),
    network=cardano_network,
)


print(" ")
print(f"Derived address: {main_address}")
print(" ")
print(f"Receive address: {receive_address}")
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

########################################################
#######           Generate Policy keys           #######
#######           IF it doesn't exist            #######
########################################################
if not exists(f"keys/policy.skey") and not exists(f"keys/policy.vkey"):
    payment_key_pair = PaymentKeyPair.generate()
    payment_signing_key = payment_key_pair.signing_key
    payment_verification_key = payment_key_pair.verification_key
    payment_signing_key.save(f"keys/policy.skey")
    payment_verification_key.save(f"keys/policy.vkey")


########################################################
#######           Initiate Policy                #######
########################################################
policy_signing_key = PaymentSigningKey.load(f"keys/policy.skey")
policy_verification_key = PaymentVerificationKey.load(f"keys/policy.vkey")
pub_key_policy = ScriptPubkey(policy_verification_key.hash())


policy = ScriptAll([pub_key_policy])

policy_id = policy.hash()
policy_id_hex = policy_id.payload.hex()
native_scripts = [policy]

asset_name = "MichielCOIN"
asset_name_bytes = asset_name.encode("utf-8")

token = AssetName(asset_name_bytes)

new_asset = Asset()
multiasset = MultiAsset()

new_asset[token] = 100

multiasset[policy_id] = new_asset


builder.native_scripts = native_scripts
builder.mint = multiasset

min_val = min_lovelace(
    cardano, output=TransactionOutput(receive_address, Value(0, multiasset))
)

builder.add_output(TransactionOutput(receive_address, Value(min_val, multiasset)))


builder.add_input_address(main_address)
signed_tx = builder.build_and_sign(
    [payment_skey, policy_signing_key], change_address=main_address
)
result = cardano.submit_tx(signed_tx.to_cbor())

print(f"Number of inputs: \t {len(signed_tx.transaction_body.inputs)}")
print(f"Number of outputs: \t {len(signed_tx.transaction_body.outputs)}")
print(f"Fee: \t\t\t {signed_tx.transaction_body.fee/1000000} ADA")
print(f"Transaction submitted! ID: {result}")
