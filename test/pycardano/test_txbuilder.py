from dataclasses import replace
from test.pycardano.test_key import SK
from test.pycardano.util import chain_context
from unittest.mock import patch

import pytest

from pycardano.address import Address
from pycardano.certificate import StakeCredential, StakeDelegation, StakeRegistration
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
    plutus_script = PlutusV1Script(b"dummy test script")
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
    assert [plutus_script] == witness.plutus_v1_script
    assert (
        "a6008282582018cbe6cadecd3f89b60e08e68e5e6c7d72d730aaa1ad21431590f7e6643438"
        "ef0082582018cbe6cadecd3f89b60e08e68e5e6c7d72d730aaa1ad21431590f7e6643438ef"
        "01018282581d60f6532850e1bccee9c72a9113ad98bcc5dbb30d2ac960262444f6e5f41a00"
        "4c4b4082581d60f6532850e1bccee9c72a9113ad98bcc5dbb30d2ac960262444f6e5f4821a"
        "00e06beba1581c876f19078b059c928258d848c8cd871864d281eb6776ed7f80b68536a149"
        "54657374546f6b656e02021a000475d509a1581c876f19078b059c928258d848c8cd871864"
        "d281eb6776ed7f80b68536a14954657374546f6b656e010b5820c0978261d9818d92926eb0"
        "31d38d141f513a05478d697555f32edf6443ebeb080d818258203131313131313131313131"
        "31313131313131313131313131313131313131313100" == tx_body.to_cbor()
    )


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
    redeemer = Redeemer(
        RedeemerTag.SPEND, PlutusData(), ExecutionUnits(1000000, 1000000)
    )
    tx_builder.add_script_input(utxo1, datum=datum, redeemer=redeemer)
    receiver = Address.from_primitive(
        "addr_test1vrm9x2zsux7va6w892g38tvchnzahvcd9tykqf3ygnmwtaqyfg52x"
    )
    tx_builder.add_output(TransactionOutput(receiver, 5000000))
    tx_body = tx_builder.build(change_address=receiver)
    witness = tx_builder.build_witness_set()
    assert [datum] == witness.plutus_data
    assert [redeemer] == witness.redeemer
    assert witness.plutus_v1_script is None
    assert (
        "a6008182582018cbe6cadecd3f89b60e08e68e5e6c7d72d730aaa1ad21431590f"
        "7e6643438ef00018282581d60f6532850e1bccee9c72a9113ad98bcc5dbb30d2a"
        "c960262444f6e5f41a004c4b4082581d60f6532850e1bccee9c72a9113ad98bcc"
        "5dbb30d2ac960262444f6e5f41a0048cc3b021a00037f050b5820032d812ee073"
        "1af78fe4ec67e4d30d16313c09e6fb675af28f825797e8b5621d0d81825820313"
        "13131313131313131313131313131313131313131313131313131313131310012"
        "8182582018cbe6cadecd3f89b60e08e68e5e6c7d72d730aaa1ad21431590f7e66"
        "43438ef00" == tx_body.to_cbor()
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

        redeemer = Redeemer(
            RedeemerTag.SPEND, PlutusData(), ExecutionUnits(1000000, 1000000)
        )
        tx_builder.add_script_input(utxo1, datum=datum, redeemer=redeemer)
        receiver = Address.from_primitive(
            "addr_test1vrm9x2zsux7va6w892g38tvchnzahvcd9tykqf3ygnmwtaqyfg52x"
        )
        tx_builder.add_output(TransactionOutput(receiver, 5000000))
        tx_body = tx_builder.build(change_address=receiver)
        witness = tx_builder.build_witness_set()
        assert [datum] == witness.plutus_data
        assert [redeemer] == witness.redeemer
        assert witness.plutus_v1_script is None
        assert [existing_script_utxo.input] == tx_body.reference_inputs
        assert (
            "a6008182582018cbe6cadecd3f89b60e08e68e5e6c7d72d730aaa1ad2143159"
            "0f7e6643438ef00018282581d60f6532850e1bccee9c72a9113ad98bcc5dbb3"
            "0d2ac960262444f6e5f41a004c4b4082581d60f6532850e1bccee9c72a9113a"
            "d98bcc5dbb30d2ac960262444f6e5f41a0048cc3b021a00037f050b5820032d"
            "812ee0731af78fe4ec67e4d30d16313c09e6fb675af28f825797e8b5621d0d8"
            "182582031313131313131313131313131313131313131313131313131313131"
            "3131313100128182582041cb004bec7051621b19b46aea28f0657a586a05ce2"
            "013152ea9b9f1a5614cc701" == tx_body.to_cbor()
        )


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

    redeemer = Redeemer(
        RedeemerTag.SPEND, PlutusData(), ExecutionUnits(1000000, 1000000)
    )
    tx_builder.add_script_input(
        utxo1, script=existing_script_utxo, datum=datum, redeemer=redeemer
    )
    receiver = Address.from_primitive(
        "addr_test1vrm9x2zsux7va6w892g38tvchnzahvcd9tykqf3ygnmwtaqyfg52x"
    )
    tx_builder.add_output(TransactionOutput(receiver, 5000000))
    tx_body = tx_builder.build(change_address=receiver)
    witness = tx_builder.build_witness_set()
    assert [datum] == witness.plutus_data
    assert [redeemer] == witness.redeemer
    assert witness.plutus_v2_script is None
    assert [existing_script_utxo.input] == tx_body.reference_inputs
    assert (
        "a6008182582018cbe6cadecd3f89b60e08e68e5e6c7d72d730aaa1ad21431590f"
        "7e6643438ef00018282581d60f6532850e1bccee9c72a9113ad98bcc5dbb30d2a"
        "c960262444f6e5f41a004c4b4082581d60f6532850e1bccee9c72a9113ad98bcc"
        "5dbb30d2ac960262444f6e5f41a0048cc3b021a00037f050b5820a7d386051637"
        "cc7cede8248ac54c2a236cbf5f243b0992690f850213908dfdc80d81825820313"
        "13131313131313131313131313131313131313131313131313131313131310012"
        "8182582041cb004bec7051621b19b46aea28f0657a586a05ce2013152ea9b9f1a"
        "5614cc701" == tx_body.to_cbor()
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

    redeemer = Redeemer(
        RedeemerTag.MINT, PlutusData(), ExecutionUnits(1000000, 1000000)
    )
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
    witness = tx_builder.build_witness_set()
    assert witness.plutus_data is None
    assert [redeemer] == witness.redeemer
    assert witness.plutus_v2_script is None
    assert [existing_script_utxo.input] == tx_body.reference_inputs
    assert (
        "a700828258203131313131313131313131313131313131313131313131313131313131313131"
        "0082582032323232323232323232323232323232323232323232323232323232323232320101"
        "8282581d60f6532850e1bccee9c72a9113ad98bcc5dbb30d2ac960262444f6e5f41a004c4b40"
        "82581d60f6532850e1bccee9c72a9113ad98bcc5dbb30d2ac960262444f6e5f4821a0057f1f3"
        "a2581c31313131313131313131313131313131313131313131313131313131a246546f6b656e"
        "310146546f6b656e3202581c669ce610ef17d3ac9f5663f0748381120376e72b031e002db95a"
        "3981a14954657374546f6b656e01021a00039b8d09a1581c669ce610ef17d3ac9f5663f07483"
        "81120376e72b031e002db95a3981a14954657374546f6b656e010b5820504d5986e26eadcddd"
        "03916366882b80e2aef090468379b67e757853505f7bc20d8182582031313131313131313131"
        "3131313131313131313131313131313131313131313100128182582041cb004bec7051621b19"
        "b46aea28f0657a586a05ce2013152ea9b9f1a5614cc701" == tx_body.to_cbor()
    )


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

        redeemer = Redeemer(
            RedeemerTag.SPEND, PlutusData(), ExecutionUnits(1000000, 1000000)
        )
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
    utxo2 = UTxO(
        tx_in2,
        TransactionOutput(
            script_address, Value(10000000, mint), datum_hash=datum.hash()
        ),
    )
    redeemer1 = Redeemer(RedeemerTag.SPEND, PlutusData())
    redeemer2 = Redeemer(RedeemerTag.MINT, PlutusData())
    redeemer3 = Redeemer(
        RedeemerTag.MINT, PlutusData(), ExecutionUnits(1000000, 1000000)
    )
    tx_builder.mint = mint
    tx_builder.add_script_input(utxo1, plutus_script, datum, redeemer1)
    tx_builder.add_script_input(utxo1, plutus_script, datum, redeemer2)
    with pytest.raises(InvalidArgumentException):
        tx_builder.add_script_input(utxo2, plutus_script, datum, redeemer3)


def test_all_redeemer_should_provide_execution_units(chain_context):
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
    redeemer1 = Redeemer(
        RedeemerTag.SPEND, PlutusData(), ExecutionUnits(1000000, 1000000)
    )
    redeemer2 = Redeemer(RedeemerTag.MINT, PlutusData())
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
    redeemer1 = Redeemer(
        RedeemerTag.MINT, PlutusData(), ExecutionUnits(1000000, 1000000)
    )
    tx_builder.mint = mint
    tx_builder.add_input(utxo1)
    tx_builder.add_minting_script(plutus_script, redeemer1)
    receiver = Address.from_primitive(
        "addr_test1vrm9x2zsux7va6w892g38tvchnzahvcd9tykqf3ygnmwtaqyfg52x"
    )
    tx_builder.add_output(TransactionOutput(receiver, Value(5000000, mint)))
    tx_body = tx_builder.build(change_address=receiver)
    witness = tx_builder.build_witness_set()
    assert [plutus_script] == witness.plutus_v1_script
    assert (
        "a6008182582018cbe6cadecd3f89b60e08e68e5e6c7d72d730aaa1ad21431590f7e6643438ef"
        "00018282581d60f6532850e1bccee9c72a9113ad98bcc5dbb30d2ac960262444f6e5f4821a00"
        "4c4b40a1581c876f19078b059c928258d848c8cd871864d281eb6776ed7f80b68536a1495465"
        "7374546f6b656e0182581d60f6532850e1bccee9c72a9113ad98bcc5dbb30d2ac960262444f6"
        "e5f41a0048c10f021a00038a3109a1581c876f19078b059c928258d848c8cd871864d281eb67"
        "76ed7f80b68536a14954657374546f6b656e010b58205fcf68adc7eb6e507d15fb07d1c4e39d"
        "908bc9dfe642368afcddd881c5d465170d818258203131313131313131313131313131313131"
        "31313131313131313131313131313100" == tx_body.to_cbor()
    )


def test_add_minting_script_wrong_redeemer_type(chain_context):
    tx_builder = TransactionBuilder(chain_context)
    plutus_script = PlutusV1Script(b"dummy test script")
    redeemer1 = Redeemer(
        RedeemerTag.SPEND, PlutusData(), ExecutionUnits(1000000, 1000000)
    )

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
    plutus_script = PlutusV1Script(b"dummy test script")
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
    assert [plutus_script] == witness.plutus_v1_script
    assert (
        "a6008182582018cbe6cadecd3f89b60e08e68e5e6c7d72d730aaa1ad21431590f7e6643438ef"
        "00018282581d60f6532850e1bccee9c72a9113ad98bcc5dbb30d2ac960262444f6e5f41a004c"
        "4b4082581d60f6532850e1bccee9c72a9113ad98bcc5dbb30d2ac960262444f6e5f4821a0048"
        "fa42a1581c876f19078b059c928258d848c8cd871864d281eb6776ed7f80b68536a149546573"
        "74546f6b656e01021a000350fe09a1581c876f19078b059c928258d848c8cd871864d281eb67"
        "76ed7f80b68536a14954657374546f6b656e010b58206b5664c6f79646f2a4c17bdc1ecb6f6b"
        "f540db5c82dfa0a9d806c435398756fa0d818258203131313131313131313131313131313131"
        "31313131313131313131313131313100" == tx_body.to_cbor()
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
        signed_tx = builder.build(change_address=address)


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
        signed_tx = builder.build(change_address=address)


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
