from fractions import Fraction
from unittest.mock import MagicMock, patch

from blockfrost import ApiUrls
from blockfrost.utils import convert_json_to_object
from requests import Response

from pycardano import ALONZO_COINS_PER_UTXO_WORD, GenesisParameters, ProtocolParameters
from pycardano.backend.blockfrost import BlockFrostChainContext
from pycardano.network import Network


@patch("pycardano.backend.blockfrost.BlockFrostApi")
def test_blockfrost_chain_context(mock_api):
    mock_api.return_value = MagicMock()
    chain_context = BlockFrostChainContext("project_id", base_url=ApiUrls.mainnet.value)
    assert chain_context.network == Network.MAINNET

    chain_context = BlockFrostChainContext("project_id", base_url=ApiUrls.testnet.value)
    assert chain_context.network == Network.TESTNET

    chain_context = BlockFrostChainContext("project_id", base_url=ApiUrls.preprod.value)
    assert chain_context.network == Network.TESTNET

    chain_context = BlockFrostChainContext("project_id", base_url=ApiUrls.preview.value)
    assert chain_context.network == Network.TESTNET


def test_epoch_property():
    with patch(
        "blockfrost.api.BlockFrostApi.epoch_latest",
        return_value=convert_json_to_object(
            {
                "epoch": 225,
                "start_time": 1603403091,
                "end_time": 1603835086,
                "first_block_time": 1603403092,
                "last_block_time": 1603835084,
                "block_count": 21298,
                "tx_count": 17856,
                "output": "7849943934049314",
                "fees": "4203312194",
                "active_stake": "784953934049314",
            }
        ),
    ):
        chain_context = BlockFrostChainContext(
            "project_id", base_url=ApiUrls.preprod.value
        )
        chain_context._check_epoch_and_update()
        assert chain_context.epoch == 225


def test_last_block_slot():
    with patch(
        "blockfrost.api.BlockFrostApi.epoch_latest",
        return_value=convert_json_to_object(
            {
                "epoch": 225,
            }
        ),
    ), patch(
        "blockfrost.api.BlockFrostApi.block_latest",
        return_value=convert_json_to_object(
            {
                "time": 1641338934,
                "height": 15243593,
                "hash": "4ea1ba291e8eef538635a53e59fddba7810d1679631cc3aed7c8e6c4091a516a",
                "slot": 412162133,
                "epoch": 425,
                "epoch_slot": 12,
                "slot_leader": "pool1pu5jlj4q9w9jlxeu370a3c9myx47md5j5m2str0naunn2qnikdy",
                "size": 3,
                "tx_count": 1,
                "output": "128314491794",
                "fees": "592661",
                "block_vrf": "vrf_vk1wf2k6lhujezqcfe00l6zetxpnmh9n6mwhpmhm0dvfh3fxgmdnrfqkms8ty",
                "op_cert": "da905277534faf75dae41732650568af545134ee08a3c0392dbefc8096ae177c",
                "op_cert_counter": "18",
                "previous_block": "43ebccb3ac72c7cebd0d9b755a4b08412c9f5dcb81b8a0ad1e3c197d29d47b05",
                "next_block": "8367f026cf4b03e116ff8ee5daf149b55ba5a6ec6dec04803b8dc317721d15fa",
                "confirmations": 4698,
            }
        ),
    ):
        chain_context = BlockFrostChainContext(
            "project_id", base_url=ApiUrls.preprod.value
        )
        assert chain_context.last_block_slot == 412162133


