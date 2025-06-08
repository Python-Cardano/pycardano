from typing import Union

from pycardano.cip.cip67 import CIP67TokenName
from pycardano.plutus import PlutusData
from pycardano.serialization import ArrayCBORSerializable
from pycardano.serialization import MapCBORSerializable
from pycardano.transaction import AssetName


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


class CIP68UserNFTName(CIP68TokenName):
    def __init__(self, data: Union[bytes, str, AssetName]):
        super().__init__(data)

        if self.label != 222:
            raise InvalidCIP68ReferenceNFT("User NFT must have label 222.")


class CIP68UserNFTFiles(MapCBORSerializable):
    name: Union[bytes, None] = None
    mediaType: bytes
    src: bytes


class CIP68UserNFTMetadata(MapCBORSerializable):
    name: bytes
    image: bytes
    description: Union[bytes, None] = None
    files: Union[CIP68UserNFTFiles, None] = None


class CIP68UserFTName(CIP68TokenName):
    def __init__(self, data: Union[bytes, str, AssetName]):
        super().__init__(data)

        if self.label != 333:
            raise InvalidCIP68ReferenceNFT("User NFT must have label 333.")


class CIP68UserFTMetadata(MapCBORSerializable):
    name: bytes
    description: bytes
    ticker: Union[bytes, None] = None
    url: Union[bytes, None] = None
    decimals: Union[int, None] = None
    logo: Union[bytes, None] = None


class CIP68UserRFTName(CIP68TokenName):
    def __init__(self, data: Union[bytes, str, AssetName]):
        super().__init__(data)

        if self.label != 444:
            raise InvalidCIP68ReferenceNFT("User NFT must have label 444.")


class CIP68UserRFTMetadata(MapCBORSerializable):
    name: bytes
    image: bytes
    description: Union[bytes, None] = None
    decimals: Union[int, None] = None
    files: Union[CIP68UserNFTFiles, None] = None


class CIP68Metadata(ArrayCBORSerializable):
    metadata: Union[
        CIP68UserNFTMetadata,
        CIP68UserFTMetadata,
        CIP68UserRFTMetadata,
        MapCBORSerializable,
        ArrayCBORSerializable,
    ]
    version: int
    extra: Union[PlutusData, None] = None
