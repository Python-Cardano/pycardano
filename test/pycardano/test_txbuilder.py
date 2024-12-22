import copy
import logging
from dataclasses import replace
from fractions import Fraction
from test.pycardano.test_key import SK
from test.pycardano.util import check_two_way_cbor
from unittest.mock import patch

import pytest

from pycardano import (
    AssetName,
    RedeemerKey,
    RedeemerMap,
    RedeemerValue,
    min_lovelace_post_alonzo,
)
from pycardano.address import Address
from pycardano.certificate import (
    PoolRegistration,
    StakeCredential,
    StakeDelegation,
    StakeRegistration,
)
from pycardano.coinselection import RandomImproveMultiAsset
from pycardano.exception import (
    InsufficientUTxOBalanceException,
    InvalidArgumentException,
    InvalidTransactionException,
    UTxOSelectionException,
)
from pycardano.hash import (
    POOL_KEY_HASH_SIZE,
    VERIFICATION_KEY_HASH_SIZE,
    PoolKeyHash,
    TransactionId,
    VerificationKeyHash,
)
from pycardano.key import VerificationKey
from pycardano.nativescript import (
    InvalidBefore,
    InvalidHereAfter,
    ScriptAll,
    ScriptPubkey,
)
from pycardano.plutus import (
    ExecutionUnits,
    PlutusData,
    PlutusV1Script,
    PlutusV2Script,
    PlutusV3Script,
    Redeemer,
    RedeemerTag,
    plutus_script_hash,
    script_hash,
)
from pycardano.transaction import (
    MultiAsset,
    TransactionInput,
    TransactionOutput,
    UTxO,
    Value,
    Withdrawals,
)
from pycardano.txbuilder import TransactionBuilder
from pycardano.utils import fee
from pycardano.witness import TransactionWitnessSet, VerificationKeyWitness


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
            [sender_address.to_primitive(), 4334587],
        ],
        2: 165413,
    }

    assert expected == tx_body.to_primitive()


def test_tx_builder_no_change(chain_context):
    tx_builder = TransactionBuilder(chain_context, [RandomImproveMultiAsset([0, 0])])
    sender = "addr_test1vrm9x2zsux7va6w892g38tvchnzahvcd9tykqf3ygnmwtaqyfg52x"
    Address.from_primitive(sender)

    # Add sender address as input
    tx_builder.add_input_address(sender).add_output(
        TransactionOutput.from_primitive([sender, 500000])
    )

    tx_builder.build()


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
                    5332431,
                    {b"1111111111111111111111111111": {b"Token1": 1, b"Token2": 2}},
                ],
            ],
        ],
        2: 167569,
    }

    assert expected == tx_body.to_primitive()


def test_tx_builder_with_potential_inputs(chain_context):
    tx_builder = TransactionBuilder(chain_context, [RandomImproveMultiAsset([0, 0])])
    sender = "addr_test1vrm9x2zsux7va6w892g38tvchnzahvcd9tykqf3ygnmwtaqyfg52x"
    sender_address = Address.from_primitive(sender)

    utxos = chain_context.utxos(sender)

    tx_builder.potential_inputs.extend(utxos)

    for i in range(20):
        utxo = copy.deepcopy(utxos[0])
        utxo.input.index = i + 100
        tx_builder.potential_inputs.append(utxo)

    assert len(tx_builder.potential_inputs) > 1

    tx_builder.add_output(
        TransactionOutput.from_primitive(
            [sender, [5000000, {b"1111111111111111111111111111": {b"Token1": 1}}]]
        )
    )

    tx_body = tx_builder.build(change_address=sender_address)

    assert len(tx_body.inputs) < len(tx_builder.potential_inputs)


def test_tx_builder_multi_asset(chain_context):
    tx_builder = TransactionBuilder(chain_context)
    sender = "addr_test1vrm9x2zsux7va6w892g38tvchnzahvcd9tykqf3ygnmwtaqyfg52x"
    sender_address = Address.from_primitive(sender)

    # Add sender address as input
    tx_builder.add_input_address(sender).add_output(
        TransactionOutput.from_primitive([sender, 3000000])
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
            [sender_address.to_primitive(), 3000000],
            # Second output
            [
                sender_address.to_primitive(),
                [2000000, {b"1111111111111111111111111111": {b"Token1": 1}}],
            ],
            # Third output as change
            [
                sender_address.to_primitive(),
                [5827767, {b"1111111111111111111111111111": {b"Token2": 2}}],
            ],
        ],
        2: 172233,
    }

    assert expected == tx_body.to_primitive()


def test_tx_builder_raises_utxo_selection(chain_context):
    tx_builder = TransactionBuilder(chain_context)
    sender = "addr_test1vrm9x2zsux7va6w892g38tvchnzahvcd9tykqf3ygnmwtaqyfg52x"
    sender_address = Address.from_primitive(sender)

    # Add sender address as input
    tx_builder.add_input_address(sender).add_output(
        TransactionOutput.from_primitive([sender, 1000000000])
    ).add_output(
        TransactionOutput.from_primitive(
            [sender, [2000000, {b"1" * 28: {b"NewToken": 1}}]]
        )
    )

    with pytest.raises(UTxOSelectionException) as e:
        tx_builder.build(
            change_address=sender_address,
        )

    # The unfulfilled amount includes requested (991000000) and estimated fees (161277)
    assert "Unfulfilled amount:\n {\n  'coin': 991161277" in e.value.args[0]
    assert "{AssetName(b'NewToken'): 1}" in e.value.args[0]


def test_tx_builder_state_logger_warning_level(chain_context, caplog):
    with caplog.at_level(logging.WARNING):
        test_tx_builder_raises_utxo_selection(chain_context)
        assert "WARNING" in caplog.text


def test_tx_builder_state_logger_error_level(chain_context, caplog):
    with caplog.at_level(logging.ERROR):
        test_tx_builder_raises_utxo_selection(chain_context)
        assert "WARNING" not in caplog.text


def test_tx_builder_state_logger_info_level(chain_context, caplog):
    with caplog.at_level(logging.INFO):
        test_tx_builder_multi_asset(chain_context)
        assert "DEBUG" not in caplog.text


def test_tx_builder_state_logger_debug_level(chain_context, caplog):
    with caplog.at_level(logging.DEBUG):
        test_tx_builder_multi_asset(chain_context)
        assert "DEBUG" in caplog.text


def test_tx_too_big_exception(chain_context):
    tx_builder = TransactionBuilder(chain_context)
    sender = "addr_test1vrm9x2zsux7va6w892g38tvchnzahvcd9tykqf3ygnmwtaqyfg52x"
    sender_address = Address.from_primitive(sender)

    # Add sender address as input
    tx_builder.add_input_address(sender)
    for _ in range(500):
        tx_builder.add_output(TransactionOutput.from_primitive([sender, 10]))

    with pytest.raises(InvalidTransactionException):
        tx_builder.build(change_address=sender_address)


def test_tx_small_utxo_precise_fee(chain_context):
    tx_builder = TransactionBuilder(chain_context, [RandomImproveMultiAsset([0, 0])])
    sender = "addr_test1vrm9x2zsux7va6w892g38tvchnzahvcd9tykqf3ygnmwtaqyfg52x"
    sender_address = Address.from_primitive(sender)

    tx_in1 = TransactionInput.from_primitive([b"1" * 32, 3])
    tx_out1 = TransactionOutput.from_primitive([sender, 4000000])
    utxo1 = UTxO(tx_in1, tx_out1)

    tx_builder.add_input(utxo1).add_output(
        TransactionOutput.from_primitive([sender, 2500000])
    )

    # This will not fail as we replace max fee constraint with more precise fee calculation
    # And remainder is greater than minimum ada required for change
    tx_body = tx_builder.build(change_address=sender_address)

    expect = {
        0: [
            [b"11111111111111111111111111111111", 3],
        ],
        1: [
            # First output
            [sender_address.to_primitive(), 2500000],
            # Second output as change
            [sender_address.to_primitive(), 1334587],
        ],
        2: 165413,
    }

    assert expect == tx_body.to_primitive()


def test_tx_small_utxo_balance_fail(chain_context):
    tx_builder = TransactionBuilder(chain_context)
    sender = "addr_test1vrm9x2zsux7va6w892g38tvchnzahvcd9tykqf3ygnmwtaqyfg52x"
    sender_address = Address.from_primitive(sender)

    tx_in1 = TransactionInput.from_primitive([b"1" * 32, 3])
    tx_out1 = TransactionOutput.from_primitive([sender, 4000000])
    utxo1 = UTxO(tx_in1, tx_out1)

    tx_builder.add_input(utxo1).add_output(
        TransactionOutput.from_primitive([sender, 3000000])
    )

    # Balance is smaller than minimum ada required in change
    # No more UTxO is available, throwing UTxO selection exception
    with pytest.raises(UTxOSelectionException):
        tx_builder.build(change_address=sender_address)


def test_tx_small_utxo_balance_pass(chain_context):
    tx_builder = TransactionBuilder(chain_context, [RandomImproveMultiAsset([0, 0])])
    sender = "addr_test1vrm9x2zsux7va6w892g38tvchnzahvcd9tykqf3ygnmwtaqyfg52x"
    sender_address = Address.from_primitive(sender)

    tx_in1 = TransactionInput.from_primitive([b"1" * 32, 3])
    tx_out1 = TransactionOutput.from_primitive([sender, 4000000])
    utxo1 = UTxO(tx_in1, tx_out1)

    tx_builder.add_input(utxo1).add_input_address(sender_address).add_output(
        TransactionOutput.from_primitive([sender, 3000000])
    )

    # Balance is smaller than minimum ada required in change
    # Additional UTxOs are selected from the input address
    tx_body = tx_builder.build(change_address=sender_address)

    expected = {
        0: [
            [b"11111111111111111111111111111111", 0],
            [b"11111111111111111111111111111111", 3],
        ],
        1: [
            # First output
            [sender_address.to_primitive(), 3000000],
            # Second output as change
            [sender_address.to_primitive(), 5833003],
        ],
        2: 166997,
    }

    assert expected == tx_body.to_primitive()


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
    sender_address: Address = Address.from_primitive(sender)

    # Add sender address as input
    mint = {policy_id.payload: {b"Token1": 1}}
    tx_builder.add_input_address(sender).add_output(
        TransactionOutput.from_primitive([sender, 3000000])
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
            [sender_address.to_primitive(), 3000000],
            # Second output
            [sender_address.to_primitive(), [2000000, mint]],
            # Third output as change
            [
                sender_address.to_primitive(),
                [
                    5809683,
                    {b"1111111111111111111111111111": {b"Token1": 1, b"Token2": 2}},
                ],
            ],
        ],
        2: 190317,
        3: 123456789,
        8: 1000,
        9: mint,
        14: [sender_address.payment_part.to_primitive()],
    }

    assert expected == tx_body.to_primitive()


