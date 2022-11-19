import os
import tempfile
import time
from typing import Dict, List, Optional, Union

import cbor2
from blockfrost import ApiUrls, BlockFrostApi
from blockfrost.utils import Namespace

from pycardano.address import Address
from pycardano.backend.base import (
    ALONZO_COINS_PER_UTXO_WORD,
    ChainContext,
    GenesisParameters,
    ProtocolParameters,
)
from pycardano.exception import TransactionFailedException
from pycardano.hash import SCRIPT_HASH_SIZE, DatumHash, ScriptHash
from pycardano.nativescript import NativeScript
from pycardano.network import Network
from pycardano.plutus import ExecutionUnits, PlutusV1Script, PlutusV2Script
from pycardano.serialization import RawCBOR
from pycardano.transaction import (
    Asset,
    AssetName,
    MultiAsset,
    TransactionInput,
    TransactionOutput,
    UTxO,
    Value,
)
from pycardano.types import JsonDict

__all__ = ["BlockFrostChainContext"]


class BlockFrostChainContext(ChainContext):
    """A `BlockFrost <https://blockfrost.io/>`_ API wrapper for the client code to interact with.

    Args:
        project_id (str): A BlockFrost project ID obtained from https://blockfrost.io.
        network (Network): Network to use.
    """

    api: BlockFrostApi
    _epoch_info: Namespace
    _epoch: Optional[int] = None
    _genesis_param: Optional[GenesisParameters] = None
    _protocol_param: Optional[ProtocolParameters] = None

    def __init__(
        self, project_id: str, network: Network = Network.TESTNET, base_url: str = ""
    ):
        self._network = network
        self._project_id = project_id
        self._base_url = (
            base_url
            if base_url
            else ApiUrls.testnet.value
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
            new_epoch: int = self.api.epoch_latest().epoch
            self._epoch = new_epoch
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
            params = self.api.epoch_latest_parameters()
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
                min_pool_cost=int(params.min_pool_cost),
                price_mem=float(params.price_mem),
                price_step=float(params.price_step),
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
            )
        return self._protocol_param

    def _get_script(
        self, script_hash: str
    ) -> Union[PlutusV1Script, PlutusV2Script, NativeScript]:
        script_type = self.api.script(script_hash).type
        if script_type == "plutusV1":
            return PlutusV1Script(
                cbor2.loads(bytes.fromhex(self.api.script_cbor(script_hash).cbor))
            )
        elif script_type == "plutusV2":
            return PlutusV2Script(
                cbor2.loads(bytes.fromhex(self.api.script_cbor(script_hash).cbor))
            )
        else:
            script_json: JsonDict = self.api.script_json(
                script_hash, return_type="json"
            )["json"]
            return NativeScript.from_dict(script_json)

    def utxos(self, address: str) -> List[UTxO]:
        results = self.api.address_utxos(address, gather_pages=True)

        utxos = []

        for result in results:
            tx_in = TransactionInput.from_primitive(
                [result.tx_hash, result.output_index]
            )
            amount = result.amount
            lovelace_amount = 0
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

            amount = Value(lovelace_amount, multi_assets)

            datum_hash = (
                DatumHash.from_primitive(result.data_hash)
                if result.data_hash and result.inline_datum is None
                else None
            )

            datum = None

            if hasattr(result, "inline_datum") and result.inline_datum is not None:
                datum = RawCBOR(bytes.fromhex(result.inline_datum))

            script = None

            if (
                hasattr(result, "reference_script_hash")
                and result.reference_script_hash
            ):
                script = self._get_script(result.reference_script_hash)

            tx_out = TransactionOutput(
                Address.from_primitive(address),
                amount=amount,
                datum_hash=datum_hash,
                datum=datum,
                script=script,
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

    def evaluate_tx(self, cbor: Union[bytes, str]) -> Dict[str, ExecutionUnits]:
        """Evaluate execution units of a transaction.

        Args:
            cbor (Union[bytes, str]): The serialized transaction to be evaluated.

        Returns:
            Dict[str, ExecutionUnits]: A list of execution units calculated for each of the transaction's redeemers

        Raises:
            :class:`TransactionFailedException`: When fails to evaluate the transaction.
        """
        if isinstance(cbor, bytes):
            cbor = cbor.hex()
        with tempfile.NamedTemporaryFile(delete=False, mode="w") as f:
            f.write(cbor)
        result = self.api.transaction_evaluate(f.name).result
        os.remove(f.name)
        return_val = {}
        if not hasattr(result, "EvaluationResult"):
            raise TransactionFailedException(result)
        else:
            for k in vars(result.EvaluationResult):
                return_val[k] = ExecutionUnits(
                    getattr(result.EvaluationResult, k).memory,
                    getattr(result.EvaluationResult, k).steps,
                )
            return return_val
