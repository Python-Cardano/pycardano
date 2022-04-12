from typing import Dict, List, Union

import pytest

from pycardano import ExecutionUnits
from pycardano.backend.base import ChainContext, GenesisParameters, ProtocolParameters
from pycardano.network import Network
from pycardano.serialization import CBORSerializable
from pycardano.transaction import TransactionInput, TransactionOutput, UTxO, Value

TEST_ADDR = "addr_test1vr2p8st5t5cxqglyjky7vk98k7jtfhdpvhl4e97cezuhn0cqcexl7"


def check_two_way_cbor(serializable: CBORSerializable):
    restored = serializable.from_cbor(serializable.to_cbor())
    assert restored == serializable


class FixedChainContext(ChainContext):

    _protocol_param = ProtocolParameters(
        min_fee_constant=155381,
        min_fee_coefficient=44,
        max_block_size=73728,
        max_tx_size=16384,
        max_block_header_size=1100,
        key_deposit=2000000,
        pool_deposit=500000000,
        pool_influence=0.3,
        treasury_expansion=0.2,
        monetary_expansion=0.003,
        decentralization_param=0,
        protocol_major_version=6,
        protocol_minor_version=0,
        min_utxo=1000000,
        min_pool_cost=340000000,
        price_mem=0.0577,
        price_step=0.0000721,
        max_tx_ex_mem=10000000,
        max_tx_ex_steps=10000000000,
        max_block_ex_mem=50000000,
        max_block_ex_steps=40000000000,
        max_val_size=5000,
        collateral_percent=150,
        max_collateral_inputs=3,
        coins_per_utxo_word=34482,
    )

    _genesis_param = GenesisParameters(
        active_slots_coefficient=0.05,
        update_quorum=5,
        max_lovelace_supply=45000000000000000,
        network_magic=764824073,
        epoch_length=432000,
        system_start=1506203091,
        slots_per_kes_period=129600,
        slot_length=1,
        max_kes_evolutions=62,
        security_param=2160,
    )

    @property
    def protocol_param(self) -> ProtocolParameters:
        """Get current protocol parameters"""
        return self._protocol_param

    # Create setter function to allow parameter modifications
    # for testing purposes
    @protocol_param.setter
    def protocol_param(self, protocol_param: ProtocolParameters):
        # if type(protocol_param) is ProtocolParameters:
        self._protocol_param = protocol_param

    @property
    def genesis_param(self) -> GenesisParameters:
        """Get chain genesis parameters"""
        return self._genesis_param

    @property
    def network(self) -> Network:
        """Cet current network"""
        return Network.TESTNET

    @property
    def epoch(self) -> int:
        """Current epoch number"""
        return 300

    @property
    def slot(self) -> int:
        """Current slot number"""
        return 2000

    def utxos(self, address: str) -> List[UTxO]:
        """Get all UTxOs associated with an address.

        Args:
            address (str): An address encoded with bech32.

        Returns:
            List[UTxO]: A list of UTxOs.
        """
        tx_in1 = TransactionInput.from_primitive([b"1" * 32, 0])
        tx_in2 = TransactionInput.from_primitive([b"2" * 32, 1])
        tx_out1 = TransactionOutput.from_primitive([address, 5000000])
        tx_out2 = TransactionOutput.from_primitive(
            [address, [6000000, {b"1" * 28: {b"Token1": 1, b"Token2": 2}}]]
        )
        return [UTxO(tx_in1, tx_out1), UTxO(tx_in2, tx_out2)]

    def submit_tx(self, cbor: Union[bytes, str]):
        """Submit a transaction to the blockchain.

        Args:
            cbor (Union[bytes, str]): The transaction to be submitted.

        Raises:
            :class:`InvalidArgumentException`: When the transaction is invalid.
            :class:`TransactionFailedException`: When fails to submit the transaction to blockchain.
        """
        pass

    def evaluate_tx(self, cbor: Union[bytes, str]) -> Dict[str, ExecutionUnits]:
        return {"spend:0": ExecutionUnits(399882, 175940720)}


@pytest.fixture
def chain_context():
    return FixedChainContext()
