from dataclasses import dataclass
from typing import List, Union

from pycardano.network import Network
from pycardano.transaction import UTxO


@dataclass
class ProtocolParameters:

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


class ChainContext:

    @property
    def protocol_param(self) -> ProtocolParameters:
        raise NotImplementedError()

    @property
    def network(self) -> Network:
        raise NotImplementedError()

    def utxos(self, address: str) -> List[UTxO]:
        raise NotImplementedError()

    def submit_tx(self, cbor: Union[bytes, str]):
        raise NotImplementedError()
