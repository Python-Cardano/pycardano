"""Definitions of transaction-related data types."""

from __future__ import annotations

from dataclasses import dataclass, field
from pprint import pformat
from typing import Any, Callable, List, Union

from nacl.encoding import RawEncoder
from nacl.hash import blake2b
from typeguard import typechecked

from pycardano.address import Address
from pycardano.exception import InvalidOperationException
from pycardano.hash import (
    TRANSACTION_HASH_SIZE,
    AuxiliaryDataHash,
    ConstrainedBytes,
    DatumHash,
    ScriptHash,
    TransactionId,
    VerificationKeyHash,
)
from pycardano.metadata import AuxiliaryData
from pycardano.network import Network
from pycardano.serialization import (
    ArrayCBORSerializable,
    DictCBORSerializable,
    MapCBORSerializable,
    list_hook,
)
from pycardano.witness import TransactionWitnessSet

__all__ = [
    "TransactionInput",
    "AssetName",
    "Asset",
    "MultiAsset",
    "Value",
    "TransactionOutput",
    "UTxO",
    "TransactionBody",
    "Transaction",
]


@dataclass(repr=False)
class TransactionInput(ArrayCBORSerializable):
    transaction_id: TransactionId

    index: int


class AssetName(ConstrainedBytes):
    MAX_SIZE = 32

    def __repr__(self):
        return f"AssetName({self.payload})"


@typechecked
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

    def __iadd__(self, other: Asset) -> Asset:
        new_item = self + other
        self.update(new_item)
        return self

    def __sub__(self, other: Asset) -> Asset:
        new_asset = self.copy()
        for n in other:
            if n not in new_asset:
                raise InvalidOperationException(
                    f"Asset: {new_asset} does not have asset with name: {n}"
                )
            # According to ledger rule, the value of an asset could be negative, so we don't check the value here and
            # will leave the check to users when necessary.
            # https://github.com/input-output-hk/cardano-ledger/blob/master/eras/alonzo/test-suite/cddl-files/alonzo.cddl#L378
            new_asset[n] -= other[n]
        return new_asset

    def __eq__(self, other):
        if not isinstance(other, Asset):
            return False
        else:
            if len(self) != len(other):
                return False
            for n in self:
                if n not in other or self[n] != other[n]:
                    return False
            return True

    def __le__(self, other: Asset) -> bool:
        for n in self:
            if n not in other or self[n] > other[n]:
                return False
        return True


@typechecked
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

    def __iadd__(self, other):
        new_item = self + other
        self.update(new_item)
        return self

    def __sub__(self, other: MultiAsset) -> MultiAsset:
        new_multi_asset = self.copy()
        for p in other:
            if p not in new_multi_asset:
                raise InvalidOperationException(
                    f"MultiAsset: {new_multi_asset} doesn't have policy: {p}"
                )
            new_multi_asset[p] -= other[p]
        return new_multi_asset

    def __eq__(self, other):
        if not isinstance(other, MultiAsset):
            return False
        else:
            if len(self) != len(other):
                return False
            for p in self:
                if p not in other or self[p] != other[p]:
                    return False
            return True

    def __le__(self, other: MultiAsset):
        for p in self:
            if p not in other or not self[p] <= other[p]:
                return False
        return True

    def filter(
        self, criteria=Callable[[ScriptHash, AssetName, int], bool]
    ) -> MultiAsset:
        """Filter items by criteria.

        Args:
            criteria: A function that takes in three input arguments (policy_id, asset_name, amount) and returns a
                bool. If returned value is True, then the asset will be kept, otherwise discarded.

        Returns:
            A new filtered MultiAsset object.
        """
        new_multi_asset = MultiAsset()

        for p in self:
            for n in self[p]:
                if criteria(p, n, self[p][n]):
                    if p not in new_multi_asset:
                        new_multi_asset[p] = Asset()
                    new_multi_asset[p][n] = self[p][n]

        return new_multi_asset


@typechecked
@dataclass(repr=False)
class Value(ArrayCBORSerializable):
    coin: int = 0
    """Amount of ADA"""

    multi_asset: MultiAsset = field(default_factory=MultiAsset)
    """Multi-assets associated with the UTxO"""

    def union(self, other: Union[Value, int]) -> Value:
        return self + other

    def __add__(self, other: Union[Value, int]):
        if isinstance(other, int):
            other = Value(other)
        return Value(self.coin + other.coin, self.multi_asset + other.multi_asset)

    def __iadd__(self, other: Union[Value, int]):
        new_item = self + other
        self.coin = new_item.coin
        self.multi_asset = new_item.multi_asset
        return self

    def __sub__(self, other: Union[Value, int]) -> Value:
        if isinstance(other, int):
            other = Value(other)
        return Value(self.coin - other.coin, self.multi_asset - other.multi_asset)

    def __eq__(self, other):
        if not isinstance(other, (Value, int)):
            return False
        else:
            if isinstance(other, int):
                other = Value(other)
            return self.coin == other.coin and self.multi_asset == other.multi_asset

    def __le__(self, other: Union[Value, int]):
        if isinstance(other, int):
            other = Value(other)
        return self.coin <= other.coin and self.multi_asset <= other.multi_asset

    def __lt__(self, other: Union[Value, int]):
        return self <= other and self != other


@dataclass(repr=False)
class TransactionOutput(ArrayCBORSerializable):
    address: Address

    amount: Union[int, Value]

    datum_hash: DatumHash = field(default=None, metadata={"optional": True})

    @property
    def lovelace(self) -> int:
        if isinstance(self.amount, int):
            return self.amount
        else:
            return self.amount.coin


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
        metadata={"key": 0, "object_hook": list_hook(TransactionInput)},
    )

    outputs: List[TransactionOutput] = field(
        default_factory=list,
        metadata={"key": 1, "object_hook": list_hook(TransactionOutput)},
    )

    fee: int = field(default=0, metadata={"key": 2})

    ttl: int = field(default=None, metadata={"key": 3, "optional": True})

    # TODO: Add certificate support
    certificates: Any = field(default=None, metadata={"key": 4, "optional": True})

    # TODO: Add reward withdraw support
    withdraws: Any = field(default=None, metadata={"key": 5, "optional": True})

    # TODO: Add proposal update support
    update: Any = field(default=None, metadata={"key": 6, "optional": True})

    auxiliary_data_hash: AuxiliaryDataHash = field(
        default=None, metadata={"key": 7, "optional": True}
    )

    validity_start: int = field(default=None, metadata={"key": 8, "optional": True})

    mint: MultiAsset = field(default=None, metadata={"key": 9, "optional": True})

    script_data_hash: ScriptHash = field(
        default=None, metadata={"key": 11, "optional": True}
    )

    collateral: List[TransactionInput] = field(
        default=None,
        metadata={
            "key": 13,
            "optional": True,
            "object_hook": list_hook(TransactionInput),
        },
    )

    required_signers: List[VerificationKeyHash] = field(
        default=None,
        metadata={
            "key": 14,
            "optional": True,
            "object_hook": list_hook(VerificationKeyHash),
        },
    )

    network_id: Network = field(default=None, metadata={"key": 15, "optional": True})

    def hash(self) -> bytes:
        return blake2b(
            self.to_cbor(encoding="bytes"), TRANSACTION_HASH_SIZE, encoder=RawEncoder
        )


@dataclass(repr=False)
class Transaction(ArrayCBORSerializable):
    transaction_body: TransactionBody

    transaction_witness_set: TransactionWitnessSet

    valid: bool = True

    auxiliary_data: Union[AuxiliaryData, type(None)] = None
