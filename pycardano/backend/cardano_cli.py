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
from typing import Dict, List, Optional, Union

import docker
from cachetools import Cache, LRUCache, TTLCache, func
from docker.errors import APIError

from pycardano.address import Address
from pycardano.backend.base import (
    ALONZO_COINS_PER_UTXO_WORD,
    ChainContext,
    GenesisParameters,
    ProtocolParameters,
)
from pycardano.cbor import cbor2
from pycardano.exception import (
    CardanoCliError,
    PyCardanoException,
    TransactionFailedException,
)
from pycardano.hash import DatumHash, ScriptHash
from pycardano.nativescript import NativeScript
from pycardano.network import Network
from pycardano.plutus import Datum, PlutusV1Script, PlutusV2Script, RawPlutusData
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
from pycardano.utils import greater_than_version

if greater_than_version((3, 13)):
    from enum import member  # type: ignore[attr-defined]


__all__ = ["CardanoCliChainContext", "CardanoCliNetwork", "DockerConfig"]


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
    CUSTOM = (
        member(partial(network_magic))
        if greater_than_version((3, 13))
        else partial(network_magic)
    )


class DockerConfig:
    """
    Docker configuration to use the cardano-cli in a Docker container
    """

    container_name: str
    """ The name of the Docker container containing the cardano-cli"""

    host_socket: Optional[Path]
    """ The path to the Docker host socket file"""

    def __init__(self, container_name: str, host_socket: Optional[Path] = None):
        self.container_name = container_name
        self.host_socket = host_socket


