## PyCardano

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

### Installation

The library is still under development. The first release will be published to PyPI soon.

### Examples

#### Transaction creation and signing

```python
"""Build a transaction using transaction builder"""

from pycardano import *

# Use testnet
network = Network.TESTNET

# Read keys to memory
# Assume there is a payment.skey file sitting in current directory
with open("payment.skey") as f:
    psk = PaymentSigningKey.from_json(f.read())

# Assume there is a stake.skey file sitting in current directory
with open("stake.skey") as f:
    ssk = StakeSigningKey.from_json(f.read())

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
        Address.from_primitive("addr_test1vrm9x2zsux7va6w892g38tvchnzahvcd9tykqf3ygnmwtaqyfg52x"),
        Value.from_primitive(
            [1500000,
             {
                 bytes.fromhex("57fca08abbaddee36da742a839f7d83a7e1d2419f1507fcbf3916522"):  # Policy ID
                 {
                     b'CHOC': 2000
                 }
             }]
        )
    )
)

# We can add multiple outputs, similar to what we can do with inputs.
# Send 2 ADA and a native asset (CHOC) in quantity of 200 to ourselves
builder.add_output(
    TransactionOutput(
        address,
        Value.from_primitive(
            [2000000,
             {
                 bytes.fromhex("57fca08abbaddee36da742a839f7d83a7e1d2419f1507fcbf3916522"):  # Policy ID
                 {
                     b'CHOC': 200
                 }
             }]
        )
    )
)

# Build a finalized transaction body with the change returning to the address we own
tx_body = builder.build(change_address=address)

# Sign the transaction body hash using the payment signing key
signature = psk.sign(tx_body.hash())

# Add verification key and the signature to the witness set
vk_witnesses = [VerificationKeyWitness(pvk, signature)]

# Create final signed transaction
signed_tx = Transaction(tx_body, TransactionWitnessSet(vkey_witnesses=vk_witnesses))

# Submit signed transaction to the network
context.submit_tx(signed_tx.to_cbor())

```

See more usages under [examples](https://github.com/cffls/pycardano/tree/main/examples).

### Documentations

https://pycardano.readthedocs.io/en/latest/


-----------------

### Development

#### Workspace setup

Clone the repository:

`git clone https://github.com/cffls/pycardano.git`

PyCardano uses [poetry](https://python-poetry.org/) to manage its dependencies. 
Install poetry for osx / linux / bashonwindows:

`curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py | python -`

Go to [poetry installation](https://python-poetry.org/docs/#installation) for more details. 


Change directory into the repo, install all dependencies using poetry, and you are done!

`cd pycardano && poetry install`

#### Test

PyCardano uses [pytest](https://docs.pytest.org/en/6.2.x/) for unit testing.

When testing or running any program, it is recommended to enter 
a [poetry shell](https://python-poetry.org/docs/cli/#shell) in which all python dependencies are automatically 
configured: `poetry shell`.

Run all tests:
`pytest`

Run all tests including doctests:
`pytest --doctest-modules --ignore=examples`

Run all tests in a specific test file:
`pytest test/pycardano/test_transaction.py`

Run a specific test function:
`pytest -k "test_transaction_body"`

Run a specific test function in a test file:
`pytest test/pycardano/test_transaction.py -k "test_transaction_body"`

#### Test coverage

Test coverage could be checked by running:
`pytest --cov=pycardano --cov-config=.coveragerc`

A coverage report visualized in html could be generated by running:
`pytest --cov=pycardano --cov-config=.coveragerc --cov-report html:cov_html`  

Run all possible tests (including doc tests) and generate html report and terminal report:
`pytest --doctest-modules --ignore=examples --cov=pycardano --cov-config=.coveragerc --cov-report html:cov_html --cov-report term`

The generated report will be in folder `./cov_html`.

### Style guidelines

The package uses 
[Google style](https://sphinxcontrib-napoleon.readthedocs.io/en/latest/example_google.html) docstring.

The code style could be checked by [flake8](https://flake8.pycqa.org/en/latest/): `flake8 pycardano`

### Docs generation

The majority of package documentation is created by the docstrings in python files. 
We use [sphinx](https://www.sphinx-doc.org/en/master/) with 
[Read the Docs theme](https://sphinx-rtd-theme.readthedocs.io/en/stable/) to generate the 
html pages.

Build htmls: 

`cd docs && make html`

Go to the main page: 

`open build/html/index.html` 


### Feature support

- [x] Shelly address
- [x] Transaction builder
- [x] Transaction signing
- [x] Multi-asset
- [X] Chain backend integration
- [ ] Fee calculation
- [X] UTxO selection
- [X] Native script
- [ ] Plutus script
- [ ] Mnemonic 
- [ ] Byron Address
- [ ] Reward withdraw
- [ ] HD Wallet
- [ ] Staking certificates
- [ ] Protocol proposal update
