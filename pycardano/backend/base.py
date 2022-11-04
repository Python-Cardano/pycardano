"""Defines interfaces for client codes to interact (read/write) with the blockchain."""

from dataclasses import dataclass
from typing import Dict, List, Union

from typeguard import typechecked

from pycardano.network import Network
from pycardano.plutus import ExecutionUnits
from pycardano.transaction import UTxO

__all__ = [
    "GenesisParameters",
    "ProtocolParameters",
    "ChainContext",
    "ALONZO_COINS_PER_UTXO_WORD",
]

ALONZO_COINS_PER_UTXO_WORD = 34482


@dataclass(frozen=True)
class GenesisParameters:
    """Cardano genesis parameters"""

    active_slots_coefficient: float

    update_quorum: int

    max_lovelace_supply: int

    network_magic: int

    epoch_length: int

    system_start: int

    slots_per_kes_period: int

    slot_length: int

    max_kes_evolutions: int

    security_param: int


@dataclass(frozen=True)
class ProtocolParameters:
    """Cardano protocol parameters"""

    min_fee_constant: int

    min_fee_coefficient: int

    max_block_size: int

    max_tx_size: int

    max_block_header_size: int

    key_deposit: int

    pool_deposit: int

    pool_influence: float

    monetary_expansion: float

    treasury_expansion: float

    decentralization_param: float

    extra_entropy: str

    protocol_major_version: int

    protocol_minor_version: int

    min_utxo: int

    min_pool_cost: int

    price_mem: float

    price_step: float

    max_tx_ex_mem: int

    max_tx_ex_steps: int

    max_block_ex_mem: int

    max_block_ex_steps: int

    max_val_size: int

    collateral_percent: int

    max_collateral_inputs: int

    coins_per_utxo_word: int

    coins_per_utxo_byte: int

    cost_models: Dict[str, Dict[str, int]]
    """A dict contains cost models for Plutus. The key will be "PlutusV1", "PlutusV2", etc.
    The value will be a dict of cost model parameters."""


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
            cbor (Union[bytes, str]): The serialized transaction to be submitted.

        Raises:
            :class:`InvalidArgumentException`: When the transaction is invalid.
            :class:`TransactionFailedException`: When fails to submit the transaction to blockchain.
        """
        raise NotImplementedError()

    def evaluate_tx(self, cbor: Union[bytes, str]) -> Dict[str, ExecutionUnits]:
        """Evaluate execution units of a transaction.

        Args:
            cbor (Union[bytes, str]): The serialized transaction to be evaluated.

        Returns:
            List[ExecutionUnits]: A list of execution units calculated for each of the transaction's redeemers
        """
        raise NotImplementedError()
