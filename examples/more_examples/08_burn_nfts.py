import os
import random
import sys
from os.path import exists

from blockfrost import ApiError, ApiUrls, BlockFrostApi, BlockFrostIPFS
from dotenv import load_dotenv

from pycardano import *

load_dotenv()
network = os.getenv("network")
wallet_mnemonic = os.getenv("wallet_mnemonic")
blockfrost_api_key = os.getenv("blockfrost_api_key")


types = ["lion", "elephant", "panda", "sloth", "tiger", "wolf"]

assets = [
    {
        "name": "CHARACTER0001",
        "attack": str(random.randint(1, 70)),
        "speed": str(random.randint(1, 70)),
        "defense": str(random.randint(1, 70)),
        "health": str(random.randint(1, 70)),
        "type": random.choice(types),
    },
    {
        "name": "CHARACTER0002",
        "attack": str(random.randint(1, 70)),
        "speed": str(random.randint(1, 70)),
        "defense": str(random.randint(1, 70)),
        "health": str(random.randint(1, 70)),
        "type": random.choice(types),
    },
    {
        "name": "CHARACTER0003",
        "attack": str(random.randint(1, 70)),
        "speed": str(random.randint(1, 70)),
        "defense": str(random.randint(1, 70)),
        "health": str(random.randint(1, 70)),
        "type": random.choice(types),
    },
    {
        "name": "CHARACTER0004",
        "attack": str(random.randint(1, 70)),
        "speed": str(random.randint(1, 70)),
        "defense": str(random.randint(1, 70)),
        "health": str(random.randint(1, 70)),
        "type": random.choice(types),
    },
    {
        "name": "CHARACTER0005",
        "attack": str(random.randint(1, 70)),
        "speed": str(random.randint(1, 70)),
        "defense": str(random.randint(1, 70)),
        "health": str(random.randint(1, 70)),
        "type": random.choice(types),
    },
]


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
receive_skey = ExtendedSigningKey.from_hdwallet(receive_key)
receive_address = Address(
    payment_part=receive_skey.to_verification_key().hash(),
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

my_asset = Asset()
my_nft = MultiAsset()

metadata = {721: {policy_id_hex: {}}}

asset_minted = []

for asset in assets:
    asset_name = asset["name"]
    asset_name_bytes = asset_name.encode("utf-8")
    metadata[721][policy_id_hex][asset_name] = {
        "name": asset_name,
        "type": asset["type"],
        "attack": asset["attack"],
        "speed": asset["speed"],
        "defense": asset["defense"],
        "health": asset["health"],
    }
    nft1 = AssetName(asset_name_bytes)
    my_asset[nft1] = -1

my_nft[policy_id] = my_asset
builder.native_scripts = native_scripts
builder.mint = my_nft


builder.add_input_address(receive_address)
signed_tx = builder.build_and_sign(
    [receive_skey, policy_signing_key], change_address=receive_address
)
result = cardano.submit_tx(signed_tx.to_cbor())

print(f"Number of inputs: \t {len(signed_tx.transaction_body.inputs)}")
print(f"Number of outputs: \t {len(signed_tx.transaction_body.outputs)}")
print(f"Fee: \t\t\t {signed_tx.transaction_body.fee/1000000} ADA")
print(f"Transaction submitted! ID: {result}")
