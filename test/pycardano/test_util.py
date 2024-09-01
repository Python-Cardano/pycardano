from test.pycardano.util import chain_context

import pytest

from pycardano.hash import SCRIPT_HASH_SIZE, ScriptDataHash
from pycardano.plutus import ExecutionUnits, PlutusData, Redeemer, RedeemerTag, Unit
from pycardano.transaction import Value
from pycardano.utils import (
    min_lovelace_pre_alonzo,
    script_data_hash,
    tiered_reference_script_fee,
)


def test_min_lovelace_ada_only(chain_context):
    assert (
        min_lovelace_pre_alonzo(2000000, chain_context)
        == chain_context.protocol_param.min_utxo
    )


def test_min_lovelace_ada_only_2(chain_context):
    assert (
        min_lovelace_pre_alonzo(Value(2000000), chain_context)
        == chain_context.protocol_param.min_utxo
    )


class TestMinLoveLaceMultiAsset:
    # Tests copied from: https://github.com/input-output-hk/cardano-ledger/blob/master/doc/explanations/min-utxo-alonzo.rst#example-min-ada-value-calculations-and-current-constants

    def test_min_lovelace_multi_asset_1(self, chain_context):
        amount = Value.from_primitive(
            [2000000, {b"1" * SCRIPT_HASH_SIZE: {b"": 1000000}}]
        )
        assert min_lovelace_pre_alonzo(amount, chain_context) == 1310316

    def test_min_lovelace_multi_asset_2(self, chain_context):
        amount = Value.from_primitive(
            [2000000, {b"1" * SCRIPT_HASH_SIZE: {b"1": 1000000}}]
        )

        assert min_lovelace_pre_alonzo(amount, chain_context) == 1344798

    def test_min_lovelace_multi_asset_3(self, chain_context):
        amount = Value.from_primitive(
            [
                2000000,
                {
                    b"1"
                    * SCRIPT_HASH_SIZE: {b"1": 1000000, b"2": 2000000, b"3": 3000000}
                },
            ]
        )

        assert min_lovelace_pre_alonzo(amount, chain_context) == 1448244

    def test_min_lovelace_multi_asset_4(self, chain_context):
        amount = Value.from_primitive(
            [
                2000000,
                {
                    b"1" * SCRIPT_HASH_SIZE: {b"": 1000000},
                    b"2" * SCRIPT_HASH_SIZE: {b"": 1000000},
                },
            ]
        )

        assert min_lovelace_pre_alonzo(amount, chain_context) == 1482726

    def test_min_lovelace_multi_asset_5(self, chain_context):
        amount = Value.from_primitive(
            [
                2000000,
                {
                    b"1" * SCRIPT_HASH_SIZE: {b"1": 1000000},
                    b"2" * SCRIPT_HASH_SIZE: {b"2": 1000000},
                },
            ]
        )

        assert min_lovelace_pre_alonzo(amount, chain_context) == 1517208

    def test_min_lovelace_multi_asset_6(self, chain_context):
        amount = Value.from_primitive(
            [
                2000000,
                {
                    b"1"
                    * SCRIPT_HASH_SIZE: {
                        i.to_bytes(1, byteorder="big"): 1000000 * i for i in range(32)
                    },
                    b"2"
                    * SCRIPT_HASH_SIZE: {
                        i.to_bytes(1, byteorder="big"): 1000000 * i
                        for i in range(32, 64)
                    },
                    b"3"
                    * SCRIPT_HASH_SIZE: {
                        i.to_bytes(1, byteorder="big"): 1000000 * i
                        for i in range(64, 96)
                    },
                },
            ]
        )

        assert min_lovelace_pre_alonzo(amount, chain_context) == 6896400

    def test_min_lovelace_multi_asset_7(self, chain_context):
        amount = Value.from_primitive(
            [2000000, {b"1" * SCRIPT_HASH_SIZE: {b"": 1000000}}]
        )

        assert min_lovelace_pre_alonzo(amount, chain_context, True) == 1655136

    def test_min_lovelace_multi_asset_8(self, chain_context):
        amount = Value.from_primitive(
            [
                2000000,
                {
                    b"1"
                    * SCRIPT_HASH_SIZE: {
                        b"1" * 32: 1000000,
                        b"2" * 32: 1000000,
                        b"3" * 32: 1000000,
                    }
                },
            ]
        )

        assert min_lovelace_pre_alonzo(amount, chain_context, True) == 2172366

    def test_min_lovelace_multi_asset_9(self, chain_context):
        amount = Value.from_primitive(
            [
                2000000,
                {
                    b"1"
                    * SCRIPT_HASH_SIZE: {
                        b"": 1000000,
                    },
                    b"2"
                    * SCRIPT_HASH_SIZE: {
                        b"": 1000000,
                    },
                },
            ]
        )

        assert min_lovelace_pre_alonzo(amount, chain_context, True) == 1827546


def test_script_data_hash():
    unit = Unit()
    redeemers = [Redeemer(unit, ExecutionUnits(1000000, 1000000))]
    redeemers[0].tag = RedeemerTag.SPEND
    assert ScriptDataHash.from_primitive(
        "032d812ee0731af78fe4ec67e4d30d16313c09e6fb675af28f825797e8b5621d"
    ) == script_data_hash(redeemers=redeemers, datums=[unit])


def test_script_data_hash_datum_only():
    unit = Unit()
    assert ScriptDataHash.from_primitive(
        "2f50ea2546f8ce020ca45bfcf2abeb02ff18af2283466f888ae489184b3d2d39"
    ) == script_data_hash(redeemers=[], datums=[unit])


def test_script_data_hash_redeemer_only():
    unit = Unit()
    redeemers = []
    assert ScriptDataHash.from_primitive(
        "a88fe2947b8d45d1f8b798e52174202579ecf847b8f17038c7398103df2d27b0"
    ) == script_data_hash(redeemers=redeemers, datums=[])


class MockProtocolParam:
    def __init__(self, max_size, base, range, multiplier):
        self.maximum_reference_scripts_size = {"bytes": max_size}
        self.min_fee_reference_scripts = {
            "base": base,
            "range": range,
            "multiplier": multiplier,
        }


class MockChainContext:
    def __init__(self, protocol_param):
        self.protocol_param = protocol_param


@pytest.mark.parametrize(
    "max_size,base,range,multiplier,scripts_size,expected",
    [
        (200 * 1024, 44, 25600, 1.2, 80 * 1024, 4489380),
    ],
)
def test_tiered_reference_script_fee(
    max_size, base, range, multiplier, scripts_size, expected
):
    protocol_param = MockProtocolParam(max_size, base, range, multiplier)
    context = MockChainContext(protocol_param)

    result = tiered_reference_script_fee(context, scripts_size)
    assert result == expected


def test_tiered_reference_script_fee_exceeds_max_size():
    protocol_param = MockProtocolParam(1000, 10, 100, 1.1)
    context = MockChainContext(protocol_param)

    with pytest.raises(
        ValueError, match="Reference scripts size: 1001 exceeds maximum allowed size"
    ):
        tiered_reference_script_fee(context, 1001)


def test_tiered_reference_script_fee_no_params():
    class EmptyProtocolParam:
        maximum_reference_scripts_size = None
        min_fee_reference_scripts = None

    context = MockChainContext(EmptyProtocolParam())

    result = tiered_reference_script_fee(context, 100)
    assert result == 0