def test_tx_builder_burn_multi_asset(chain_context):
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
    sender_address: Address = Address.from_primitive(sender)

    # Add sender address as input
    to_burn = MultiAsset.from_primitive({policy_id.payload: {b"Token1": -1}})
    tx_input = TransactionInput.from_primitive([b"1" * 32, 123])
    tx_builder.potential_inputs.append(
        UTxO(
            tx_input,
            TransactionOutput.from_primitive(
                [sender, [2000000, {policy_id.payload: {b"Token1": 1}}]]
            ),
        )
    )
    tx_builder.add_input_address(sender).add_output(
        TransactionOutput.from_primitive([sender, 3000000])
    ).add_output(TransactionOutput.from_primitive([sender, 2000000]))

    tx_builder.mint = to_burn

    tx_body = tx_builder.build(change_address=sender_address)

    assert tx_input in tx_body.inputs


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
                [1034400, {b"1111111111111111111111111111": {b"Token1": 1}}],
            ],
            # Second change output from split due to change size limit exceed
            # Fourth output as change
            [
                sender_address.to_primitive(),
                [2793367, {b"1111111111111111111111111111": {b"Token2": 2}}],
            ],
        ],
        2: 172233,
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
        TransactionOutput.from_primitive([sender, 8000000])
    )
    tx_builder.mint = MultiAsset.from_primitive(mint)
    tx_builder.native_scripts = [script]
    tx_builder.ttl = 123456789

    with pytest.raises(InsufficientUTxOBalanceException):
        tx_builder.build(change_address=sender_address)


def test_not_enough_input_amount(chain_context):
    tx_builder = TransactionBuilder(chain_context)
    sender = "addr_test1vrm9x2zsux7va6w892g38tvchnzahvcd9tykqf3ygnmwtaqyfg52x"
    sender_address = Address.from_primitive(sender)
    input_utxo = chain_context.utxos(sender)[0]

    # Make output amount equal to the input amount
    tx_builder.add_input(input_utxo).add_output(
        TransactionOutput(Address.from_primitive(sender), input_utxo.output.amount)
    )

    with pytest.raises(UTxOSelectionException):
        # Tx builder must fail here because there is not enough amount of input ADA to pay tx fee
        tx_builder.build(change_address=sender_address)


def test_add_script_input(chain_context):
    tx_builder = TransactionBuilder(chain_context)
    tx_in1 = TransactionInput.from_primitive(
        ["18cbe6cadecd3f89b60e08e68e5e6c7d72d730aaa1ad21431590f7e6643438ef", 0]
    )
    tx_in2 = TransactionInput.from_primitive(
        ["18cbe6cadecd3f89b60e08e68e5e6c7d72d730aaa1ad21431590f7e6643438ef", 1]
    )
    plutus_script = PlutusV1Script(b"dummy test script")
    script_hash = plutus_script_hash(plutus_script)
    script_address = Address(script_hash)
    datum = PlutusData()
    utxo1 = UTxO(
        tx_in1, TransactionOutput(script_address, 10000000, datum_hash=datum.hash())
    )
    mint = MultiAsset.from_primitive({script_hash.payload: {b"TestToken": 1}})
    UTxO(
        tx_in2,
        TransactionOutput(
            script_address, Value(10000000, mint), datum_hash=datum.hash()
        ),
    )
    redeemer1 = Redeemer(PlutusData(), ExecutionUnits(1000000, 1000000))
    redeemer2 = Redeemer(PlutusData(), ExecutionUnits(5000000, 1000000))
    tx_builder.mint = mint
    tx_builder.add_script_input(utxo1, plutus_script, datum, redeemer1)
    tx_builder.add_minting_script(plutus_script, redeemer2)
    receiver = Address.from_primitive(
        "addr_test1vrm9x2zsux7va6w892g38tvchnzahvcd9tykqf3ygnmwtaqyfg52x"
    )
    tx_builder.add_output(TransactionOutput(receiver, 5000000))
    tx_builder.build(change_address=receiver)
    tx_builder.use_redeemer_map = False
    witness = tx_builder.build_witness_set()
    assert [datum] == witness.plutus_data
    assert [redeemer1, redeemer2] == witness.redeemer
    assert [plutus_script] == witness.plutus_v1_script

    # Test deserialization
    TransactionWitnessSet.from_cbor(witness.to_cbor_hex())


def test_add_script_input_no_script(chain_context):
    tx_builder = TransactionBuilder(chain_context)
    tx_in1 = TransactionInput.from_primitive(
        ["18cbe6cadecd3f89b60e08e68e5e6c7d72d730aaa1ad21431590f7e6643438ef", 0]
    )
    plutus_script = PlutusV1Script(b"dummy test script")
    script_hash = plutus_script_hash(plutus_script)
    script_address = Address(script_hash)
    datum = PlutusData()
    utxo1 = UTxO(
        tx_in1,
        TransactionOutput(
            script_address, 10000000, datum_hash=datum.hash(), script=plutus_script
        ),
    )
    redeemer = Redeemer(PlutusData(), ExecutionUnits(1000000, 1000000))
    tx_builder.add_script_input(utxo1, datum=datum, redeemer=redeemer)
    receiver = Address.from_primitive(
        "addr_test1vrm9x2zsux7va6w892g38tvchnzahvcd9tykqf3ygnmwtaqyfg52x"
    )
    tx_builder.add_output(TransactionOutput(receiver, 5000000))
    tx_builder.build(change_address=receiver)
    tx_builder.use_redeemer_map = False
    witness = tx_builder.build_witness_set(
        remove_dup_script=True,
    )
    assert [datum] == witness.plutus_data
    assert [redeemer] == witness.redeemer
    assert witness.plutus_v1_script is None


def test_add_script_input_payment_script(chain_context):
    tx_builder = TransactionBuilder(chain_context)
    tx_in1 = TransactionInput.from_primitive(
        ["18cbe6cadecd3f89b60e08e68e5e6c7d72d730aaa1ad21431590f7e6643438ef", 0]
    )
    plutus_script = PlutusV1Script(b"dummy test script")
    vk1 = VerificationKey.from_cbor(
        "58206443a101bdb948366fc87369336224595d36d8b0eee5602cba8b81a024e58473"
    )
    script_address = Address(vk1.hash())
    datum = PlutusData()
    utxo1 = UTxO(
        tx_in1,
        TransactionOutput(script_address, 10000000, datum_hash=datum.hash()),
    )
    redeemer = Redeemer(PlutusData(), ExecutionUnits(1000000, 1000000))
    pytest.raises(
        InvalidArgumentException,
        tx_builder.add_script_input,
        utxo1,
        datum=datum,
        redeemer=redeemer,
        script=plutus_script,
    )


def test_add_script_input_find_script(chain_context):
    original_utxos = chain_context.utxos(
        "addr_test1vrm9x2zsux7va6w892g38tvchnzahvcd9tykqf3ygnmwtaqyfg52x"
    )
    with patch.object(chain_context, "utxos") as mock_utxos:
        tx_builder = TransactionBuilder(chain_context)
        tx_in1 = TransactionInput.from_primitive(
            ["18cbe6cadecd3f89b60e08e68e5e6c7d72d730aaa1ad21431590f7e6643438ef", 0]
        )
        plutus_script = PlutusV1Script(b"dummy test script")
        script_hash = plutus_script_hash(plutus_script)
        script_address = Address(script_hash)
        datum = PlutusData()
        utxo1 = UTxO(
            tx_in1, TransactionOutput(script_address, 10000000, datum_hash=datum.hash())
        )

        existing_script_utxo = UTxO(
            TransactionInput.from_primitive(
                [
                    "41cb004bec7051621b19b46aea28f0657a586a05ce2013152ea9b9f1a5614cc7",
                    1,
                ]
            ),
            TransactionOutput(script_address, 1234567, script=plutus_script),
        )

        mock_utxos.return_value = original_utxos + [existing_script_utxo]

        redeemer = Redeemer(PlutusData(), ExecutionUnits(1000000, 1000000))
        tx_builder.add_script_input(utxo1, datum=datum, redeemer=redeemer)
        receiver = Address.from_primitive(
            "addr_test1vrm9x2zsux7va6w892g38tvchnzahvcd9tykqf3ygnmwtaqyfg52x"
        )
        tx_builder.add_output(TransactionOutput(receiver, 5000000))
        tx_body = tx_builder.build(change_address=receiver)
        tx_builder.use_redeemer_map = False
        witness = tx_builder.build_witness_set()
        assert [datum] == witness.plutus_data
        assert [redeemer] == witness.redeemer
        assert witness.plutus_v1_script is None
        assert [existing_script_utxo.input] == tx_body.reference_inputs


