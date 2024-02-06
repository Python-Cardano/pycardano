import json
from pathlib import Path
from typing import List
from unittest.mock import patch

import pytest

from pycardano import (
    ALONZO_COINS_PER_UTXO_WORD,
    CardanoCliChainContext,
    CardanoCliNetwork,
    GenesisParameters,
    MultiAsset,
    ProtocolParameters,
    TransactionInput,
)

QUERY_TIP_RESULT = {
    "block": 1460093,
    "epoch": 98,
    "era": "Babbage",
    "hash": "c1bda7b2975dd3bf9969a57d92528ba7d60383b6e1c4a37b68379c4f4330e790",
    "slot": 41008115,
    "slotInEpoch": 313715,
    "slotsToEpochEnd": 118285,
    "syncProgress": "100.00",
}

QUERY_PROTOCOL_PARAMETERS_RESULT = {
    "collateralPercentage": 150,
    "costModels": {
        "PlutusV1": [
            205665,
            812,
            1,
            1,
            1000,
            571,
            0,
            1,
            1000,
            24177,
            4,
            1,
            1000,
            32,
            117366,
            10475,
            4,
            23000,
            100,
            23000,
            100,
            23000,
            100,
            23000,
            100,
            23000,
            100,
            23000,
            100,
            100,
            100,
            23000,
            100,
            19537,
            32,
            175354,
            32,
            46417,
            4,
            221973,
            511,
            0,
            1,
            89141,
            32,
            497525,
            14068,
            4,
            2,
            196500,
            453240,
            220,
            0,
            1,
            1,
            1000,
            28662,
            4,
            2,
            245000,
            216773,
            62,
            1,
            1060367,
            12586,
            1,
            208512,
            421,
            1,
            187000,
            1000,
            52998,
            1,
            80436,
            32,
            43249,
            32,
            1000,
            32,
            80556,
            1,
            57667,
            4,
            1000,
            10,
            197145,
            156,
            1,
            197145,
            156,
            1,
            204924,
            473,
            1,
            208896,
            511,
            1,
            52467,
            32,
            64832,
            32,
            65493,
            32,
            22558,
            32,
            16563,
            32,
            76511,
            32,
            196500,
            453240,
            220,
            0,
            1,
            1,
            69522,
            11687,
            0,
            1,
            60091,
            32,
            196500,
            453240,
            220,
            0,
            1,
            1,
            196500,
            453240,
            220,
            0,
            1,
            1,
            806990,
            30482,
            4,
            1927926,
            82523,
            4,
            265318,
            0,
            4,
            0,
            85931,
            32,
            205665,
            812,
            1,
            1,
            41182,
            32,
            212342,
            32,
            31220,
            32,
            32696,
            32,
            43357,
            32,
            32247,
            32,
            38314,
            32,
            57996947,
            18975,
            10,
        ],
        "PlutusV2": [
            205665,
            812,
            1,
            1,
            1000,
            571,
            0,
            1,
            1000,
            24177,
            4,
            1,
            1000,
            32,
            117366,
            10475,
            4,
            23000,
            100,
            23000,
            100,
            23000,
            100,
            23000,
            100,
            23000,
            100,
            23000,
            100,
            100,
            100,
            23000,
            100,
            19537,
            32,
            175354,
            32,
            46417,
            4,
            221973,
            511,
            0,
            1,
            89141,
            32,
            497525,
            14068,
            4,
            2,
            196500,
            453240,
            220,
            0,
            1,
            1,
            1000,
            28662,
            4,
            2,
            245000,
            216773,
            62,
            1,
            1060367,
            12586,
            1,
            208512,
            421,
            1,
            187000,
            1000,
            52998,
            1,
            80436,
            32,
            43249,
            32,
            1000,
            32,
            80556,
            1,
            57667,
            4,
            1000,
            10,
            197145,
            156,
            1,
            197145,
            156,
            1,
            204924,
            473,
            1,
            208896,
            511,
            1,
            52467,
            32,
            64832,
            32,
            65493,
            32,
            22558,
            32,
            16563,
            32,
            76511,
            32,
            196500,
            453240,
            220,
            0,
            1,
            1,
            69522,
            11687,
            0,
            1,
            60091,
            32,
            196500,
            453240,
            220,
            0,
            1,
            1,
            196500,
            453240,
            220,
            0,
            1,
            1,
            1159724,
            392670,
            0,
            2,
            806990,
            30482,
            4,
            1927926,
            82523,
            4,
            265318,
            0,
            4,
            0,
            85931,
            32,
            205665,
            812,
            1,
            1,
            41182,
            32,
            212342,
            32,
            31220,
            32,
            32696,
            32,
            43357,
            32,
            32247,
            32,
            38314,
            32,
            35892428,
            10,
            57996947,
            18975,
            10,
            38887044,
            32947,
            10,
        ],
    },
    "decentralization": None,
    "executionUnitPrices": {"priceMemory": 5.77e-2, "priceSteps": 7.21e-5},
    "extraPraosEntropy": None,
    "maxBlockBodySize": 90112,
    "maxBlockExecutionUnits": {"memory": 62000000, "steps": 20000000000},
    "maxBlockHeaderSize": 1100,
    "maxCollateralInputs": 3,
    "maxTxExecutionUnits": {"memory": 14000000, "steps": 10000000000},
    "maxTxSize": 16384,
    "maxValueSize": 5000,
    "minPoolCost": 340000000,
    "minUTxOValue": None,
    "monetaryExpansion": 3.0e-3,
    "poolPledgeInfluence": 0.3,
    "poolRetireMaxEpoch": 18,
    "protocolVersion": {"major": 8, "minor": 0},
    "stakeAddressDeposit": 2000000,
    "stakePoolDeposit": 500000000,
    "stakePoolTargetNum": 500,
    "treasuryCut": 0.2,
    "txFeeFixed": 155381,
    "txFeePerByte": 44,
    "utxoCostPerByte": 4310,
    "utxoCostPerWord": None,
}

