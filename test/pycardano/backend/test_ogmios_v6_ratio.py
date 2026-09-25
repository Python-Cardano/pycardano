from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from pycardano.backend.ogmios_v6 import OgmiosV6ChainContext


def _ogmios_params(**overrides):
    params = dict(
        min_fee_constant=SimpleNamespace(lovelace=155381),
        min_fee_coefficient=44,
        min_stake_pool_cost=SimpleNamespace(lovelace=0),
        max_block_body_size={"bytes": 65536},
        max_transaction_size={"bytes": 16384},
        max_block_header_size={"bytes": 1100},
        stake_credential_deposit=SimpleNamespace(lovelace=0),
        stake_pool_deposit=SimpleNamespace(lovelace=0),
        stake_pool_pledge_influence="1/10",
        monetary_expansion="1/10",
        treasury_expansion="1/10",
        extra_entropy="neutral",
        version={"major": 9, "minor": 0},
        script_execution_prices={"memory": "721/10000000", "cpu": "577/10000"},
        max_execution_units_per_transaction={"memory": 1, "cpu": 1},
        max_execution_units_per_block={"memory": 1, "cpu": 1},
        max_value_size={"bytes": 4000},
        collateral_percentage=150,
        max_collateral_inputs=3,
        min_utxo_deposit_coefficient=4310,
        plutus_cost_models={},
        max_ref_script_size={"bytes": 200000},
        min_fee_ref_scripts=None,
    )
    params.update(overrides)
    return SimpleNamespace(**params)


def _fetch(params):
    ctx = OgmiosV6ChainContext()
    client = MagicMock()
    client.query_protocol_parameters.execute.return_value = (params, None)
    client.__enter__.return_value = client
    with patch("pycardano.backend.ogmios_v6.OgmiosClient", return_value=client):
        return ctx._fetch_protocol_param()


def test_protocol_ratio_rejects_a_python_expression():
    with pytest.raises(ValueError):
        _fetch(_ogmios_params(monetary_expansion="1+1"))


def test_protocol_ratio_parses_a_fraction():
    parsed = _fetch(_ogmios_params())
    assert parsed.monetary_expansion == 0.1
    assert parsed.price_mem == 721 / 10000000