def test_add_script_input_with_script_from_specified_utxo(chain_context):
    tx_builder = TransactionBuilder(chain_context)
    tx_in1 = TransactionInput.from_primitive(
        ["18cbe6cadecd3f89b60e08e68e5e6c7d72d730aaa1ad21431590f7e6643438ef", 0]
    )
    plutus_script = PlutusV2Script(b"dummy test script")
    script_hash = plutus_script_hash(plutus_script)
    script_address = Address(script_hash)
    datum = PlutusData()
    utxo1 = UTxO(
        tx_in1, TransactionOutput(script_address, 10000000, datum_hash=datum.hash())
    )

    existing_script_utxo = UTxO(
        TransactionInput.from_primitive(
            [
                "41cb004bec7051621b19b46aea28f0657a586a05ce2013152ea9b9f1a5614cc7",
                1,
            ]
        ),
        TransactionOutput(script_address, 1234567, script=plutus_script),
    )

    redeemer = Redeemer(PlutusData(), ExecutionUnits(1000000, 1000000))
    tx_builder.add_script_input(
        utxo1, script=existing_script_utxo, datum=datum, redeemer=redeemer
    )
    receiver = Address.from_primitive(
        "addr_test1vrm9x2zsux7va6w892g38tvchnzahvcd9tykqf3ygnmwtaqyfg52x"
    )
    tx_builder.add_output(TransactionOutput(receiver, 5000000))
    tx_body = tx_builder.build(change_address=receiver)
    tx_builder.use_redeemer_map = False
    witness = tx_builder.build_witness_set()
    assert [datum] == witness.plutus_data
    assert [redeemer] == witness.redeemer
    assert witness.plutus_v2_script is None
    assert [existing_script_utxo.input] == tx_body.reference_inputs


def test_add_script_input_incorrect_script(chain_context):
    tx_builder = TransactionBuilder(chain_context)
    tx_in1 = TransactionInput.from_primitive(
        ["18cbe6cadecd3f89b60e08e68e5e6c7d72d730aaa1ad21431590f7e6643438ef", 0]
    )
    tx_in2 = TransactionInput.from_primitive(
        ["18cbe6cadecd3f89b60e08e68e5e6c7d72d730aaa1ad21431590f7e6643438ef", 1]
    )
    plutus_script = PlutusV1Script(b"dummy test script")
    script_hash = plutus_script_hash(plutus_script)
    incorrect_plutus_script = PlutusV2Script(b"dummy test script2")
    script_address = Address(script_hash)
    datum = PlutusData()
    utxo1 = UTxO(
        tx_in1, TransactionOutput(script_address, 10000000, datum_hash=datum.hash())
    )
    mint = MultiAsset.from_primitive({script_hash.payload: {b"TestToken": 1}})
    UTxO(
        tx_in2,
        TransactionOutput(
            script_address, Value(10000000, mint), datum_hash=datum.hash()
        ),
    )
    redeemer1 = Redeemer(PlutusData(), ExecutionUnits(1000000, 1000000))
    pytest.raises(
        InvalidArgumentException,
        tx_builder.add_script_input,
        utxo1,
        script=incorrect_plutus_script,
        datum=datum,
        redeemer=redeemer1,
    )


def test_add_script_input_no_script_no_attached_script(chain_context):
    tx_builder = TransactionBuilder(chain_context)
    tx_in1 = TransactionInput.from_primitive(
        ["18cbe6cadecd3f89b60e08e68e5e6c7d72d730aaa1ad21431590f7e6643438ef", 0]
    )
    plutus_script = PlutusV1Script(b"dummy test script")
    script_hash = plutus_script_hash(plutus_script)
    script_address = Address(script_hash)
    datum = PlutusData()
    utxo1 = UTxO(
        tx_in1,
        TransactionOutput(script_address, 10000000, datum_hash=datum.hash()),
    )
    redeemer = Redeemer(PlutusData(), ExecutionUnits(1000000, 1000000))
    pytest.raises(
        InvalidArgumentException,
        tx_builder.add_script_input,
        utxo1,
        datum=datum,
        redeemer=redeemer,
    )


def test_add_script_input_find_incorrect_script(chain_context):
    original_utxos = chain_context.utxos(
        "addr_test1vrm9x2zsux7va6w892g38tvchnzahvcd9tykqf3ygnmwtaqyfg52x"
    )
    with patch.object(chain_context, "utxos") as mock_utxos:
        tx_builder = TransactionBuilder(chain_context)
        tx_in1 = TransactionInput.from_primitive(
            ["18cbe6cadecd3f89b60e08e68e5e6c7d72d730aaa1ad21431590f7e6643438ef", 0]
        )
        plutus_script = PlutusV1Script(b"dummy test script")
        incorrect_plutus_script = PlutusV2Script(b"dummy test script2")
        script_hash = plutus_script_hash(plutus_script)
        script_address = Address(script_hash)
        datum = PlutusData()
        utxo1 = UTxO(
            tx_in1, TransactionOutput(script_address, 10000000, datum_hash=datum.hash())
        )

        existing_script_utxo = UTxO(
            TransactionInput.from_primitive(
                [
                    "41cb004bec7051621b19b46aea28f0657a586a05ce2013152ea9b9f1a5614cc7",
                    1,
                ]
            ),
            TransactionOutput(script_address, 1234567, script=incorrect_plutus_script),
        )

        mock_utxos.return_value = original_utxos + [existing_script_utxo]

        redeemer = Redeemer(PlutusData(), ExecutionUnits(1000000, 1000000))
        pytest.raises(
            InvalidArgumentException,
            tx_builder.add_script_input,
            utxo1,
            datum=datum,
            redeemer=redeemer,
        )


def test_add_script_input_with_script_from_specified_utxo_with_incorrect_script(
    chain_context,
):
    tx_builder = TransactionBuilder(chain_context)
    tx_in1 = TransactionInput.from_primitive(
        ["18cbe6cadecd3f89b60e08e68e5e6c7d72d730aaa1ad21431590f7e6643438ef", 0]
    )
    plutus_script = PlutusV2Script(b"dummy test script")
    incorrect_plutus_script = PlutusV1Script(b"dummy test script2")
    script_hash = plutus_script_hash(plutus_script)
    script_address = Address(script_hash)
    datum = PlutusData()
    utxo1 = UTxO(
        tx_in1, TransactionOutput(script_address, 10000000, datum_hash=datum.hash())
    )

    existing_script_utxo = UTxO(
        TransactionInput.from_primitive(
            [
                "41cb004bec7051621b19b46aea28f0657a586a05ce2013152ea9b9f1a5614cc7",
                1,
            ]
        ),
        TransactionOutput(script_address, 1234567, script=incorrect_plutus_script),
    )

    redeemer = Redeemer(PlutusData(), ExecutionUnits(1000000, 1000000))
    pytest.raises(
        InvalidArgumentException,
        tx_builder.add_script_input,
        utxo1,
        script=existing_script_utxo,
        datum=datum,
        redeemer=redeemer,
    )

    existing_script_utxo = UTxO(
        TransactionInput.from_primitive(
            [
                "41cb004bec7051621b19b46aea28f0657a586a05ce2013152ea9b9f1a5614cc7",
                1,
            ]
        ),
        TransactionOutput(script_address, 1234567, script=None),
    )
    pytest.raises(
        InvalidArgumentException,
        tx_builder.add_script_input,
        utxo1,
        script=existing_script_utxo,
        datum=datum,
        redeemer=redeemer,
    )


def test_add_script_input_multiple_redeemers(chain_context):
    tx_builder = TransactionBuilder(chain_context)
    tx_in1 = TransactionInput.from_primitive(
        ["18cbe6cadecd3f89b60e08e68e5e6c7d72d730aaa1ad21431590f7e6643438ef", 0]
    )
    tx_in2 = TransactionInput.from_primitive(
        ["18cbe6cadecd3f89b60e08e68e5e6c7d72d730aaa1ad21431590f7e6643438ef", 1]
    )
    plutus_script = PlutusV2Script(b"dummy test script")
    script_hash = plutus_script_hash(plutus_script)
    script_address = Address(script_hash)
    datum = PlutusData()
    utxo1 = UTxO(
        tx_in1, TransactionOutput(script_address, 10000000, datum_hash=datum.hash())
    )

    existing_script_utxo = UTxO(
        TransactionInput.from_primitive(
            [
                "41cb004bec7051621b19b46aea28f0657a586a05ce2013152ea9b9f1a5614cc7",
                1,
            ]
        ),
        TransactionOutput(script_address, 1234567, script=plutus_script),
    )

    utxo2 = UTxO(
        tx_in2, TransactionOutput(script_address, 10000000, datum_hash=datum.hash())
    )

    existing_script_utxo = UTxO(
        TransactionInput.from_primitive(
            [
                "41cb004bec7051621b19b46aea28f0657a586a05ce2013152ea9b9f1a5614cc7",
                1,
            ]
        ),
        TransactionOutput(script_address, 1234567, script=plutus_script),
    )

    tx_builder.add_script_input(
        utxo1, script=existing_script_utxo, datum=datum, redeemer=Redeemer(PlutusData())
    )

    tx_builder.add_script_input(
        utxo2, script=existing_script_utxo, datum=datum, redeemer=Redeemer(PlutusData())
    )

    pytest.raises(
        InvalidArgumentException,
        tx_builder.add_script_input,
        utxo2,
        script=existing_script_utxo,
        datum=datum,
        redeemer=Redeemer(PlutusData(), ExecutionUnits(1000000, 1000000)),
    )

    tx_builder = TransactionBuilder(chain_context)

    tx_builder.add_script_input(
        utxo1,
        script=existing_script_utxo,
        datum=datum,
        redeemer=Redeemer(PlutusData(), ExecutionUnits(1000000, 1000000)),
    )

    tx_builder.add_script_input(
        utxo2,
        script=existing_script_utxo,
        datum=datum,
        redeemer=Redeemer(PlutusData(), ExecutionUnits(1000000, 1000000)),
    )

    pytest.raises(
        InvalidArgumentException,
        tx_builder.add_script_input,
        utxo2,
        script=existing_script_utxo,
        datum=datum,
        redeemer=Redeemer(PlutusData()),
    )