QUERY_UTXO_RESULT = '{"fbaa018740241abb935240051134914389c3f94647d8bd6c30cb32d3fdb799bf#0": {"address": "addr1x8nz307k3sr60gu0e47cmajssy4fmld7u493a4xztjrll0aj764lvrxdayh2ux30fl0ktuh27csgmpevdu89jlxppvrswgxsta", "datum": null, "inlineDatum": {"constructor": 0, "fields": [{"constructor": 0, "fields": [{"bytes": "2e11e7313e00ccd086cfc4f1c3ebed4962d31b481b6a153c23601c0f"}, {"bytes": "636861726c69335f6164615f6e6674"}]}, {"constructor": 0, "fields": [{"bytes": ""}, {"bytes": ""}]}, {"constructor": 0, "fields": [{"bytes": "8e51398904a5d3fc129fbf4f1589701de23c7824d5c90fdb9490e15a"}, {"bytes": "434841524c4933"}]}, {"constructor": 0, "fields": [{"bytes": "d8d46a3e430fab5dc8c5a0a7fc82abbf4339a89034a8c804bb7e6012"}, {"bytes": "636861726c69335f6164615f6c71"}]}, {"int": 997}, {"list": [{"bytes": "4dd98a2ef34bc7ac3858bbcfdf94aaa116bb28ca7e01756140ba4d19"}]}, {"int": 10000000000}]}, "inlineDatumhash": "c56003cba9cfcf2f73cf6a5f4d6354d03c281bcd2bbd7a873d7475faa10a7123", "referenceScript": null, "value": {"2e11e7313e00ccd086cfc4f1c3ebed4962d31b481b6a153c23601c0f": {"636861726c69335f6164615f6e6674": 1}, "8e51398904a5d3fc129fbf4f1589701de23c7824d5c90fdb9490e15a": {"434841524c4933": 1367726755}, "d8d46a3e430fab5dc8c5a0a7fc82abbf4339a89034a8c804bb7e6012": {"636861726c69335f6164615f6c71": 9223372035870126880}, "lovelace": 708864940}}}'


