"""
This is a walk through of the Wallet class in pycardano.
This class offers a number of methods which simplify many basic use cases, 
and abstracts away some of the lower level details.
If you need more advanced functionality, you can directly use the lower level classes and methods, 
sometimes in tandem with the Wallet class.

Note: If you plan to use Blockfrost as your chain context, you can set the following environment variables:
    `BLOCKFROST_ID_MAINNET` for mainnet
    `BLOCKFROST_ID_PREPROD` for preprod
    `BLOCKFROST_ID_PREVIEW` for preview
    

"""

from datetime import datetime
from multiprocessing import pool
from pycardano import *
from pycardano.wallet import Output, Wallet, Ada, TokenPolicy, Token

"""Create a new wallet"""
# Make sure to provide a name so you can easily load it later
# this will save the keys to ./keys/my_wallet.*
# payment and staking keys will be automatically generated, or loaded a wallet of the given name already exists
w = Wallet(name="my_wallet")   # set the parameter `network` to mainnet, preprod, or preview



w.query_utxos()  # query the wallet for its balance

w.utxos  # list of wallets UTXOs
w.ada    # view total amount of ADA
w.lovelace  # view total amount of lovelace
w.tokens  # get a list of all tokens in the wallet


"""Send ADA using the wallet"""

receiver = Address("addr_test1vrm9x2zsux7va6w892g38tvchnzahvcd9tykqf3ygnmwtaqyfg52x")

tx_id = w.send_ada(receiver, Ada(2))  # send 2 ADA to the receiver


"""Sending an entire UTxO"""
# useful if you have to send a refund, for example
tx_id = w.send_utxo(receiver, w.utxos[0])  # send the first UTXO in the wallet to the receiver


"""Empty an entire wallet"""
# Careful with this one!
tx_id = w.empty_wallet(receiver)


"""Sign data"""
# can sign a message with either the payment or stake keys
signed_message = w.sign_data("Hello world!", mode="payment")  # default mode is "payment"


"""Mint a token"""

# first generate a policy
my_policy = TokenPolicy(name="my_policy")  # give it a descriptive name

# generate a locking policy with expiration
# note: the actual policy locking time might be slightly off from the datetime provided
# this will save a file to ./policy/my_policy.policy
my_policy.generate_minting_policy(signers=w, expiration=datetime(2025, 5, 12, 12, 0, 0)) 

# create a token with metadata
metadata = {
    "description": "This is my first NFT thanks to PyCardano",
    "name": "PyCardano NFT example token 1",
    "id": 1,
    "image": "ipfs://QmRhTTbUrPYEw3mJGGhQqQST9k86v1DPBiTTWJGKDJsVFw",
}

my_nft = Token(policy=my_policy, amount=2, name="MY_NFT_1", metadata=metadata)

tx_id = w.mint_tokens(
    to=receiver,
    mints=my_nft,  # can be a single Token or list of multiple
)


"""Burn a token"""
# Oops, we minted two. Let's burn one.
# There are two ways to do this:

# Method 2
# create a token object with the quantity you want to burn
# note you don't have to include metadata here since it's only relevant for minting, not burning
my_nft = Token(policy=my_policy, amount=1, name="MY_NFT_1")

# this will automatically switch the amount to negative and burn them
tx_id = w.burn_tokens(my_nft)

# Method 2
# this method might be relevant in case you want to mint and burn multiple tokens in one transaction
# set amount to negative integer to burn
my_nft = Token(policy=my_policy, amount=-1, name="MY_NFT_1")  

# then use the mint_tokens method
tx_id = w.mint_tokens(
    to=receiver,
    mints=my_nft,  # can be a single Token or list of multiple
)


"""Register a stake address and delegate to a pool"""

pool_hash = "pool17arkxvwwh8rx0ldrzc54ysmpq4pd6gwzl66qe84a0nmh7qx7ze5"

tx_id = w.delegate(pool_hash)


"""Withdraw staking rewards"""
# withdraws all rewards by default, otherwise set `withdraw_amount` to a specific quantity
tx_id = w.withdraw()  

"""Fully Manual Transaction"""
# Let's make a monster transaction with all the bells and whistles

my_nft = Token(policy=my_policy, amount=1, name="MY_NFT_1", metadata=metadata)
your_nft = Token(policy=my_policy, amount=1, name="YOUR_NFT_1", metadata={"Name": "Your NFT"})


tx_id = w.transact(
    inputs=w,                                 # use all UTXOs in the wallet, can also specify unique UTxOs or addresses
    outputs=[
        Output(w, Ada(0), [my_nft]),          # mint an NFT to myself, setting Ada(0) will automatically calculate the minimum amount of ADA needed
        Output(receiver, Ada(10), [my_nft]),  # send 10 ADA and an NFT to the receiver
    ],
    mints=[my_nft, your_nft],                 # must list all mints/burns here, even if they are sent to yourself
    # signers = [w, other_w],                 # if you want to sign with multiple wallets or keys, specify them here
    delegations=pool_hash,                    # delegate to a pool
    withdrawals=Ada(2),                       # withdraw 2 ADA
    # change_address=w,                       # specify a change address, will default to itself if not specified
    message="I love PyCardano",               # attach a message to the transaction metadata [CIP-0020]
    other_metadata={                          # attach any other metadata
        "247": {"random": "metadata"}
    },
    # submit=True                             # set to False to return the transaction body as CBOR
    await_confirmation=True,                  # set to True to block the code and periodically check until the transaction is confirmed
)
