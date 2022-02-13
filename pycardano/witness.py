"""Transaction witness."""

from dataclasses import dataclass, field
from typing import Any, List

from pycardano.key import VerificationKey
from pycardano.nativescript import NativeScript
from pycardano.serialization import (
    ArrayCBORSerializable,
    MapCBORSerializable,
    list_hook,
)

__all__ = ["VerificationKeyWitness", "TransactionWitnessSet"]


@dataclass(repr=False)
class VerificationKeyWitness(ArrayCBORSerializable):
    vkey: VerificationKey
    signature: bytes


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

    # TODO: Add plutus script support
    plutus_script: List[Any] = field(
        default=None, metadata={"optional": True, "key": 3}
    )

    plutus_data: List[Any] = field(default=None, metadata={"optional": True, "key": 4})

    redeemer: List[Any] = field(default=None, metadata={"optional": True, "key": 5})
