"""Defines interfaces for client codes to interact (read/write) with the blockchain."""

from dataclasses import dataclass
from typing import List, Union

from typeguard import typechecked

from pycardano.network import Network
from pycardano.transaction import UTxO


@dataclass
class GenesisParameters:
    """Cardano genesis parameters"""

    active_slots_coefficient: float = None

    update_quorum: int = None

    max_lovelace_supply: int = None

    network_magic: int = None

    epoch_length: int = None

    system_start: int = None

    slots_per_kes_period: int = None

    slot_length: int = None

    max_kes_evolutions: int = None

    security_param: int = None


@dataclass
class ProtocolParameters:
    """Cardano protocol parameters"""

    min_fee_constant: int = None

    min_fee_coefficient: int = None

    max_block_size: int = None

    max_tx_size: int = None

    max_block_header_size: int = None

    key_deposit: int = None

    pool_deposit: int = None

    pool_influence: float = None

    monetary_expansion: float = None

    treasury_expansion: float = None

    decentralization_param: float = None

    extra_entropy: str = None

    protocol_major_version: int = None

    protocol_minor_version: int = None

    min_utxo: int = None

    min_pool_cost: int = None

    price_mem: float = None

    price_step: float = None

    max_tx_ex_mem: int = None

    max_tx_ex_steps: int = None

    max_block_ex_mem: int = None

    max_block_ex_steps: int = None

    max_val_size: int = None

    collateral_percent: int = None

    max_collateral_inputs: int = None

    coins_per_utxo_word: int = None


@typechecked
class ChainContext:
    """Interfaces through which the library interacts with Cardano blockchain."""

    @property
    def protocol_param(self) -> ProtocolParameters:
        """Get current protocol parameters"""
        raise NotImplementedError()

    @property
    def genesis_param(self) -> GenesisParameters:
        """Get chain genesis parameters"""
        raise NotImplementedError()

    @property
    def network(self) -> Network:
        """Cet current network"""
        raise NotImplementedError()

    @property
    def epoch(self) -> int:
        """Current epoch number"""
        raise NotImplementedError()

    @property
    def last_block_slot(self) -> int:
        """Slot number of last block"""
        raise NotImplementedError()

    def utxos(self, address: str) -> List[UTxO]:
        """Get all UTxOs associated with an address.

        Args:
            address (str): An address encoded with bech32.

        Returns:
            List[UTxO]: A list of UTxOs.
        """
        raise NotImplementedError()

    def submit_tx(self, cbor: Union[bytes, str]):
        """Submit a transaction to the blockchain.

        Args:
            cbor (Union[bytes, str]): The transaction to be submitted.

        Raises:
            :class:`InvalidArgumentException`: When the transaction is invalid.
            :class:`TransactionFailedException`: When fails to submit the transaction to blockchain.
        """
        raise NotImplementedError()
