import calendar
import json
import time
from typing import List, Union

import websocket

from pycardano.address import Address
from pycardano.backend.base import ChainContext, GenesisParameters, ProtocolParameters
from pycardano.exception import TransactionFailedException
from pycardano.hash import DatumHash, ScriptHash
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

__all__ = ["OgmiosChainContext"]


class OgmiosChainContext(ChainContext):
    def __init__(self, ws_url: str, network: Network, compact_result=True):
        self._ws_url = ws_url
        self._network = network
        self._service_name = "ogmios.v1:compact" if compact_result else "ogmios"
        self._last_known_block_slot = 0
        self._genesis_param = None
        self._protocol_param = None

    def _request(self, method: str, args: dict) -> dict:
        ws = websocket.WebSocket()
        ws.connect(self._ws_url)
        request = json.dumps(
            {
                "type": "jsonwsp/request",
                "version": "1.0",
                "servicename": self._service_name,
                "methodname": method,
                "args": args,
            },
            separators=(",", ":"),
        )
        ws.send(request)
        response = ws.recv()
        ws.close()
        return json.loads(response)["result"]

    def _check_chain_tip_and_update(self):
        slot = self.last_block_slot
        if self._last_known_block_slot != slot:
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
        method = "Query"
        args = {"query": "currentProtocolParameters"}
        if not self._protocol_param or self._check_chain_tip_and_update():
            result = self._request(method, args)
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
                    result["decentralizationParameter"]
                ),
                extra_entropy=result["extraEntropy"],
                protocol_major_version=result["protocolVersion"]["major"],
                protocol_minor_version=result["protocolVersion"]["minor"],
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
                coins_per_utxo_word=result["coinsPerUtxoWord"],
            )
            self._protocol_param = param
        return self._protocol_param

    @property
    def genesis_param(self) -> GenesisParameters:
        """Get chain genesis parameters"""
        method = "Query"
        args = {"query": "genesisConfig"}
        if not self._genesis_param or self._check_chain_tip_and_update():
            result = self._request(method, args)
            system_start_unix = int(
                calendar.timegm(
                    time.strptime(
                        result["systemStart"].split(".")[0], "%Y-%m-%dT%H:%M:%S"
                    ),
                )
            )
            self._genesis_param = GenesisParameters(
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
        return self._genesis_param

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
        method = "Query"
        args = {"query": "chainTip"}
        return self._request(method, args)["slot"]

    def utxos(self, address: str) -> List[UTxO]:
        """Get all UTxOs associated with an address.

        Args:
            address (str): An address encoded with bech32.

        Returns:
            List[UTxO]: A list of UTxOs.
        """
        method = "Query"
        args = {"query": {"utxo": [address]}}
        results = self._request(method, args)

        utxos = []

        for result in results:
            in_ref = result[0]
            output = result[1]
            tx_in = TransactionInput.from_primitive([in_ref["txId"], in_ref["index"]])

            lovelace_amount = output["value"]["coins"]

            datum_hash = (
                DatumHash.from_primitive(output["datum"]) if output["datum"] else None
            )

            if not output["value"]["assets"]:
                tx_out = TransactionOutput(
                    Address.from_primitive(address),
                    amount=lovelace_amount,
                    datum_hash=datum_hash,
                )
            else:
                multi_assets = MultiAsset()

                for asset in output["value"]["assets"]:
                    quantity = output["value"]["assets"][asset]
                    policy_hex, asset_name_hex = asset.split(".")
                    policy = ScriptHash.from_primitive(policy_hex)
                    asset_name_hex = AssetName.from_primitive(asset_name_hex)
                    multi_assets.setdefault(policy, Asset())[asset_name_hex] = quantity

                tx_out = TransactionOutput(
                    Address.from_primitive(address),
                    amount=Value(lovelace_amount, multi_assets),
                    datum_hash=datum_hash,
                )
            utxos.append(UTxO(tx_in, tx_out))

        return utxos

    def submit_tx(self, cbor: Union[bytes, str]):
        """Submit a transaction to the blockchain.

        Args:
            cbor (Union[bytes, str]): The transaction to be submitted.

        Raises:
            :class:`InvalidArgumentException`: When the transaction is invalid.
            :class:`TransactionFailedException`: When fails to submit the transaction to blockchain.
        """
        if isinstance(cbor, bytes):
            cbor = cbor.hex()

        method = "SubmitTx"
        args = {"bytes": cbor}
        result = self._request(method, args)
        if "SubmitFail" in result:
            raise TransactionFailedException(result["SubmitFail"])
