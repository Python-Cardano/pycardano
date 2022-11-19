from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, ClassVar, List, Type, Union

from cbor2 import CBORTag
from nacl.encoding import RawEncoder
from nacl.hash import blake2b

from pycardano.exception import DeserializeException, InvalidArgumentException
from pycardano.hash import AUXILIARY_DATA_HASH_SIZE, AuxiliaryDataHash
from pycardano.nativescript import NativeScript
from pycardano.serialization import (
    ArrayCBORSerializable,
    CBORSerializable,
    DictCBORSerializable,
    MapCBORSerializable,
    Primitive,
    limit_primitive_type,
    list_hook,
)

__all__ = ["Metadata", "ShellayMarryMetadata", "AlonzoMetadata", "AuxiliaryData"]


class Metadata(DictCBORSerializable):
    KEY_TYPE = int  # transaction_metadatum_label, see https://github.com/cardano-foundation/CIPs/tree/master/CIP-0010
    VALUE_TYPE = Any

    MAX_ITEM_SIZE = 64
    INTERNAL_TYPES = (dict, list, int, bytes, str)

    def _validate(self):
        def _validate_type_and_size(data):
            if not isinstance(data, self.INTERNAL_TYPES):
                raise InvalidArgumentException(
                    f"A value in Metadata has to be one of {self.INTERNAL_TYPES}, "
                    f"got {type(data)} instead."
                )
            if isinstance(data, bytes):
                if len(data) > self.MAX_ITEM_SIZE:
                    raise InvalidArgumentException(
                        f"The size of {data} exceeds {self.MAX_ITEM_SIZE} bytes."
                    )
            elif isinstance(data, str):
                if len(data.encode("utf-8")) > self.MAX_ITEM_SIZE:
                    raise InvalidArgumentException(
                        f"The size of {data} exceeds {self.MAX_ITEM_SIZE} bytes."
                    )
            elif isinstance(data, list):
                for item in data:
                    _validate_type_and_size(item)
            elif isinstance(data, dict):
                for key in data:
                    _validate_type_and_size(data[key])

        for k in self:
            if not isinstance(k, self.KEY_TYPE):
                raise InvalidArgumentException(
                    f"Keys in the first layer of Metadata has to be {self.KEY_TYPE}, "
                    f"got {type(k)} instead."
                )
            _validate_type_and_size(self[k])

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._validate()


@dataclass
class ShellayMarryMetadata(ArrayCBORSerializable):
    metadata: Metadata
    native_scripts: List[NativeScript] = field(
        default=None, metadata={"object_hook": list_hook(NativeScript)}
    )


@dataclass
class AlonzoMetadata(MapCBORSerializable):
    TAG: ClassVar[int] = 259

    metadata: Metadata = field(default=None, metadata={"optional": True, "key": 0})
    native_scripts: List[NativeScript] = field(
        default=None,
        metadata={"optional": True, "key": 1, "object_hook": list_hook(NativeScript)},
    )
    plutus_scripts: List[bytes] = field(
        default=None, metadata={"optional": True, "key": 2}
    )

    def to_primitive(self) -> Primitive:
        return CBORTag(AlonzoMetadata.TAG, super(AlonzoMetadata, self).to_primitive())

    @classmethod
    @limit_primitive_type(CBORTag)
    def from_primitive(cls: Type[AlonzoMetadata], value: CBORTag) -> AlonzoMetadata:
        if not hasattr(value, "tag"):
            raise DeserializeException(
                f"{value} does not match the data schema of AlonzoMetadata."
            )
        elif value.tag != cls.TAG:
            raise DeserializeException(
                f"Expect CBOR tag: {cls.TAG}, got {value.tag} instead."
            )
        return super(AlonzoMetadata, cls).from_primitive(value.value)


@dataclass
class AuxiliaryData(CBORSerializable):
    data: Union[Metadata, ShellayMarryMetadata, AlonzoMetadata]

    def to_primitive(self) -> Primitive:
        return self.data.to_primitive()

    @classmethod
    def from_primitive(cls: Type[AuxiliaryData], value: Primitive) -> AuxiliaryData:
        for t in [AlonzoMetadata, ShellayMarryMetadata, Metadata]:
            # The schema of metadata in different eras are mutually exclusive, so we can try deserializing
            # them one by one without worrying about mismatch.
            try:
                return AuxiliaryData(t.from_primitive(value))
            except DeserializeException:
                pass
        raise DeserializeException(f"Couldn't parse auxiliary data: {value}")

    def hash(self) -> AuxiliaryDataHash:
        return AuxiliaryDataHash(
            blake2b(self.to_cbor("bytes"), AUXILIARY_DATA_HASH_SIZE, encoder=RawEncoder)
        )
