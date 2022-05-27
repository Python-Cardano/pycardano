from dataclasses import replace
from test.pycardano.test_key import SK
from test.pycardano.util import chain_context

import pytest

from pycardano.address import Address
from pycardano.certificate import StakeCredential, StakeDelegation, StakeRegistration
from pycardano.coinselection import RandomImproveMultiAsset
from pycardano.exception import (
    InsufficientUTxOBalanceException,
    InvalidTransactionException,
    UTxOSelectionException,
)
from pycardano.hash import (
    POOL_KEY_HASH_SIZE,
    VERIFICATION_KEY_HASH_SIZE,
    PoolKeyHash,
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
    Redeemer,
    RedeemerTag,
    plutus_script_hash,
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
from pycardano.witness import VerificationKeyWitness


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
                    5332431,
                    {b"1111111111111111111111111111": {b"Token1": 1, b"Token2": 2}},
                ],
            ],
        ],
        2: 167569,
    }

    assert expected == tx_body.to_primitive()


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
        tx_body = tx_builder.build(change_address=sender_address)

    # The unfulfilled amount includes requested (991000000) and estimated fees (161277)
    assert "Unfulfilled amount:\n {'coin': 991161277" in e.value.args[0]
    assert "{AssetName(b'NewToken'): 1}" in e.value.args[0]


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
        tx_body = tx_builder.build(change_address=sender_address)


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
    sender_address = Address.from_primitive(sender)

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
                    5811267,
                    {b"1111111111111111111111111111": {b"Token1": 1, b"Token2": 2}},
                ],
            ],
        ],
        2: 188733,
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
                [2482969, {b"1111111111111111111111111111": {b"Token2": 2}}],
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
        TransactionOutput(Address.from_primitive(sender), input_utxo.output.amount)
    )

    with pytest.raises(UTxOSelectionException):
        # Tx builder must fail here because there is not enough amount of input ADA to pay tx fee
        tx_body = tx_builder.build(change_address=sender_address)


def test_add_script_input(chain_context):
    tx_builder = TransactionBuilder(chain_context)
    tx_in1 = TransactionInput.from_primitive(
        ["18cbe6cadecd3f89b60e08e68e5e6c7d72d730aaa1ad21431590f7e6643438ef", 0]
    )
    tx_in2 = TransactionInput.from_primitive(
        ["18cbe6cadecd3f89b60e08e68e5e6c7d72d730aaa1ad21431590f7e6643438ef", 1]
    )
    plutus_script = b"dummy test script"
    script_hash = plutus_script_hash(plutus_script)
    script_address = Address(script_hash)
    datum = PlutusData()
    utxo1 = UTxO(
        tx_in1, TransactionOutput(script_address, 10000000, datum_hash=datum.hash())
    )
    mint = MultiAsset.from_primitive({script_hash.payload: {b"TestToken": 1}})
    utxo2 = UTxO(
        tx_in2,
        TransactionOutput(
            script_address, Value(10000000, mint), datum_hash=datum.hash()
        ),
    )
    redeemer1 = Redeemer(
        RedeemerTag.SPEND, PlutusData(), ExecutionUnits(1000000, 1000000)
    )
    redeemer2 = Redeemer(
        RedeemerTag.MINT, PlutusData(), ExecutionUnits(1000000, 1000000)
    )
    tx_builder.mint = mint
    tx_builder.add_script_input(utxo1, plutus_script, datum, redeemer1)
    tx_builder.add_script_input(utxo2, plutus_script, datum, redeemer2)
    receiver = Address.from_primitive(
        "addr_test1vrm9x2zsux7va6w892g38tvchnzahvcd9tykqf3ygnmwtaqyfg52x"
    )
    tx_builder.add_output(TransactionOutput(receiver, 5000000))
    tx_body = tx_builder.build(change_address=receiver)
    witness = tx_builder.build_witness_set()
    assert [datum] == witness.plutus_data
    assert [redeemer1, redeemer2] == witness.redeemer
    assert [plutus_script] == witness.plutus_script
    assert (
        "a5008282582018cbe6cadecd3f89b60e08e68e5e6c7d72d730aaa1ad2143159"
        "0f7e6643438ef0082582018cbe6cadecd3f89b60e08e68e5e6c7d72d730aaa1"
        "ad21431590f7e6643438ef01018282581d60f6532850e1bccee9c72a9113ad9"
        "8bcc5dbb30d2ac960262444f6e5f41a004c4b4082581d60f6532850e1bccee9"
        "c72a9113ad98bcc5dbb30d2ac960262444f6e5f4821a00e083cfa1581c876f1"
        "9078b059c928258d848c8cd871864d281eb6776ed7f80b68536a14954657374"
        "546f6b656e02021a00045df109a1581c876f19078b059c928258d848c8cd871"
        "864d281eb6776ed7f80b68536a14954657374546f6b656e010b5820c0978261"
        "d9818d92926eb031d38d141f513a05478d697555f32edf6443ebeb08" == tx_body.to_cbor()
    )


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
    tx = tx_builder2.build_and_sign([SK], change_address=sender_address)

    assert tx.transaction_witness_set.vkey_witnesses == [
        VerificationKeyWitness(SK.to_verification_key(), SK.sign(tx_body.hash()))
    ]
    assert (
        "a300818258203131313131313131313131313131313131313131313131313131313131313131"
        "00018282581d60f6532850e1bccee9c72a9113ad98bcc5dbb30d2ac960262444f6e5f41a0007"
        "a12082581d60f6532850e1bccee9c72a9113ad98bcc5dbb30d2ac960262444f6e5f41a004223"
        "fb021a00028625" == tx_body.to_cbor()
    )