def test_add_minting_script_from_specified_utxo(chain_context):
    tx_builder = TransactionBuilder(chain_context)
    plutus_script = PlutusV2Script(b"dummy test script")
    script_hash = plutus_script_hash(plutus_script)
    script_address = Address(script_hash)

    existing_script_utxo = UTxO(
        TransactionInput.from_primitive(
            [
                "41cb004bec7051621b19b46aea28f0657a586a05ce2013152ea9b9f1a5614cc7",
                1,
            ]
        ),
        TransactionOutput(script_address, 1234567, script=plutus_script),
    )

    mint = MultiAsset.from_primitive({script_hash.payload: {b"TestToken": 1}})

    redeemer = Redeemer(PlutusData(), ExecutionUnits(1000000, 1000000))
    tx_builder.add_minting_script(existing_script_utxo, redeemer=redeemer)
    receiver = Address.from_primitive(
        "addr_test1vrm9x2zsux7va6w892g38tvchnzahvcd9tykqf3ygnmwtaqyfg52x"
    )
    tx_builder.add_input_address(
        "addr_test1vrm9x2zsux7va6w892g38tvchnzahvcd9tykqf3ygnmwtaqyfg52x"
    )
    tx_builder.add_output(TransactionOutput(receiver, 5000000))
    tx_builder.mint = mint
    tx_body = tx_builder.build(change_address=receiver)
    tx_builder.use_redeemer_map = False
    witness = tx_builder.build_witness_set()
    assert witness.plutus_data is None
    assert [redeemer] == witness.redeemer
    assert witness.plutus_v2_script is None
    assert [existing_script_utxo.input] == tx_body.reference_inputs


def test_collateral_return(chain_context):
    original_utxos = chain_context.utxos(
        "addr_test1vrm9x2zsux7va6w892g38tvchnzahvcd9tykqf3ygnmwtaqyfg52x"
    )
    with patch.object(chain_context, "utxos") as mock_utxos:
        tx_builder = TransactionBuilder(chain_context)
        tx_in1 = TransactionInput.from_primitive(
            ["18cbe6cadecd3f89b60e08e68e5e6c7d72d730aaa1ad21431590f7e6643438ef", 0]
        )
        plutus_script = PlutusV1Script(b"dummy test script")
        script_hash = plutus_script_hash(plutus_script)
        script_address = Address(script_hash)
        datum = PlutusData()
        utxo1 = UTxO(
            tx_in1, TransactionOutput(script_address, 10000000, datum_hash=datum.hash())
        )

        existing_script_utxo = UTxO(
            TransactionInput.from_primitive(
                [
                    "41cb004bec7051621b19b46aea28f0657a586a05ce2013152ea9b9f1a5614cc7",
                    1,
                ]
            ),
            TransactionOutput(script_address, 1234567, script=plutus_script),
        )

        original_utxos[0].output.amount.multi_asset = MultiAsset.from_primitive(
            {b"1" * 28: {b"Token1": 1, b"Token2": 2}}
        )

        mock_utxos.return_value = original_utxos + [existing_script_utxo]

        redeemer = Redeemer(PlutusData(), ExecutionUnits(1000000, 1000000))
        tx_builder.add_script_input(utxo1, datum=datum, redeemer=redeemer)
        receiver = Address.from_primitive(
            "addr_test1vrm9x2zsux7va6w892g38tvchnzahvcd9tykqf3ygnmwtaqyfg52x"
        )
        tx_builder.add_output(TransactionOutput(receiver, 5000000))
        tx_body = tx_builder.build(change_address=receiver)
        assert tx_body.collateral_return.address == receiver
        assert (
            tx_body.collateral_return.amount + tx_body.total_collateral
            == original_utxos[0].output.amount
        )


@pytest.mark.parametrize(
    "collateral_amount, collateral_return_threshold, has_return",
    [
        (Value(4_000_000), 0, False),
        (Value(4_000_000), 1_000_000, False),
        (Value(6_000_000), 2_000_000, True),
        (Value(6_000_000), 3_000_000, False),
        (
            Value(
                6_000_000,
                MultiAsset.from_primitive({b"1" * 28: {b"Token1": 1, b"Token2": 2}}),
            ),
            3_000_000,
            True,
        ),
    ],
)
def test_no_collateral_return(
    chain_context, collateral_amount, collateral_return_threshold, has_return
):
    original_utxos = chain_context.utxos(
        "addr_test1vrm9x2zsux7va6w892g38tvchnzahvcd9tykqf3ygnmwtaqyfg52x"
    )
    with patch.object(chain_context, "utxos") as mock_utxos:
        tx_builder = TransactionBuilder(
            chain_context, collateral_return_threshold=collateral_return_threshold
        )
        tx_in1 = TransactionInput.from_primitive(
            ["18cbe6cadecd3f89b60e08e68e5e6c7d72d730aaa1ad21431590f7e6643438ef", 0]
        )
        plutus_script = PlutusV1Script(b"dummy test script")
        script_hash = plutus_script_hash(plutus_script)
        script_address = Address(script_hash)
        datum = PlutusData()
        utxo1 = UTxO(
            tx_in1, TransactionOutput(script_address, 10000000, datum_hash=datum.hash())
        )

        existing_script_utxo = UTxO(
            TransactionInput.from_primitive(
                [
                    "41cb004bec7051621b19b46aea28f0657a586a05ce2013152ea9b9f1a5614cc7",
                    1,
                ]
            ),
            TransactionOutput(script_address, 1234567, script=plutus_script),
        )

        original_utxos[0].output.amount = collateral_amount

        mock_utxos.return_value = original_utxos[:1] + [existing_script_utxo]

        redeemer = Redeemer(PlutusData(), ExecutionUnits(1000000, 1000000))
        tx_builder.add_script_input(utxo1, datum=datum, redeemer=redeemer)
        receiver = Address.from_primitive(
            "addr_test1vrm9x2zsux7va6w892g38tvchnzahvcd9tykqf3ygnmwtaqyfg52x"
        )
        tx_builder.add_output(TransactionOutput(receiver, 5000000))
        tx_body = tx_builder.build(change_address=receiver)
        assert (tx_body.collateral_return is not None) == has_return
        assert (tx_body.total_collateral is not None) == has_return


def test_collateral_return_min_return_amount(chain_context):
    original_utxos = chain_context.utxos(
        "addr_test1vrm9x2zsux7va6w892g38tvchnzahvcd9tykqf3ygnmwtaqyfg52x"
    )
    with patch.object(chain_context, "utxos") as mock_utxos:
        tx_builder = TransactionBuilder(chain_context)
        tx_in1 = TransactionInput.from_primitive(
            ["18cbe6cadecd3f89b60e08e68e5e6c7d72d730aaa1ad21431590f7e6643438ef", 0]
        )
        plutus_script = PlutusV1Script(b"dummy test script")
        script_hash = plutus_script_hash(plutus_script)
        script_address = Address(script_hash)
        datum = PlutusData()
        utxo1 = UTxO(
            tx_in1, TransactionOutput(script_address, 10000000, datum_hash=datum.hash())
        )

        existing_script_utxo = UTxO(
            TransactionInput.from_primitive(
                [
                    "41cb004bec7051621b19b46aea28f0657a586a05ce2013152ea9b9f1a5614cc7",
                    1,
                ]
            ),
            TransactionOutput(script_address, 1234567, script=plutus_script),
        )

        original_utxos[0].output.amount.multi_asset = MultiAsset.from_primitive(
            {
                b"1"
                * 28: {
                    b"Token" + i.to_bytes(10, byteorder="big"): i for i in range(500)
                }
            }
        )

        original_utxos[0].output.amount.coin = min_lovelace_post_alonzo(
            original_utxos[0].output, chain_context
        )

        mock_utxos.return_value = original_utxos + [existing_script_utxo]

        redeemer = Redeemer(PlutusData(), ExecutionUnits(1000000, 1000000))
        tx_builder.add_script_input(utxo1, datum=datum, redeemer=redeemer)
        receiver = Address.from_primitive(
            "addr_test1vrm9x2zsux7va6w892g38tvchnzahvcd9tykqf3ygnmwtaqyfg52x"
        )
        tx_builder.add_output(TransactionOutput(receiver, 5000000))
        tx_body = tx_builder.build(change_address=receiver)
        assert tx_body.collateral_return.address == receiver
        assert tx_body.collateral_return.amount.coin >= min_lovelace_post_alonzo(
            tx_body.collateral_return, chain_context
        )


def test_wrong_redeemer_execution_units(chain_context):
    tx_builder = TransactionBuilder(chain_context)
    tx_in1 = TransactionInput.from_primitive(
        ["18cbe6cadecd3f89b60e08e68e5e6c7d72d730aaa1ad21431590f7e6643438ef", 0]
    )
    tx_in2 = TransactionInput.from_primitive(
        ["18cbe6cadecd3f89b60e08e68e5e6c7d72d730aaa1ad21431590f7e6643438ef", 1]
    )
    plutus_script = PlutusV1Script(b"dummy test script")
    script_hash = plutus_script_hash(plutus_script)
    script_address = Address(script_hash)
    datum = PlutusData()
    utxo1 = UTxO(
        tx_in1, TransactionOutput(script_address, 10000000, datum_hash=datum.hash())
    )
    mint = MultiAsset.from_primitive({script_hash.payload: {b"TestToken": 1}})
    UTxO(
        tx_in2,
        TransactionOutput(
            script_address, Value(10000000, mint), datum_hash=datum.hash()
        ),
    )
    redeemer1 = Redeemer(PlutusData())
    redeemer2 = Redeemer(PlutusData())
    redeemer3 = Redeemer(PlutusData(), ExecutionUnits(1000000, 1000000))
    tx_builder.mint = mint
    tx_builder.add_script_input(utxo1, plutus_script, datum, redeemer1)
    tx_builder.add_minting_script(plutus_script, redeemer2)
    with pytest.raises(InvalidArgumentException):
        tx_builder.add_minting_script(plutus_script, redeemer3)


def test_all_redeemer_should_provide_execution_units(chain_context):
    tx_builder = TransactionBuilder(chain_context)
    tx_in1 = TransactionInput.from_primitive(
        ["18cbe6cadecd3f89b60e08e68e5e6c7d72d730aaa1ad21431590f7e6643438ef", 0]
    )
    TransactionInput.from_primitive(
        ["18cbe6cadecd3f89b60e08e68e5e6c7d72d730aaa1ad21431590f7e6643438ef", 1]
    )
    plutus_script = PlutusV1Script(b"dummy test script")
    script_hash = plutus_script_hash(plutus_script)
    script_address = Address(script_hash)
    datum = PlutusData()
    utxo1 = UTxO(
        tx_in1, TransactionOutput(script_address, 10000000, datum_hash=datum.hash())
    )
    mint = MultiAsset.from_primitive({script_hash.payload: {b"TestToken": 1}})
    redeemer1 = Redeemer(PlutusData(), ExecutionUnits(1000000, 1000000))
    redeemer2 = Redeemer(PlutusData())
    tx_builder.mint = mint
    tx_builder.add_script_input(utxo1, plutus_script, datum, redeemer1)
    with pytest.raises(InvalidArgumentException):
        tx_builder.add_script_input(utxo1, plutus_script, datum, redeemer2)