def test_genesis_param():
    genesis_json = {
        "active_slots_coefficient": 0.05,
        "update_quorum": 5,
        "max_lovelace_supply": "45000000000000000",
        "network_magic": 764824073,
        "epoch_length": 432000,
        "system_start": 1506203091,
        "slots_per_kes_period": 129600,
        "slot_length": 1,
        "max_kes_evolutions": 62,
        "security_param": 2160,
    }

    with patch(
        "blockfrost.api.BlockFrostApi.epoch_latest",
        return_value=convert_json_to_object(
            {
                "epoch": 225,
            }
        ),
    ), patch(
        "blockfrost.api.BlockFrostApi.genesis",
        return_value=convert_json_to_object(genesis_json),
    ):
        chain_context = BlockFrostChainContext(
            "project_id", base_url=ApiUrls.preprod.value
        )
        assert chain_context.genesis_param == GenesisParameters(**genesis_json)


def test_protocol_param():
    protocol_param_json = {
        "epoch": 225,
        "min_fee_a": 44,
        "min_fee_b": 155381,
        "max_block_size": 65536,
        "max_tx_size": 16384,
        "max_block_header_size": 1100,
        "key_deposit": "2000000",
        "pool_deposit": "500000000",
        "e_max": 18,
        "n_opt": 150,
        "a0": 0.3,
        "rho": 0.003,
        "tau": 0.2,
        "decentralisation_param": 0.5,
        "extra_entropy": None,
        "protocol_major_ver": 2,
        "protocol_minor_ver": 0,
        "min_utxo": "1000000",
        "min_pool_cost": "340000000",
        "nonce": "1a3be38bcbb7911969283716ad7aa550250226b76a61fc51cc9a9a35d9276d81",
        "cost_models": {
            "PlutusV1": {
                "addInteger-cpu-arguments-intercept": 197209,
                "addInteger-cpu-arguments-slope": 0,
            },
            "PlutusV2": {
                "addInteger-cpu-arguments-intercept": 197209,
                "addInteger-cpu-arguments-slope": 0,
            },
        },
        "cost_models_raw": {"PlutusV1": [197209, 0], "PlutusV2": [197209, 0]},
        "price_mem": 0.0577,
        "price_step": 0.0000721,
        "max_tx_ex_mem": "10000000",
        "max_tx_ex_steps": "10000000000",
        "max_block_ex_mem": "50000000",
        "max_block_ex_steps": "40000000000",
        "max_val_size": "5000",
        "collateral_percent": 150,
        "max_collateral_inputs": 3,
        "coins_per_utxo_size": "34482",
        "coins_per_utxo_word": "34482",
        "pvt_motion_no_confidence": 1,
        "pvt_committee_normal": 1,
        "pvt_committee_no_confidence": 1,
        "pvt_hard_fork_initiation": 1,
        "dvt_motion_no_confidence": 1,
        "dvt_committee_normal": 1,
        "dvt_committee_no_confidence": 1,
        "dvt_update_to_constitution": 1,
        "dvt_hard_fork_initiation": 1,
        "dvt_p_p_network_group": 1,
        "dvt_p_p_economic_group": 1,
        "dvt_p_p_technical_group": 1,
        "dvt_p_p_gov_group": 1,
        "dvt_treasury_withdrawal": 1,
        "committee_min_size": "…",
        "committee_max_term_length": "…",
        "gov_action_lifetime": "…",
        "gov_action_deposit": "…",
        "drep_deposit": "…",
        "drep_activity": "…",
        "pvtpp_security_group": 1,
        "pvt_p_p_security_group": 1,
        "min_fee_ref_script_cost_per_byte": 1,
    }

    with patch(
        "blockfrost.api.BlockFrostApi.epoch_latest",
        return_value=convert_json_to_object(
            {
                "epoch": 225,
            }
        ),
    ), patch(
        "blockfrost.api.BlockFrostApi.epoch_latest_parameters",
        return_value=convert_json_to_object(protocol_param_json),
    ):
        chain_context = BlockFrostChainContext(
            "project_id", base_url=ApiUrls.preprod.value
        )

        params = convert_json_to_object(protocol_param_json)
        assert chain_context.protocol_param == ProtocolParameters(
            min_fee_constant=int(params.min_fee_b),
            min_fee_coefficient=int(params.min_fee_a),
            max_block_size=int(params.max_block_size),
            max_tx_size=int(params.max_tx_size),
            max_block_header_size=int(params.max_block_header_size),
            key_deposit=int(params.key_deposit),
            pool_deposit=int(params.pool_deposit),
            pool_influence=Fraction(params.a0),
            monetary_expansion=Fraction(params.rho),
            treasury_expansion=Fraction(params.tau),
            decentralization_param=Fraction(params.decentralisation_param),
            extra_entropy=params.extra_entropy,
            protocol_major_version=int(params.protocol_major_ver),
            protocol_minor_version=int(params.protocol_minor_ver),
            min_utxo=int(params.min_utxo),
            min_pool_cost=int(params.min_pool_cost),
            price_mem=Fraction(params.price_mem),
            price_step=Fraction(params.price_step),
            max_tx_ex_mem=int(params.max_tx_ex_mem),
            max_tx_ex_steps=int(params.max_tx_ex_steps),
            max_block_ex_mem=int(params.max_block_ex_mem),
            max_block_ex_steps=int(params.max_block_ex_steps),
            max_val_size=int(params.max_val_size),
            collateral_percent=int(params.collateral_percent),
            max_collateral_inputs=int(params.max_collateral_inputs),
            coins_per_utxo_word=int(params.coins_per_utxo_word)
            or ALONZO_COINS_PER_UTXO_WORD,
            coins_per_utxo_byte=int(params.coins_per_utxo_size),
            cost_models={
                k: v.to_dict() for k, v in params.cost_models.to_dict().items()
            },
            maximum_reference_scripts_size={"bytes": 200000},
            min_fee_reference_scripts={
                "base": params.min_fee_ref_script_cost_per_byte,
                "range": 200000,
                "multiplier": 1,
            },
        )


