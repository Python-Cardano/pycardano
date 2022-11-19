"""Cardano native script"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import ClassVar, List, Type, Union, cast

from nacl.encoding import RawEncoder
from nacl.hash import blake2b

from pycardano.exception import DeserializeException
from pycardano.hash import SCRIPT_HASH_SIZE, ScriptHash, VerificationKeyHash
from pycardano.serialization import (
    ArrayCBORSerializable,
    Primitive,
    limit_primitive_type,
    list_hook,
)
from pycardano.types import JsonDict

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
    json_tag: ClassVar[str]
    json_field: ClassVar[str]

    @classmethod
    @limit_primitive_type(list)
    def from_primitive(
        cls: Type[NativeScript], value: list
    ) -> Union[
        ScriptPubkey, ScriptAll, ScriptAny, ScriptNofK, InvalidBefore, InvalidHereAfter
    ]:
        script_type: int = value[0]
        if script_type == ScriptPubkey._TYPE:
            return super(NativeScript, ScriptPubkey).from_primitive(value[1:])
        elif script_type == ScriptAll._TYPE:
            return super(NativeScript, ScriptAll).from_primitive(value[1:])
        elif script_type == ScriptAny._TYPE:
            return super(NativeScript, ScriptAny).from_primitive(value[1:])
        elif script_type == ScriptNofK._TYPE:
            return super(NativeScript, ScriptNofK).from_primitive(value[1:])
        elif script_type == InvalidBefore._TYPE:
            return super(NativeScript, InvalidBefore).from_primitive(value[1:])
        elif script_type == InvalidHereAfter._TYPE:
            return super(NativeScript, InvalidHereAfter).from_primitive(value[1:])
        else:
            raise DeserializeException(f"Unknown script type indicator: {script_type}")

    def hash(self) -> ScriptHash:
        cbor_bytes = cast(bytes, self.to_cbor("bytes"))
        return ScriptHash(
            blake2b(bytes(1) + cbor_bytes, SCRIPT_HASH_SIZE, encoder=RawEncoder)
        )

    @classmethod
    def from_dict(
        cls: Type[NativeScript], script_json: JsonDict
    ) -> Union[
        ScriptPubkey, ScriptAll, ScriptAny, ScriptNofK, InvalidBefore, InvalidHereAfter
    ]:
        """Parse a standard native script dictionary (potentially parsed from a JSON file)."""
        script_primitive = cls._script_json_to_primitive(script_json)
        return cls.from_primitive(script_primitive)

    @classmethod
    def _script_json_to_primitive(
        cls: Type[NativeScript], script_json: JsonDict
    ) -> List[Primitive]:
        """Serialize a standard JSON native script into a primitive array"""
        script_type: str = script_json["type"]
        native_script: List[Primitive] = [JSON_TAG_TO_INT[script_type]]

        for key, value in script_json.items():
            if key == "type":
                continue
            elif key == "scripts":
                native_script.append(cls._script_jsons_to_primitive(value))
            else:
                native_script.append(value)
        return native_script

    @classmethod
    def _script_jsons_to_primitive(
        cls: Type[NativeScript], script_jsons: List[JsonDict]
    ) -> List[List[Primitive]]:
        """Parse a list of JSON scripts into a list of primitive arrays"""
        native_script = [cls._script_json_to_primitive(i) for i in script_jsons]
        return native_script

    def to_dict(self) -> JsonDict:
        """Export to standard native script dictionary (potentially to dump to a JSON file)."""
        script: JsonDict = {}
        for value in self.__dict__.values():
            script["type"] = self.json_tag

            if isinstance(value, list):
                script["scripts"] = [i.to_dict() for i in value]
            elif isinstance(value, int):
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

    before: int


@dataclass
class InvalidHereAfter(NativeScript):
    json_tag: ClassVar[str] = "before"
    json_field: ClassVar[str] = "slot"
    _TYPE: int = field(default=5, init=False)

    after: int


JSON_TAG_TO_INT = {
    ScriptPubkey.json_tag: ScriptPubkey._TYPE,
    ScriptAll.json_tag: ScriptAll._TYPE,
    ScriptAny.json_tag: ScriptAny._TYPE,
    ScriptNofK.json_tag: ScriptNofK._TYPE,
    InvalidBefore.json_tag: InvalidBefore._TYPE,
    InvalidHereAfter.json_tag: InvalidHereAfter._TYPE,
}