def override_run_command(cmd: List[str]):
    """
    Override the run_command method of CardanoCliChainContext to return a mock result
    Args:
        cmd: The command to run

    Returns:
        The mock result
    """
    if "tip" in cmd:
        return json.dumps(QUERY_TIP_RESULT)
    if "protocol-parameters" in cmd:
        return json.dumps(QUERY_PROTOCOL_PARAMETERS_RESULT)
    if "utxo" in cmd:
        return QUERY_UTXO_RESULT
    if "txid" in cmd:
        return "270be16fa17cdb3ef683bf2c28259c978d4b7088792074f177c8efda247e23f7"
    else:
        return None


@pytest.fixture
def chain_context(genesis_file, config_file):
    """
    Create a CardanoCliChainContext with a mock run_command method
    Args:
        genesis_file: The genesis file
        config_file: The config file

    Returns:
        The CardanoCliChainContext
    """
    with patch(
        "pycardano.backend.cardano_cli.CardanoCliChainContext._run_command",
        side_effect=override_run_command,
    ):
        context = CardanoCliChainContext(
            binary=Path("cardano-cli"),
            socket=Path("node.socket"),
            config_file=config_file,
            network=CardanoCliNetwork.PREPROD,
        )
        context._run_command = override_run_command
    return context


class TestCardanoCliChainContext:
    def test_protocol_param(self, chain_context):
        assert (
            ProtocolParameters(
                min_fee_constant=QUERY_PROTOCOL_PARAMETERS_RESULT["txFeeFixed"],
                min_fee_coefficient=QUERY_PROTOCOL_PARAMETERS_RESULT["txFeePerByte"],
                max_block_size=QUERY_PROTOCOL_PARAMETERS_RESULT["maxBlockBodySize"],
                max_tx_size=QUERY_PROTOCOL_PARAMETERS_RESULT["maxTxSize"],
                max_block_header_size=QUERY_PROTOCOL_PARAMETERS_RESULT[
                    "maxBlockHeaderSize"
                ],
                key_deposit=QUERY_PROTOCOL_PARAMETERS_RESULT["stakeAddressDeposit"],
                pool_deposit=QUERY_PROTOCOL_PARAMETERS_RESULT["stakePoolDeposit"],
                pool_influence=QUERY_PROTOCOL_PARAMETERS_RESULT["poolPledgeInfluence"],
                monetary_expansion=QUERY_PROTOCOL_PARAMETERS_RESULT[
                    "monetaryExpansion"
                ],
                treasury_expansion=QUERY_PROTOCOL_PARAMETERS_RESULT["treasuryCut"],
                decentralization_param=QUERY_PROTOCOL_PARAMETERS_RESULT.get(
                    "decentralization", 0
                ),
                extra_entropy=QUERY_PROTOCOL_PARAMETERS_RESULT.get(
                    "extraPraosEntropy", ""
                ),
                protocol_major_version=int(
                    QUERY_PROTOCOL_PARAMETERS_RESULT["protocolVersion"]["major"]
                ),
                protocol_minor_version=int(
                    QUERY_PROTOCOL_PARAMETERS_RESULT["protocolVersion"]["minor"]
                ),
                min_utxo=QUERY_PROTOCOL_PARAMETERS_RESULT["utxoCostPerByte"],
                min_pool_cost=QUERY_PROTOCOL_PARAMETERS_RESULT["minPoolCost"],
                price_mem=float(
                    QUERY_PROTOCOL_PARAMETERS_RESULT["executionUnitPrices"][
                        "priceMemory"
                    ]
                ),
                price_step=float(
                    QUERY_PROTOCOL_PARAMETERS_RESULT["executionUnitPrices"][
                        "priceSteps"
                    ]
                ),
                max_tx_ex_mem=int(
                    QUERY_PROTOCOL_PARAMETERS_RESULT["maxTxExecutionUnits"]["memory"]
                ),
                max_tx_ex_steps=int(
                    QUERY_PROTOCOL_PARAMETERS_RESULT["maxTxExecutionUnits"]["steps"]
                ),
                max_block_ex_mem=int(
                    QUERY_PROTOCOL_PARAMETERS_RESULT["maxBlockExecutionUnits"]["memory"]
                ),
                max_block_ex_steps=int(
                    QUERY_PROTOCOL_PARAMETERS_RESULT["maxBlockExecutionUnits"]["steps"]
                ),
                max_val_size=QUERY_PROTOCOL_PARAMETERS_RESULT["maxValueSize"],
                collateral_percent=QUERY_PROTOCOL_PARAMETERS_RESULT[
                    "collateralPercentage"
                ],
                max_collateral_inputs=QUERY_PROTOCOL_PARAMETERS_RESULT[
                    "maxCollateralInputs"
                ],
                coins_per_utxo_word=QUERY_PROTOCOL_PARAMETERS_RESULT.get(
                    "coinsPerUtxoWord", ALONZO_COINS_PER_UTXO_WORD
                ),
                coins_per_utxo_byte=QUERY_PROTOCOL_PARAMETERS_RESULT.get(
                    "coinsPerUtxoByte", 0
                ),
                cost_models=QUERY_PROTOCOL_PARAMETERS_RESULT["costModels"],
            )
            == chain_context.protocol_param
        )

    def test_genesis(self, chain_context, genesis_json):
        assert (
            GenesisParameters(
                active_slots_coefficient=genesis_json["activeSlotsCoeff"],
                update_quorum=genesis_json["updateQuorum"],
                max_lovelace_supply=genesis_json["maxLovelaceSupply"],
                network_magic=genesis_json["networkMagic"],
                epoch_length=genesis_json["epochLength"],
                system_start=genesis_json["systemStart"],
                slots_per_kes_period=genesis_json["slotsPerKESPeriod"],
                slot_length=genesis_json["slotLength"],
                max_kes_evolutions=genesis_json["maxKESEvolutions"],
                security_param=genesis_json["securityParam"],
            )
            == chain_context.genesis_param
        )

    def test_utxo(self, chain_context):
        results = chain_context.utxos(
            "addr_test1qqmnh90jyfaajul4h2mawrxz4rfx04hpaadstm6y8wr90kyhf4dqfm247jlvna83g5wx9veaymzl6g9t833grknh3yhqxhzh4n"
        )

        assert results[0].input == TransactionInput.from_primitive(
            ["fbaa018740241abb935240051134914389c3f94647d8bd6c30cb32d3fdb799bf", 0]
        )
        assert results[0].output.amount.coin == 708864940

        assert (
            str(results[0].output.address)
            == "addr1x8nz307k3sr60gu0e47cmajssy4fmld7u493a4xztjrll0aj764lvrxdayh2ux30fl0ktuh27csgmpevdu89jlxppvrswgxsta"
        )

        assert isinstance(results[0].output.datum, dict)

        assert results[0].output.amount.multi_asset == MultiAsset.from_primitive(
            {
                "2e11e7313e00ccd086cfc4f1c3ebed4962d31b481b6a153c23601c0f": {
                    "636861726c69335f6164615f6e6674": 1
                },
                "8e51398904a5d3fc129fbf4f1589701de23c7824d5c90fdb9490e15a": {
                    "434841524c4933": 1367726755
                },
                "d8d46a3e430fab5dc8c5a0a7fc82abbf4339a89034a8c804bb7e6012": {
                    "636861726c69335f6164615f6c71": 9223372035870126880
                },
            }
        )

    def test_submit_tx(self, chain_context):
        results = chain_context.submit_tx("testcborhexfromtransaction")

        assert (
            results
            == "270be16fa17cdb3ef683bf2c28259c978d4b7088792074f177c8efda247e23f7"
        )
