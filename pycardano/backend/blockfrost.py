import os
import tempfile
import time

from typing import List, Union

from blockfrost import BlockFrostApi, ApiUrls

from pycardano.address import Address
from pycardano.backend.base import ChainContext, GenesisParameters, ProtocolParameters
from pycardano.hash import DatumHash, ScriptHash, SCRIPT_HASH_SIZE
from pycardano.network import Network
from pycardano.transaction import (TransactionInput, TransactionOutput, UTxO,
                                   FullMultiAsset, MultiAsset, Asset, AssetName)


class BlockFrostChainContext(ChainContext):
    """A `BlockFrost <https://blockfrost.io/>`_ API wrapper for the client code to interact with.

    Args:
        project_id (str): A BlockFrost project ID obtained from https://blockfrost.io.
        network (Network): Network to use.
    """

    def __init__(self, project_id: str, network: Network = Network.TESTNET):
        self._network = network
        self._project_id = project_id
        self._base_url = ApiUrls.testnet.value if self.network == Network.TESTNET else ApiUrls.mainnet.value
        self.api = BlockFrostApi(project_id=self._project_id, base_url=self._base_url)

    @property
    def network(self) -> Network:
        return self._network

    @property
    def epoch(self) -> int:
        return self.api.epoch_latest().epoch

    @property
    def slot(self) -> int:
        slot_length = self.genesis_param.slot_length
        cur_time = int(time.time())
        return (cur_time - self.genesis_param.system_start) // slot_length

    @property
    def genesis_param(self) -> GenesisParameters:
        params = vars(self.api.genesis())
        return GenesisParameters(
            **params
        )

    @property
    def protocol_param(self) -> ProtocolParameters:
        params = self.api.epoch_latest_parameters(self.epoch)
        return ProtocolParameters(
            min_fee_constant=params.min_fee_b,
            min_fee_coefficient=params.min_fee_a,
            max_block_size=params.max_block_size,
            max_tx_size=params.max_tx_size,
            max_block_header_size=params.max_block_header_size,
            key_deposit=params.key_deposit,
            pool_deposit=params.pool_deposit,
            pool_influence=params.a0,
            monetary_expansion=params.rho,
            treasury_expansion=params.tau,
            decentralization_param=params.decentralisation_param,
            extra_entropy=params.extra_entropy,
            protocol_major_version=params.protocol_major_ver,
            protocol_minor_version=params.protocol_minor_ver,
            min_utxo=params.min_utxo,
            price_mem=params.price_mem,
            price_step=params.price_step,
            max_tx_ex_mem=params.max_tx_ex_mem,
            max_tx_ex_steps=params.max_tx_ex_steps,
            max_block_ex_mem=params.max_block_ex_mem,
            max_block_ex_steps=params.max_block_ex_steps,
            max_val_size=params.max_val_size,
            collateral_percent=params.collateral_percent,
            max_collateral_inputs=params.max_collateral_inputs,
            coins_per_utxo_word=params.coins_per_utxo_word,
        )

    def utxos(self, address: str) -> List[UTxO]:
        results = self.api.address_utxos(address, gather_pages=True)

        utxos = []

        for result in results:
            tx_in = TransactionInput.from_primitive([result.tx_hash, result.output_index])
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

            datum_hash = DatumHash.from_primitive(result.data_hash) if result.data_hash else None

            if not multi_assets:
                tx_out = TransactionOutput(Address.from_primitive(address),
                                           amount=lovelace_amount,
                                           datum_hash=datum_hash)
            else:
                tx_out = TransactionOutput(Address.from_primitive(address),
                                           amount=FullMultiAsset(lovelace_amount,
                                                                 multi_assets),
                                           datum_hash=datum_hash)
            utxos.append(UTxO(tx_in, tx_out))

        return utxos

    def submit_tx(self, cbor: Union[bytes, str]):
        if isinstance(cbor, str):
            cbor = bytes.fromhex(cbor)
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(cbor)
        self.api.transaction_submit(f.name)
        os.remove(f.name)
