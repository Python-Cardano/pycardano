from unittest.mock import MagicMock, patch

from blockfrost import ApiUrls

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
