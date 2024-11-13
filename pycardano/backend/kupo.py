from typing import Dict, List, Optional, Tuple, Union

import requests
from cachetools import Cache, LRUCache, TTLCache

from pycardano.address import Address
from pycardano.backend.base import ChainContext, GenesisParameters, ProtocolParameters
from pycardano.backend.blockfrost import _try_fix_script
from pycardano.hash import DatumHash, ScriptHash
from pycardano.network import Network
from pycardano.plutus import ExecutionUnits, PlutusScript
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

__all__ = ["KupoChainContextExtension"]


def extract_asset_info(asset_hash: str) -> Tuple[str, ScriptHash, AssetName]:
    split_result = asset_hash.split(".")

    if len(split_result) == 1:
        policy_hex, asset_name_hex = split_result[0], ""
    elif len(split_result) == 2:
        policy_hex, asset_name_hex = split_result
    else:
        raise ValueError(f"Unable to parse asset hash: {asset_hash}")

    policy = ScriptHash.from_primitive(policy_hex)
    asset_name = AssetName.from_primitive(asset_name_hex)

    return policy_hex, policy, asset_name


class KupoChainContextExtension(ChainContext):
    _wrapped_backend: ChainContext
    _kupo_url: Optional[str]
    _utxo_cache: Cache
    _datum_cache: Cache
    _refetch_chain_tip_interval: int

    def __init__(
        self,
        wrapped_backend: ChainContext,
        kupo_url: Optional[str] = None,
        refetch_chain_tip_interval: int = 10,
        utxo_cache_size: int = 1000,
        datum_cache_size: int = 1000,
    ):
        self._kupo_url = kupo_url
        self._wrapped_backend = wrapped_backend
        self._refetch_chain_tip_interval = refetch_chain_tip_interval
        self._utxo_cache = TTLCache(
            ttl=self._refetch_chain_tip_interval, maxsize=utxo_cache_size
        )
        self._datum_cache = LRUCache(maxsize=datum_cache_size)

    @property
    def genesis_param(self) -> GenesisParameters:
        """Get chain genesis parameters"""

        return self._wrapped_backend.genesis_param

    @property
    def protocol_param(self) -> ProtocolParameters:
        """Get current protocol parameters"""
        return self._wrapped_backend.protocol_param

    @property
    def network(self) -> Network:
        """Get current network"""
        return self._wrapped_backend.network

    @property
    def epoch(self) -> int:
        """Current epoch number"""
        return self._wrapped_backend.epoch

    @property
    def last_block_slot(self) -> int:
        """Last block slot"""
        return self._wrapped_backend.last_block_slot

    def _utxos(self, address: str) -> List[UTxO]:
        """Get all UTxOs associated with an address.

        Args:
            address (str): An address encoded with bech32.

        Returns:
            List[UTxO]: A list of UTxOs.
        """
        key = (self.last_block_slot, address)
        if key in self._utxo_cache:
            return self._utxo_cache[key]

        if self._kupo_url:
            utxos = self._utxos_kupo(address)
        else:
            utxos = self._wrapped_backend.utxos(address)

        self._utxo_cache[key] = utxos

        return utxos

    def _get_datum_from_kupo(self, datum_hash: str) -> Optional[RawCBOR]:
        """Get datum from Kupo.

        Args:
            datum_hash (str): A datum hash.

        Returns:
            Optional[RawCBOR]: A datum.
        """
        datum = self._datum_cache.get(datum_hash, None)

        if datum is not None:
            return datum

        if self._kupo_url is None:
            raise AssertionError(
                "kupo_url object attribute has not been assigned properly."
            )

        kupo_datum_url = self._kupo_url + "/datums/" + datum_hash
        datum_result = requests.get(kupo_datum_url).json()
        if datum_result and datum_result["datum"] != datum_hash:
            datum = RawCBOR(bytes.fromhex(datum_result["datum"]))

        self._datum_cache[datum_hash] = datum
        return datum

    def _utxos_kupo(self, address: str) -> List[UTxO]:
        """Get all UTxOs associated with an address with Kupo.
        Since UTxO querying will be deprecated from Ogmios in next
        major release: https://ogmios.dev/mini-protocols/local-state-query/.

        Args:
            address (str): An address encoded with bech32.

        Returns:
            List[UTxO]: A list of UTxOs.
        """
        if self._kupo_url is None:
            raise AssertionError(
                "kupo_url object attribute has not been assigned properly."
            )

        kupo_utxo_url = self._kupo_url + "/matches/" + address + "?unspent"
        results = requests.get(kupo_utxo_url).json()

        utxos = []

        for result in results:
            tx_id = result["transaction_id"]
            index = result["output_index"]

            if result["spent_at"] is None:
                tx_in = TransactionInput.from_primitive([tx_id, index])

                lovelace_amount = result["value"]["coins"]

                script = None
                script_hash = result.get("script_hash", None)
                if script_hash:
                    kupo_script_url = self._kupo_url + "/scripts/" + script_hash
                    script = requests.get(kupo_script_url).json()
                    ver = int(script["language"].removeprefix("plutus:v"))
                    if 1 <= ver <= 3:
                        script = PlutusScript.from_version(
                            ver, bytes.fromhex(script["script"])
                        )
                        script = _try_fix_script(script_hash, script)
                    else:
                        raise ValueError("Unknown plutus script type")

                datum = None
                datum_hash = (
                    DatumHash.from_primitive(result["datum_hash"])
                    if result["datum_hash"]
                    else None
                )
                if datum_hash and result.get("datum_type", "inline"):
                    datum = self._get_datum_from_kupo(result["datum_hash"])

                if not result["value"]["assets"]:
                    tx_out = TransactionOutput(
                        Address.from_primitive(address),
                        amount=lovelace_amount,
                        datum_hash=datum_hash,
                        datum=datum,
                        script=script,
                    )
                else:
                    multi_assets = MultiAsset()

                    for asset, quantity in result["value"]["assets"].items():
                        policy_hex, policy, asset_name_hex = extract_asset_info(asset)
                        multi_assets.setdefault(policy, Asset())[
                            asset_name_hex
                        ] = quantity

                    tx_out = TransactionOutput(
                        Address.from_primitive(address),
                        amount=Value(lovelace_amount, multi_assets),
                        datum_hash=datum_hash,
                        datum=datum,
                        script=script,
                    )
                utxos.append(UTxO(tx_in, tx_out))
            else:
                continue

        return utxos

    def submit_tx_cbor(self, cbor: Union[bytes, str]):
        """Submit a transaction to the blockchain.

        Args:
            cbor (Union[bytes, str]): The transaction to be submitted.

        Raises:
            :class:`InvalidArgumentException`: When the transaction is invalid.
            :class:`TransactionFailedException`: When fails to submit the transaction to blockchain.
        """
        return self._wrapped_backend.submit_tx_cbor(cbor)

    def evaluate_tx_cbor(self, cbor: Union[bytes, str]) -> Dict[str, ExecutionUnits]:
        """Evaluate execution units of a transaction.

        Args:
            cbor (Union[bytes, str]): The serialized transaction to be evaluated.

        Returns:
            Dict[str, ExecutionUnits]: A list of execution units calculated for each of the transaction's redeemers

        Raises:
            :class:`TransactionFailedException`: When fails to evaluate the transaction.
        """
        return self._wrapped_backend.evaluate_tx_cbor(cbor)
