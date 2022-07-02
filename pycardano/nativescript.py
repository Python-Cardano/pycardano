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

    @classmethod
    def from_dict(
        cls: NativeScript, script: dict, top_level: bool = True
    ) -> Union[
        ScriptPubkey, ScriptAll, ScriptAny, ScriptNofK, InvalidBefore, InvalidHereAfter
    ]:

        TYPES = {
            "sig": ScriptPubkey,
            "all": ScriptAll,
            "any": ScriptAny,
            "atLeast": ScriptNofK,
            "after": InvalidBefore,
            "before": InvalidHereAfter,
        }

        if isinstance(script, dict):
            native_script = []

            for key, value in script.items():
                if key == "type":
                    native_script.insert(0, list(TYPES.keys()).index(value))
                elif key == "scripts":
                    native_script.append(cls.from_dict(value, top_level=False))
                else:
                    native_script.append(value)

        elif isinstance(script, list):  # list
            native_script = [cls.from_dict(i, top_level=False) for i in script]

        if not top_level:
            return native_script
        else:
            return super(NativeScript, TYPES[script["type"]]).from_primitive(
                native_script[1:]
            )

    def to_dict(self) -> dict:

        TAGS = [
            "sig",
            "all",
            "any",
            "atLeast",
            "after",
            "before",
        ]

        FIELDS = ["keyHash", "scripts", "scripts", "required", "slot", "slot"]

        script = {}

        for value in self.__dict__.values():
            script["type"] = TAGS[self._TYPE]

            if isinstance(value, list):
                script["scripts"] = [i.to_dict() for i in value]

            else:
                if isinstance(value, int):
                    script[FIELDS[self._TYPE]] = value
                else:
                    script[FIELDS[self._TYPE]] = str(value)

        return script


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
