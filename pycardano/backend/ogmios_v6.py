import time
from typing import Dict, List, Optional, Union

from cachetools import Cache, LRUCache, TTLCache, func
from ogmios.client import Client as OgmiosClient
from ogmios.datatypes import Address as OgmiosAddress
from ogmios.datatypes import Era as OgmiosEra
from ogmios.datatypes import ProtocolParameters as OgmiosProtocolParameters
from ogmios.datatypes import Tip as OgmiosTip
from ogmios.datatypes import TxOutputReference as OgmiosTxOutputReference
from ogmios.datatypes import Utxo as OgmiosUtxo
from ogmios.utils import GenesisParameters as OgmiosGenesisParameters
from ogmios.utils import get_current_era

from pycardano.address import Address
from pycardano.backend.base import ChainContext, GenesisParameters, ProtocolParameters
from pycardano.backend.kupo import KupoChainContextExtension
from pycardano.hash import DatumHash, ScriptHash
from pycardano.network import Network
from pycardano.plutus import (
    PLUTUS_V1_COST_MODEL,
    PLUTUS_V2_COST_MODEL,
    ExecutionUnits,
    PlutusScript,
)
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

ALONZO_COINS_PER_UTXO_WORD = 34482
DEFAULT_REFETCH_INTERVAL = 1000

__all__ = ["OgmiosV6ChainContext", "OgmiosChainContext", "KupoOgmiosV6ChainContext"]