def test_add_minting_script(chain_context):
    tx_builder = TransactionBuilder(chain_context)
    tx_in1 = TransactionInput.from_primitive(
        ["18cbe6cadecd3f89b60e08e68e5e6c7d72d730aaa1ad21431590f7e6643438ef", 0]
    )
    plutus_script = PlutusV1Script(b"dummy test script")
    script_hash = plutus_script_hash(plutus_script)
    script_address = Address(script_hash)
    utxo1 = UTxO(tx_in1, TransactionOutput(script_address, 10000000))
    mint = MultiAsset.from_primitive({script_hash.payload: {b"TestToken": 1}})
    redeemer1 = Redeemer(PlutusData(), ExecutionUnits(1000000, 1000000))
    tx_builder.mint = mint
    tx_builder.add_input(utxo1)
    tx_builder.add_minting_script(plutus_script, redeemer1)
    receiver = Address.from_primitive(
        "addr_test1vrm9x2zsux7va6w892g38tvchnzahvcd9tykqf3ygnmwtaqyfg52x"
    )
    tx_builder.add_output(TransactionOutput(receiver, Value(5000000, mint)))
    tx_builder.build(change_address=receiver)
    tx_builder.use_redeemer_map = False
    witness = tx_builder.build_witness_set()
    assert [plutus_script] == witness.plutus_v1_script


def test_add_minting_script_only(chain_context):
    tx_builder = TransactionBuilder(chain_context)
    tx_in1 = TransactionInput.from_primitive(
        ["18cbe6cadecd3f89b60e08e68e5e6c7d72d730aaa1ad21431590f7e6643438ef", 0]
    )
    plutus_script = PlutusV1Script(b"dummy test script")
    script_hash = plutus_script_hash(plutus_script)
    script_address = Address(script_hash)
    utxo1 = UTxO(tx_in1, TransactionOutput(script_address, 10000000))
    mint = MultiAsset.from_primitive({script_hash.payload: {b"TestToken": 1}})
    tx_builder.mint = mint
    tx_builder.add_input(utxo1)
    tx_builder.add_minting_script(plutus_script)
    receiver = Address.from_primitive(
        "addr_test1vrm9x2zsux7va6w892g38tvchnzahvcd9tykqf3ygnmwtaqyfg52x"
    )
    tx_builder.add_output(TransactionOutput(receiver, Value(5000000, mint)))
    tx_builder.build(change_address=receiver)
    tx_builder.use_redeemer_map = False
    witness = tx_builder.build_witness_set()
    assert [plutus_script] == witness.plutus_v1_script


def test_add_minting_script_wrong_redeemer_type(chain_context):
    tx_builder = TransactionBuilder(chain_context)
    plutus_script = PlutusV1Script(b"dummy test script")
    redeemer1 = Redeemer(PlutusData(), ExecutionUnits(1000000, 1000000))
    redeemer1.tag = RedeemerTag.SPEND

    with pytest.raises(InvalidArgumentException):
        tx_builder.add_minting_script(plutus_script, redeemer1)


def test_excluded_input(chain_context):
    tx_builder = TransactionBuilder(chain_context, [RandomImproveMultiAsset([0, 0])])
    sender = "addr_test1vrm9x2zsux7va6w892g38tvchnzahvcd9tykqf3ygnmwtaqyfg52x"
    sender_address = Address.from_primitive(sender)

    # Add sender address as input
    tx_builder.add_input_address(sender).add_output(
        TransactionOutput.from_primitive([sender, 500000])
    )

    tx_builder.excluded_inputs.append(chain_context.utxos(sender)[0])

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
                    5332431,
                    {b"1111111111111111111111111111": {b"Token1": 1, b"Token2": 2}},
                ],
            ],
        ],
        2: 167569,
    }

    assert expected == tx_body.to_primitive()


def test_build_and_sign(chain_context):
    sender = "addr_test1vrm9x2zsux7va6w892g38tvchnzahvcd9tykqf3ygnmwtaqyfg52x"
    sender_address = Address.from_primitive(sender)

    tx_builder1 = TransactionBuilder(
        chain_context, [RandomImproveMultiAsset([0, 0, 0, 0, 0])]
    )
    tx_builder1.add_input_address(sender).add_output(
        TransactionOutput.from_primitive([sender, 500000])
    )

    tx_body = tx_builder1.build(change_address=sender_address)

    tx_builder2 = TransactionBuilder(
        chain_context, [RandomImproveMultiAsset([0, 0, 0, 0, 0])]
    )
    tx_builder2.add_input_address(sender).add_output(
        TransactionOutput.from_primitive([sender, 500000])
    )
    tx = tx_builder2.build_and_sign(
        [SK],
        change_address=sender_address,
        force_skeys=True,
    )

    assert tx.transaction_witness_set.vkey_witnesses == [
        VerificationKeyWitness(SK.to_verification_key(), SK.sign(tx_body.hash()))
    ]
    assert (
        "a300818258203131313131313131313131313131313131313131313131313131313131313131"
        "00018282581d60f6532850e1bccee9c72a9113ad98bcc5dbb30d2ac960262444f6e5f41a0007"
        "a12082581d60f6532850e1bccee9c72a9113ad98bcc5dbb30d2ac960262444f6e5f41a004223"
        "fb021a00028625" == tx_body.to_cbor_hex()
    )


def test_estimate_execution_unit(chain_context):
    tx_builder = TransactionBuilder(chain_context)
    tx_in1 = TransactionInput.from_primitive(
        ["18cbe6cadecd3f89b60e08e68e5e6c7d72d730aaa1ad21431590f7e6643438ef", 0]
    )
    plutus_script = PlutusV1Script(b"dummy test script")
    script_hash = plutus_script_hash(plutus_script)
    script_address = Address(script_hash)
    datum = PlutusData()
    utxo1 = UTxO(
        tx_in1, TransactionOutput(script_address, 10000000, datum_hash=datum.hash())
    )
    mint = MultiAsset.from_primitive({script_hash.payload: {b"TestToken": 1}})
    redeemer1 = Redeemer(PlutusData())
    tx_builder.mint = mint
    tx_builder.add_script_input(utxo1, plutus_script, datum, redeemer1)
    receiver = Address.from_primitive(
        "addr_test1vrm9x2zsux7va6w892g38tvchnzahvcd9tykqf3ygnmwtaqyfg52x"
    )
    tx_builder.add_output(TransactionOutput(receiver, 5000000))
    tx_builder.build(change_address=receiver)
    tx_builder.use_redeemer_map = False
    witness = tx_builder.build_witness_set()
    assert [datum] == witness.plutus_data
    assert [redeemer1] == witness.redeemer
    assert redeemer1.ex_units is not None
    assert [plutus_script] == witness.plutus_v1_script


def test_add_script_input_inline_datum_extra(chain_context):
    tx_builder = TransactionBuilder(chain_context)
    tx_in1 = TransactionInput.from_primitive(
        ["18cbe6cadecd3f89b60e08e68e5e6c7d72d730aaa1ad21431590f7e6643438ef", 0]
    )
    tx_in2 = TransactionInput.from_primitive(
        ["18cbe6cadecd3f89b60e08e68e5e6c7d72d730aaa1ad21431590f7e6643438ef", 1]
    )
    plutus_script = PlutusV1Script(b"dummy test script")
    script_hash = plutus_script_hash(plutus_script)
    script_address = Address(script_hash)
    datum = PlutusData()
    utxo1 = UTxO(tx_in1, TransactionOutput(script_address, 10000000, datum=datum))
    redeemer1 = Redeemer(PlutusData(), ExecutionUnits(1000000, 1000000))
    pytest.raises(
        InvalidArgumentException,
        tx_builder.add_script_input,
        utxo1,
        plutus_script,
        datum,
        redeemer1,
    )


def test_tx_builder_exact_fee_no_change(chain_context):
    tx_builder = TransactionBuilder(chain_context)
    sender = "addr_test1vrm9x2zsux7va6w892g38tvchnzahvcd9tykqf3ygnmwtaqyfg52x"
    sender_address = Address.from_primitive(sender)

    input_amount = 10000000

    tx_in1 = TransactionInput.from_primitive([b"1" * 32, 3])
    tx_out1 = TransactionOutput.from_primitive([sender, input_amount])
    utxo1 = UTxO(tx_in1, tx_out1)

    tx_builder.add_input(utxo1)

    tx_builder.add_output(TransactionOutput.from_primitive([sender, 5000000]))

    tx_body = tx_builder.build()

    tx_builder = TransactionBuilder(chain_context)

    tx_in1 = TransactionInput.from_primitive([b"1" * 32, 3])
    tx_out1 = TransactionOutput.from_primitive([sender, input_amount])
    utxo1 = UTxO(tx_in1, tx_out1)

    tx_builder.add_input(utxo1)

    tx_builder.add_output(
        TransactionOutput.from_primitive([sender, input_amount - tx_body.fee])
    )

    tx = tx_builder.build_and_sign([SK])

    expected = {
        0: [[b"11111111111111111111111111111111", 3]],
        1: [
            [sender_address.to_primitive(), 9836215],
        ],
        2: 163785,
    }

    assert expected == tx.transaction_body.to_primitive()
    assert tx.transaction_body.fee >= fee(chain_context, len(tx.to_cbor()))


