from pycardano.address import Address
from pycardano.coinselection import RandomImproveMultiAsset
from pycardano.transaction import TransactionOutput
from pycardano.txbuilder import TransactionBuilder

from test.pycardano.util import chain_context


def test_tx_builder(chain_context):
    tx_builder = TransactionBuilder(chain_context, [RandomImproveMultiAsset([0, 0])])
    sender = "addr_test1vrm9x2zsux7va6w892g38tvchnzahvcd9tykqf3ygnmwtaqyfg52x"
    sender_address = Address.from_primitive(sender)

    # Add sender address as input
    tx_builder.add_input_address(sender) \
        .add_output(TransactionOutput.from_primitive([sender, 500000]))

    tx_body = tx_builder.build(change_address=sender_address)

    expected = {
        0: [[b'11111111111111111111111111111111', 0]],
        1: [
            # First output
            [sender_address.to_primitive(), 500000],
            # Second output as change
            [sender_address.to_primitive(), 2325723]
        ],
        2: 2174277
    }

    assert expected == tx_body.to_primitive()


def test_tx_builder_with_certain_input(chain_context):
    tx_builder = TransactionBuilder(chain_context, [RandomImproveMultiAsset([0, 0])])
    sender = "addr_test1vrm9x2zsux7va6w892g38tvchnzahvcd9tykqf3ygnmwtaqyfg52x"
    sender_address = Address.from_primitive(sender)

    utxos = chain_context.utxos(sender)

    # Add sender address as input
    tx_builder.add_input_address(sender) \
        .add_input(utxos[1]) \
        .add_output(TransactionOutput.from_primitive([sender, 500000]))

    tx_body = tx_builder.build(change_address=sender_address)

    expected = {
        0: [[b'22222222222222222222222222222222', 1]],
        1: [
            # First output
            [sender_address.to_primitive(), 500000],
            # Second output as change
            [sender_address.to_primitive(),
             [3325723, {b'1111111111111111111111111111': {b'Token1': 1,
                                                          b'Token2': 2}}]]],
        2: 2174277
    }

    assert expected == tx_body.to_primitive()


def test_tx_builder_multi_asset(chain_context):
    tx_builder = TransactionBuilder(chain_context)
    sender = "addr_test1vrm9x2zsux7va6w892g38tvchnzahvcd9tykqf3ygnmwtaqyfg52x"
    sender_address = Address.from_primitive(sender)

    # Add sender address as input
    tx_builder.add_input_address(sender) \
        .add_output(TransactionOutput.from_primitive([sender, 1000000])) \
        .add_output(TransactionOutput.from_primitive([sender, [2000000,
                                                               {
                                                                   b"1" * 28: {
                                                                       b"Token1": 1
                                                                   }
                                                               }]]))

    tx_body = tx_builder.build(change_address=sender_address)

    expected = {
        0: [[b'11111111111111111111111111111111', 0],
            [b'22222222222222222222222222222222', 1]],
        1: [
            # First output
            [sender_address.to_primitive(), 1000000],
            # Second output
            [sender_address.to_primitive(),
             [2000000, {b'1111111111111111111111111111': {b'Token1': 1}}]],
            # Third output as change
            [sender_address.to_primitive(),
             [5825723, {b'1111111111111111111111111111': {b'Token2': 2}}]]],
        2: 2174277
    }

    assert expected == tx_body.to_primitive()
