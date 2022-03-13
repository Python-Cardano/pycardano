from dataclasses import replace
from test.pycardano.util import chain_context

import pytest

from pycardano.address import Address
from pycardano.coinselection import RandomImproveMultiAsset
from pycardano.exception import (
    InsufficientUTxOBalanceException,
    InvalidTransactionException,
)
from pycardano.key import VerificationKey
from pycardano.nativescript import (
    InvalidBefore,
    InvalidHereAfter,
    ScriptAll,
    ScriptPubkey,
)
from pycardano.transaction import MultiAsset, TransactionOutput
from pycardano.txbuilder import TransactionBuilder


def test_tx_builder(chain_context):
    tx_builder = TransactionBuilder(chain_context, [RandomImproveMultiAsset([0, 0])])
    sender = "addr_test1vrm9x2zsux7va6w892g38tvchnzahvcd9tykqf3ygnmwtaqyfg52x"
    sender_address = Address.from_primitive(sender)

    # Add sender address as input
    tx_builder.add_input_address(sender).add_output(
        TransactionOutput.from_primitive([sender, 500000])
    )

    tx_body = tx_builder.build(change_address=sender_address)

    expected = {
        0: [[b"11111111111111111111111111111111", 0]],
        1: [
            # First output
            [sender_address.to_primitive(), 500000],
            # Second output as change
            [sender_address.to_primitive(), 4334499],
        ],
        2: 165501,
    }

    assert expected == tx_body.to_primitive()


def test_tx_builder_no_change(chain_context):
    tx_builder = TransactionBuilder(chain_context, [RandomImproveMultiAsset([0, 0])])
    sender = "addr_test1vrm9x2zsux7va6w892g38tvchnzahvcd9tykqf3ygnmwtaqyfg52x"
    sender_address = Address.from_primitive(sender)

    # Add sender address as input
    tx_builder.add_input_address(sender).add_output(
        TransactionOutput.from_primitive([sender, 500000])
    )

    tx_body = tx_builder.build()


def test_tx_builder_with_certain_input(chain_context):
    tx_builder = TransactionBuilder(chain_context, [RandomImproveMultiAsset([0, 0])])
    sender = "addr_test1vrm9x2zsux7va6w892g38tvchnzahvcd9tykqf3ygnmwtaqyfg52x"
    sender_address = Address.from_primitive(sender)

    utxos = chain_context.utxos(sender)

    # Add sender address as input
    tx_builder.add_input_address(sender).add_input(utxos[1]).add_output(
        TransactionOutput.from_primitive([sender, 500000])
    )

    tx_body = tx_builder.build(change_address=sender_address)

    expected = {
        0: [[b"22222222222222222222222222222222", 1]],
        1: [
            # First output
            [sender_address.to_primitive(), 500000],
            # Second output as change
            [
                sender_address.to_primitive(),
                [
                    5332343,
                    {b"1111111111111111111111111111": {b"Token1": 1, b"Token2": 2}},
                ],
            ],
        ],
        2: 167657,
    }

    assert expected == tx_body.to_primitive()


def test_tx_builder_multi_asset(chain_context):
    tx_builder = TransactionBuilder(chain_context)
    sender = "addr_test1vrm9x2zsux7va6w892g38tvchnzahvcd9tykqf3ygnmwtaqyfg52x"
    sender_address = Address.from_primitive(sender)

    # Add sender address as input
    tx_builder.add_input_address(sender).add_output(
        TransactionOutput.from_primitive([sender, 1000000])
    ).add_output(
        TransactionOutput.from_primitive(
            [sender, [2000000, {b"1" * 28: {b"Token1": 1}}]]
        )
    )

    tx_body = tx_builder.build(change_address=sender_address)

    expected = {
        0: [
            [b"11111111111111111111111111111111", 0],
            [b"22222222222222222222222222222222", 1],
        ],
        1: [
            # First output
            [sender_address.to_primitive(), 1000000],
            # Second output
            [
                sender_address.to_primitive(),
                [2000000, {b"1111111111111111111111111111": {b"Token1": 1}}],
            ],
            # Third output as change
            [
                sender_address.to_primitive(),
                [7827679, {b"1111111111111111111111111111": {b"Token2": 2}}],
            ],
        ],
        2: 172321,
    }

    assert expected == tx_body.to_primitive()


def test_tx_too_big_exception(chain_context):
    tx_builder = TransactionBuilder(chain_context)
    sender = "addr_test1vrm9x2zsux7va6w892g38tvchnzahvcd9tykqf3ygnmwtaqyfg52x"
    sender_address = Address.from_primitive(sender)

    # Add sender address as input
    tx_builder.add_input_address(sender)
    for _ in range(500):
        tx_builder.add_output(TransactionOutput.from_primitive([sender, 10]))

    with pytest.raises(InvalidTransactionException):
        tx_body = tx_builder.build(change_address=sender_address)


