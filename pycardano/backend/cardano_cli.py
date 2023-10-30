"""
Cardano CLI Chain Context
"""
import json
import os
import subprocess
import tempfile
import time
from enum import Enum
from functools import partial
from pathlib import Path
from typing import Optional, List, Dict, Union

from cachetools import Cache, LRUCache, TTLCache, func

from pycardano import Network
from pycardano.address import Address
from pycardano.backend.base import (
    ALONZO_COINS_PER_UTXO_WORD,
    ChainContext,
    GenesisParameters,
    ProtocolParameters,
)
from pycardano.exception import (
    TransactionFailedException,
    CardanoCliError,
    PyCardanoException,
)
from pycardano.hash import DatumHash, ScriptHash
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

__all__ = ["CardanoCliChainContext", "CardanoCliNetwork"]


class Mode(str, Enum):
    """
    Mode enumeration.
    """

    ONLINE = "online"
    OFFLINE = "offline"


def network_magic(magic_number: int) -> List[str]:
    """
    Returns the network magic number for the cardano-cli
    Args:
        magic_number: The network magic number

    Returns:
        The network magic number arguments
    """
    return ["--testnet-magic", str(magic_number)]


class CardanoCliNetwork(Enum):
    """
    Enum class for Cardano Era
    """

    MAINNET = ["--mainnet"]
    TESTNET = ["--testnet-magic", str(1097911063)]
    PREVIEW = ["--testnet-magic", str(2)]
    PREPROD = ["--testnet-magic", str(1)]
    GUILDNET = ["--testnet-magic", str(141)]
    CUSTOM = partial(network_magic)


