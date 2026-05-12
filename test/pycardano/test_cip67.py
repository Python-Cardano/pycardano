import pytest

from pycardano.cip.cip67 import CIP67TokenName, InvalidCIP67Token
from pycardano.transaction import AssetName, Value, MultiAsset, Asset
from pycardano.hash import ScriptHash


@pytest.mark.parametrize("token_data", [
    # Valid tokens
    ("000643b0617273656372797074", 100),  # Reference NFT with label 100
    ("000de1404d794e4654", 222),  # NFT with label 222
    ("0014df10546f6b656e31", 333),  # FT with label 333
    ("001bc280546f6b656e31", 444),  # RFT with label 444
    # Invalid tokens
    pytest.param(
        ("100643b0617273656372797074", None),  # Invalid first hex
        marks=pytest.mark.xfail(raises=InvalidCIP67Token),
        id="invalid_first_hex"
    ),
    pytest.param(
        ("000643b1617273656372797074", None),  # Invalid last hex
        marks=pytest.mark.xfail(raises=InvalidCIP67Token),
        id="invalid_last_hex"
    ),
    pytest.param(
        ("00064300617273656372797074", None),  # Invalid checksum
        marks=pytest.mark.xfail(raises=InvalidCIP67Token),
        id="invalid_checksum"
    ),
    pytest.param(
        ("000643b", None),  # Too short
        marks=pytest.mark.xfail(raises=(InvalidCIP67Token, IndexError)),
        id="too_short"
    ),
])
def test_cip67_token_name_format(token_data):
    token_str, expected_label = token_data
    # Create a Value object with asset names and dummy policyID
    policy = ScriptHash.from_primitive("00000000000000000000000000000000000000000000000000000000")
    asset = Asset()
    asset[AssetName(token_str)] = 1
    multi_asset = MultiAsset()
    multi_asset[policy] = asset
    value = Value(0, multi_asset)
    # Extract the AssetName from the Value object and create CIP67TokenName
    token_name = next(iter(next(iter(value.multi_asset.values())).keys()))
    token = CIP67TokenName(token_name)
    
    if expected_label is not None:
        assert token.label == expected_label


def test_cip67_input_types():
    token_str = "000643b0617273656372797074"
    CIP67TokenName(token_str)  # string input
    CIP67TokenName(bytes.fromhex(token_str))  # bytes input
    CIP67TokenName(AssetName(bytes.fromhex(token_str)))  # AssetName input
    
    with pytest.raises(TypeError):
        CIP67TokenName(123)  # int input should fail
    with pytest.raises(TypeError):
        CIP67TokenName(None)