def test_tx_builder_mint_multi_asset(chain_context):
    vk1 = VerificationKey.from_cbor(
        "58206443a101bdb948366fc87369336224595d36d8b0eee5602cba8b81a024e58473"
    )
    vk2 = VerificationKey.from_cbor(
        "58206443a101bdb948366fc87369336224595d36d8b0eee5602cba8b81a024e58475"
    )
    spk1 = ScriptPubkey(key_hash=vk1.hash())
    spk2 = ScriptPubkey(key_hash=vk2.hash())
    before = InvalidHereAfter(123456789)
    after = InvalidBefore(123456780)
    script = ScriptAll([before, after, spk1, ScriptAll([spk1, spk2])])
    policy_id = script.hash()

    tx_builder = TransactionBuilder(chain_context)
    sender = "addr_test1vrm9x2zsux7va6w892g38tvchnzahvcd9tykqf3ygnmwtaqyfg52x"
    sender_address = Address.from_primitive(sender)

    # Add sender address as input
    mint = {policy_id.payload: {b"Token1": 1}}
    tx_builder.add_input_address(sender).add_output(
        TransactionOutput.from_primitive([sender, 1000000])
    ).add_output(TransactionOutput.from_primitive([sender, [2000000, mint]]))
    tx_builder.mint = MultiAsset.from_primitive(mint)
    tx_builder.native_scripts = [script]
    tx_builder.ttl = 123456789

    tx_body = tx_builder.build(change_address=sender_address)

    expected = {
        0: [
            [b"11111111111111111111111111111111", 0],
            [b"22222222222222222222222222222222", 1],
        ],
        1: [
            # First output
            [sender_address.to_primitive(), 1000000],
            # Second output
            [sender_address.to_primitive(), [2000000, mint]],
            # Third output as change
            [
                sender_address.to_primitive(),
                [
                    7811003,
                    {b"1111111111111111111111111111": {b"Token1": 1, b"Token2": 2}},
                ],
            ],
        ],
        2: 188997,
        3: 123456789,
        9: mint,
    }

    assert expected == tx_body.to_primitive()


def test_tx_add_change_split_nfts(chain_context):
    # Set the max value size to be very small for testing purpose
    param = {"max_val_size": 50}
    temp_protocol_param = replace(chain_context.protocol_param, **param)
    chain_context.protocol_param = temp_protocol_param
    tx_builder = TransactionBuilder(chain_context, [RandomImproveMultiAsset([0, 0])])
    sender = "addr_test1vrm9x2zsux7va6w892g38tvchnzahvcd9tykqf3ygnmwtaqyfg52x"
    sender_address = Address.from_primitive(sender)

    tx_builder.add_input_address(sender).add_output(
        TransactionOutput.from_primitive([sender, 7000000])
    )

    tx_body = tx_builder.build(change_address=sender_address)

    expected = {
        0: [
            [b"11111111111111111111111111111111", 0],
            [b"22222222222222222222222222222222", 1],
        ],
        1: [
            # First output
            [sender_address.to_primitive(), 7000000],
            # Change output
            [
                sender_address.to_primitive(),
                [1344798, {b"1111111111111111111111111111": {b"Token1": 1}}],
            ],
            # Second change output from split due to change size limit exceed
            # Fourth output as change
            [
                sender_address.to_primitive(),
                [2482881, {b"1111111111111111111111111111": {b"Token2": 2}}],
            ],
        ],
        2: 172321,
    }

    assert expected == tx_body.to_primitive()


def test_tx_add_change_split_nfts_not_enough_add(chain_context):
    vk1 = VerificationKey.from_cbor(
        "58206443a101bdb948366fc87369336224595d36d8b0eee5602cba8b81a024e58473"
    )
    vk2 = VerificationKey.from_cbor(
        "58206443a101bdb948366fc87369336224595d36d8b0eee5602cba8b81a024e58475"
    )
    spk1 = ScriptPubkey(key_hash=vk1.hash())
    spk2 = ScriptPubkey(key_hash=vk2.hash())
    before = InvalidHereAfter(123456789)
    after = InvalidBefore(123456780)
    script = ScriptAll([before, after, spk1, ScriptAll([spk1, spk2])])
    policy_id = script.hash()

    # Set the max value size to be very small for testing purpose
    param = {"max_val_size": 50}
    temp_protocol_param = replace(chain_context.protocol_param, **param)
    chain_context.protocol_param = temp_protocol_param
    tx_builder = TransactionBuilder(chain_context)
    sender = "addr_test1vrm9x2zsux7va6w892g38tvchnzahvcd9tykqf3ygnmwtaqyfg52x"
    sender_address = Address.from_primitive(sender)

    # Add sender address as input
    mint = {policy_id.payload: {b"Token3": 1}}
    tx_builder.add_input_address(sender).add_output(
        TransactionOutput.from_primitive([sender, 7000000])
    )
    tx_builder.mint = MultiAsset.from_primitive(mint)
    tx_builder.native_scripts = [script]
    tx_builder.ttl = 123456789

    with pytest.raises(InsufficientUTxOBalanceException):
        tx_body = tx_builder.build(change_address=sender_address)


def test_not_enough_input_amount(chain_context):
    tx_builder = TransactionBuilder(chain_context)
    sender = "addr_test1vrm9x2zsux7va6w892g38tvchnzahvcd9tykqf3ygnmwtaqyfg52x"
    sender_address = Address.from_primitive(sender)
    input_utxo = chain_context.utxos(sender)[0]

    # Make output amount equal to the input amount
    tx_builder.add_input(input_utxo).add_output(
        TransactionOutput.from_primitive([sender, input_utxo.output.amount])
    )

    with pytest.raises(InvalidTransactionException):
        # Tx builder must fail here because there is not enough amount of input ADA to pay tx fee
        tx_body = tx_builder.build(change_address=sender_address)
