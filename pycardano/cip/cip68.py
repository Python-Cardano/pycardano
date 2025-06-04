from typing import Union, Dict, List, Any, Optional, TypedDict, Required
from dataclasses import dataclass, field
from cbor2 import CBORTag
import cbor2
from pycardano.cip.cip67 import CIP67TokenName
from pycardano.plutus import PlutusData, Unit, get_tag, Primitive, ArrayCBORSerializable
from pycardano.transaction import AssetName
from pycardano.serialization import IndefiniteList, CBORSerializable
from pycardano.exception import DeserializeException


class InvalidCIP68ReferenceNFT(Exception):
    pass


class CIP68TokenName(CIP67TokenName):
    @property
    def reference_token(self) -> "CIP68ReferenceNFTName":
        ref_token = self.payload.hex()[0] + "00643b" + self.payload.hex()[7:]

        return CIP68ReferenceNFTName(ref_token)


class CIP68ReferenceNFTName(CIP68TokenName):
    def __init__(self, data: Union[bytes, str, AssetName]):
        super().__init__(data)

        if self.label != 100:
            raise InvalidCIP68ReferenceNFT("Reference NFT must have label 100.")

    
# class CIP68BaseMetadata(DictCBORSerializable):
#     """Base class for CIP-68 metadata"""
#     KEY_TYPE = bytes
#     VALUE_TYPE = Any  # Validation handled in each child class using FIELD_TYPES
#     MAX_ITEM_SIZE = 64
#     FIELD_TYPES = {}

#     def __init__(self, *args, **kwargs):
#         super().__init__(args[0] if args else kwargs)
#         self._validate()

#     def _validate(self):
#         """Validate field types and sizes"""
#         for k, v in self.items():
#             if not isinstance(k, bytes):
#                 raise ValueError(f"Keys must be bytes, got {type(k)} instead")
            
#             if k in self.FIELD_TYPES:
#                 expected_type = self.FIELD_TYPES[k]
#                 if not isinstance(v, expected_type):
#                     raise ValueError(f"Field {k} must be {expected_type}, got {type(v)} instead")
            
#             if isinstance(v, bytes) and len(v) > self.MAX_ITEM_SIZE:
#                 raise ValueError(f"The size of {v} exceeds {self.MAX_ITEM_SIZE} bytes.")

#     # def to_primitive(self) -> dict:
#     #     """Convert to primitive form with string keys for JSON compatibility"""
#     #     primitive = super().to_primitive()
#     #     # Convert bytes keys to strings for JSON serialization
#     #     return {k.decode() if isinstance(k, bytes) else k: v for k, v in primitive.items()}


class CIP68UserNFTName(CIP68TokenName):
    def __init__(self, data: Union[bytes, str, AssetName]):
        super().__init__(data)

        if self.label != 222:
            raise InvalidCIP68ReferenceNFT("User NFT must have label 222.")


class CIP68UserNFTFiles(TypedDict, total=False):
    name: bytes
    mediaType: Required[bytes]
    src: Required[bytes]


# class CIP68UserNFTFiles(CIP68BaseMetadata):
#     """Files metadata for User NFTs"""
#     FIELD_TYPES = {
#         b"name": bytes,
#         b"mediaType": bytes,
#         b"src": bytes
#     }

#     def _validate(self):
#         super()._validate()
#         if self and not all(k in self.keys() for k in [b"mediaType", b"src"]):
#             print("self.keys():", self.keys())
#             print("self.items():", self.items())
#             print("self:", self)
#             raise ValueError("mediaType and src are required fields")

class CIP68UserNFTMetadata(TypedDict, total=False):
    name: Required[bytes]
    image: Required[bytes]
    description: bytes
    files: Union[List[Dict[bytes, bytes]], None]

# class CIP68UserNFTMetadata(CIP68BaseMetadata):
#     """Metadata for User NFTs"""
#     FIELD_TYPES = {
#         b"name": bytes,
#         b"image": bytes,
#         b"description": bytes,
#         b"files": (CIP68UserNFTFiles, list, dict, None)
#     }

#     def _validate(self):
#         super()._validate()
#         if not all(k in self.keys() for k in [b"name", b"image"]):
#             raise ValueError("name and image are required fields")


class CIP68UserFTName(CIP68TokenName):
    def __init__(self, data: Union[bytes, str, AssetName]):
        super().__init__(data)

        if self.label != 333:
            raise InvalidCIP68ReferenceNFT("User NFT must have label 333.")


class CIP68UserFTMetadata(TypedDict, total=False):
    name: Required[bytes]
    description: Required[bytes]
    ticker: bytes
    url: bytes
    logo: bytes
    decimals: int

# class CIP68UserFTMetadata(CIP68BaseMetadata):
#     """Metadata for User FTs"""
#     FIELD_TYPES = {
#         "name": bytes,
#         "description": bytes,
#         "ticker": bytes,
#         "url": bytes,
#         "logo": bytes,
#         "decimals": int
#     }

#     def _validate(self):
#         super()._validate()
#         if not all(k in self for k in ["name", "description"]):
#             raise ValueError("name and description are required fields")


class CIP68UserRFTName(CIP68TokenName):
    def __init__(self, data: Union[bytes, str, AssetName]):
        super().__init__(data)

        if self.label != 444:
            raise InvalidCIP68ReferenceNFT("User NFT must have label 444.")


class CIP68UserRFTMetadata(TypedDict, total=False):
    name: Required[bytes]
    image: Required[bytes]
    description: bytes


# class CIP68UserRFTMetadata(CIP68BaseMetadata):
#     """Metadata for User RFTs"""
#     FIELD_TYPES = {
#         "name": bytes,
#         "image": bytes,
#         "description": bytes
#     }

#     def _validate(self):
#         super()._validate()
#         if not all(k in self for k in ["name", "image"]):
#             raise ValueError("name and image are required fields")


@dataclass
class CIP68Datum(PlutusData):
    """Wrapper class for CIP-68 metadata to be used as inline datum"""
    CONSTR_ID = 0

    metadata: Dict[bytes, Any]
    version: int
    extra: Any      # This should be PlutusData or Unit() for empty PlutusData
 
    def __post_init__(self):
        # Convert string keys to bytes in metadata
        converted_metadata: Dict[bytes, Any] = {}
        for k, v in self.metadata.items():
            key = k.encode() if isinstance(k, str) else k
            # Handle nested dictionaries (like in files)
            if isinstance(v, dict):
                v = dict((k.encode() if isinstance(k, str) else k, v) for k, v in v.items())
            # Handle lists of dictionaries (allows multiple files)
            elif isinstance(v, list):
                v = IndefiniteList([dict((k.encode() if isinstance(k, str) else k, v) for k, v in item.items())
                     if isinstance(item, dict) else item for item in v])
            converted_metadata[key] = v
        self.metadata = converted_metadata

    def to_shallow_primitive(self) -> CBORTag:
        primitives: Primitive = super().to_shallow_primitive()
        if isinstance(primitives, CBORTag):
            value = primitives.value
            if value:
                extra = value[2]
                if isinstance(extra, Unit):
                    # Convert Unit to CBORTag with IndefiniteList([])
                    extra = CBORTag(121, IndefiniteList([]))
                elif isinstance(extra, CBORTag):
                    extra = CBORTag(extra.tag, IndefiniteList(extra.value))
                value = [value[0], value[1], extra]
        return CBORTag(121, value)
        
 