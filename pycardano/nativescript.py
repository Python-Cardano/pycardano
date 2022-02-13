"""Cardano native script"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, ClassVar, List, Union

from nacl.encoding import RawEncoder
from nacl.hash import blake2b

from pycardano.exception import DeserializeException, InvalidArgumentException
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
    # We need to move TYPE field from last place to the first, in order to follow the protocol.
    field_sorter: ClassVar[Callable[[List], List]] = lambda x: x[-1:] + x[:-1]

    def __post_init__(self):
        if self.TYPE != self.__class__.TYPE:
            raise InvalidArgumentException(
                f"TYPE of {self.__class__} could not be changed!"
            )

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
            if t.TYPE == script_type:
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
    key_hash: VerificationKeyHash

    # Make TYPE optional by placing it after key_hash because we don't want users to pass any value to TYPE.
    TYPE: int = 0


@dataclass
class ScriptAll(NativeScript):
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

    TYPE: int = 1


@dataclass
class ScriptAny(NativeScript):
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

    TYPE: int = 2


@dataclass
class ScriptNofK(NativeScript):
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

    TYPE: int = 3


@dataclass
class InvalidBefore(NativeScript):
    before: int = None

    TYPE: int = 4


@dataclass
class InvalidHereAfter(NativeScript):
    after: int = None

    TYPE: int = 5
