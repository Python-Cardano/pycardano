<p align="center">
  <img src="./logo.png" height=200 width=200 />
</p>

---

## PyCardano

[![PyPi version](https://badgen.net/pypi/v/pycardano)](https://pypi.python.org/pypi/pycardano/)
[![PyPI pyversions](https://img.shields.io/pypi/pyversions/pycardano)](https://pypi.python.org/pypi/pycardano/)
[![PyPI download month](https://img.shields.io/pypi/dm/pycardano)](https://pypi.python.org/pypi/pycardano/)
[![Discord](https://img.shields.io/discord/949404918903631923.svg?label=chat&logo=discord&logoColor=ffffff&color=7389D8&labelColor=6A7EC2)](https://discord.gg/qT9Mn9xjgz)

[![PyCardano](https://github.com/cffls/pycardano/actions/workflows/main.yml/badge.svg)](https://github.com/cffls/pycardano/actions/workflows/main.yml)
[![codecov](https://codecov.io/gh/cffls/pycardano/branch/main/graph/badge.svg?token=62N0IL9IMQ)](https://codecov.io/gh/cffls/pycardano)
[![Documentation Status](https://readthedocs.org/projects/pycardano/badge/?version=latest)](https://pycardano.readthedocs.io/en/latest/?badge=latest)


PyCardano is a Cardano library written in Python. It allows users to create and sign transactions without 
depending on third-party Cardano serialization tools, such as
[cardano-cli](https://github.com/input-output-hk/cardano-node#cardano-cli) and 
[cardano-serialization-lib](https://github.com/Emurgo/cardano-serialization-lib), making it a lightweight library, which 
is simple and fast to set up in all types of environments.

Current goal of this project is to enable developers to write off-chain code and tests in pure Python for Plutus DApps.
Nevertheless, we see the potential in expanding this project to a full Cardano node client, which 
could be beneficial for faster R&D iterations.

### Features

- [x] Shelly address
- [x] Transaction builder
- [x] Transaction signing
- [x] Multi-asset
- [X] Chain backend integration
- [X] Fee calculation
- [X] UTxO selection
- [X] Native script
- [X] Native token
- [X] Metadata
- [X] Plutus script
- [X] Staking certificates
- [X] Reward withdraw
- [X] Mnemonic 
- [X] HD Wallet
- [ ] Byron Address
- [ ] Pool certificate
- [ ] Protocol proposal update


### Installation

Install the library using [pip](https://pip.pypa.io/en/stable/):

`pip install pycardano`

### Documentation

https://pycardano.readthedocs.io/en/latest/

### Examples

#### Full stack DApp

A full stack testnet DApp is hosted on replit: https://pycardano.cffls.repl.co/

To learn more details, go to the [DApp page](https://github.com/cffls/pycardano/tree/main/examples/full_stack).

#### Transaction creation and signing

<details>
  <summary>Expand code</summary>
  
```python
"""Build a transaction using transaction builder"""

from pycardano import *

# Use testnet
network = Network.TESTNET

# Read keys to memory
# Assume there is a payment.skey file sitting in current directory
psk = PaymentSigningKey.load("payment.skey")
# Assume there is a stake.skey file sitting in current directory
ssk = StakeSigningKey.load("stake.skey")

pvk = PaymentVerificationKey.from_signing_key(psk)
svk = StakeVerificationKey.from_signing_key(ssk)

# Derive an address from payment verification key and stake verification key
address = Address(pvk.hash(), svk.hash(), network)

# Create a BlockFrost chain context
context = BlockFrostChainContext("your_blockfrost_project_id", network)

# Create a transaction builder
builder = TransactionBuilder(context)

# Tell the builder that transaction input will come from a specific address, assuming that there are some ADA and native
# assets sitting at this address. "add_input_address" could be called multiple times with different address.
builder.add_input_address(address)

# Get all UTxOs currently sitting at this address
utxos = context.utxos(str(address))

# We can also tell the builder to include a specific UTxO in the transaction.
# Similarly, "add_input" could be called multiple times.
builder.add_input(utxos[0])

# Send 1.5 ADA and a native asset (CHOC) in quantity of 2000 to an address.
builder.add_output(
    TransactionOutput(
        Address.from_primitive(
            "addr_test1vrm9x2zsux7va6w892g38tvchnzahvcd9tykqf3ygnmwtaqyfg52x"
        ),
        Value.from_primitive(
            [
                1500000,
                {
                    bytes.fromhex(
                        "57fca08abbaddee36da742a839f7d83a7e1d2419f1507fcbf3916522"  # Policy ID
                    ): {
                        b"CHOC": 2000  # Asset name and amount
                    }
                },
            ]
        ),
    )
)

# We can add multiple outputs, similar to what we can do with inputs.
# Send 2 ADA and a native asset (CHOC) in quantity of 200 to ourselves
builder.add_output(
    TransactionOutput(
        address,
        Value.from_primitive(
            [
                2000000,
                {
                    bytes.fromhex(
                        "57fca08abbaddee36da742a839f7d83a7e1d2419f1507fcbf3916522"  # Policy ID
                    ): {
                        b"CHOC": 200  # Asset name and amount
                    }
                },
            ]
        ),
    )
)

# Create final signed transaction
signed_tx = builder.build_and_sign([psk], change_address=address)

# Submit signed transaction to the network
context.submit_tx(signed_tx.to_cbor())

```
</details>

See more usages under [examples](https://github.com/cffls/pycardano/tree/main/examples).


### Development

<details>
<summary>Click to expand</summary>

#### Workspace setup

Clone the repository:

`git clone https://github.com/cffls/pycardano.git`

PyCardano uses [poetry](https://python-poetry.org/) to manage its dependencies. 
Install poetry for osx / linux / bashonwindows:

`curl -sSL https://install.python-poetry.org | python3 -`

Go to [poetry installation](https://python-poetry.org/docs/#installation) for more details. 


Change directory into the repo, install all dependencies using poetry, and you are all set!

`cd pycardano && poetry install`

When testing or running any program, it is recommended to enter 
a [poetry shell](https://python-poetry.org/docs/cli/#shell) in which all python dependencies are automatically 
configured: `poetry shell`.


#### Test

PyCardano uses [pytest](https://docs.pytest.org/en/6.2.x/) for unit testing.

Run all tests:
`make test`

Run all tests in a specific test file:
`poetry run pytest test/pycardano/test_transaction.py`

Run a specific test function:
`poetry run pytest -k "test_transaction_body"`

Run a specific test function in a test file:
`poetry run pytest test/pycardano/test_transaction.py -k "test_transaction_body"`

#### Test coverage

We use [Coverage](https://coverage.readthedocs.io/en/latest/) to calculate the test coverage.

Test coverage could be generated by: `make cov`

A html report could be generated and opened in browser by: `make cov-html`

### Style guidelines

The package uses 
[Google style](https://sphinxcontrib-napoleon.readthedocs.io/en/latest/example_google.html) docstring.

Code could be formatted with command: `make format`

The code style could be checked by [flake8](https://flake8.pycqa.org/en/latest/): `make qa`

### Docs generation

The majority of package documentation is created by the docstrings in python files. 
We use [sphinx](https://www.sphinx-doc.org/en/master/) with 
[Read the Docs theme](https://sphinx-rtd-theme.readthedocs.io/en/stable/) to generate the 
html pages.

Build docs and open the docs in browser: 

`make docs`

</details>

## Sponsors :heart:

<p align="left">
  <a href="https://www.blockery.io/"><img src="https://avatars.githubusercontent.com/u/97766045?s=50&v=4"/></a>
  <a href="https://github.com/KtorZ"><img src="https://avatars.githubusercontent.com/u/5680256?s=50&v=4"/></a>
  <a href="https://github.com/lacepool"><img src="https://avatars.githubusercontent.com/u/79309785?s=50&v=4"/></a>
  <a href="https://github.com/muppetADA"><img width="50" src="https://avatars.githubusercontent.com/u/115075316?s=50&v=4"/></a>
  <a href="https://github.com/CardanoDur"><img width="50" src="https://avatars.githubusercontent.com/u/1000466?s=50&v=4"/></a>
</p>
