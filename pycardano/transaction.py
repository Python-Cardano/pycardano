from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Union
from pprint import pformat

from nacl.encoding import RawEncoder
from nacl.hash import blake2b

from pycardano.address import Address
from pycardano.exception import InvalidOperationException
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

    def union(self, other: Asset) -> Asset:
        return self + other

    def __add__(self, other: Asset) -> Asset:
        new_asset = self.copy()
        for n in other:
            new_asset[n] = new_asset.get(n, 0) + other[n]
        return new_asset

    def __sub__(self, other: Asset) -> Asset:
        new_asset = self.copy()
        for n in other:
            if n not in new_asset:
                raise InvalidOperationException(f"Asset: {new_asset} does not have asset with name: {n}")
            # According to ledger rule, the value of an asset could be negative, so we don't check the value here and
            # will leave the check to user when necessary.
            # https://github.com/input-output-hk/cardano-ledger/blob/master/eras/alonzo/test-suite/cddl-files/alonzo.cddl#L378
            new_asset[n] -= other[n]
        return new_asset


class MultiAsset(DictCBORSerializable):
    KEY_TYPE = ScriptHash

    VALUE_TYPE = Asset

    def union(self, other: MultiAsset) -> MultiAsset:
        return self + other

    def __add__(self, other):
        new_multi_asset = self.copy()
        for p in other:
            if p not in new_multi_asset:
                new_multi_asset[p] = Asset()
            new_multi_asset[p] += other[p]
        return new_multi_asset

    def __sub__(self, other: MultiAsset) -> MultiAsset:
        new_multi_asset = self.copy()
        for p in other:
            if p not in new_multi_asset:
                raise InvalidOperationException(f"MultiAsset: {new_multi_asset} doesn't have policy: {p}")
            new_multi_asset[p] -= other[p]
        return new_multi_asset


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
