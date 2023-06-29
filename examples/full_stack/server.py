import os

from flask import Flask, render_template, request

from pycardano import (
    Address,
    Asset,
    BlockFrostChainContext,
    MultiAsset,
    Network,
    Transaction,
    TransactionBuilder,
    TransactionOutput,
    TransactionWitnessSet,
    Value,
)

app = Flask(__name__)

block_forst_project_id = os.environ.get("BLOCKFROST_ID")

# Use BlockFrostChainContext for simplicity. You can also implement your own chain context.
chain_context = BlockFrostChainContext(
    block_forst_project_id, base_url="https://cardano-preview.blockfrost.io/api"
)


def build_transaction(data):
    input_addresses = [
        Address.from_primitive(bytes.fromhex(sender)) for sender in data["senders"]
    ]
    change_address = Address.from_primitive(bytes.fromhex(data["change_address"]))
    transaction_outputs = [
        TransactionOutput.from_primitive([address, int(amount) * 1000000])
        for address, amount in data["recipients"]
    ]

    print(f"Input addresses: {input_addresses}")
    print(f"Transaction outputs: {transaction_outputs}")
    print(f"Change address: {change_address}")

    builder = TransactionBuilder(chain_context)
    for input_address in input_addresses:
        builder.add_input_address(input_address)
    for transaction_output in transaction_outputs:
        builder.add_output(transaction_output)

    tx_body = builder.build(change_address=change_address)

    return Transaction(tx_body, TransactionWitnessSet())


def compose_tx_and_witness(data):
    tx = Transaction.from_cbor(data["tx"])
    witness = TransactionWitnessSet.from_cbor(data["witness"])
    tx.transaction_witness_set = witness
    return tx


@app.route("/")
def home_page():
    return render_template("index.html")


@app.route("/build_tx", methods=["POST"])
def build_tx():
    tx = build_transaction(request.json)
    cbor_hex = tx.to_cbor_hex()
    print(cbor_hex)
    return {"tx": cbor_hex}


@app.route("/submit_tx", methods=["POST"])
def submit_tx():
    tx = compose_tx_and_witness(request.json)
    tx_id = tx.transaction_body.hash().hex()
    print(f"Transaction: \n {tx}")
    print(f"Transaction cbor: {tx.to_cbor_hex()}")
    print(f"Transaction ID: {tx_id}")
    chain_context.submit_tx(tx)
    return {"tx_id": tx_id}