def test_utxos():
    utxos_json = [
        {
            "address": "addr1qxqs59lphg8g6qndelq8xwqn60ag3aeyfcp33c2kdp46a09re5df3pzwwmyq946axfcejy5n4x0y99wqpgtp2gd0k09qsgy6pz",
            "tx_hash": "39a7a284c2a0948189dc45dec670211cd4d72f7b66c5726c08d9b3df11e44d58",
            "output_index": 0,
            "amount": [{"unit": "lovelace", "quantity": "42000000"}],
            "block": "7eb8e27d18686c7db9a18f8bbcfe34e3fed6e047afaa2d969904d15e934847e6",
            "data_hash": "9e478573ab81ea7a8e31891ce0648b81229f408d596a3483e6f4f9b92d3cf710",
            "inline_datum": None,
            "reference_script_hash": None,
        },
        {
            "address": "addr1qxqs59lphg8g6qndelq8xwqn60ag3aeyfcp33c2kdp46a09re5df3pzwwmyq946axfcejy5n4x0y99wqpgtp2gd0k09qsgy6pz",
            "tx_hash": "4c4e67bafa15e742c13c592b65c8f74c769cd7d9af04c848099672d1ba391b49",
            "output_index": 0,
            "amount": [{"unit": "lovelace", "quantity": "729235000"}],
            "block": "953f1b80eb7c11a7ffcd67cbd4fde66e824a451aca5a4065725e5174b81685b7",
            "data_hash": None,
            "inline_datum": None,
            "reference_script_hash": None,
        },
        {
            "address": "addr1qxqs59lphg8g6qndelq8xwqn60ag3aeyfcp33c2kdp46a09re5df3pzwwmyq946axfcejy5n4x0y99wqpgtp2gd0k09qsgy6pz",
            "tx_hash": "768c63e27a1c816a83dc7b07e78af673b2400de8849ea7e7b734ae1333d100d2",
            "output_index": 1,
            "amount": [
                {"unit": "lovelace", "quantity": "42000000"},
                {
                    "unit": "b0d07d45fe9514f80213f4020e5a61241458be626841cde717cb38a76e7574636f696e",
                    "quantity": "12",
                },
            ],
            "block": "5c571f83fe6c784d3fbc223792627ccf0eea96773100f9aedecf8b1eda4544d7",
            "data_hash": None,
            "inline_datum": None,
            "reference_script_hash": None,
        },
    ]

    with patch(
        "blockfrost.api.BlockFrostApi.epoch_latest",
        return_value=convert_json_to_object(
            {
                "epoch": 225,
            }
        ),
    ), patch(
        "blockfrost.api.BlockFrostApi.address_utxos",
        return_value=convert_json_to_object(utxos_json),
    ):
        chain_context = BlockFrostChainContext(
            "project_id", base_url=ApiUrls.preprod.value
        )

        utxos = chain_context.utxos(
            "addr1qxqs59lphg8g6qndelq8xwqn60ag3aeyfcp33c2kdp46a09re5df3pzwwmyq946axfcejy5n4x0y99wqpgtp2gd0k09qsgy6pz"
        )
        assert len(utxos) == 3


