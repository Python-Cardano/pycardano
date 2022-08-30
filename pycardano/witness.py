"""Transaction witness."""

from dataclasses import dataclass, field
from typing import Any, List, Union

from pycardano.key import ExtendedVerificationKey, VerificationKey
from pycardano.nativescript import NativeScript
from pycardano.plutus import RawPlutusData, Redeemer
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
    vkey_witnesses: List[VerificationKeyWitness] = field(
        default=None,
        metadata={
            "optional": True,
            "key": 0,
            "object_hook": list_hook(VerificationKeyWitness),
        },
    )

    native_scripts: List[NativeScript] = field(
        default=None,
        metadata={"optional": True, "key": 1, "object_hook": list_hook(NativeScript)},
    )

    # TODO: Add bootstrap witness (byron) support
    bootstrap_witness: List[Any] = field(
        default=None, metadata={"optional": True, "key": 2}
    )

    plutus_v1_script: List[bytes] = field(
        default=None, metadata={"optional": True, "key": 3}
    )

    plutus_v2_script: List[bytes] = field(
        default=None, metadata={"optional": True, "key": 6}
    )

    plutus_data: List[Any] = field(
        default=None,
        metadata={"optional": True, "key": 4, "object_hook": list_hook(RawPlutusData)},
    )

    redeemer: List[Redeemer] = field(
        default=None,
        metadata={"optional": True, "key": 5, "object_hook": list_hook(Redeemer)},
    )
