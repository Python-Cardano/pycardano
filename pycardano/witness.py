"""Transaction witness."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Optional, Type, Union

from pprintpp import pformat

from pycardano.key import ExtendedVerificationKey, VerificationKey
from pycardano.nativescript import NativeScript
from pycardano.plutus import PlutusV1Script, PlutusV2Script, PlutusV3Script, Redeemers
from pycardano.serialization import (
    ArrayCBORSerializable,
    IndefiniteList,
    MapCBORSerializable,
    NonEmptyOrderedSet,
    limit_primitive_type,
)

__all__ = ["VerificationKeyWitness", "TransactionWitnessSet"]


@dataclass(repr=False)
class VerificationKeyWitness(ArrayCBORSerializable):
    vkey: Union[VerificationKey, ExtendedVerificationKey]
    signature: bytes

    @property
    def json_type(self) -> str:
        return "TxWitness ConwayEra"

    @property
    def json_description(self) -> str:
        return "Key Witness ShelleyEra"

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

    def to_shallow_primitive(self) -> Union[list, tuple]:
        """Convert to a shallow primitive representation."""
        return [self.vkey.to_primitive(), self.signature]

    def __eq__(self, other):
        if not isinstance(other, VerificationKeyWitness):
            return False
        else:
            return (
                self.vkey.payload == other.vkey.payload
                and self.signature == other.signature
            )

    def __repr__(self):
        fields = {
            "vkey": self.vkey.payload.hex(),
            "signature": self.signature.hex(),
        }
        return pformat(fields, indent=2)


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

    plutus_data: Optional[Union[List[Any], IndefiniteList, NonEmptyOrderedSet[Any]]] = (
        field(
            default=None,
            metadata={"optional": True, "key": 4},
        )
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

    def convert_to_latest_spec(self):
        # Convert lists to NonEmptyOrderedSet for fields that should use NonEmptyOrderedSet
        if isinstance(self.vkey_witnesses, list):
            self.vkey_witnesses = NonEmptyOrderedSet(self.vkey_witnesses)
        if isinstance(self.native_scripts, list):
            self.native_scripts = NonEmptyOrderedSet(self.native_scripts)
        if isinstance(self.plutus_data, list) and not isinstance(
            self.plutus_data, NonEmptyOrderedSet
        ):
            self.plutus_data = NonEmptyOrderedSet(list(self.plutus_data))
        if isinstance(self.plutus_v1_script, list):
            self.plutus_v1_script = NonEmptyOrderedSet(self.plutus_v1_script)
        if isinstance(self.plutus_v2_script, list):
            self.plutus_v2_script = NonEmptyOrderedSet(self.plutus_v2_script)
        if isinstance(self.plutus_v3_script, list):
            self.plutus_v3_script = NonEmptyOrderedSet(self.plutus_v3_script)

    def is_empty(self) -> bool:
        """Check if the witness set is empty."""
        return (
            not self.vkey_witnesses
            and not self.native_scripts
            and not self.bootstrap_witness
            and not self.plutus_v1_script
            and not self.plutus_data
            and not self.redeemer
            and not self.plutus_v2_script
            and not self.plutus_v3_script
        )