class OgmiosV6ChainContext(ChainContext):
    """Ogmios chain context for use with PyCardano"""

    _network: Network
    _client: OgmiosClient
    _service_name: str
    _last_known_block_slot: int
    _last_chain_tip_fetch: float
    _genesis_param: Optional[GenesisParameters]
    _protocol_param: Optional[OgmiosProtocolParameters]
    _utxo_cache: Cache
    _datum_cache: Cache

    def __init__(
        self,
        host: str = "localhost",
        port: int = 1337,
        path: str = "",
        secure: bool = False,
        refetch_chain_tip_interval: Optional[float] = None,
        utxo_cache_size: int = 10000,
        datum_cache_size: int = 10000,
        network: Network = Network.TESTNET,
        additional_headers: Optional[dict] = None,
    ):
        self.host = host
        self.port = port
        self.path = path
        self.secure = secure
        self.additional_headers = additional_headers or {}
        self._network = network
        self._service_name = "ogmios"
        self._last_known_block_slot = 0
        self._refetch_chain_tip_interval = (
            refetch_chain_tip_interval
            if refetch_chain_tip_interval is not None
            else DEFAULT_REFETCH_INTERVAL
        )
        self._last_chain_tip_fetch = 0
        self._genesis_param = None
        self._protocol_param = None

        self._utxo_cache = TTLCache(
            ttl=self._refetch_chain_tip_interval, maxsize=utxo_cache_size
        )
        self._datum_cache = LRUCache(maxsize=datum_cache_size)

    def _query_current_era(self) -> OgmiosEra:
        with OgmiosClient(
            self.host, self.port, self.path, self.secure, self.additional_headers
        ) as client:
            return get_current_era(client)

    def _query_current_epoch(self) -> int:
        with OgmiosClient(
            self.host, self.port, self.path, self.secure, self.additional_headers
        ) as client:
            epoch, _ = client.query_epoch.execute()
            return epoch

    def _query_chain_tip(self) -> OgmiosTip:
        with OgmiosClient(
            self.host, self.port, self.path, self.secure, self.additional_headers
        ) as client:
            tip, _ = client.query_network_tip.execute()
            return tip

    def _query_utxos_by_address(self, address: Address) -> List[OgmiosUtxo]:
        with OgmiosClient(
            self.host, self.port, self.path, self.secure, self.additional_headers
        ) as client:
            utxos, _ = client.query_utxo.execute([address])
            return utxos

    def _query_utxos_by_tx_id(self, tx_id: str, index: int) -> List[OgmiosUtxo]:
        with OgmiosClient(
            self.host, self.port, self.path, self.secure, self.additional_headers
        ) as client:
            utxos, _ = client.query_utxo.execute(
                [OgmiosTxOutputReference(tx_id, index)]
            )
            return utxos

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
        if not self._protocol_param or self._is_chain_tip_updated():
            self._protocol_param = self._fetch_protocol_param()
        return self._protocol_param

    def _fetch_protocol_param(self) -> ProtocolParameters:
        with OgmiosClient(
            self.host, self.port, self.path, self.secure, self.additional_headers
        ) as client:
            protocol_parameters, _ = client.query_protocol_parameters.execute()
            pyc_protocol_params = ProtocolParameters(
                min_fee_constant=protocol_parameters.min_fee_constant.lovelace,
                min_fee_coefficient=protocol_parameters.min_fee_coefficient,
                min_pool_cost=protocol_parameters.min_stake_pool_cost.lovelace,
                max_block_size=protocol_parameters.max_block_body_size.get("bytes"),
                max_tx_size=protocol_parameters.max_transaction_size.get("bytes"),
                max_block_header_size=protocol_parameters.max_block_header_size.get(
                    "bytes"
                ),
                key_deposit=protocol_parameters.stake_credential_deposit.lovelace,
                pool_deposit=protocol_parameters.stake_pool_deposit.lovelace,
                pool_influence=eval(protocol_parameters.stake_pool_pledge_influence),
                monetary_expansion=eval(protocol_parameters.monetary_expansion),
                treasury_expansion=eval(protocol_parameters.treasury_expansion),
                decentralization_param=None,  # type: ignore[arg-type]
                extra_entropy=protocol_parameters.extra_entropy,
                protocol_major_version=protocol_parameters.version.get("major"),
                protocol_minor_version=protocol_parameters.version.get("minor"),
                min_utxo=None,  # type: ignore[arg-type]
                price_mem=eval(
                    protocol_parameters.script_execution_prices.get("memory")
                ),
                price_step=eval(protocol_parameters.script_execution_prices.get("cpu")),
                max_tx_ex_mem=protocol_parameters.max_execution_units_per_transaction.get(
                    "memory"
                ),
                max_tx_ex_steps=protocol_parameters.max_execution_units_per_transaction.get(
                    "cpu"
                ),
                max_block_ex_mem=protocol_parameters.max_execution_units_per_block.get(
                    "memory"
                ),
                max_block_ex_steps=protocol_parameters.max_execution_units_per_block.get(
                    "cpu"
                ),
                max_val_size=protocol_parameters.max_value_size.get("bytes"),
                collateral_percent=protocol_parameters.collateral_percentage,
                max_collateral_inputs=protocol_parameters.max_collateral_inputs,
                coins_per_utxo_word=ALONZO_COINS_PER_UTXO_WORD,
                coins_per_utxo_byte=protocol_parameters.min_utxo_deposit_coefficient,
                cost_models=self._parse_cost_models(
                    protocol_parameters.plutus_cost_models
                ),
                maximum_reference_scripts_size=protocol_parameters.max_ref_script_size,
                min_fee_reference_scripts=protocol_parameters.min_fee_ref_scripts,
            )
            return pyc_protocol_params

    @property
    def genesis_param(self) -> GenesisParameters:
        if not self._genesis_param or self._is_chain_tip_updated():
            # TODO transform to PyCardano GenesisParameters?
            self._genesis_param = self._fetch_genesis_param()  # type: ignore[assignment]

            # Update the refetch interval if we haven't calculated it yet
            if (
                self._refetch_chain_tip_interval == DEFAULT_REFETCH_INTERVAL
                and self._genesis_param is not None
                and self._genesis_param.slot_length is not None
                and self._genesis_param.active_slots_coefficient is not None
            ):
                self._refetch_chain_tip_interval = (
                    self._genesis_param.slot_length
                    / float(self._genesis_param.active_slots_coefficient)
                )
        return self._genesis_param  # type: ignore[return-value]

    def _fetch_genesis_param(self) -> OgmiosGenesisParameters:
        with OgmiosClient(
            self.host, self.port, self.path, self.secure, self.additional_headers
        ) as client:
            return OgmiosGenesisParameters(client, self._query_current_era())

    @property
    def network(self) -> Network:
        return self._network

    @property
    def epoch(self) -> int:
        return self._query_current_epoch()

    @property
    @func.ttl_cache(ttl=1)
    def last_block_slot(self) -> int:
        tip = self._query_chain_tip()
        return tip.slot

    def _utxos(self, address: str) -> List[UTxO]:
        key = (self.last_block_slot, address)
        if key in self._utxo_cache:
            return self._utxo_cache[key]

        utxos = self._utxos_ogmios(OgmiosAddress(address=address))

        self._utxo_cache[key] = utxos

        return utxos

    def _check_utxo_unspent(self, tx_id: str, index: int) -> bool:
        results = self._query_utxos_by_tx_id(tx_id, index)
        return len(results) > 0

    def _utxos_ogmios(self, address: Address) -> List[OgmiosUtxo]:
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

    def _utxo_from_ogmios_result(self, utxo: OgmiosUtxo) -> UTxO:
        """Convert an Ogmios UTxO result to a PyCardano UTxO."""
        tx_in = TransactionInput.from_primitive([utxo.tx_id, utxo.index])
        lovelace_amount = utxo.value.get("ada").get("lovelace", 0)
        script = utxo.script
        if script:
            # TODO: Need to test with native scripts
            if script["language"].startswith("plutus:v"):
                script = PlutusScript.from_version(
                    int(script["language"].removeprefix("plutus:v")),
                    bytes.fromhex(script["cbor"]),
                )
            else:
                raise ValueError("Unknown plutus script type")
        datum_hash = (
            DatumHash.from_primitive(utxo.datum_hash) if utxo.datum_hash else None
        )
        datum = None
        if utxo.datum and utxo.datum != utxo.datum_hash:
            datum = RawCBOR(bytes.fromhex(utxo.datum))
        if set(utxo.value.keys()) == {"ada"}:
            tx_out = TransactionOutput(
                Address.from_primitive(utxo.address),
                amount=lovelace_amount,
                datum_hash=datum_hash,
                datum=datum,
                script=script,
            )
        else:
            multi_assets = MultiAsset()
            for asset_hex, token in utxo.value.items():
                if asset_hex != "ada":
                    for token_name_hex, quantity in token.items():
                        policy = ScriptHash.from_primitive(asset_hex)
                        token_name = AssetName.from_primitive(token_name_hex)
                        multi_assets.setdefault(policy, Asset())[token_name] = quantity

            tx_out = TransactionOutput(
                Address.from_primitive(utxo.address),
                amount=Value(lovelace_amount, multi_assets),
                datum_hash=datum_hash,
                datum=datum,
                script=script,
            )
        pyc_utxo = UTxO(tx_in, tx_out)
        return pyc_utxo

    def utxo_by_tx_id(self, tx_id: str, index: int) -> Optional[UTxO]:
        utxos = self._query_utxos_by_tx_id(tx_id, index)
        if len(utxos) > 0:
            return self._utxo_from_ogmios_result(utxos[0])
        return None

    def query_account_reward_summaries(
        self, scripts: Optional[List[str]] = None, keys: Optional[List[str]] = None
    ) -> List[dict]:
        with OgmiosClient(
            self.host, self.port, self.path, self.secure, self.additional_headers
        ) as client:
            summaries, _ = client.query_reward_account_summaries.execute(
                scripts=scripts, keys=keys
            )
            return summaries

    def submit_tx_cbor(self, cbor: Union[bytes, str]):
        if isinstance(cbor, bytes):
            cbor = cbor.hex()
        with OgmiosClient(
            self.host, self.port, self.path, self.secure, self.additional_headers
        ) as client:
            client.submit_transaction.execute(cbor)

    def evaluate_tx_cbor(self, cbor: Union[bytes, str]) -> Dict[str, ExecutionUnits]:
        if isinstance(cbor, bytes):
            cbor = cbor.hex()
        with OgmiosClient(
            self.host, self.port, self.path, self.secure, self.additional_headers
        ) as client:
            result, _ = client.evaluate_transaction.execute(cbor)
            result_dict = {}
            for res in result:
                purpose = res["validator"]["purpose"]
                # Hotfix: this purpose has been renamed in the latest version of Ogmios
                if purpose == "withdraw":
                    purpose = "withdrawal"
                result_dict[f"{purpose}:{res['validator']['index']}"] = ExecutionUnits(
                    mem=res["budget"]["memory"],
                    steps=res["budget"]["cpu"],
                )
            return result_dict

    def _parse_cost_models(self, plutus_cost_models):
        ogmios_cost_models = plutus_cost_models or {}

        cost_models = {}
        if "plutus:v1" in ogmios_cost_models:
            cost_models["PlutusV1"] = dict(
                zip(
                    sorted(PLUTUS_V1_COST_MODEL.keys()),
                    ogmios_cost_models["plutus:v1"].copy(),
                )
            )
        if "plutus:v2" in ogmios_cost_models:
            cost_models["PlutusV2"] = dict(
                zip(
                    sorted(PLUTUS_V2_COST_MODEL.keys()),
                    ogmios_cost_models["plutus:v2"].copy(),
                )
            )
        if "plutus:v3" in ogmios_cost_models:
            cost_models["PlutusV3"] = {}
            width = len(f'{len(ogmios_cost_models["plutus:v3"])}')
            for i, v in enumerate(ogmios_cost_models["plutus:v3"].copy()):
                cost_models["PlutusV3"][f"{i:0{width}d}"] = v
        return cost_models


class OgmiosChainContext(OgmiosV6ChainContext):
    """An alias of OgmiosV6ChainContext for backwards compatibility."""

    pass


def KupoOgmiosV6ChainContext(
    host: str,
    port: int,
    path: str,
    secure: bool,
    refetch_chain_tip_interval: Optional[float] = None,
    utxo_cache_size: int = 10000,
    datum_cache_size: int = 10000,
    network: Network = Network.TESTNET,
    additional_headers: Optional[dict] = None,
    kupo_url: Optional[str] = None,
) -> KupoChainContextExtension:
    return KupoChainContextExtension(
        OgmiosV6ChainContext(
            host,
            port,
            path,
            secure,
            refetch_chain_tip_interval,
            utxo_cache_size,
            datum_cache_size,
            network,
            additional_headers,
        ),
        kupo_url,
    )
