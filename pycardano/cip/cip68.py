from typing import Union, Dict, List, Any, TypedDict, Required
from dataclasses import dataclass
from cbor2 import CBORTag

from pycardano.cip.cip67 import CIP67TokenName
from pycardano.plutus import PlutusData, Unit, Primitive
from pycardano.transaction import AssetName
from pycardano.serialization import IndefiniteList


class InvalidCIP68ReferenceNFT(Exception):
    pass


class CIP68TokenName(CIP67TokenName):
    """Generates a CIP-68 reference token name from an input asset name.

    The reference_token property generates a reference token name by slicing off the label
    portion of the asset name and assigning the (100) label hex value.

    For more information on CIP-68 labels:
    https://github.com/cardano-foundation/CIPs/tree/master/CIP-0068

    Args:
        data: The token name as bytes, str, or AssetName
    """
    @property
    def reference_token(self) -> "CIP68ReferenceNFTName":
        ref_token = self.payload.hex()[0] + "00643b" + self.payload.hex()[7:]

        return CIP68ReferenceNFTName(ref_token)


class CIP68ReferenceNFTName(CIP68TokenName):
    """Validates that an asset name has the 100 label for reference NFTs."""
    def __init__(self, data: Union[bytes, str, AssetName]):
        super().__init__(data)

        if self.label != 100:
            raise InvalidCIP68ReferenceNFT("Reference NFT must have label 100.")


class CIP68UserNFTName(CIP68TokenName):
    """Validates that an asset name has the 222 label for NFTs."""
    def __init__(self, data: Union[bytes, str, AssetName]):
        super().__init__(data)

        if self.label != 222:
            raise InvalidCIP68ReferenceNFT("User NFT must have label 222.")


class CIP68UserNFTFile(TypedDict, total=False):
    """Metadata for a single file in NFT metadata."""
    name: bytes
    mediaType: Required[bytes]
    src: Required[bytes]


class CIP68UserNFTMetadata(TypedDict, total=False):
    """Metadata for a user NFT.

    Multiple files can be included as a list of dictionaries or CIP68UserNFTFile objects.
    """
    name: Required[bytes]
    image: Required[bytes]
    description: bytes
    files: Union[List[CIP68UserNFTFile], None]


class CIP68UserFTName(CIP68TokenName):
    """Validates that an asset name has the 333 label for FTs."""
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


class CIP68UserRFTName(CIP68TokenName):
    """Validates that an asset name has the 444 label for RFTs."""
    def __init__(self, data: Union[bytes, str, AssetName]):
        super().__init__(data)

        if self.label != 444:
            raise InvalidCIP68ReferenceNFT("User NFT must have label 444.")


class CIP68UserRFTMetadata(TypedDict, total=False):
    name: Required[bytes]
    image: Required[bytes]
    description: bytes


@dataclass
class CIP68Datum(PlutusData):
    """Wrapper class for CIP-68 metadata to be used as inline datum.
    
    For detailed information on CIP-68 metadata structure and token types:
    https://github.com/cardano-foundation/CIPs/tree/master/CIP-0068

    This class wraps metadata dictionaries in a PlutusData class for attaching to a
    reference NFT transaction as an inline datum.

    Args:
        metadata: A metadata dictionary. TypedDict classes are provided to define required
            fields for each token type.
        version: Metadata version number as 'int'
        extra: Required - must be a PlutusData, or Unit() for empty PlutusData.

    Example:
        metadata = {
            b"name": b"My NFT",
            b"image": b"ipfs://...",
            b"files": [{"mediaType": b"image/png", "src": b"ipfs://..."}]
        }
        datum = CIP68Datum(metadata=metadata, version=1, extra=Unit())
    """
    CONSTR_ID = 0

    metadata: Dict[bytes, Any]
    version: int
    extra: Any      # This should be PlutusData or Unit() for empty PlutusData
 
    def __post_init__(self):
        converted_metadata: Dict[bytes, Any] = {}
        for k, v in self.metadata.items():
            key = k.encode() if isinstance(k, str) else k
            if isinstance(v, dict):
                v = dict((k.encode() if isinstance(k, str) else k, v) for k, v in v.items())
            elif isinstance(v, list):
                v = IndefiniteList([dict((k.encode() if isinstance(k, str) else k, v) for k, v in item.items())
                     if isinstance(item, dict) else item for item in v])
            converted_metadata[key] = v
        self.metadata = converted_metadata

    def to_shallow_primitive(self) -> CBORTag:
        """Wraps PlutusData in 'extra' field in an indefinite list when converted to a CBOR primitive."""
        primitives: Primitive = super().to_shallow_primitive()
        if isinstance(primitives, CBORTag):
            value = primitives.value
            if value:
                extra = value[2]
                if isinstance(extra, Unit):
                    extra = CBORTag(121, IndefiniteList([]))
                elif isinstance(extra, CBORTag):
                    extra = CBORTag(extra.tag, IndefiniteList(extra.value))
                value = [value[0], value[1], extra]
        return CBORTag(121, value)
        
 