def test_tx_builder_certificates(chain_context):
    tx_builder = TransactionBuilder(chain_context, [RandomImproveMultiAsset([0, 0])])
    sender = "addr_test1vrm9x2zsux7va6w892g38tvchnzahvcd9tykqf3ygnmwtaqyfg52x"
    sender_address = Address.from_primitive(sender)

    stake_key_hash = VerificationKeyHash(b"1" * VERIFICATION_KEY_HASH_SIZE)

    stake_credential = StakeCredential(stake_key_hash)

    pool_hash = PoolKeyHash(b"1" * POOL_KEY_HASH_SIZE)

    stake_registration = StakeRegistration(stake_credential)

    stake_delegation = StakeDelegation(stake_credential, pool_hash)

    # Add sender address as input
    tx_builder.add_input_address(sender).add_output(
        TransactionOutput.from_primitive([sender, 500000])
    )

    tx_builder.certificates = [stake_registration, stake_delegation]

    tx_body = tx_builder.build(change_address=sender_address)

    expected = {
        0: [[b"11111111111111111111111111111111", 0]],
        1: [
            # First output
            [sender_address.to_primitive(), 500000],
            # Second output as change
            [sender_address.to_primitive(), 2325743],
        ],
        2: 174257,
        4: [
            [0, [0, b"1111111111111111111111111111"]],
            [2, [0, b"1111111111111111111111111111"], b"1111111111111111111111111111"],
        ],
    }

    assert expected == tx_body.to_primitive()


def test_tx_builder_certificates_script(chain_context):
    tx_builder = TransactionBuilder(chain_context, [RandomImproveMultiAsset([0, 0])])
    sender = "addr_test1vrm9x2zsux7va6w892g38tvchnzahvcd9tykqf3ygnmwtaqyfg52x"
    sender_address = Address.from_primitive(sender)

    plutus_script = PlutusV2Script(b"dummy test script")
    script_hash = plutus_script_hash(plutus_script)

    stake_credential = StakeCredential(script_hash)

    pool_hash = PoolKeyHash(b"1" * POOL_KEY_HASH_SIZE)

    stake_registration = StakeRegistration(stake_credential)

    stake_delegation = StakeDelegation(stake_credential, pool_hash)

    # Add sender address as input
    tx_builder.add_input_address(sender).add_output(
        TransactionOutput.from_primitive([sender, 500000])
    )

    tx_builder.certificates = [stake_registration, stake_delegation]
    redeemer = Redeemer(PlutusData(), ExecutionUnits(100000, 1000000))
    tx_builder.add_certificate_script(plutus_script, redeemer=redeemer)
    tx_builder.ttl = 123456

    tx_builder.build(change_address=sender_address)
    tx_builder.use_redeemer_map = False
    witness = tx_builder.build_witness_set()
    assert [redeemer] == witness.redeemer
    assert witness.redeemer[0].index == 1
    assert [plutus_script] == witness.plutus_v2_script


def test_tx_builder_cert_redeemer_wrong_tag(chain_context):
    tx_builder = TransactionBuilder(chain_context)
    plutus_script = PlutusV2Script(b"dummy test script")
    redeemer = Redeemer(PlutusData(), ExecutionUnits(100000, 1000000))
    redeemer.tag = RedeemerTag.MINT
    with pytest.raises(InvalidArgumentException) as e:
        tx_builder.add_certificate_script(plutus_script, redeemer=redeemer)


def test_add_cert_script_from_utxo(chain_context):
    tx_builder = TransactionBuilder(chain_context)
    sender = "addr_test1vrm9x2zsux7va6w892g38tvchnzahvcd9tykqf3ygnmwtaqyfg52x"
    sender_address = Address.from_primitive(sender)
    plutus_script = PlutusV2Script(b"dummy test script")
    script_hash = plutus_script_hash(plutus_script)
    script_address = Address(script_hash)
    existing_script_utxo = UTxO(
        TransactionInput.from_primitive(
            [
                "41cb004bec7051621b19b46aea28f0657a586a05ce2013152ea9b9f1a5614cc7",
                1,
            ]
        ),
        TransactionOutput(script_address, 1234567, script=plutus_script),
    )

    stake_credential = StakeCredential(script_hash)
    pool_hash = PoolKeyHash(b"1" * POOL_KEY_HASH_SIZE)
    stake_registration = StakeRegistration(stake_credential)
    stake_delegation = StakeDelegation(stake_credential, pool_hash)
    tx_builder.certificates = [stake_registration, stake_delegation]
    tx_builder.add_input_address(sender).add_output(
        TransactionOutput.from_primitive([sender, 500000])
    )

    redeemer = Redeemer(PlutusData(), ExecutionUnits(100000, 1000000))
    tx_builder.add_certificate_script(existing_script_utxo, redeemer=redeemer)
    tx_builder.ttl = 123456

    tx_body = tx_builder.build(change_address=sender_address)
    tx_builder.use_redeemer_map = False
    witness = tx_builder.build_witness_set()
    assert witness.plutus_data is None
    assert [redeemer] == witness.redeemer
    assert witness.plutus_v2_script is None
    assert [existing_script_utxo.input] == tx_body.reference_inputs


def test_tx_builder_stake_pool_registration(chain_context, pool_params):
    tx_builder = TransactionBuilder(chain_context, [RandomImproveMultiAsset([0, 0])])
    sender = "addr_test1vrm9x2zsux7va6w892g38tvchnzahvcd9tykqf3ygnmwtaqyfg52x"
    sender_address = Address.from_primitive(sender)

    pool_registration = PoolRegistration(pool_params)

    tx_in3 = TransactionInput.from_primitive([b"2" * 32, 2])
    tx_out3 = TransactionOutput.from_primitive([sender, 505000000])
    utxo = UTxO(tx_in3, tx_out3)

    tx_builder.add_input(utxo)

    tx_builder.initial_stake_pool_registration = True

    tx_builder.certificates = [pool_registration]

    tx_body = tx_builder.build(change_address=sender_address)

    expected = {
        0: [[b"22222222222222222222222222222222", 2]],
        1: [
            [
                b"`\xf6S(P\xe1\xbc\xce\xe9\xc7*\x91\x13\xad\x98\xbc\xc5\xdb\xb3\r*\xc9`&$D\xf6\xe5\xf4",
                4819407,
            ]
        ],
        2: 180593,
        4: [
            [
                3,
                b"1111111111111111111111111111",
                b"11111111111111111111111111111111",
                100000000,
                340000000,
                Fraction(1, 50),
                b"11111111111111111111111111111",
                [b"1111111111111111111111111111"],
                [
                    [
                        0,
                        3001,
                        b"\xc0\xa8\x00\x01",
                        b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01",
                    ],
                    [1, 3001, "relay1.example.com"],
                    [2, "relay1.example.com"],
                ],
                ["https://meta1.example.com", b"11111111111111111111111111111111"],
            ]
        ],
    }

    assert expected == tx_body.to_primitive()


def test_tx_builder_withdrawal(chain_context):
    tx_builder = TransactionBuilder(chain_context, [RandomImproveMultiAsset([0, 0])])
    sender = "addr_test1vrm9x2zsux7va6w892g38tvchnzahvcd9tykqf3ygnmwtaqyfg52x"
    sender_address = Address.from_primitive(sender)

    stake_address = Address.from_primitive(
        "stake_test1upyz3gk6mw5he20apnwfn96cn9rscgvmmsxc9r86dh0k66gswf59n"
    )

    # Add sender address as input
    tx_builder.add_input_address(sender).add_output(
        TransactionOutput.from_primitive([sender, 500000])
    )

    withdrawals = Withdrawals({bytes(stake_address): 10000})
    tx_builder.withdrawals = withdrawals

    tx_body = tx_builder.build(change_address=sender_address)

    expected = {
        0: [[b"11111111111111111111111111111111", 0]],
        1: [
            # First output
            [sender_address.to_primitive(), 500000],
            # Second output as change
            [sender_address.to_primitive(), 4338559],
        ],
        2: 171441,
        5: {
            b"\xe0H(\xa2\xda\xdb\xa9|\xa9\xfd\x0c\xdc\x99\x97X\x99G\x0c!\x9b\xdc\r\x82\x8c\xfam\xdfmi": 10000
        },
    }

    assert expected == tx_body.to_primitive()


def test_tx_builder_no_output(chain_context):
    tx_builder = TransactionBuilder(chain_context)
    sender = "addr_test1vrm9x2zsux7va6w892g38tvchnzahvcd9tykqf3ygnmwtaqyfg52x"
    sender_address = Address.from_primitive(sender)

    input_amount = 10000000

    tx_in1 = TransactionInput.from_primitive([b"1" * 32, 3])
    tx_out1 = TransactionOutput.from_primitive([sender, input_amount])
    utxo1 = UTxO(tx_in1, tx_out1)

    tx_builder.add_input(utxo1)

    tx_body = tx_builder.build(
        change_address=sender_address,
        merge_change=True,
    )

    expected = {
        0: [[b"11111111111111111111111111111111", 3]],
        1: [
            [sender_address.to_primitive(), 9836215],
        ],
        2: 163785,
    }

    assert expected == tx_body.to_primitive()


def test_tx_builder_merge_change_to_output(chain_context):
    tx_builder = TransactionBuilder(chain_context)
    sender = "addr_test1vrm9x2zsux7va6w892g38tvchnzahvcd9tykqf3ygnmwtaqyfg52x"
    sender_address = Address.from_primitive(sender)

    input_amount = 10000000

    tx_in1 = TransactionInput.from_primitive([b"1" * 32, 3])
    tx_out1 = TransactionOutput.from_primitive([sender, input_amount])
    utxo1 = UTxO(tx_in1, tx_out1)

    tx_builder.add_input(utxo1)
    tx_builder.add_output(TransactionOutput.from_primitive([sender, 10000]))

    tx_body = tx_builder.build(
        change_address=sender_address,
        merge_change=True,
    )

    expected = {
        0: [[b"11111111111111111111111111111111", 3]],
        1: [
            [sender_address.to_primitive(), 9836215],
        ],
        2: 163785,
    }

    assert expected == tx_body.to_primitive()


