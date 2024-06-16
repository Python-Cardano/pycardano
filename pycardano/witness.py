"""Transaction witness."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Optional, Type, Union

from pycardano.key import ExtendedVerificationKey, VerificationKey
from pycardano.nativescript import NativeScript
from pycardano.plutus import PlutusV1Script, PlutusV2Script, RawPlutusData, Redeemer
from pycardano.serialization import (
    ArrayCBORSerializable,
    MapCBORSerializable,
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
    @limit_primitive_type(list)
    def from_primitive(
        cls: Type[VerificationKeyWitness], values: Union[list, tuple]
    ) -> VerificationKeyWitness:
        return cls(
            vkey=VerificationKey.from_primitive(values[0]),
            signature=values[1],
        )


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

    @classmethod
    @limit_primitive_type(dict, list)
    def from_primitive(
        cls: Type[TransactionWitnessSet], values: Union[dict, list, tuple]
    ) -> TransactionWitnessSet | None:
        def _get_vkey_witnesses(data: Any):
            return (
                [VerificationKeyWitness.from_primitive(witness) for witness in data]
                if data
                else None
            )

        def _get_native_scripts(data: Any):
            return (
                [NativeScript.from_primitive(script) for script in data]
                if data
                else None
            )

        def _get_plutus_v1_scripts(data: Any):
            return [PlutusV1Script(script) for script in data] if data else None

        def _get_plutus_v2_scripts(data: Any):
            return [PlutusV2Script(script) for script in data] if data else None

        def _get_redeemers(data: Any):
            return (
                [Redeemer.from_primitive(redeemer) for redeemer in data]
                if data
                else None
            )

        def _get_cls(data: Any):
            return cls(
                vkey_witnesses=_get_vkey_witnesses(data.get(0)),
                native_scripts=_get_native_scripts(data.get(1)),
                bootstrap_witness=data.get(2),
                plutus_v1_script=_get_plutus_v1_scripts(data.get(3)),
                plutus_data=data.get(4),
                redeemer=_get_redeemers(data.get(5)),
                plutus_v2_script=_get_plutus_v2_scripts(data.get(6)),
            )

        if isinstance(values, dict):
            return _get_cls(values)
        elif isinstance(values, list):
            # TODO: May need to handle this differently
            values = dict(values)
            return _get_cls(values)
        return None
