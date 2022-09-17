"""Cardano native script"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import ClassVar, List, Union

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
        """Parse a standard native script dictionary (potentially parsed from a JSON file)."""

        types = {
            p.json_tag: p
            for p in [
                ScriptPubkey,
                ScriptAll,
                ScriptAny,
                ScriptNofK,
                InvalidBefore,
                InvalidHereAfter,
            ]
        }

        native_script = []
        if isinstance(script, dict):

            for key, value in script.items():
                if key == "type":
                    native_script.insert(0, list(types.keys()).index(value))
                elif key == "scripts":
                    native_script.append(cls.from_dict(value, top_level=False))
                else:
                    native_script.append(value)

        elif isinstance(script, list):  # list
            native_script = [cls.from_dict(i, top_level=False) for i in script]

        if not top_level:
            return native_script
        else:
            return super(NativeScript, types[script["type"]]).from_primitive(
                native_script[1:]
            )

    def to_dict(self) -> dict:
        """Export to standard native script dictionary (potentially to dump to a JSON file)."""

        script = {}

        for value in self.__dict__.values():
            script["type"] = self.json_tag

            if isinstance(value, list):
                script["scripts"] = [i.to_dict() for i in value]

            else:
                if isinstance(value, int):
                    script[self.json_field] = value
                else:
                    script[self.json_field] = str(value)

        return script


@dataclass
class ScriptPubkey(NativeScript):
    json_tag: ClassVar[str] = "sig"
    json_field: ClassVar[str] = "keyHash"
    _TYPE: int = field(default=0, init=False)

    key_hash: VerificationKeyHash


@dataclass
class ScriptAll(NativeScript):
    json_tag: ClassVar[str] = "all"
    json_field: ClassVar[str] = "scripts"
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
    json_tag: ClassVar[str] = "any"
    json_field: ClassVar[str] = "scripts"
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
    json_tag: ClassVar[str] = "atLeast"
    json_field: ClassVar[str] = "required"
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
    json_tag: ClassVar[str] = "after"
    json_field: ClassVar[str] = "slot"
    _TYPE: int = field(default=4, init=False)

    before: int = None


@dataclass
class InvalidHereAfter(NativeScript):
    json_tag: ClassVar[str] = "before"
    json_field: ClassVar[str] = "slot"
    _TYPE: int = field(default=5, init=False)

    after: int = None
