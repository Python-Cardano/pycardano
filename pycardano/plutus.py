"""Plutus related classes and functions."""

from __future__ import annotations

import inspect
from dataclasses import dataclass, fields
from typing import ClassVar, Optional, Type, TypeVar

from cbor2 import CBORTag

from pycardano.exception import DeserializeException
from pycardano.serialization import ArrayCBORSerializable, IndefiniteList

__all__ = ["PlutusData"]

PData = TypeVar("PData", bound="PlutusData")


def get_tag(constr_id: int) -> Optional[int]:
    if 0 <= constr_id < 7:
        return 121 + constr_id
    elif 7 <= constr_id < 128:
        return 1280 + (constr_id - 7)
    else:
        return None


@dataclass(repr=False)
class PlutusData(ArrayCBORSerializable):
    """
    PlutusData is the base class of all Datum and Redeemer type. It is not required to use this class in order to
    interact with Plutus script. However, inheriting datum(s) and redeemers in a PlutusData class will reduce the
    complexity of serialization and deserialization tremendously.

    Examples:

        >>> @dataclass
        ... class Test(PlutusData):
        ...     CONSTR_ID = 1
        ...     a: int
        ...     b: bytes
        >>> test = Test(123, b"321")
        >>> test.to_cbor()
        'd87a9f187b43333231ff'
        >>> assert test == Test.from_cbor("d87a9f187b43333231ff")
    """

    CONSTR_ID: ClassVar[int] = 0
    """Constructor ID of this plutus data.
       It is primarily used by Plutus core to reconstruct a data structure from serialized CBOR bytes."""

    def __post_init__(self):
        valid_types = (PlutusData, dict, list, int, bytes)
        for f in fields(self):
            if inspect.isclass(f.type) and not issubclass(f.type, valid_types):
                raise TypeError(
                    f"Invalid field type: {f.type}. A field in PlutusData should be one of {valid_types}"
                )

    def to_shallow_primitive(self) -> CBORTag:
        primitives = super().to_shallow_primitive()
        if primitives:
            primitives = IndefiniteList(primitives)
        tag = get_tag(self.CONSTR_ID)
        if tag:
            return CBORTag(tag, primitives)
        else:
            return CBORTag(102, [self.CONSTR_ID, primitives])

    @classmethod
    def from_primitive(cls: Type[PData], value: CBORTag) -> PData:
        if value.tag == 102:
            tag = value.value[0]
            if tag != cls.CONSTR_ID:
                raise DeserializeException(
                    f"Unexpected constructor ID for {cls}. Expect {cls.CONSTR_ID}, got "
                    f"{tag} instead."
                )
            if len(value.value) != 2:
                raise DeserializeException(
                    f"Expect the length of value to be exactly 2, got {len(value.value)} instead."
                )
            return super(PlutusData, cls).from_primitive(value.value[1])
        else:
            expected_tag = get_tag(cls.CONSTR_ID)
            if expected_tag != value.tag:
                raise DeserializeException(
                    f"Unexpected constructor ID for {cls}. Expect {expected_tag}, got "
                    f"{value.tag} instead."
                )
            return super(PlutusData, cls).from_primitive(value.value)
