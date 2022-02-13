import os
import tempfile
import time
from typing import List, Union

from blockfrost import ApiUrls, BlockFrostApi

from pycardano.address import Address
from pycardano.backend.base import ChainContext, GenesisParameters, ProtocolParameters
from pycardano.hash import SCRIPT_HASH_SIZE, DatumHash, ScriptHash
from pycardano.network import Network
from pycardano.transaction import (
    Asset,
    AssetName,
    MultiAsset,
    TransactionInput,
    TransactionOutput,
    UTxO,
    Value,
)


class BlockFrostChainContext(ChainContext):
    """A `BlockFrost <https://blockfrost.io/>`_ API wrapper for the client code to interact with.

    Args:
        project_id (str): A BlockFrost project ID obtained from https://blockfrost.io.
        network (Network): Network to use.
    """

    def __init__(self, project_id: str, network: Network = Network.TESTNET):
        self._network = network
        self._project_id = project_id
        self._base_url = (
            ApiUrls.testnet.value
            if self.network == Network.TESTNET
            else ApiUrls.mainnet.value
        )
        self.api = BlockFrostApi(project_id=self._project_id, base_url=self._base_url)
        self._epoch_info = self.api.epoch_latest()
        self._epoch = None
        self._genesis_param = None
        self._protocol_param = None

    def _check_epoch_and_update(self):
        if int(time.time()) >= self._epoch_info.end_time:
            self._epoch_info = self.api.epoch_latest()
            return True
        else:
            return False

    @property
    def network(self) -> Network:
        return self._network

    @property
    def epoch(self) -> int:
        if not self._epoch or self._check_epoch_and_update():
            self._epoch = self.api.epoch_latest().epoch
        return self._epoch

    @property
    def last_block_slot(self) -> int:
        block = self.api.block_latest()
        return block.slot

    @property
    def genesis_param(self) -> GenesisParameters:
        if not self._genesis_param or self._check_epoch_and_update():
            params = vars(self.api.genesis())
            self._genesis_param = GenesisParameters(**params)
        return self._genesis_param

    @property
    def protocol_param(self) -> ProtocolParameters:
        if not self._protocol_param or self._check_epoch_and_update():
            params = self.api.epoch_latest_parameters(self.epoch)
            self._protocol_param = ProtocolParameters(
                min_fee_constant=int(params.min_fee_b),
                min_fee_coefficient=int(params.min_fee_a),
                max_block_size=int(params.max_block_size),
                max_tx_size=int(params.max_tx_size),
                max_block_header_size=int(params.max_block_header_size),
                key_deposit=int(params.key_deposit),
                pool_deposit=int(params.pool_deposit),
                pool_influence=float(params.a0),
                monetary_expansion=float(params.rho),
                treasury_expansion=float(params.tau),
                decentralization_param=float(params.decentralisation_param),
                extra_entropy=params.extra_entropy,
                protocol_major_version=int(params.protocol_major_ver),
                protocol_minor_version=int(params.protocol_minor_ver),
                min_utxo=int(params.min_utxo),
                price_mem=float(params.price_mem),
                price_step=float(params.price_step),
                max_tx_ex_mem=int(params.max_tx_ex_mem),
                max_tx_ex_steps=int(params.max_tx_ex_steps),
                max_block_ex_mem=int(params.max_block_ex_mem),
                max_block_ex_steps=int(params.max_block_ex_steps),
                max_val_size=int(params.max_val_size),
                collateral_percent=int(params.collateral_percent),
                max_collateral_inputs=int(params.max_collateral_inputs),
                coins_per_utxo_word=int(params.coins_per_utxo_word),
            )
        return self._protocol_param

    def utxos(self, address: str) -> List[UTxO]:
        results = self.api.address_utxos(address, gather_pages=True)

        utxos = []

        for result in results:
            tx_in = TransactionInput.from_primitive(
                [result.tx_hash, result.output_index]
            )
            amount = result.amount
            lovelace_amount = None
            multi_assets = MultiAsset()
            for item in amount:
                if item.unit == "lovelace":
                    lovelace_amount = int(item.quantity)
                else:
                    # The utxo contains Multi-asset
                    data = bytes.fromhex(item.unit)
                    policy_id = ScriptHash(data[:SCRIPT_HASH_SIZE])
                    asset_name = AssetName(data[SCRIPT_HASH_SIZE:])

                    if policy_id not in multi_assets:
                        multi_assets[policy_id] = Asset()
                    multi_assets[policy_id][asset_name] = int(item.quantity)

            datum_hash = (
                DatumHash.from_primitive(result.data_hash) if result.data_hash else None
            )

            if not multi_assets:
                tx_out = TransactionOutput(
                    Address.from_primitive(address),
                    amount=lovelace_amount,
                    datum_hash=datum_hash,
                )
            else:
                tx_out = TransactionOutput(
                    Address.from_primitive(address),
                    amount=Value(lovelace_amount, multi_assets),
                    datum_hash=datum_hash,
                )
            utxos.append(UTxO(tx_in, tx_out))

        return utxos

    def submit_tx(self, cbor: Union[bytes, str]):
        if isinstance(cbor, str):
            cbor = bytes.fromhex(cbor)
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(cbor)
        self.api.transaction_submit(f.name)
        os.remove(f.name)
