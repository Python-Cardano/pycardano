import os
from pathlib import Path

from retry import retry

from pycardano import (
    CardanoCliChainContext,
    CardanoCliNetwork,
    GenesisParameters,
    Network,
    ProtocolParameters,
)
from pycardano.backend.cardano_cli import DockerConfig

from .base import TEST_RETRIES


class TestCardanoCli:
    network_env = os.getenv("NETWORK", "local-alonzo")
    host_socket = os.getenv("DOCKER_HOST", None)
    network_magic = os.getenv("NETWORK_MAGIC", 42)

    configs_dir = Path(__file__).parent.parent / "configs"

    chain_context = CardanoCliChainContext(
        binary=Path("cardano-cli"),
        socket=Path("/ipc/node.socket"),
        config_file=configs_dir / network_env / "config.json",
        network=CardanoCliNetwork.CUSTOM,
        docker_config=DockerConfig(
            container_name="integration-test_cardano-node_1",
            host_socket=Path(host_socket) if host_socket else None,
        ),
        network_magic_number=int(network_magic),
    )

    @retry(tries=TEST_RETRIES, backoff=1.5, delay=6, jitter=(0, 4))
    def test_protocol_param(self):
        protocol_param = self.chain_context.protocol_param

        assert protocol_param is not None
        assert isinstance(protocol_param, ProtocolParameters)
        assert protocol_param.coins_per_utxo_byte is not None

        cost_models = protocol_param.cost_models
        for cost_model in cost_models.items():
            assert len(cost_model) > 0

    def test_genesis_param(self):
        genesis_param = self.chain_context.genesis_param

        assert genesis_param is not None
        assert isinstance(genesis_param, GenesisParameters)

    def test_network(self):
        network = self.chain_context.network

        assert network is not None
        assert isinstance(network, Network)

    def test_epoch(self):
        epoch = self.chain_context.epoch

        assert epoch is not None
        assert isinstance(epoch, int)
        assert epoch > 0

    def test_last_block_slot(self):
        last_block_slot = self.chain_context.last_block_slot

        assert isinstance(last_block_slot, int)
        assert last_block_slot > 0
