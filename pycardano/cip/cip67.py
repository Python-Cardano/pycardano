from typing import Union

from crc8 import crc8

from pycardano.transaction import AssetName


class InvalidCIP67Token(Exception):
    pass


class CIP67TokenName(AssetName):
    def __repr__(self):
        return f"{self.__class__.__name__}({self.payload})"

    def __init__(self, data: Union[bytes, str, AssetName]):
        if isinstance(data, AssetName):
            data = data.payload

        if isinstance(data, bytes):
            data = data.hex()

        if data[0] != "0" or data[7] != "0":
            raise InvalidCIP67Token(
                "The first and eighth hex values must be 0. Instead found:\n"
                + f"first={data[0]}\n"
                + f"eigth={data[7]}"
            )

        checksum = crc8(bytes.fromhex(data[1:5])).hexdigest()
        if data[5:7] != checksum:
            raise InvalidCIP67Token(
                f"Token label {data[1:5]} does not match token checksum.\n"
                + f"expected={checksum}\n"
                + f"received={data[5:7]}"
            )

        super().__init__(bytes.fromhex(data))

    @property
    def label(self) -> int:
        return int.from_bytes(self.payload[:3], "big") >> 4
