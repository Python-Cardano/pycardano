from pycardano.backend.base import GenesisParameters, ProtocolParameters
from pycardano.backend.ogmios import OgmiosChainContext
from pycardano.network import Network
from pycardano.transaction import MultiAsset, TransactionInput

PROTOCOL_RESULT = {
    "minFeeCoefficient": 44,
    "minFeeConstant": 155381,
    "maxBlockBodySize": 65536,
    "maxBlockHeaderSize": 1100,
    "maxTxSize": 16384,
    "stakeKeyDeposit": 0,
    "poolDeposit": 0,
    "poolRetirementEpochBound": 18,
    "desiredNumberOfPools": 100,
    "poolInfluence": "0/1",
    "monetaryExpansion": "1/10",
    "treasuryExpansion": "1/10",
    "decentralizationParameter": "1/1",
    "extraEntropy": "neutral",
    "protocolVersion": {"major": 5, "minor": 0},
    "minPoolCost": 0,
    "coinsPerUtxoWord": 1,
    "prices": {"memory": "1/10", "steps": "1/10"},
    "maxExecutionUnitsPerTransaction": {"memory": 500000000000, "steps": 500000000000},
    "maxExecutionUnitsPerBlock": {"memory": 500000000000, "steps": 500000000000},
    "maxValueSize": 4000,
    "collateralPercentage": 1,
    "maxCollateralInputs": 5,
}

GENESIS_RESULT = {
    "systemStart": "2021-12-21T03:17:14.803874404Z",
    "networkMagic": 42,
    "network": "testnet",
    "activeSlotsCoefficient": "1/10",
    "securityParameter": 1000000000,
    "epochLength": 500,
    "slotsPerKesPeriod": 129600,
    "maxKesEvolutions": 60000000,
    "slotLength": 1,
    "updateQuorum": 2,
    "maxLovelaceSupply": 1000000000000,
}

UTXOS = [
    [
        {
            "txId": "3a42f652bd8dee788577e8c39b6217db3df659c33b10a2814c20fb66089ca167",
            "index": 1,
        },
        {
            "address": "addr_test1qraen6hr9zs5yae8cxnhlkh7rk2nfl7rnpg0xvmel3a0xf70v3kz6ee7mtq86x6gmrnw8j7kuf485902akkr7tlcx24qemz34a",
            "value": {"coins": 764295183, "assets": {}},
            "datum": None,
        },
    ],
    [
        {
            "txId": "c93d5dac64e3267abd2a91b9759e0d08395090d7bd89dfdfecd7ccc566661bcd",
            "index": 1,
        },
        {
            "address": "addr_test1qraen6hr9zs5yae8cxnhlkh7rk2nfl7rnpg0xvmel3a0xf70v3kz6ee7mtq86x6gmrnw8j7kuf485902akkr7tlcx24qemz34a",
            "value": {
                "coins": 3241308,
                "assets": {
                    "126b8676446c84a5cd6e3259223b16a2314c5676b88ae1c1f8579a8f.744d494e": 762462,
                    "57fca08abbaddee36da742a839f7d83a7e1d2419f1507fcbf3916522.43484f43": 9945000,
                    "fc3ef8db4a16c1959fbabfcbc3fb7669bf315967ffef260ececc47a3.53484942": 1419813131821,
                },
            },
            "datum": None,
        },
    ],
]


class TestOgmiosChainContext:
    chain_context = OgmiosChainContext("", Network.TESTNET)

    def override_request(method, args):
        if args["query"] == "currentProtocolParameters":
            return PROTOCOL_RESULT
        elif args["query"] == "genesisConfig":
            return GENESIS_RESULT
        elif "utxo" in args["query"]:
            return UTXOS
        else:
            return None

    chain_context._request = override_request

    def test_protocol_param(self):
        assert (
            ProtocolParameters(
                min_fee_constant=155381,
                min_fee_coefficient=44,
                max_block_size=65536,
                max_tx_size=16384,
                max_block_header_size=1100,
                key_deposit=0,
                pool_deposit=0,
                pool_influence=0.0,
                monetary_expansion=0.1,
                treasury_expansion=0.1,
                decentralization_param=1.0,
                extra_entropy="neutral",
                protocol_major_version=5,
                protocol_minor_version=0,
                min_utxo=None,
                min_pool_cost=0,
                price_mem=0.1,
                price_step=0.1,
                max_tx_ex_mem=500000000000,
                max_tx_ex_steps=500000000000,
                max_block_ex_mem=500000000000,
                max_block_ex_steps=500000000000,
                max_val_size=4000,
                collateral_percent=1,
                max_collateral_inputs=5,
                coins_per_utxo_word=1,
            )
            == self.chain_context.protocol_param
        )

    def test_genesis(self):
        assert (
            GenesisParameters(
                active_slots_coefficient=0.1,
                update_quorum=2,
                max_lovelace_supply=1000000000000,
                network_magic=42,
                epoch_length=500,
                system_start=1640056634,
                slots_per_kes_period=129600,
                slot_length=1,
                max_kes_evolutions=60000000,
                security_param=1000000000,
            )
            == self.chain_context.genesis_param
        )

    def test_utxo(self):

        results = self.chain_context.utxos(
            "addr_test1qraen6hr9zs5yae8cxnhlkh7rk2nfl7rnpg0xvmel3a0xf70v3kz6ee7mtq86x6gmrnw8j7kuf485902akkr7tlcx24qemz34a"
        )

        assert results[0].input == TransactionInput.from_primitive(
            ["3a42f652bd8dee788577e8c39b6217db3df659c33b10a2814c20fb66089ca167", 1]
        )
        assert results[0].output.amount == 764295183

        assert results[1].input == TransactionInput.from_primitive(
            ["c93d5dac64e3267abd2a91b9759e0d08395090d7bd89dfdfecd7ccc566661bcd", 1]
        )
        assert results[1].output.amount.coin == 3241308
        assert results[1].output.amount.multi_asset == MultiAsset.from_primitive(
            {
                "126b8676446c84a5cd6e3259223b16a2314c5676b88ae1c1f8579a8f": {
                    "744d494e": 762462
                },
                "57fca08abbaddee36da742a839f7d83a7e1d2419f1507fcbf3916522": {
                    "43484f43": 9945000
                },
                "fc3ef8db4a16c1959fbabfcbc3fb7669bf315967ffef260ececc47a3": {
                    "53484942": 1419813131821
                },
            }
        )
