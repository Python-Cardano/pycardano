"""Definitions of transaction-related data types."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Callable, List, Optional, Type, Union

from cbor2 import CBORTag
from nacl.encoding import RawEncoder
from nacl.hash import blake2b
from pprintpp import pformat

from pycardano.address import Address
from pycardano.cbor import cbor2
from pycardano.certificate import Certificate
from pycardano.exception import InvalidDataException
from pycardano.governance import ProposalProcedure, VotingProcedures
from pycardano.hash import (
    TRANSACTION_HASH_SIZE,
    AuxiliaryDataHash,
    ConstrainedBytes,
    DatumHash,
    ScriptDataHash,
    ScriptHash,
    TransactionId,
    VerificationKeyHash,
)
from pycardano.metadata import AuxiliaryData
from pycardano.nativescript import NativeScript
from pycardano.network import Network
from pycardano.plutus import Datum, PlutusScript, RawPlutusData
from pycardano.serialization import (
    ArrayCBORSerializable,
    CBORSerializable,
    DictBase,
    DictCBORSerializable,
    MapCBORSerializable,
    NonEmptyOrderedSet,
    OrderedSet,
    Primitive,
    default_encoder,
    limit_primitive_type,
    list_hook,
)
from pycardano.types import typechecked
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
    "Withdrawals",
]

_MAX_INT64 = (1 << 63) - 1
_MIN_INT64 = -(1 << 63)


@dataclass(repr=False)
class TransactionInput(ArrayCBORSerializable):
    transaction_id: TransactionId

    index: int

    def __hash__(self):
        return hash(str(self.transaction_id) + str(self.index))


class AssetName(ConstrainedBytes):
    MAX_SIZE = 32

    def __repr__(self):
        return f"AssetName({self.payload})"


@typechecked
class Asset(DictCBORSerializable):
    KEY_TYPE = AssetName

    VALUE_TYPE = int

    def normalize(self) -> Asset:
        """Normalize the Asset by removing zero values."""
        for k, v in list(self.items()):
            if v == 0:
                self.pop(k)

        return self

    def union(self, other: Asset) -> Asset:
        return self + other

    def __add__(self, other: Asset) -> Asset:
        new_asset = deepcopy(self)
        for n in other:
            new_asset[n] = new_asset.get(n, 0) + other[n]
        return new_asset.normalize()

    def __iadd__(self, other: Asset) -> Asset:
        new_item = self + other
        self.data = new_item.data  # type: ignore[has-type]
        return self.normalize()

    def __sub__(self, other: Asset) -> Asset:
        new_asset = deepcopy(self)
        for n in other:
            new_asset[n] = new_asset.get(n, 0) - other[n]
        return new_asset.normalize()

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

    def __lt__(self, other: Asset):
        return self <= other and self != other

    def __ge__(self, other: Asset) -> bool:
        for n in other:
            if n not in self or self[n] < other[n]:
                return False
        return True

    def __gt__(self, other: Asset) -> bool:
        return self >= other and self != other

    @classmethod
    @limit_primitive_type(dict)
    def from_primitive(cls: Type[DictBase], value: dict) -> DictBase:
        res = super().from_primitive(value)
        # pop zero values
        for n, v in list(res.items()):
            if v == 0:
                res.pop(n)
        return res

    def to_shallow_primitive(self) -> dict:
        x = deepcopy(self).normalize()
        return super(self.__class__, x).to_shallow_primitive()


@typechecked
class MultiAsset(DictCBORSerializable):
    KEY_TYPE = ScriptHash

    VALUE_TYPE = Asset

    def union(self, other: MultiAsset) -> MultiAsset:
        return self + other

    def normalize(self) -> MultiAsset:
        """Normalize the MultiAsset by removing zero values."""
        for k, v in list(self.items()):
            v.normalize()
            if len(v) == 0:
                self.pop(k)
        return self

    def __add__(self, other):
        new_multi_asset = deepcopy(self)
        for p in other:
            new_multi_asset[p] = new_multi_asset.get(p, Asset()) + other[p]
        return new_multi_asset.normalize()

    def __iadd__(self, other):
        new_item = self + other
        self.data = new_item.data
        return self.normalize()

    def __sub__(self, other: MultiAsset) -> MultiAsset:
        new_multi_asset = deepcopy(self)
        for p in other:
            new_multi_asset[p] = new_multi_asset.get(p, Asset()) - other[p]
        return new_multi_asset.normalize()

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

    def __ge__(self, other: MultiAsset) -> bool:
        for n in other:
            if n not in self:
                return False
            if not self[n] >= other[n]:
                return False
        return True

    def __gt__(self, other: MultiAsset) -> bool:
        return self >= other and self != other

    def __le__(self, other: MultiAsset):
        for p in self:
            if p not in other:
                return False
            if not self[p] <= other[p]:
                return False
        return True

    def __lt__(self, other: MultiAsset):
        return self <= other and self != other

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

    def count(self, criteria=Callable[[ScriptHash, AssetName, int], bool]) -> int:
        """Count number of distinct assets that satisfy a certain criteria.

        Args:
            criteria: A function that takes in three input arguments (policy_id, asset_name, amount) and returns a
                bool.

        Returns:
            int: Total number of distinct assets that satisfy the criteria.
        """
        count = 0
        for p in self:
            for n in self[p]:
                if criteria(p, n, self[p][n]):
                    count += 1

        return count

    @classmethod
    @limit_primitive_type(dict)
    def from_primitive(cls: Type[DictBase], value: dict) -> DictBase:
        res = super().from_primitive(value)
        # pop empty values
        for n, v in list(res.items()):
            if not v:
                res.pop(n)
        return res

    def to_shallow_primitive(self) -> dict:
        x = deepcopy(self).normalize()
        return super(self.__class__, x).to_shallow_primitive()


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

    def __ge__(self, other: Union[Value, int]):
        if isinstance(other, int):
            other = Value(other)
        return self.coin >= other.coin and self.multi_asset >= other.multi_asset

    def __gt__(self, other: Union[Value, int]):
        return self >= other and self != other

    def to_shallow_primitive(self):
        if self.multi_asset:
            return super().to_shallow_primitive()
        else:
            return self.coin


@dataclass(repr=False)
class _Script(ArrayCBORSerializable):
    _TYPE: int = field(init=False, default=0)

    script: Union[NativeScript, PlutusScript]

    def __post_init__(self):
        if isinstance(self.script, NativeScript):
            self._TYPE = 0
        elif isinstance(self.script, PlutusScript):
            self._TYPE = self.script.version

    @classmethod
    def from_primitive(
        cls: Type[_Script], values: List[Primitive], type_args: Optional[tuple] = None
    ) -> _Script:
        if values[0] == 0:
            return cls(NativeScript.from_primitive(values[1]))
        assert isinstance(values[1], bytes)
        assert isinstance(values[0], int)
        return cls(PlutusScript.from_version(values[0], values[1]))


@dataclass(repr=False)
class _DatumOption(ArrayCBORSerializable):
    _TYPE: int = field(init=False, default=0)

    datum: Union[DatumHash, Any]

    def __post_init__(self):
        if isinstance(self.datum, DatumHash):
            self._TYPE = 0
        else:
            self._TYPE = 1

    def to_shallow_primitive(self) -> Primitive:
        data: Union[CBORTag, DatumHash]
        if self._TYPE == 1:
            data = CBORTag(24, cbor2.dumps(self.datum, default=default_encoder))
        else:
            data = self.datum
        return [self._TYPE, data]

    @classmethod
    def from_primitive(
        cls: Type[_DatumOption],
        values: List[Primitive],
        type_args: Optional[tuple] = None,
    ) -> _DatumOption:
        if values[0] == 0:
            assert isinstance(values[1], bytes)
            return _DatumOption(DatumHash(values[1]))
        else:
            assert isinstance(values[1], CBORTag)
            v = cbor2.loads(values[1].value)
            if isinstance(v, CBORTag):
                return _DatumOption(RawPlutusData.from_primitive(v))
            else:
                return _DatumOption(v)


@dataclass(repr=False)
class _ScriptRef(CBORSerializable):
    script: _Script

    def to_primitive(self) -> Primitive:
        return CBORTag(24, cbor2.dumps(self.script, default=default_encoder))

    @classmethod
    def from_primitive(
        cls: Type[_ScriptRef], value: List[Primitive], type_args: Optional[tuple] = None
    ) -> _ScriptRef:
        assert isinstance(value, CBORTag)
        return cls(_Script.from_primitive(cbor2.loads(value.value)))


@dataclass(repr=False)
class _TransactionOutputPostAlonzo(MapCBORSerializable):
    address: Address = field(metadata={"key": 0})

    amount: Union[int, Value] = field(metadata={"key": 1})

    datum: Optional[_DatumOption] = field(
        default=None, metadata={"key": 2, "optional": True}
    )

    script_ref: Optional[_ScriptRef] = field(
        default=None, metadata={"key": 3, "optional": True}
    )

    @property
    def script(
        self,
    ) -> Optional[Union[NativeScript, PlutusScript]]:
        if self.script_ref:
            return self.script_ref.script.script
        else:
            return None


@dataclass(repr=False)
class _TransactionOutputLegacy(ArrayCBORSerializable):
    address: Address

    amount: Union[int, Value]

    datum_hash: Optional[DatumHash] = field(default=None, metadata={"optional": True})


@dataclass(repr=False)
class TransactionOutput(CBORSerializable):
    address: Address

    amount: Union[Value]

    datum_hash: Optional[DatumHash] = None

    datum: Optional[Datum] = None

    script: Optional[Union[NativeScript, PlutusScript]] = None

    post_alonzo: Optional[bool] = False

    def __post_init__(self):
        if isinstance(self.address, str):
            self.address = Address.from_primitive(self.address)
        if isinstance(self.amount, int):
            self.amount = Value(self.amount)

    def validate(self):
        super().validate()
        if isinstance(self.amount, Value) and (
            self.amount.coin < 0
            or self.amount.multi_asset.count(lambda p, n, v: v < 0) > 0
        ):
            raise InvalidDataException(
                f"Transaction output cannot have negative amount of ADA or "
                f"native asset: \n {self.amount}"
            )

    @property
    def lovelace(self) -> int:
        return self.amount.coin

    def to_primitive(self) -> Primitive:
        if self.datum or self.script or self.post_alonzo:
            datum = (
                _DatumOption(self.datum_hash or self.datum)
                if self.datum is not None or self.datum_hash is not None
                else None
            )
            script_ref = (
                _ScriptRef(_Script(self.script)) if self.script is not None else None
            )
            return _TransactionOutputPostAlonzo(
                self.address, self.amount, datum, script_ref
            ).to_primitive()
        else:
            return _TransactionOutputLegacy(
                self.address, self.amount, self.datum_hash
            ).to_primitive()

    @classmethod
    def from_primitive(
        cls: Type[TransactionOutput],
        value: List[Primitive],
        type_args: Optional[tuple] = None,
    ) -> TransactionOutput:
        if isinstance(value, list):
            output = _TransactionOutputLegacy.from_primitive(value)
            return cls(output.address, output.amount, datum_hash=output.datum_hash)
        else:
            output = _TransactionOutputPostAlonzo.from_primitive(value)
            datum = output.datum.datum if output.datum else None
            if isinstance(datum, DatumHash):
                return cls(
                    output.address,
                    output.amount,
                    datum_hash=datum,
                    script=output.script,
                )
            else:
                return cls(
                    output.address,
                    output.amount,
                    datum=datum,
                    script=output.script,
                )


@dataclass(repr=False)
class UTxO(ArrayCBORSerializable):
    input: TransactionInput

    output: TransactionOutput

    def __repr__(self):
        return pformat(vars(self))

    def __hash__(self):
        return hash(blake2b(self.input.to_cbor() + self.output.to_cbor(), 32))


class Withdrawals(DictCBORSerializable):
    """A disctionary of reward addresses to reward withdrawal amount.

    Key is address bytes, value is an integer.

    Examples:

        >>> address = Address.from_primitive("stake_test1upyz3gk6mw5he20apnwfn96cn9rscgvmmsxc9r86dh0k66gswf59n")
        >>> Withdrawals({bytes(address): 1000000}) # doctest: +NORMALIZE_WHITESPACE
        {b'\\xe0H(\\xa2\\xda\\xdb\\xa9|\\xa9\\xfd\\x0c\\xdc\\x99\\x97X\\x99G\\x0c!\\x9b\\xdc\\r\\x82\\x8c\\xfam\\xdfmi':
        1000000}
    """

    KEY_TYPE = bytes

    VALUE_TYPE = int


@dataclass(repr=False)
class TransactionBody(MapCBORSerializable):
    inputs: Union[List[TransactionInput], OrderedSet[TransactionInput]] = field(
        default_factory=OrderedSet,
        metadata={"key": 0},
    )

    outputs: List[TransactionOutput] = field(
        default_factory=list,
        metadata={"key": 1, "object_hook": list_hook(TransactionOutput)},
    )

    fee: int = field(default=0, metadata={"key": 2})

    ttl: Optional[int] = field(default=None, metadata={"key": 3, "optional": True})

    certificates: Optional[
        Union[List[Certificate], NonEmptyOrderedSet[Certificate]]
    ] = field(
        default=None,
        metadata={
            "key": 4,
            "optional": True,
        },
    )

    withdraws: Optional[Withdrawals] = field(
        default=None, metadata={"key": 5, "optional": True}
    )

    update: Any = field(default=None, metadata={"key": 6, "optional": True})

    auxiliary_data_hash: Optional[AuxiliaryDataHash] = field(
        default=None, metadata={"key": 7, "optional": True}
    )

    validity_start: Optional[int] = field(
        default=None, metadata={"key": 8, "optional": True}
    )

    mint: Optional[MultiAsset] = field(
        default=None, metadata={"key": 9, "optional": True}
    )

    script_data_hash: Optional[ScriptDataHash] = field(
        default=None, metadata={"key": 11, "optional": True}
    )

    collateral: Optional[
        Union[List[TransactionInput], NonEmptyOrderedSet[TransactionInput]]
    ] = field(
        default=None,
        metadata={
            "key": 13,
            "optional": True,
        },
    )

    required_signers: Optional[
        Union[List[VerificationKeyHash], NonEmptyOrderedSet[VerificationKeyHash]]
    ] = field(
        default=None,
        metadata={
            "key": 14,
            "optional": True,
        },
    )

    network_id: Optional[Network] = field(
        default=None, metadata={"key": 15, "optional": True}
    )

    collateral_return: Optional[TransactionOutput] = field(
        default=None, metadata={"key": 16, "optional": True}
    )

    total_collateral: Optional[int] = field(
        default=None, metadata={"key": 17, "optional": True}
    )

    reference_inputs: Optional[
        Union[List[TransactionInput], NonEmptyOrderedSet[TransactionInput]]
    ] = field(
        default=None,
        metadata={
            "key": 18,
            "optional": True,
        },
    )

    voting_procedures: Optional[VotingProcedures] = field(
        default=None, metadata={"key": 19, "optional": True}
    )

    proposal_procedures: Optional[NonEmptyOrderedSet[ProposalProcedure]] = field(
        default=None, metadata={"key": 20, "optional": True}
    )

    current_treasury_value: Optional[int] = field(
        default=None, metadata={"key": 21, "optional": True}
    )

    donation: Optional[int] = field(
        default=None, metadata={"key": 22, "optional": True}
    )

    def validate(self):
        if (
            self.mint
            and self.mint.count(lambda p, n, v: v < _MIN_INT64 or v > _MAX_INT64) > 0
        ):
            raise InvalidDataException(
                f"Mint amount must be between {_MIN_INT64} and {_MAX_INT64}. \n Mint amount: {self.mint}"
            )

    def hash(self) -> bytes:
        return blake2b(self.to_cbor(), TRANSACTION_HASH_SIZE, encoder=RawEncoder)  # type: ignore

    @property
    def id(self) -> TransactionId:
        return TransactionId(self.hash())


@dataclass(repr=False)
class Transaction(ArrayCBORSerializable):
    transaction_body: TransactionBody

    transaction_witness_set: TransactionWitnessSet

    valid: Optional[bool] = field(default=True, metadata={"optional": True})

    auxiliary_data: Optional[AuxiliaryData] = None

    @property
    def json_type(self) -> str:
        return (
            "Unwitnessed Tx ConwayEra"
            if self.transaction_witness_set.vkey_witnesses is None
            else "Signed Tx ConwayEra"
        )

    @property
    def json_description(self) -> str:
        return "Ledger Cddl Format"

    @property
    def id(self) -> TransactionId:
        return self.transaction_body.id
