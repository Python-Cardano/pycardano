from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, ClassVar, List, Union

from cbor2 import CBORTag
from nacl.encoding import RawEncoder
from nacl.hash import blake2b

from pycardano.exception import DeserializeException
from pycardano.hash import AuxiliaryDataHash, AUXILIARY_DATA_HASH_SIZE
from pycardano.nativescript import NativeScript
from pycardano.serialization import (CBORSerializable, DictCBORSerializable, ArrayCBORSerializable,
                                     MapCBORSerializable, Primitive, list_hook)


class Metadata(DictCBORSerializable):
    KEY_TYPE = int  # transaction_metadatum_label, see https://github.com/cardano-foundation/CIPs/tree/master/CIP-0010
    VALUE_TYPE = Any


@dataclass
class ShellayMarryMetadata(ArrayCBORSerializable):
    metadata: Metadata
    native_scripts: List[NativeScript] = field(default=None, metadata={"object_hook": list_hook(NativeScript)})


@dataclass
class AlonzoMetadata(MapCBORSerializable):
    TAG: ClassVar[int] = 259

    metadata: Metadata = field(default=None, metadata={"optional": True, "key": 0})
    native_scripts: List[NativeScript] = field(default=None,
                                               metadata={"optional": True,
                                                         "key": 1,
                                                         "object_hook": list_hook(NativeScript)})
    plutus_scripts: List[bytes] = field(default=None, metadata={"optional": True, "key": 2})

    def to_primitive(self) -> Primitive:
        return CBORTag(AlonzoMetadata.TAG, super(AlonzoMetadata, self).to_primitive())

    @classmethod
    def from_primitive(cls: AlonzoMetadata, value: CBORTag) -> AlonzoMetadata:
        if not hasattr(value, "tag"):
            raise DeserializeException(f"{value} does not match the data schema of AlonzoMetadata.")
        elif value.tag != cls.TAG:
            raise DeserializeException(f"Expect CBOR tag: {cls.TAG}, got {value.tag} instead.")
        return super(AlonzoMetadata, cls).from_primitive(value.value)


@dataclass
class AuxiliaryData(CBORSerializable):
    data: Union[Metadata, ShellayMarryMetadata, AlonzoMetadata]

    def to_primitive(self) -> Primitive:
        return self.data.to_primitive()

    @classmethod
    def from_primitive(cls: AuxiliaryData, value: Primitive) -> AuxiliaryData:
        for t in [AlonzoMetadata, ShellayMarryMetadata, Metadata]:
            # The schema of metadata in different eras are mutually exclusive, so we can try deserializing
            # them one by one without worrying about mismatch.
            try:
                return AuxiliaryData(t.from_primitive(value))
            except DeserializeException:
                pass
        raise DeserializeException(f"Couldn't parse auxiliary data: {value}")

    def hash(self) -> AuxiliaryDataHash:
        return AuxiliaryDataHash(blake2b(self.to_cbor("bytes"), AUXILIARY_DATA_HASH_SIZE, encoder=RawEncoder))