def test_tx_builder_merge_change_to_output_2(chain_context):
    tx_builder = TransactionBuilder(chain_context)
    sender = "addr_test1vrm9x2zsux7va6w892g38tvchnzahvcd9tykqf3ygnmwtaqyfg52x"
    sender_address = Address.from_primitive(sender)
    receiver = "addr_test1vr2p8st5t5cxqglyjky7vk98k7jtfhdpvhl4e97cezuhn0cqcexl7"
    receiver_address = Address.from_primitive(receiver)

    input_amount = 10000000

    tx_in1 = TransactionInput.from_primitive([b"1" * 32, 3])
    tx_out1 = TransactionOutput.from_primitive([sender, input_amount])
    utxo1 = UTxO(tx_in1, tx_out1)

    tx_builder.add_input(utxo1)
    tx_builder.add_output(TransactionOutput.from_primitive([sender, 10000]))
    tx_builder.add_output(TransactionOutput.from_primitive([receiver, 10000]))
    tx_builder.add_output(TransactionOutput.from_primitive([sender, 0]))

    tx_body = tx_builder.build(
        change_address=sender_address,
        merge_change=True,
    )

    expected = {
        0: [[b"11111111111111111111111111111111", 3]],
        1: [
            [sender_address.to_primitive(), 10000],
            [receiver_address.to_primitive(), 10000],
            [sender_address.to_primitive(), 9813135],
        ],
        2: 166865,
    }

    assert expected == tx_body.to_primitive()


def test_tx_builder_merge_change_to_zero_amount_output(chain_context):
    tx_builder = TransactionBuilder(chain_context)
    sender = "addr_test1vrm9x2zsux7va6w892g38tvchnzahvcd9tykqf3ygnmwtaqyfg52x"
    sender_address = Address.from_primitive(sender)

    input_amount = 10000000

    tx_in1 = TransactionInput.from_primitive([b"1" * 32, 3])
    tx_out1 = TransactionOutput.from_primitive([sender, input_amount])
    utxo1 = UTxO(tx_in1, tx_out1)

    tx_builder.add_input(utxo1)
    tx_builder.add_output(TransactionOutput.from_primitive([sender, 0]))

    tx_body = tx_builder.build(
        change_address=sender_address,
        merge_change=True,
    )

    expected = {
        0: [[b"11111111111111111111111111111111", 3]],
        1: [
            [sender_address.to_primitive(), 9836215],
        ],
        2: 163785,
    }

    assert expected == tx_body.to_primitive()


def test_tx_builder_merge_change_smaller_than_min_utxo(chain_context):
    tx_builder = TransactionBuilder(chain_context)
    sender = "addr_test1vrm9x2zsux7va6w892g38tvchnzahvcd9tykqf3ygnmwtaqyfg52x"
    sender_address = Address.from_primitive(sender)

    input_amount = 10000000

    tx_in1 = TransactionInput.from_primitive([b"1" * 32, 3])
    tx_out1 = TransactionOutput.from_primitive([sender, input_amount])
    utxo1 = UTxO(tx_in1, tx_out1)

    tx_builder.add_input(utxo1)
    tx_builder.add_output(TransactionOutput.from_primitive([sender, 9800000]))

    tx_body = tx_builder.build(
        change_address=sender_address,
        merge_change=True,
    )

    expected = {
        0: [[b"11111111111111111111111111111111", 3]],
        1: [
            [sender_address.to_primitive(), 9836215],
        ],
        2: 163785,
    }

    assert expected == tx_body.to_primitive()


def test_tx_builder_small_utxo_input(chain_context):
    with patch.object(chain_context, "utxos") as mock_utxos:
        mock_utxos.return_value = [
            UTxO(
                TransactionInput.from_primitive(
                    [
                        "41cb004bec7051621b19b46aea28f0657a586a05ce2013152ea9b9f1a5614cc7",
                        1,
                    ]
                ),
                TransactionOutput.from_primitive(
                    [
                        "addr1qytqt3v9ej3kzefxcy8f59h9atf2knracnj5snkgtaea6p4r8g3mu652945v3gldw7v88dn5lrfudx0un540ak9qt2kqhfjl0d",
                        2991353,
                    ]
                ),
            )
        ]
        builder = TransactionBuilder(chain_context)
        address = Address.from_primitive(
            "addr1qytqt3v9ej3kzefxcy8f59h9atf2knracnj5snkgtaea6p4r8g3mu652945v3gldw7v88dn5lrfudx0un540ak9qt2kqhfjl0d"
        )
        builder.add_input_address(address)

        builder.add_output(
            TransactionOutput(
                Address.from_primitive(
                    "addr1qyady0evsaxqsfmz0z8rvmq62fmuas5w8n4m8z6qcm4wrt3e8dlsen8n464ucw69acfgdxgguscgfl5we3rwts4s57ashysyee"
                ),
                Value.from_primitive(
                    [
                        1000000,
                    ]
                ),
            )
        )
        builder.build(change_address=address)


def test_tx_builder_small_utxo_input_2(chain_context):
    with patch.object(chain_context, "utxos") as mock_utxos:
        mock_utxos.return_value = [
            UTxO(
                TransactionInput.from_primitive(
                    [
                        "233a835316f4c27bceafdd190639c9c7b834224a7ab7fce13330495437d977fa",
                        0,
                    ]
                ),
                TransactionOutput.from_primitive(
                    [
                        "addr1q872eujv4xcuckfarjklttdfep7224gjt7wrxkpu8ve3v6g4x2yx743payyucr327fz0dkdwkj9yc8gemtctgmzpjd8qcdw8qr",
                        5639430,
                    ]
                ),
            ),
            UTxO(
                TransactionInput.from_primitive(
                    [
                        "233a835316f4c27bceafdd190639c9c7b834224a7ab7fce13330495437d977fa",
                        1,
                    ]
                ),
                TransactionOutput.from_primitive(
                    [
                        "addr1q872eujv4xcuckfarjklttdfep7224gjt7wrxkpu8ve3v6g4x2yx743payyucr327fz0dkdwkj9yc8gemtctgmzpjd8qcdw8qr",
                        [
                            1379280,
                            {
                                bytes.fromhex(
                                    "c4d5ae259e40eb7830df9de67b0a6a536b7e3ed645de2a13eedc7ece"
                                ): {
                                    b"x your eyes": 1,
                                }
                            },
                        ],
                    ]
                ),
            ),
        ]
        builder = TransactionBuilder(chain_context)
        address = Address.from_primitive(
            "addr1q872eujv4xcuckfarjklttdfep7224gjt7wrxkpu8ve3v6g4x2yx743payyucr327fz0dkdwkj9yc8gemtctgmzpjd8qcdw8qr"
        )
        builder.add_input_address(address)

        builder.add_output(
            TransactionOutput(
                Address.from_primitive(
                    "addr1qxx7lc2kyrjp4qf3gkpezp24ugu35em2f5h05apejzzy73c7yf794gk9yzhngdse36rae52c7a6rv5seku25cd8ntves7f5fe4"
                ),
                Value.from_primitive(
                    [
                        3000000,
                        {
                            bytes.fromhex(
                                "c4d5ae259e40eb7830df9de67b0a6a536b7e3ed645de2a13eedc7ece"
                            ): {
                                b"x your eyes": 1,
                            }
                        },
                    ],
                ),
            )
        )
        builder.build(change_address=address)


def test_tx_builder_merge_change_to_output_3(chain_context):
    with patch.object(chain_context, "utxos") as mock_utxos:
        mock_utxos.return_value = [
            UTxO(
                TransactionInput.from_primitive(
                    [
                        "41cb004bec7051621b19b46aea28f0657a586a05ce2013152ea9b9f1a5614cc7",
                        1,
                    ]
                ),
                TransactionOutput.from_primitive(
                    [
                        "addr1qytqt3v9ej3kzefxcy8f59h9atf2knracnj5snkgtaea6p4r8g3mu652945v3gldw7v88dn5lrfudx0un540ak9qt2kqhfjl0d",
                        2991353,
                    ]
                ),
            )
        ]
        builder = TransactionBuilder(chain_context)
        address = Address.from_primitive(
            "addr1qytqt3v9ej3kzefxcy8f59h9atf2knracnj5snkgtaea6p4r8g3mu652945v3gldw7v88dn5lrfudx0un540ak9qt2kqhfjl0d"
        )
        builder.add_input_address(address)

        builder.add_output(
            TransactionOutput(
                Address.from_primitive(
                    "addr1qytqt3v9ej3kzefxcy8f59h9atf2knracnj5snkgtaea6p4r8g3mu652945v3gldw7v88dn5lrfudx0un540ak9qt2kqhfjl0d"
                ),
                Value.from_primitive(
                    [
                        1000000,
                    ]
                ),
            )
        )
        tx = builder.build(change_address=address, merge_change=True)
        assert len(tx.outputs) == 1


def test_build_witness_set_mixed_scripts(chain_context):
    # Create dummy scripts
    plutus_v1_script = PlutusV1Script(b"plutus v1 script")
    plutus_v2_script = PlutusV2Script(b"plutus v2 script")
    plutus_v3_script = PlutusV3Script(b"plutus v3 script")

    # Create a TransactionBuilder instance
    builder = TransactionBuilder(chain_context)

    # Add inputs with different scripts
    input_v1 = UTxO(
        TransactionInput(TransactionId(32 * b"0"), 0),
        TransactionOutput(
            Address(script_hash(plutus_v1_script)),
            Value(1000000),
            script=plutus_v1_script,
        ),
    )
    input_v2 = UTxO(
        TransactionInput(TransactionId(32 * b"0"), 1),
        TransactionOutput(
            Address(script_hash(plutus_v2_script)),
            Value(1000000),
            script=plutus_v2_script,
        ),
    )
    input_v3 = UTxO(
        TransactionInput(TransactionId(32 * b"0"), 3),
        TransactionOutput(
            Address(script_hash(plutus_v3_script)),
            Value(1000000),
            script=plutus_v3_script,
        ),
    )
    builder.add_input(input_v1)
    builder.add_input(input_v2)
    builder.add_input(input_v3)

    # Add scripts to the builder
    builder._inputs_to_scripts[input_v1] = plutus_v1_script
    builder._inputs_to_scripts[input_v2] = plutus_v2_script
    builder._inputs_to_scripts[input_v3] = plutus_v3_script

    # Add an additional PlutusV1Script
    additional_v1_script = PlutusV1Script(b"additional v1 script")
    builder._inputs_to_scripts[
        UTxO(
            TransactionInput(TransactionId(32 * b"1"), 0),
            TransactionOutput(
                Address(script_hash(additional_v1_script)), Value(1000000)
            ),
        )
    ] = additional_v1_script

    # Test with remove_dup_script=True
    witness_set = builder.build_witness_set(remove_dup_script=True)
    assert len(witness_set.plutus_v1_script) == 1
    assert script_hash(witness_set.plutus_v1_script[0]) == script_hash(
        additional_v1_script
    )
    assert witness_set.plutus_v2_script is None
    assert witness_set.plutus_v3_script is None

    # Test with remove_dup_script=False
    witness_set = builder.build_witness_set(remove_dup_script=False)
    assert len(witness_set.plutus_v1_script) == 2
    assert len(witness_set.plutus_v2_script) == 1
    assert len(witness_set.plutus_v3_script) == 1


