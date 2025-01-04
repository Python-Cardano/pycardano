import os

from blockfrost import ApiError, ApiUrls, BlockFrostApi, BlockFrostIPFS
from dotenv import load_dotenv

from pycardano import *

load_dotenv()
network = os.getenv("network")
wallet_mnemonic = os.getenv("wallet_mnemonic")


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


print("Enterprise address (only payment):")
print("Payment Derivation path: m/1852'/1815'/0'/0/0")

enterprise_address = Address(
    payment_part=payment_skey.to_verification_key().hash(), network=cardano_network
)
print(enterprise_address)

print(" ")
print("Staking enabled address:")
print("Payment Derivation path: m/1852'/1815'/0'/0/0")
print("Staking Derivation path: m/1852'/1815'/0'/2/0")

staking_enabled_address = Address(
    payment_part=payment_skey.to_verification_key().hash(),
    staking_part=staking_skey.to_verification_key().hash(),
    network=cardano_network,
)
print(staking_enabled_address)

print(" ")
next_step = input("Press Enter to continue...")
print(" ")

for i in range(5):
    derivation_path = f"m/1852'/1815'/0'/0/{i}"

    payment_key = new_wallet.derive_from_path(derivation_path)
    payment_skey = ExtendedSigningKey.from_hdwallet(payment_key)

    enterprise_address = Address(
        payment_part=payment_skey.to_verification_key().hash(), network=cardano_network
    )
    print(f"Address {derivation_path}: {enterprise_address}")

print(" ")
next_step = input("Press Enter to continue...")
print(" ")

for i in range(5):
    derivation_path = f"m/1852'/1815'/0'/0/{i}"

    payment_key = new_wallet.derive_from_path(derivation_path)
    payment_skey = ExtendedSigningKey.from_hdwallet(payment_key)

    staking_enabled_address = Address(
        payment_part=payment_skey.to_verification_key().hash(),
        staking_part=staking_skey.to_verification_key().hash(),
        network=cardano_network,
    )
    print(f"Address {derivation_path}: {staking_enabled_address}")