def test_submit_tx_cbor():
    response = Response()
    response.status_code = 200
    with patch(
        "blockfrost.api.BlockFrostApi.epoch_latest",
        return_value=convert_json_to_object(
            {
                "epoch": 225,
            }
        ),
    ), patch(
        "blockfrost.api.BlockFrostApi.transaction_submit",
        return_value=response,
    ):
        chain_context = BlockFrostChainContext(
            "project_id", base_url=ApiUrls.preprod.value
        )

        tx_cbor = (
            "84a70081825820b35a4ba9ef3ce21adcd6879d08553642224304704d206c74d3ffb3e6eed3ca28000d80018182581d60cc"
            "30497f4ff962f4c1dca54cceefe39f86f1d7179668009f8eb71e598200a1581cec8b7d1dd0b124e8333d3fa8d818f6eac0"
            "68231a287554e9ceae490ea24f5365636f6e6454657374746f6b656e1a009896804954657374746f6b656e1a0098968002"
            "1a000493e00e8009a1581cec8b7d1dd0b124e8333d3fa8d818f6eac068231a287554e9ceae490ea24f5365636f6e645465"
            "7374746f6b656e1a009896804954657374746f6b656e1a00989680075820592a2df0e091566969b3044626faa8023dabe6"
            "f39c78f33bed9e105e55159221a200828258206443a101bdb948366fc87369336224595d36d8b0eee5602cba8b81a024e5"
            "84735840846f408dee3b101fda0f0f7ca89e18b724b7ca6266eb29775d3967d6920cae7457accb91def9b77571e15dd2ed"
            "e38b12cf92496ce7382fa19eb90ab7f73e49008258205797dc2cc919dfec0bb849551ebdf30d96e5cbe0f33f734a87fe82"
            "6db30f7ef95840bdc771aa7b8c86a8ffcbe1b7a479c68503c8aa0ffde8059443055bf3e54b92f4fca5e0b9ca5bb11ab23b"
            "1390bb9ffce414fa398fc0b17f4dc76fe9f7e2c99c09018182018482051a075bcd1582041a075bcd0c8200581c9139e5c0"
            "a42f0f2389634c3dd18dc621f5594c5ba825d9a8883c66278200581c835600a2be276a18a4bebf0225d728f090f724f4c0"
            "acd591d066fa6ff5d90103a100a11902d1a16b7b706f6c6963795f69647da16d7b706f6c6963795f6e616d657da66b6465"
            "736372697074696f6e6a3c6f7074696f6e616c3e65696d6167656a3c72657175697265643e686c6f636174696f6ea36761"
            "7277656176656a3c6f7074696f6e616c3e6568747470736a3c6f7074696f6e616c3e64697066736a3c7265717569726564"
            "3e646e616d656a3c72657175697265643e667368613235366a3c72657175697265643e64747970656a3c72657175697265643e"
        )

        resp = chain_context.submit_tx_cbor(tx_cbor)
        assert resp.status_code == 200