def test_add_script_input_post_chang(chain_context):
    tx_builder = TransactionBuilder(chain_context)
    tx_in1 = TransactionInput.from_primitive(
        ["18cbe6cadecd3f89b60e08e68e5e6c7d72d730aaa1ad21431590f7e6643438ef", 0]
    )
    tx_in2 = TransactionInput.from_primitive(
        ["18cbe6cadecd3f89b60e08e68e5e6c7d72d730aaa1ad21431590f7e6643438ef", 1]
    )
    plutus_script = PlutusV1Script(b"dummy test script")
    script_hash = plutus_script_hash(plutus_script)
    script_address = Address(script_hash)
    datum = PlutusData()
    utxo1 = UTxO(
        tx_in1, TransactionOutput(script_address, 10000000, datum_hash=datum.hash())
    )
    mint = MultiAsset.from_primitive({script_hash.payload: {b"TestToken": 1}})
    UTxO(
        tx_in2,
        TransactionOutput(
            script_address, Value(10000000, mint), datum_hash=datum.hash()
        ),
    )
    redeemer1 = Redeemer(PlutusData(), ExecutionUnits(1000000, 1000000))
    redeemer2 = Redeemer(PlutusData(), ExecutionUnits(5000000, 1000000))
    tx_builder.mint = mint
    tx_builder.add_script_input(utxo1, plutus_script, datum, redeemer1)
    tx_builder.add_minting_script(plutus_script, redeemer2)
    receiver = Address.from_primitive(
        "addr_test1vrm9x2zsux7va6w892g38tvchnzahvcd9tykqf3ygnmwtaqyfg52x"
    )
    tx_builder.add_output(TransactionOutput(receiver, 5000000))
    tx_builder.build(change_address=receiver)
    witness = tx_builder.build_witness_set()
    assert [datum] == witness.plutus_data
    assert [plutus_script] == witness.plutus_v1_script

    expected_redeemer_map = RedeemerMap(
        {
            RedeemerKey(RedeemerTag.SPEND, 0): RedeemerValue(
                PlutusData(), ExecutionUnits(1000000, 1000000)
            ),
            RedeemerKey(RedeemerTag.MINT, 0): RedeemerValue(
                PlutusData(), ExecutionUnits(5000000, 1000000)
            ),
        }
    )

    assert expected_redeemer_map == witness.redeemer


def test_transaction_witness_set_redeemers_list(chain_context):
    """Test that TransactionBuilder correctly stores Redeemer list"""
    tx_builder = TransactionBuilder(chain_context)
    redeemer_data = [
        [0, 0, 42, [1000000, 2000000]],
        [1, 1, "Hello", [3000000, 4000000]],
    ]
    tx_builder._redeemers = [Redeemer.from_primitive(r) for r in redeemer_data]

    assert tx_builder._redeemers is not None
    assert len(tx_builder._redeemers) == 2
    assert tx_builder._redeemers[0].tag == RedeemerTag.SPEND
    assert tx_builder._redeemers[0].index == 0
    assert tx_builder._redeemers[0].data == 42
    assert tx_builder._redeemers[0].ex_units == ExecutionUnits(1000000, 2000000)
    assert tx_builder._redeemers[1].tag == RedeemerTag.MINT
    assert tx_builder._redeemers[1].index == 1
    assert tx_builder._redeemers[1].data == "Hello"
    assert tx_builder._redeemers[1].ex_units == ExecutionUnits(3000000, 4000000)


def test_transaction_witness_set_redeemers_dict(chain_context):
    """Test that TransactionBuilder correctly stores RedeemerMap"""
    tx_builder = TransactionBuilder(chain_context)
    redeemer_data = {
        (0, 0): [42, [1000000, 2000000]],
        (1, 1): ["Hello", [3000000, 4000000]],
    }
    tx_builder._redeemers = RedeemerMap(
        {
            RedeemerKey(RedeemerTag(tag), index): RedeemerValue(
                data, ExecutionUnits(*ex_units)
            )
            for (tag, index), (data, ex_units) in redeemer_data.items()
        }
    )

    assert tx_builder._redeemers is not None
    assert isinstance(tx_builder._redeemers, RedeemerMap)
    assert len(tx_builder._redeemers) == 2

    key1 = RedeemerKey(RedeemerTag.SPEND, 0)
    assert tx_builder._redeemers[key1].data == 42
    assert tx_builder._redeemers[key1].ex_units == ExecutionUnits(1000000, 2000000)

    key2 = RedeemerKey(RedeemerTag.MINT, 1)
    assert tx_builder._redeemers[key2].data == "Hello"
    assert tx_builder._redeemers[key2].ex_units == ExecutionUnits(3000000, 4000000)


def test_transaction_witness_set_redeemers_invalid_format(chain_context):
    """Test that TransactionBuilder can store invalid redeemer data"""
    tx_builder = TransactionBuilder(chain_context)
    invalid_redeemer_data = "invalid_data"
    tx_builder._redeemers = invalid_redeemer_data
    assert tx_builder._redeemers == "invalid_data"


def test_transaction_witness_set_no_redeemers(chain_context):
    """Test that build_witness_set() returns a WitnessSet with no Redeemer"""
    tx_builder = TransactionBuilder(chain_context)
    witness_set = tx_builder.build_witness_set()
    assert witness_set.redeemer is None


def test_burning_all_assets_under_single_policy(chain_context):
    """
    Test burning all assets under a single policy with TransactionBuilder.

    This test ensures that burning multiple assets (AssetName1, AssetName2, AssetName3, AssetName4)
    under policy_id_1 removes them from the multi-asset map.

    Steps:
    1. Define assets under policy_id_1 and simulate burning 1 unit of each.
    2. Add UTXOs for the assets and burning instructions.
    3. Build the transaction and verify that all burned assets are removed.

    Args:
        chain_context: The blockchain context.

    Assertions:
        - AssetName1, AssetName2, AssetName3, and AssetName4 are removed after burning.
    """
    tx_builder = TransactionBuilder(chain_context)

    # Create change address
    sender = "addr_test1vrm9x2zsux7va6w892g38tvchnzahvcd9tykqf3ygnmwtaqyfg52x"
    sender_address = Address.from_primitive(sender)

    # Create four transaction inputs
    tx_in1 = TransactionInput.from_primitive(
        ["a6cbe6cadecd3f89b60e08e68e5e6c7d72d730aaa1ad21431590f7e6643438ef", 0]
    )
    tx_in2 = TransactionInput.from_primitive(
        ["b6cbe6cadecd3f89b60e08e68e5e6c7d72d730aaa1ad21431590f7e6643438ef", 1]
    )
    tx_in3 = TransactionInput.from_primitive(
        ["c6cbe6cadecd3f89b60e08e68e5e6c7d72d730aaa1ad21431590f7e6643438ef", 2]
    )
    tx_in4 = TransactionInput.from_primitive(
        ["d6cbe6cadecd3f89b60e08e68e5e6c7d72d730aaa1ad21431590f7e6643438ef", 3]
    )
    # Define a policy ID and asset names
    policy_id_1 = plutus_script_hash(PlutusV1Script(b"dummy script1"))
    multi_asset1 = MultiAsset.from_primitive({policy_id_1.payload: {b"AssetName1": 1}})
    multi_asset2 = MultiAsset.from_primitive({policy_id_1.payload: {b"AssetName2": 1}})
    multi_asset3 = MultiAsset.from_primitive(
        {
            policy_id_1.payload: {b"AssetName3": 1},
        }
    )
    multi_asset4 = MultiAsset.from_primitive(
        {
            policy_id_1.payload: {b"AssetName4": 1},
        }
    )

    # Simulate minting and burning of assets
    mint = MultiAsset.from_primitive(
        {
            policy_id_1.payload: {
                b"AssetName1": -1,
                b"AssetName2": -1,
                b"AssetName3": -1,
                b"AssetName4": -1,
            }
        }
    )

    # Set UTXO for the inputs
    utxo1 = UTxO(
        tx_in1, TransactionOutput(Address(policy_id_1), Value(10000000, multi_asset1))
    )
    utxo2 = UTxO(
        tx_in2, TransactionOutput(Address(policy_id_1), Value(10000000, multi_asset2))
    )
    utxo3 = UTxO(
        tx_in3, TransactionOutput(Address(policy_id_1), Value(10000000, multi_asset3))
    )
    utxo4 = UTxO(
        tx_in4, TransactionOutput(Address(policy_id_1), Value(10000000, multi_asset4))
    )

    # Add UTXO inputs
    tx_builder.add_input(utxo1).add_input(utxo2).add_input(utxo3).add_input(utxo4)

    # Add the minting to the builder
    tx_builder.mint = mint

    # Build the transaction
    tx = tx_builder.build(change_address=sender_address)

    # Check that the transaction has outputs
    assert tx.outputs

    # Loop through the transaction outputs to verify the multi-asset quantities
    for output in tx.outputs:
        multi_asset = output.amount.multi_asset

        # Ensure that AssetName1, AssetName2, AssetName3 and AssetName4 were burnt (removed)
        assert AssetName(b"AssetName1") not in multi_asset.get(policy_id_1, {})
        assert AssetName(b"AssetName2") not in multi_asset.get(policy_id_1, {})
        assert AssetName(b"AssetName3") not in multi_asset.get(policy_id_1, {})
        assert AssetName(b"AseetName4") not in multi_asset.get(policy_id_1, {})
