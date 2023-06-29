"""Transaction witness."""

from dataclasses import dataclass, field
from typing import Any, List, Optional, Union

from pycardano.key import ExtendedVerificationKey, VerificationKey
from pycardano.nativescript import NativeScript
from pycardano.plutus import PlutusV1Script, PlutusV2Script, RawPlutusData, Redeemer
from pycardano.serialization import (
    ArrayCBORSerializable,
    MapCBORSerializable,
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


@dataclass(repr=False)
class TransactionWitnessSet(MapCBORSerializable):
    vkey_witnesses: Optional[List[VerificationKeyWitness]] = field(
        default=None,
        metadata={
            "optional": True,
            "key": 0,
            "object_hook": list_hook(VerificationKeyWitness),
        },
    )

    native_scripts: Optional[List[NativeScript]] = field(
        default=None,
        metadata={"optional": True, "key": 1, "object_hook": list_hook(NativeScript)},
    )

    # TODO: Add bootstrap witness (byron) support
    bootstrap_witness: Optional[List[Any]] = field(
        default=None, metadata={"optional": True, "key": 2}
    )

    plutus_v1_script: Optional[List[PlutusV1Script]] = field(
        default=None, metadata={"optional": True, "key": 3}
    )

    plutus_v2_script: Optional[List[PlutusV2Script]] = field(
        default=None, metadata={"optional": True, "key": 6}
    )

    plutus_data: Optional[List[Any]] = field(
        default=None,
        metadata={"optional": True, "key": 4, "object_hook": list_hook(RawPlutusData)},
    )

    redeemer: Optional[List[Redeemer]] = field(
        default=None,
        metadata={"optional": True, "key": 5, "object_hook": list_hook(Redeemer)},
    )
