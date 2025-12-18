<p align="center">
  <img src="./.github/logo.png" height=200 width=200 />
</p>

---

## PyCardano

[![PyPi version](https://badgen.net/pypi/v/pycardano)](https://pypi.python.org/pypi/pycardano/)
[![PyPI pyversions](https://img.shields.io/pypi/pyversions/pycardano)](https://pypi.python.org/pypi/pycardano/)
[![PyPI Downloads](https://static.pepy.tech/badge/pycardano/month)](https://pepy.tech/projects/pycardano)

[![PyCardano](https://github.com/Python-Cardano/pycardano/actions/workflows/main.yml/badge.svg)](https://github.com/Python-Cardano/pycardano/actions/workflows/main.yml)
[![codecov](https://codecov.io/gh/Python-Cardano/pycardano/graph/badge.svg?token=62N0IL9IMQ)](https://codecov.io/gh/Python-Cardano/pycardano)
[![Documentation Status](https://readthedocs.org/projects/pycardano/badge/?version=latest)](https://pycardano.readthedocs.io/en/latest/?badge=latest)

[![Discord](https://img.shields.io/discord/949404918903631923.svg?label=chat&logo=discord&logoColor=ffffff&color=7389D8&labelColor=6A7EC2)](https://discord.gg/qT9Mn9xjgz)
[![Twitter](https://img.shields.io/twitter/follow/PyCardano?style=social&label=Follow%20%40PyCardano)](https://twitter.com/PyCardano)


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
- [x] Pool certificate
- [x] Protocol proposal update
- [x] Governance actions
- [x] Byron Address


### Installation

Install the library using [pip](https://pip.pypa.io/en/stable/):

`pip install pycardano`

#### cbor2
[cbor2](https://github.com/agronholm/cbor2/tree/master) is a dependency of pycardano. It is used to encode and decode CBOR data.
It has two implementations: one is pure Python and the other is C, which is installed by default. The C implementation is faster, but it is less flexible than the pure Python implementation.

For some users, the C implementation may not work properly when deserializing cbor data. For example, the order of inputs of a transaction isn't guaranteed to be the same as the order of inputs in the original transaction (details could be found in [this issue](https://github.com/Python-Cardano/pycardano/issues/311)). This would result in a different transaction hash when the transaction is serialized again.

To solve this problem, a fork of cbor2 is created at [cbor2pure](https://github.com/cffls/cbor2pure). This fork removes C extension and only uses pure python for cbor decoding. By default, for correctness, pycardano uses cbor2pure in decoding. However, if speed is preferred over accuracy, users can set `CBOR_C_EXTENSION=1` in their environment, and the default C extension would be used instead.

```bash
ensure_pure_cbor2.sh
```

### Documentation

https://pycardano.readthedocs.io/en/latest/

#### Frequently asked questions

https://pycardano.readthedocs.io/en/latest/frequently_asked_questions.html

### Examples

#### Transaction creation and signing

<details>
  <summary>Expand code</summary>
  
```python
"""Build a transaction using transaction builder"""

from blockfrost import ApiUrls
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
context = BlockFrostChainContext("your_blockfrost_project_id", base_url=ApiUrls.preprod.value)

# Create a transaction builder
builder = TransactionBuilder(context)

# Tell the builder that transaction input will come from a specific address, assuming that there are some ADA and native
# assets sitting at this address. "add_input_address" could be called multiple times with different address.
builder.add_input_address(address)

# Get all UTxOs currently sitting at this address
utxos = context.utxos(address)

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
context.submit_tx(signed_tx)

```
</details>

See more usages under project [examples](https://github.com/Python-Cardano/pycardano/tree/main/examples).

There is also a collection of examples under [awesome-pycardano](https://github.com/B3nac/awesome-pycardano).

### Development

<details>
<summary>Click to expand</summary>

#### Workspace setup

Clone the repository:

`git clone https://github.com/Python-Cardano/pycardano.git`

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

## Donation and Sponsor
If you find this project helpful, please consider donate or sponsor us. Your donation and sponsor will allow us to
 spend more time on improving PyCardano and adding more features in the future.

You can support us by 1) sponsoring through Github, or 2) donating ADA to our ADA Handle `pycardano` or to the address below:

[`addr1vxa4qadv7hk2dd3jtz9rep7sp92lkgwzefwkmsy3qkglq5qzv8c0d`](https://cardanoscan.io/address/61bb5075acf5eca6b632588a3c87d00955fb21c2ca5d6dc0910591f050)

<p>
  <img src="./.github/donate_addr.png" height=150 width=150/>
</p>


## Sponsors :heart:

<p align="left">
  <a href="https://github.com/blockfrost"><img src="https://avatars.githubusercontent.com/u/70073210?s=50&v=4"/></a>
</p>
