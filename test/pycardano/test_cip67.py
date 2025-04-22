import pytest

from pycardano.cip.cip67 import CIP67TokenName, InvalidCIP67Token
from pycardano.transaction import AssetName


@pytest.mark.parametrize("valid_token", [
    ("000643b0617273656372797074", 100),  # Reference NFT with label 100
    ("000643b04d7943617264", 100),        # Another reference NFT with label 100
    ("000de1404d794e4654", 222),           # User NFT with label 222
    ("000de140556e697175654e4654", 222),   # Another user NFT with label 222
    ("0014df10546f6b656e31", 333),         # User FT with label 333
    ("0014df10436f696e31", 333),
    ('001bc280546f6b656e31', 444),          # RFT with label 444
    ('001bc2804d7943617264', 444),          # User RFT with label 444
])

def test_token_name_format(valid_token):
    token_str, expected_label = valid_token
    token = CIP67TokenName(token_str)
    assert token.label == expected_label


@pytest.mark.parametrize("invalid_token", [
    "100643b0617273656372797074",  # Invalid first hex
    "000643b1617273656372797074",  # Invalid last hex
    "00064300617273656372797074",  # Invalid checksum
    "000643b", # Too short
    "000643b0617273656372797074a", # Too long
])

def test_invalid_token_name_format(invalid_token):
    with pytest.raises((InvalidCIP67Token, IndexError, ValueError)):
        CIP67TokenName(invalid_token)

def test_input_types():
    token_str = "000643b0617273656372797074"
    CIP67TokenName(token_str)  # string input
    CIP67TokenName(bytes.fromhex(token_str))  # bytes input
    CIP67TokenName(AssetName(bytes.fromhex(token_str)))  # AssetName input
    with pytest.raises(TypeError):
        CIP67TokenName(123)  # int input should fail
    with pytest.raises(TypeError):
        CIP67TokenName(None)

