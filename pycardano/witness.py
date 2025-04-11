"""Transaction witness."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Optional, Type, Union

from pycardano.key import ExtendedVerificationKey, VerificationKey
from pycardano.nativescript import NativeScript
from pycardano.plutus import (
    PlutusV1Script,
    PlutusV2Script,
    PlutusV3Script,
    RawPlutusData,
    Redeemers,
)
from pycardano.serialization import (
    ArrayCBORSerializable,
    MapCBORSerializable,
    NonEmptyOrderedSet,
    limit_primitive_type,
    list_hook,
)

__all__ = ["VerificationKeyWitness", "TransactionWitnessSet"]


@dataclass(repr=False)
class VerificationKeyWitness(ArrayCBORSerializable):
    vkey: Union[VerificationKey, ExtendedVerificationKey]
    signature: bytes

    def __post_init__(self):
        # When vkey is in extended format, we need to convert it to non-extended, so it can match the
        # key hash of the input address we are trying to spend.
        if isinstance(self.vkey, ExtendedVerificationKey):
            self.vkey = self.vkey.to_non_extended()

    @classmethod
    @limit_primitive_type(list, tuple)
    def from_primitive(
        cls: Type[VerificationKeyWitness], values: Union[list, tuple]
    ) -> VerificationKeyWitness:
        return cls(
            vkey=VerificationKey.from_primitive(values[0]),
            signature=values[1],
        )


@dataclass(repr=False)
class TransactionWitnessSet(MapCBORSerializable):
    vkey_witnesses: Optional[
        Union[List[VerificationKeyWitness], NonEmptyOrderedSet[VerificationKeyWitness]]
    ] = field(
        default=None,
        metadata={
            "key": 0,
            "optional": True,
        },
    )

    native_scripts: Optional[
        Union[List[NativeScript], NonEmptyOrderedSet[NativeScript]]
    ] = field(
        default=None,
        metadata={
            "key": 1,
            "optional": True,
        },
    )

    # TODO: Add bootstrap witness (byron) support
    bootstrap_witness: Optional[List[Any]] = field(
        default=None, metadata={"optional": True, "key": 2}
    )

    plutus_v1_script: Optional[
        Union[List[PlutusV1Script], NonEmptyOrderedSet[PlutusV1Script]]
    ] = field(
        default=None,
        metadata={
            "key": 3,
            "optional": True,
        },
    )

    plutus_data: Optional[List[Any]] = field(
        default=None,
        metadata={"optional": True, "key": 4, "object_hook": list_hook(RawPlutusData)},
    )

    redeemer: Optional[Redeemers] = field(
        default=None,
        metadata={"optional": True, "key": 5},
    )

    plutus_v2_script: Optional[
        Union[List[PlutusV2Script], NonEmptyOrderedSet[PlutusV2Script]]
    ] = field(
        default=None,
        metadata={
            "key": 6,
            "optional": True,
        },
    )

    plutus_v3_script: Optional[
        Union[List[PlutusV3Script], NonEmptyOrderedSet[PlutusV3Script]]
    ] = field(
        default=None,
        metadata={
            "key": 7,
            "optional": True,
        },
    )

    def __post_init__(self):
        # Convert lists to NonEmptyOrderedSet for fields that should use NonEmptyOrderedSet
        if isinstance(self.vkey_witnesses, list):
            self.vkey_witnesses = NonEmptyOrderedSet(self.vkey_witnesses)
        if isinstance(self.native_scripts, list):
            self.native_scripts = NonEmptyOrderedSet(self.native_scripts)
        if isinstance(self.plutus_v1_script, list):
            self.plutus_v1_script = NonEmptyOrderedSet(self.plutus_v1_script)
        if isinstance(self.plutus_v2_script, list):
            self.plutus_v2_script = NonEmptyOrderedSet(self.plutus_v2_script)
        if isinstance(self.plutus_v3_script, list):
            self.plutus_v3_script = NonEmptyOrderedSet(self.plutus_v3_script)
