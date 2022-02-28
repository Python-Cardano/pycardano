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
chain_context = BlockFrostChainContext(block_forst_project_id, network=Network.TESTNET)


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

    # It seems like cardano-serialization-lib will sort policy and asset names by their lengths first, and then
    # by their value in lexicographical order. Therefore, without sorting, Nami wallet can potentially
    # reconstruct a different transaction where the order of asset is altered, and therefore resulting a mismatch
    # between the signature it creates and the transaction we sent to it.
    # Notice that it uses a BTreeMap to store values: https://github.com/Emurgo/cardano-serialization-lib/blob/10.0.4/rust/src/serialization.rs#L3354
    # The short-term solution is to sort policies and asset names in the same way as cardano-serialization-lib, so the
    # restored transaction in Nami wallet will be identical to the one we sent.
    # Long-term solution is to create an issue in cardano-serialization-lib and ask it to respect the order from CBOR.
    for output in tx_body.outputs:
        if isinstance(output.amount, Value):
            for policy in list(output.amount.multi_asset.keys()):
                # Sort each asset in current policy
                asset = output.amount.multi_asset[policy]
                sorted_asset = Asset(
                    sorted(
                        asset.items(), key=lambda x: (len(x[0].payload), x[0].payload)
                    )
                )
                output.amount.multi_asset[policy] = sorted_asset

            # Sort policies
            output.amount.multi_asset = MultiAsset(
                sorted(output.amount.multi_asset.items(), key=lambda x: x[0].payload)
            )

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
    cbor_hex = tx.to_cbor()
    print(cbor_hex)
    return {"tx": cbor_hex}


@app.route("/submit_tx", methods=["POST"])
def submit_tx():
    tx = compose_tx_and_witness(request.json)
    tx_id = tx.transaction_body.hash().hex()
    print(f"Transaction: \n {tx}")
    print(f"Transaction cbor: {tx.to_cbor()}")
    print(f"Transaction ID: {tx_id}")
    chain_context.submit_tx(tx.to_cbor())
    return {"tx_id": tx_id}
