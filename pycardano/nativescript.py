"""Cardano native script"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Union

from nacl.encoding import RawEncoder
from nacl.hash import blake2b

from pycardano.exception import DeserializeException
from pycardano.hash import SCRIPT_HASH_SIZE, ScriptHash, VerificationKeyHash
from pycardano.serialization import ArrayCBORSerializable, Primitive, list_hook

__all__ = [
    "NativeScript",
    "ScriptPubkey",
    "ScriptAll",
    "ScriptAny",
    "ScriptNofK",
    "InvalidBefore",
    "InvalidHereAfter",
]


@dataclass
class NativeScript(ArrayCBORSerializable):
    @classmethod
    def from_primitive(
        cls: NativeScript, value: Primitive
    ) -> Union[
        ScriptPubkey, ScriptAll, ScriptAny, ScriptNofK, InvalidBefore, InvalidHereAfter
    ]:
        script_type = value[0]
        for t in [
            ScriptPubkey,
            ScriptAll,
            ScriptAny,
            ScriptNofK,
            InvalidBefore,
            InvalidHereAfter,
        ]:
            if t._TYPE == script_type:
                return super(NativeScript, t).from_primitive(value[1:])
        else:
            raise DeserializeException(f"Unknown script type indicator: {script_type}")

    def hash(self) -> ScriptHash:
        return ScriptHash(
            blake2b(
                bytes(1) + self.to_cbor("bytes"), SCRIPT_HASH_SIZE, encoder=RawEncoder
            )
        )


@dataclass
class ScriptPubkey(NativeScript):
    _TYPE: int = field(default=0, init=False)

    key_hash: VerificationKeyHash


@dataclass
class ScriptAll(NativeScript):
    _TYPE: int = field(default=1, init=False)

    native_scripts: List[
        Union[
            ScriptPubkey,
            ScriptAll,
            ScriptAny,
            ScriptNofK,
            InvalidBefore,
            InvalidHereAfter,
        ]
    ] = field(metadata={"object_hook": list_hook(NativeScript)})


@dataclass
class ScriptAny(NativeScript):
    _TYPE: int = field(default=2, init=False)

    native_scripts: List[
        Union[
            ScriptPubkey,
            ScriptAll,
            ScriptAny,
            ScriptNofK,
            InvalidBefore,
            InvalidHereAfter,
        ]
    ] = field(metadata={"object_hook": list_hook(NativeScript)})


@dataclass
class ScriptNofK(NativeScript):
    _TYPE: int = field(default=3, init=False)

    n: int

    native_scripts: List[
        Union[
            ScriptPubkey,
            ScriptAll,
            ScriptAny,
            ScriptNofK,
            InvalidBefore,
            InvalidHereAfter,
        ]
    ] = field(metadata={"object_hook": list_hook(NativeScript)})


@dataclass
class InvalidBefore(NativeScript):
    _TYPE: int = field(default=4, init=False)

    before: int = None


@dataclass
class InvalidHereAfter(NativeScript):
    _TYPE: int = field(default=5, init=False)

    after: int = None