class CardanoCliChainContext(ChainContext):
    _binary: Path
    _socket: Optional[Path]
    _config_file: Path
    _network: CardanoCliNetwork
    _last_known_block_slot: int
    _last_chain_tip_fetch: float
    _genesis_param: Optional[GenesisParameters]
    _protocol_param: Optional[ProtocolParameters]
    _utxo_cache: Cache
    _datum_cache: Cache
    _docker_config: Optional[DockerConfig]
    _network_magic_number: Optional[int]

    def __init__(
        self,
        binary: Path,
        socket: Path,
        config_file: Path,
        network: CardanoCliNetwork,
        refetch_chain_tip_interval: Optional[float] = None,
        utxo_cache_size: int = 10000,
        datum_cache_size: int = 10000,
        docker_config: Optional[DockerConfig] = None,
        network_magic_number: Optional[int] = None,
    ):
        if docker_config is None:
            if not binary.exists() or not binary.is_file():
                raise CardanoCliError(f"cardano-cli binary file not found: {binary}")

            # Check the socket path file and set the CARDANO_NODE_SOCKET_PATH environment variable
            try:
                if not socket.exists():
                    raise CardanoCliError(f"cardano-node socket not found: {socket}")
                elif not socket.is_socket():
                    raise CardanoCliError(f"{socket} is not a socket file")

                self._socket = socket
                os.environ["CARDANO_NODE_SOCKET_PATH"] = self._socket.as_posix()
            except CardanoCliError:
                self._socket = None

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
            self._refetch_chain_tip_interval = float(
                self.genesis_param.slot_length
                / self.genesis_param.active_slots_coefficient
            )

        self._utxo_cache = TTLCache(
            ttl=self._refetch_chain_tip_interval, maxsize=utxo_cache_size
        )
        self._datum_cache = LRUCache(maxsize=datum_cache_size)
        self._docker_config = docker_config
        self._network_magic_number = network_magic_number

    @property
    def _network_args(self) -> List[str]:
        if self._network is CardanoCliNetwork.CUSTOM:
            return self._network.value(self._network_magic_number)
        else:
            return self._network.value

    def _run_command(self, cmd: List[str]) -> str:
        """
        Runs the command in the cardano-cli. If the docker configuration is set, it will run the command in the
        docker container.

        :param cmd: Command as a list of strings
        :return: The stdout if the command runs successfully
        """
        try:
            if self._docker_config:
                docker_config = self._docker_config
                if docker_config.host_socket is None:
                    client = docker.from_env()
                else:
                    client = docker.DockerClient(
                        base_url=docker_config.host_socket.as_posix()
                    )

                container = client.containers.get(docker_config.container_name)

                exec_result = container.exec_run(
                    [self._binary.as_posix()] + cmd, stdout=True, stderr=True
                )

                if exec_result.exit_code == 0:
                    output = exec_result.output.decode()
                    return output
                else:
                    error = exec_result.output.decode()
                    raise CardanoCliError(error)
            else:
                result = subprocess.run(
                    [self._binary.as_posix()] + cmd, capture_output=True, check=True
                )
                return result.stdout.decode().strip()
        except subprocess.CalledProcessError as err:
            raise CardanoCliError(err.stderr.decode()) from err
        except APIError as err:
            raise CardanoCliError(err) from err

    def _query_chain_tip(self) -> JsonDict:
        result = self._run_command(["query", "tip"] + self._network_args)
        return json.loads(result)

    def _query_current_protocol_params(self) -> JsonDict:
        result = self._run_command(
            ["query", "protocol-parameters"] + self._network_args
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
        else:
            return 0

    @staticmethod
    def _parse_cost_models(cli_result: JsonDict) -> Dict[str, Dict[str, int]]:
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

        # After 8.x.x, cardano-cli returns cost models as a list
        for m in cost_models:
            if isinstance(cost_models[m], list):
                cost_models[m] = {i: v for i, v in enumerate(cost_models[m])}

        return cost_models

    def _is_chain_tip_updated(self):
        # fetch at almost every twenty seconds!
        if time.time() - self._last_chain_tip_fetch < self._refetch_chain_tip_interval:
            return False
        self._last_chain_tip_fetch = time.time()
        result = self._query_chain_tip()
        return float(result["syncProgress"]) != 100.0

    def _fetch_protocol_param(self) -> ProtocolParameters:
        result = self._query_current_protocol_params()
        return ProtocolParameters(
            min_fee_constant=(
                result["minFeeConstant"]
                if "minFeeConstant" in result
                else result["txFeeFixed"]
            ),
            min_fee_coefficient=(
                result["minFeeCoefficient"]
                if "minFeeCoefficient" in result
                else result["txFeePerByte"]
            ),
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
            price_mem=(
                result["executionUnitPrices"]["priceMemory"]
                if "executionUnitPrices" in result
                else result["executionPrices"]["priceMemory"]
            ),
            price_step=(
                result["executionUnitPrices"]["priceSteps"]
                if "executionUnitPrices" in result
                else result["executionPrices"]["priceSteps"]
            ),
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
            coins_per_utxo_byte=(
                result["coinsPerUtxoByte"]
                if "coinsPerUtxoByte" in result
                else result.get("utxoCostPerByte", 0) or 0
            ),
            cost_models=self._parse_cost_models(result),
        )

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

    @staticmethod
    def _get_script(
        reference_script: dict,
    ) -> Union[PlutusV1Script, PlutusV2Script, NativeScript]:
        """
        Get a script object from a reference script dictionary.
        Args:
            reference_script:

        Returns:

        """
        script_type = reference_script["script"]["type"]
        script_json: JsonDict = reference_script["script"]
        if script_type == "PlutusScriptV1":
            v1script = PlutusV1Script(
                cbor2.loads(bytes.fromhex(script_json["cborHex"]))
            )
            return v1script
        elif script_type == "PlutusScriptV2":
            v2script = PlutusV2Script(
                cbor2.loads(bytes.fromhex(script_json["cborHex"]))
            )
            return v2script
        else:
            return NativeScript.from_dict(script_json)

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
            ["query", "utxo", "--address", address, "--out-file", "/dev/stdout"]
            + self._network_args
        )

        raw_utxos = json.loads(result)

        utxos = []
        for tx_hash in raw_utxos.keys():
            tx_id, tx_idx = tx_hash.split("#")
            utxo = raw_utxos[tx_hash]
            tx_in = TransactionInput.from_primitive([tx_id, int(tx_idx)])

            value = Value()
            multi_asset = MultiAsset()
            for asset in utxo["value"].keys():
                if asset == "lovelace":
                    value.coin = utxo["value"][asset]
                else:
                    policy_id = asset
                    policy = ScriptHash.from_primitive(policy_id)

                    for asset_hex_name in utxo["value"][asset].keys():
                        asset_name = AssetName.from_primitive(asset_hex_name)
                        amount = utxo["value"][asset][asset_hex_name]
                        multi_asset.setdefault(policy, Asset())[asset_name] = amount

            value.multi_asset = multi_asset

            datum_hash = (
                DatumHash.from_primitive(utxo["datumhash"])
                if utxo.get("datumhash") is not None
                else None
            )

            datum: Optional[Datum] = None

            if utxo.get("datum"):
                datum = RawCBOR(bytes.fromhex(utxo["datum"]))
            elif utxo.get("inlineDatumhash"):
                datum = RawPlutusData.from_dict(utxo["inlineDatum"])

            script = None

            if utxo.get("referenceScript"):
                script = self._get_script(utxo["referenceScript"])

            tx_out = TransactionOutput(
                Address.from_primitive(utxo["address"]),
                amount=value,
                datum_hash=datum_hash,
                datum=datum,
                script=script,
            )

            utxos.append(UTxO(tx_in, tx_out))

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
                    [
                        "latest",
                        "transaction",
                        "submit",
                        "--tx-file",
                        tmp_tx_file.name,
                    ]
                    + self._network_args
                )
            except CardanoCliError:
                try:
                    self._run_command(
                        ["transaction", "submit", "--tx-file", tmp_tx_file.name]
                        + self._network_args
                    )
                except CardanoCliError as err:
                    raise TransactionFailedException(
                        "Failed to submit transaction"
                    ) from err

            # Get the transaction ID
            try:
                txid = self._run_command(
                    ["latest", "transaction", "txid", "--tx-file", tmp_tx_file.name]
                )
            except CardanoCliError:
                try:
                    txid = self._run_command(
                        ["transaction", "txid", "--tx-file", tmp_tx_file.name]
                    )
                except CardanoCliError as err:
                    raise PyCardanoException(
                        f"Unable to get transaction id for {tmp_tx_file.name}"
                    ) from err

        return txid