def test_estimate_execution_unit(chain_context):
    tx_builder = TransactionBuilder(chain_context)
    tx_in1 = TransactionInput.from_primitive(
        ["18cbe6cadecd3f89b60e08e68e5e6c7d72d730aaa1ad21431590f7e6643438ef", 0]
    )
    plutus_script = b"dummy test script"
    script_hash = plutus_script_hash(plutus_script)
    script_address = Address(script_hash)
    datum = PlutusData()
    utxo1 = UTxO(
        tx_in1, TransactionOutput(script_address, 10000000, datum_hash=datum.hash())
    )
    mint = MultiAsset.from_primitive({script_hash.payload: {b"TestToken": 1}})
    redeemer1 = Redeemer(RedeemerTag.SPEND, PlutusData())
    tx_builder.mint = mint
    tx_builder.add_script_input(utxo1, plutus_script, datum, redeemer1)
    receiver = Address.from_primitive(
        "addr_test1vrm9x2zsux7va6w892g38tvchnzahvcd9tykqf3ygnmwtaqyfg52x"
    )
    tx_builder.add_output(TransactionOutput(receiver, 5000000))
    tx_body = tx_builder.build(change_address=receiver)
    witness = tx_builder.build_witness_set()
    assert [datum] == witness.plutus_data
    assert [redeemer1] == witness.redeemer
    assert redeemer1.ex_units is not None
    assert [plutus_script] == witness.plutus_script
    assert (
        "a5008182582018cbe6cadecd3f89b60e08e68e5e6c7d72d730aaa1ad21431590f7e6643438e"
        "f00018282581d60f6532850e1bccee9c72a9113ad98bcc5dbb30d2ac960262444f6e5f41a00"
        "4c4b4082581d60f6532850e1bccee9c72a9113ad98bcc5dbb30d2ac960262444f6e5f4821a0"
        "0491226a1581c876f19078b059c928258d848c8cd871864d281eb6776ed7f80b68536a14954"
        "657374546f6b656e01021a0003391a09a1581c876f19078b059c928258d848c8cd871864d28"
        "1eb6776ed7f80b68536a14954657374546f6b656e010b58206b5664c6f79646f2a4c17bdc1e"
        "cb6f6bf540db5c82dfa0a9d806c435398756fa" == tx_body.to_cbor()
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
    assert tx.transaction_body.fee >= fee(chain_context, len(tx.to_cbor("bytes")))


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

    tx_body = tx_builder.build(change_address=sender_address, merge_change=True)

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

    tx_body = tx_builder.build(change_address=sender_address, merge_change=True)

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

    tx_body = tx_builder.build(change_address=sender_address, merge_change=True)

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

    tx_body = tx_builder.build(change_address=sender_address, merge_change=True)

    expected = {
        0: [[b"11111111111111111111111111111111", 3]],
        1: [
            [sender_address.to_primitive(), 9836215],
        ],
        2: 163785,
    }

    assert expected == tx_body.to_primitive()
