import json
import time
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union

import requests
import websocket
from cachetools import Cache, LRUCache, TTLCache, func

from pycardano.address import Address
from pycardano.backend.base import (
    ALONZO_COINS_PER_UTXO_WORD,
    ChainContext,
    GenesisParameters,
    ProtocolParameters,
)
from pycardano.backend.blockfrost import _try_fix_script
from pycardano.exception import TransactionFailedException
from pycardano.hash import DatumHash, ScriptHash
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

__all__ = ["OgmiosChainContext"]


class OgmiosQueryType(str, Enum):
    Query = "Query"
    SubmitTx = "SubmitTx"
    EvaluateTx = "EvaluateTx"


class OgmiosChainContext(ChainContext):
    _ws_url: str
    _network: Network
    _service_name: str
    _kupo_url: Optional[str]
    _last_known_block_slot: int
    _last_chain_tip_fetch: float
    _genesis_param: Optional[GenesisParameters]
    _protocol_param: Optional[ProtocolParameters]
    _utxo_cache: Cache
    _datum_cache: Cache

    def __init__(
        self,
        ws_url: str,
        network: Network,
        compact_result=True,
        kupo_url=None,
        refetch_chain_tip_interval: Optional[float] = None,
        utxo_cache_size: int = 10000,
        datum_cache_size: int = 10000,
    ):
        self._ws_url = ws_url
        self._network = network
        self._service_name = "ogmios.v1:compact" if compact_result else "ogmios"
        self._kupo_url = kupo_url
        self._last_known_block_slot = 0
        self._refetch_chain_tip_interval = (
            refetch_chain_tip_interval
            if refetch_chain_tip_interval is not None
            else 1000
        )
        self._last_chain_tip_fetch = 0
        self._genesis_param = None
        self._protocol_param = None
        if refetch_chain_tip_interval is None:
            self._refetch_chain_tip_interval = (
                self.genesis_param.slot_length
                / self.genesis_param.active_slots_coefficient
            )

        self._utxo_cache = TTLCache(
            ttl=self._refetch_chain_tip_interval, maxsize=utxo_cache_size
        )
        self._datum_cache = LRUCache(maxsize=datum_cache_size)

    def _request(self, method: OgmiosQueryType, args: JsonDict) -> Any:
        ws = websocket.WebSocket()
        ws.connect(self._ws_url)
        request = json.dumps(
            {
                "type": "jsonwsp/request",
                "version": "1.0",
                "servicename": self._service_name,
                "methodname": method.value,
                "args": args,
            },
            separators=(",", ":"),
        )
        ws.send(request)
        response = ws.recv()
        ws.close()
        if "result" not in response:
            raise TransactionFailedException(
                f"Ogmios ran into an error. Reponse: {response}"
            )
        return json.loads(response)["result"]

    def _query_current_protocol_params(self) -> JsonDict:
        args = {"query": "currentProtocolParameters"}
        return self._request(OgmiosQueryType.Query, args)

    def _query_genesis_config(self) -> JsonDict:
        args = {"query": "genesisConfig"}
        return self._request(OgmiosQueryType.Query, args)

    def _query_current_epoch(self) -> int:
        args = {"query": "currentEpoch"}
        return self._request(OgmiosQueryType.Query, args)

    def _query_chain_tip(self) -> JsonDict:
        args = {"query": "chainTip"}
        return self._request(OgmiosQueryType.Query, args)

    def _query_utxos_by_address(self, address: str) -> List[List[JsonDict]]:
        args = {"query": {"utxo": [address]}}
        return self._request(OgmiosQueryType.Query, args)

    def _query_utxos_by_tx_id(self, tx_id: str, index: int) -> List[List[JsonDict]]:
        args = {"query": {"utxo": [{"txId": tx_id, "index": index}]}}
        return self._request(OgmiosQueryType.Query, args)

    def _is_chain_tip_updated(self):
        # fetch at most every twenty seconds!
        if time.time() - self._last_chain_tip_fetch < self._refetch_chain_tip_interval:
            return False
        self._last_chain_tip_fetch = time.time()
        slot = self.last_block_slot
        if self._last_known_block_slot < slot:
            self._last_known_block_slot = slot
            return True
        else:
            return False

    @staticmethod
    def _fraction_parser(fraction: str) -> float:
        x, y = fraction.split("/")
        return int(x) / int(y)

    @property
    def protocol_param(self) -> ProtocolParameters:
        """Get current protocol parameters"""
        if not self._protocol_param or self._is_chain_tip_updated():
            self._protocol_param = self._fetch_protocol_param()
        return self._protocol_param

    def _fetch_protocol_param(self) -> ProtocolParameters:
        result = self._query_current_protocol_params()
        param = ProtocolParameters(
            min_fee_constant=result["minFeeConstant"],
            min_fee_coefficient=result["minFeeCoefficient"],
            max_block_size=result["maxBlockBodySize"],
            max_tx_size=result["maxTxSize"],
            max_block_header_size=result["maxBlockHeaderSize"],
            key_deposit=result["stakeKeyDeposit"],
            pool_deposit=result["poolDeposit"],
            pool_influence=self._fraction_parser(result["poolInfluence"]),
            monetary_expansion=self._fraction_parser(result["monetaryExpansion"]),
            treasury_expansion=self._fraction_parser(result["treasuryExpansion"]),
            decentralization_param=self._fraction_parser(
                result.get("decentralizationParameter", "0/1")
            ),
            extra_entropy=result.get("extraEntropy", ""),
            protocol_major_version=result["protocolVersion"]["major"],
            protocol_minor_version=result["protocolVersion"]["minor"],
            min_utxo=self._get_min_utxo(),
            min_pool_cost=result["minPoolCost"],
            price_mem=self._fraction_parser(result["prices"]["memory"]),
            price_step=self._fraction_parser(result["prices"]["steps"]),
            max_tx_ex_mem=result["maxExecutionUnitsPerTransaction"]["memory"],
            max_tx_ex_steps=result["maxExecutionUnitsPerTransaction"]["steps"],
            max_block_ex_mem=result["maxExecutionUnitsPerBlock"]["memory"],
            max_block_ex_steps=result["maxExecutionUnitsPerBlock"]["steps"],
            max_val_size=result["maxValueSize"],
            collateral_percent=result["collateralPercentage"],
            max_collateral_inputs=result["maxCollateralInputs"],
            coins_per_utxo_word=result.get(
                "coinsPerUtxoWord", ALONZO_COINS_PER_UTXO_WORD
            ),
            coins_per_utxo_byte=result.get("coinsPerUtxoByte", 0),
            cost_models=self._parse_cost_models(result),
        )

        return param

    def _get_min_utxo(self) -> int:
        result = self._query_genesis_config()
        return result["protocolParameters"]["minUtxoValue"]

    def _parse_cost_models(self, ogmios_result: JsonDict) -> Dict[str, Dict[str, int]]:
        ogmios_cost_models = ogmios_result.get("costModels", {})

        cost_models = {}
        if "plutus:v1" in ogmios_cost_models:
            cost_models["PlutusV1"] = ogmios_cost_models["plutus:v1"].copy()
        if "plutus:v2" in ogmios_cost_models:
            cost_models["PlutusV2"] = ogmios_cost_models["plutus:v2"].copy()
        return cost_models

    @property
    def genesis_param(self) -> GenesisParameters:
        """Get chain genesis parameters"""

        @func.lru_cache(maxsize=10)
        def _genesis_param_cache(slot) -> GenesisParameters:
            return self._fetch_genesis_param()

        return _genesis_param_cache(self.last_block_slot)

    def _fetch_genesis_param(self) -> GenesisParameters:
        result = self._query_genesis_config()
        start_str = result["systemStart"].split(".")[0]
        dt = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
        dt = dt.replace(tzinfo=timezone.utc)
        system_start_unix = int(dt.timestamp())
        return GenesisParameters(
            active_slots_coefficient=self._fraction_parser(
                result["activeSlotsCoefficient"]
            ),
            update_quorum=result["updateQuorum"],
            max_lovelace_supply=result["maxLovelaceSupply"],
            network_magic=result["networkMagic"],
            epoch_length=result["epochLength"],
            system_start=system_start_unix,
            slots_per_kes_period=result["slotsPerKesPeriod"],
            slot_length=result["slotLength"],
            max_kes_evolutions=result["maxKesEvolutions"],
            security_param=result["securityParameter"],
        )

    @property
    def network(self) -> Network:
        """Get current network"""
        return self.network

    @property
    def epoch(self) -> int:
        """Current epoch number"""
        return self._query_current_epoch()

    @property
    @func.ttl_cache(ttl=1)
    def last_block_slot(self) -> int:
        result = self._query_chain_tip()
        slot = result["slot"]
        return slot

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
            utxos = self._utxos_ogmios(address)

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
                    if script["language"] == "plutus:v2":
                        script = PlutusV2Script(bytes.fromhex(script["script"]))
                        script = _try_fix_script(script_hash, script)
                    elif script["language"] == "plutus:v1":
                        script = PlutusV1Script(bytes.fromhex(script["script"]))
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
                    if datum is not None:
                        datum_hash = None

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
                        policy_hex, policy, asset_name_hex = self._extract_asset_info(
                            asset
                        )
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

    def _check_utxo_unspent(self, tx_id: str, index: int) -> bool:
        """Check whether an UTxO is unspent with Ogmios.

        Args:
            tx_id (str): transaction id.
            index (int): transaction index.
        """
        results = self._query_utxos_by_tx_id(tx_id, index)
        return len(results) > 0

    def _extract_asset_info(self, asset_hash: str) -> Tuple[str, ScriptHash, AssetName]:
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

    def _utxos_ogmios(self, address: str) -> List[UTxO]:
        """Get all UTxOs associated with an address with Ogmios.

        Args:
            address (str): An address encoded with bech32.

        Returns:
            List[UTxO]: A list of UTxOs.
        """
        results = self._query_utxos_by_address(address)

        utxos = []
        for result in results:
            utxos.append(self._utxo_from_ogmios_result(result))

        return utxos

    def utxo_by_tx_id(self, tx_id: str, index: int) -> Optional[UTxO]:
        """Get a UTxO associated with a tx_id and index.

        Args:
            tx_id (str): The transaction id.
            index (int): The index for the UTxO at the specified transaction.

        Returns:
            Optional[UTxO]: Return a UTxO if exists at the tx_id and index.
        """
        results = self._query_utxos_by_tx_id(tx_id, index)
        assert len(results) < 2, f"Query for UTxO {tx_id}#{index} should be unique!"

        utxos = []
        for result in results:
            utxos.append(self._utxo_from_ogmios_result(result))

        if len(utxos) > 0:
            return utxos[0]
        return None

    def _utxo_from_ogmios_result(self, result) -> UTxO:
        in_ref = result[0]
        output = result[1]
        tx_in = TransactionInput.from_primitive([in_ref["txId"], in_ref["index"]])
        lovelace_amount = output["value"]["coins"]
        script = output.get("script", None)
        if script:
            if "plutus:v2" in script:
                script = PlutusV2Script(bytes.fromhex(script["plutus:v2"]))
            elif "plutus:v1" in script:
                script = PlutusV1Script(bytes.fromhex(script["plutus:v1"]))
            else:
                raise ValueError("Unknown plutus script type")
        datum_hash = (
            DatumHash.from_primitive(output["datumHash"])
            if output.get("datumHash", None)
            else None
        )
        datum = None
        if output["datum"] and output["datum"] != output["datumHash"]:
            datum = RawCBOR(bytes.fromhex(output["datum"]))
        if not output["value"]["assets"]:
            tx_out = TransactionOutput(
                Address.from_primitive(output["address"]),
                amount=lovelace_amount,
                datum_hash=datum_hash,
                datum=datum,
                script=script,
            )
        else:
            multi_assets = MultiAsset()

            for asset, quantity in output["value"]["assets"].items():
                policy_hex, policy, asset_name_hex = self._extract_asset_info(asset)
                multi_assets.setdefault(policy, Asset())[asset_name_hex] = quantity

            tx_out = TransactionOutput(
                Address.from_primitive(output["address"]),
                amount=Value(lovelace_amount, multi_assets),
                datum_hash=datum_hash,
                datum=datum,
                script=script,
            )
        utxo = UTxO(tx_in, tx_out)
        return utxo

    def submit_tx_cbor(self, cbor: Union[bytes, str]):
        """Submit a transaction to the blockchain.

        Args:
            cbor (Union[bytes, str]): The transaction to be submitted.

        Raises:
            :class:`InvalidArgumentException`: When the transaction is invalid.
            :class:`TransactionFailedException`: When fails to submit the transaction to blockchain.
        """
        if isinstance(cbor, bytes):
            cbor = cbor.hex()

        args = {"submit": cbor}
        result = self._request(OgmiosQueryType.SubmitTx, args)
        if "SubmitFail" in result:
            raise TransactionFailedException(result["SubmitFail"])

    def evaluate_tx_cbor(self, cbor: Union[bytes, str]) -> Dict[str, ExecutionUnits]:
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

        args = {"evaluate": cbor}
        result = self._request(OgmiosQueryType.EvaluateTx, args)
        if "EvaluationResult" not in result:
            raise TransactionFailedException(result)
        else:
            for k in result["EvaluationResult"].keys():
                result["EvaluationResult"][k] = ExecutionUnits(
                    result["EvaluationResult"][k]["memory"],
                    result["EvaluationResult"][k]["steps"],
                )
            return result["EvaluationResult"]
