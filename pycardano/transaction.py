from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Union
from pprint import pformat

from nacl.encoding import RawEncoder
from nacl.hash import blake2b

from pycardano.address import Address
from pycardano.hash import (TransactionId, DatumHash, AuxiliaryDataHash, ScriptHash, AddrKeyHash,
                            TRANSACTION_HASH_SIZE, ConstrainedBytes)
from pycardano.network import Network
from pycardano.serialization import (ArrayCBORSerializable, DictCBORSerializable,
                                     MapCBORSerializable, list_hook)
from pycardano.witness import TransactionWitnessSet


@dataclass(repr=False)
class TransactionInput(ArrayCBORSerializable):
    transaction_id: TransactionId

    index: int


class AssetName(ConstrainedBytes):
    MAX_SIZE = 32

    def __repr__(self):
        return str(self.payload)


class Asset(DictCBORSerializable):
    KEY_TYPE = AssetName

    VALUE_TYPE = int


class MultiAsset(DictCBORSerializable):
    KEY_TYPE = ScriptHash

    VALUE_TYPE = Asset


@dataclass(repr=False)
class FullMultiAsset(ArrayCBORSerializable):
    coin: int
    """Amount of ADA"""

    multi_asset: MultiAsset
    """Multi-assets associated with the UTxO"""


@dataclass(repr=False)
class TransactionOutput(ArrayCBORSerializable):
    address: Address

    amount: Union[int, FullMultiAsset]

    datum_hash: DatumHash = field(default=None, metadata={"optional": True})


@dataclass(repr=False)
class UTxO:

    input: TransactionInput

    output: TransactionOutput

    def __repr__(self):
        return pformat(vars(self))


@dataclass(repr=False)
class TransactionBody(MapCBORSerializable):
    inputs: List[TransactionInput] = field(
        default_factory=list,
        metadata={"key": 0,
                  "object_hook": list_hook(TransactionInput)})

    outputs: List[TransactionOutput] = field(
        default_factory=list,
        metadata={"key": 1,
                  "object_hook": list_hook(TransactionOutput)})

    fee: int = field(default=0, metadata={"key": 2})

    ttl: int = field(default=None, metadata={"key": 3, "optional": True})

    # TODO: Add certificate support
    certificates: Any = field(default=None, metadata={"key": 4, "optional": True})

    # TODO: Add reward withdraw support
    withdraws: Any = field(default=None, metadata={"key": 5, "optional": True})

    # TODO: Add proposal update support
    update: Any = field(default=None, metadata={"key": 6, "optional": True})

    auxiliary_data_hash: AuxiliaryDataHash = field(default=None, metadata={"key": 7, "optional": True})

    validity_start: int = field(default=None, metadata={"key": 8, "optional": True})

    mint: MultiAsset = field(default=None, metadata={"key": 9, "optional": True})

    script_data_hash: ScriptHash = field(default=None, metadata={"key": 11, "optional": True})

    collateral: List[TransactionInput] = field(
        default=None,
        metadata={"key": 13,
                  "optional": True,
                  "object_hook": list_hook(TransactionInput)})

    required_signers: List[AddrKeyHash] = field(
        default=None,
        metadata={"key": 14,
                  "optional": True,
                  "object_hook": list_hook(AddrKeyHash)})

    network_id: Network = field(default=None, metadata={"key": 15, "optional": True})

    def hash(self) -> bytes:
        return blake2b(self.to_cbor(encoding="bytes"), TRANSACTION_HASH_SIZE, encoder=RawEncoder)


@dataclass(repr=False)
class Transaction(ArrayCBORSerializable):
    transaction_body: TransactionBody

    transaction_witness_set: TransactionWitnessSet

    valid: bool = True

    # TODO: Add axuiliary data support
    auxiliary_data: Union[Any, type(None)] = None