class CardanoCliChainContext(ChainContext):
    _binary: Path
    _socket: Optional[Path]
    _config_file: Path
    _mode: Mode
    _network: CardanoCliNetwork
    _last_known_block_slot: int
    _last_chain_tip_fetch: float
    _genesis_param: Optional[GenesisParameters]
    _protocol_param: Optional[ProtocolParameters]
    _utxo_cache: Cache
    _datum_cache: Cache

    def __init__(
        self,
        binary: Path,
        socket: Path,
        config_file: Path,
        network: CardanoCliNetwork,
        refetch_chain_tip_interval: Optional[float] = None,
        utxo_cache_size: int = 10000,
        datum_cache_size: int = 10000,
    ):
        if not binary.exists() or not binary.is_file():
            raise CardanoCliError(f"cardano-cli binary file not found: {binary}")

        # Check the socket path file and set the CARDANO_NODE_SOCKET_PATH environment variable
        try:
            if not socket.exists():
                raise CardanoCliError(f"cardano-cli binary file not found: {binary}")
            elif not socket.is_socket():
                raise CardanoCliError(f"{socket} is not a socket file")

            self._socket = socket
            os.environ["CARDANO_NODE_SOCKET_PATH"] = self._socket.as_posix()
            self._mode = Mode.ONLINE
        except CardanoCliError:
            self._socket = None
            self._mode = Mode.OFFLINE

        self._binary = binary
        self._network = network
        self._config_file = config_file
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

    def _run_command(self, cmd: List[str]) -> str:
        """
        Runs the command in the cardano-cli

        :param cmd: Command as a list of strings
        :return: The stdout if the command runs successfully
        """
        try:
            result = subprocess.run(
                [self._binary.as_posix()] + cmd, capture_output=True, check=True
            )
            return result.stdout.decode().strip()
        except subprocess.CalledProcessError as err:
            raise CardanoCliError(err.stderr.decode()) from err

    def _query_chain_tip(self) -> JsonDict:
        result = self._run_command(["query", "tip"] + self._network.value)
        return json.loads(result)

    def _query_current_protocol_params(self) -> JsonDict:
        result = self._run_command(
            ["query", "protocol-parameters"] + self._network.value
        )
        return json.loads(result)

    def _query_genesis_config(self) -> JsonDict:
        if not self._config_file.exists() or not self._config_file.is_file():
            raise CardanoCliError(f"Cardano config file not found: {self._config_file}")
        with open(self._config_file, encoding="utf-8") as config_file:
            config_json = json.load(config_file)
            shelly_genesis_file = (
                self._config_file.parent / config_json["ShelleyGenesisFile"]
            )
        if not shelly_genesis_file.exists() or not shelly_genesis_file.is_file():
            raise CardanoCliError(
                f"Shelly Genesis file not found: {shelly_genesis_file}"
            )
        with open(shelly_genesis_file, encoding="utf-8") as genesis_file:
            genesis_json = json.load(genesis_file)
        return genesis_json

    def _get_min_utxo(self) -> int:
        params = self._query_current_protocol_params()
        if "minUTxOValue" in params and params["minUTxOValue"] is not None:
            return params["minUTxOValue"]
        elif (
            "lovelacePerUTxOWord" in params
            and params["lovelacePerUTxOWord"] is not None
        ):
            return params["lovelacePerUTxOWord"]
        elif "utxoCostPerWord" in params and params["utxoCostPerWord"] is not None:
            return params["utxoCostPerWord"]
        elif "utxoCostPerByte" in params and params["utxoCostPerByte"] is not None:
            return params["utxoCostPerByte"]
        raise ValueError("Cannot determine minUTxOValue, invalid protocol params")

    def _parse_cost_models(self, cli_result: JsonDict) -> Dict[str, Dict[str, int]]:
        cli_cost_models = cli_result.get("costModels", {})

        cost_models = {}
        if "PlutusScriptV1" in cli_cost_models:
            cost_models["PlutusScriptV1"] = cli_cost_models["PlutusScriptV1"].copy()
        elif "PlutusV1" in cli_cost_models:
            cost_models["PlutusV1"] = cli_cost_models["PlutusV1"].copy()

        if "PlutusScriptV2" in cli_cost_models:
            cost_models["PlutusScriptV2"] = cli_cost_models["PlutusScriptV2"].copy()
        elif "PlutusV2" in cli_cost_models:
            cost_models["PlutusV2"] = cli_cost_models["PlutusV2"].copy()

        return cost_models

    def _is_chain_tip_updated(self):
        # fetch at most every twenty seconds!
        if time.time() - self._last_chain_tip_fetch < self._refetch_chain_tip_interval:
            return False
        self._last_chain_tip_fetch = time.time()
        result = self._query_chain_tip()
        return float(result["syncProgress"]) != 100.0

    def _fetch_protocol_param(self) -> ProtocolParameters:
        result = self._query_current_protocol_params()
        return ProtocolParameters(
            min_fee_constant=result["minFeeConstant"]
            if "minFeeConstant" in result
            else result["txFeeFixed"],
            min_fee_coefficient=result["minFeeCoefficient"]
            if "minFeeCoefficient" in result
            else result["txFeePerByte"],
            max_block_size=result["maxBlockBodySize"],
            max_tx_size=result["maxTxSize"],
            max_block_header_size=result["maxBlockHeaderSize"],
            key_deposit=result["stakeAddressDeposit"],
            pool_deposit=result["stakePoolDeposit"],
            pool_influence=result["poolPledgeInfluence"],
            monetary_expansion=result["monetaryExpansion"],
            treasury_expansion=result["treasuryCut"],
            decentralization_param=result.get("decentralization", 0),
            extra_entropy=result.get("extraPraosEntropy", ""),
            protocol_major_version=result["protocolVersion"]["major"],
            protocol_minor_version=result["protocolVersion"]["minor"],
            min_utxo=self._get_min_utxo(),
            min_pool_cost=result["minPoolCost"],
            price_mem=result["executionUnitPrices"]["priceMemory"]
            if "executionUnitPrices" in result
            else result["executionPrices"]["priceMemory"],
            price_step=result["executionUnitPrices"]["priceSteps"]
            if "executionUnitPrices" in result
            else result["executionPrices"]["priceSteps"],
            max_tx_ex_mem=result["maxTxExecutionUnits"]["memory"],
            max_tx_ex_steps=result["maxTxExecutionUnits"]["steps"],
            max_block_ex_mem=result["maxBlockExecutionUnits"]["memory"],
            max_block_ex_steps=result["maxBlockExecutionUnits"]["steps"],
            max_val_size=result["maxValueSize"],
            collateral_percent=result["collateralPercentage"],
            max_collateral_inputs=result["maxCollateralInputs"],
            coins_per_utxo_word=result.get(
                "coinsPerUtxoWord", ALONZO_COINS_PER_UTXO_WORD
            ),
            coins_per_utxo_byte=result.get("coinsPerUtxoByte", 0),
            cost_models=self._parse_cost_models(result),
        )

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

    @property
    def genesis_param(self) -> GenesisParameters:
        """Get chain genesis parameters"""
        genesis_params = self._query_genesis_config()
        return GenesisParameters(
            active_slots_coefficient=genesis_params["activeSlotsCoeff"],
            update_quorum=genesis_params["updateQuorum"],
            max_lovelace_supply=genesis_params["maxLovelaceSupply"],
            network_magic=genesis_params["networkMagic"],
            epoch_length=genesis_params["epochLength"],
            system_start=genesis_params["systemStart"],
            slots_per_kes_period=genesis_params["slotsPerKESPeriod"],
            slot_length=genesis_params["slotLength"],
            max_kes_evolutions=genesis_params["maxKESEvolutions"],
            security_param=genesis_params["securityParam"],
        )

    @property
    def network(self) -> Network:
        """Cet current network"""
        if self._network == CardanoCliNetwork.MAINNET:
            return Network.MAINNET
        return Network.TESTNET

    @property
    def epoch(self) -> int:
        """Current epoch number"""
        result = self._query_chain_tip()
        return result["epoch"]

    @property
    def era(self) -> int:
        """Current Cardano era"""
        result = self._query_chain_tip()
        return result["era"]

    @property
    @func.ttl_cache(ttl=1)
    def last_block_slot(self) -> int:
        result = self._query_chain_tip()
        return result["slot"]

    def version(self):
        """
        Gets the cardano-cli version
        """
        return self._run_command(["version"])

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

        result = self._run_command(
            ["query", "utxo", "--address", address] + self._network.value
        )
        raw_utxos = result.split("\n")[2:]

        # Parse the UTXOs into a list of dict objects
        utxos = []
        for utxo_line in raw_utxos:
            if len(utxo_line) == 0:
                continue

            vals = utxo_line.split()
            utxo_dict = {
                "tx_hash": vals[0],
                "tx_ix": vals[1],
                "lovelaces": int(vals[2]),
                "type": vals[3],
            }

            tx_in = TransactionInput.from_primitive(
                [utxo_dict["tx_hash"], int(utxo_dict["tx_ix"])]
            )
            lovelace_amount = utxo_dict["lovelaces"]

            tx_out = TransactionOutput(
                Address.from_primitive(address), amount=Value(coin=int(lovelace_amount))
            )

            extra = [i for i, j in enumerate(vals) if j == "+"]
            for i in extra:
                if "TxOutDatumNone" in vals[i + 1]:
                    continue
                elif "TxOutDatumHash" in vals[i + 1] and "Data" in vals[i + 2]:
                    datum_hash = DatumHash.from_primitive(vals[i + 3])
                    tx_out.datum_hash = datum_hash
                else:
                    multi_assets = MultiAsset()

                    policy_id = vals[i + 2].split(".")[0]
                    asset_hex_name = vals[i + 2].split(".")[1]
                    quantity = int(vals[i + 1])

                    policy = ScriptHash.from_primitive(policy_id)
                    asset_name = AssetName.from_primitive(asset_hex_name)

                    multi_assets.setdefault(policy, Asset())[asset_name] = quantity

                    tx_out.amount = Value(lovelace_amount, multi_assets)

            utxo = UTxO(input=tx_in, output=tx_out)

            utxos.append(utxo)

        self._utxo_cache[key] = utxos

        return utxos

    def submit_tx_cbor(self, cbor: Union[bytes, str]) -> str:
        """Submit a transaction to the blockchain.

        Args:
            cbor (Union[bytes, str]): The transaction to be submitted.

        Returns:
            str: The transaction hash.

        Raises:
            :class:`TransactionFailedException`: When fails to submit the transaction to blockchain.
            :class:`PyCardanoException`: When fails to retrieve the transaction hash.
        """
        if isinstance(cbor, bytes):
            cbor = cbor.hex()

        with tempfile.NamedTemporaryFile(mode="w") as tmp_tx_file:
            tx_json = {
                "type": f"Witnessed Tx {self.era}Era",
                "description": "Generated by PyCardano",
                "cborHex": cbor,
            }

            tmp_tx_file.write(json.dumps(tx_json))

            tmp_tx_file.flush()

            try:
                self._run_command(
                    ["transaction", "submit", "--tx-file", tmp_tx_file.name]
                    + self._network.value
                )
            except CardanoCliError as err:
                raise TransactionFailedException(
                    "Failed to submit transaction"
                ) from err

            # Get the transaction ID
            try:
                txid = self._run_command(
                    ["transaction", "txid", "--tx-file", tmp_tx_file.name]
                )
            except CardanoCliError as err:
                raise PyCardanoException(
                    f"Unable to get transaction id for {tmp_tx_file.name}"
                ) from err

        return txid
