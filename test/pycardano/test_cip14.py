import pytest

from pycardano.cip.cip14 import encode_asset
from pycardano.hash import ScriptHash
from pycardano.transaction import AssetName


@pytest.mark.parametrize(
    "input_types", [(str, str), (bytes, bytes), (ScriptHash, AssetName)]
)
@pytest.mark.parametrize(
    "asset",
    [
        {
            "policy_id": "7eae28af2208be856f7a119668ae52a49b73725e326dc16579dcc373",
            "asset_name": "",
            "asset_fingerprint": "asset1rjklcrnsdzqp65wjgrg55sy9723kw09mlgvlc3",
        },
        {
            "policy_id": "7eae28af2208be856f7a119668ae52a49b73725e326dc16579dcc37e",
            "asset_name": "",
            "asset_fingerprint": "asset1nl0puwxmhas8fawxp8nx4e2q3wekg969n2auw3",
        },
        {
            "policy_id": "1e349c9bdea19fd6c147626a5260bc44b71635f398b67c59881df209",
            "asset_name": "",
            "asset_fingerprint": "asset1uyuxku60yqe57nusqzjx38aan3f2wq6s93f6ea",
        },
        {
            "policy_id": "7eae28af2208be856f7a119668ae52a49b73725e326dc16579dcc373",
            "asset_name": "504154415445",
            "asset_fingerprint": "asset13n25uv0yaf5kus35fm2k86cqy60z58d9xmde92",
        },
        {
            "policy_id": "1e349c9bdea19fd6c147626a5260bc44b71635f398b67c59881df209",
            "asset_name": "504154415445",
            "asset_fingerprint": "asset1hv4p5tv2a837mzqrst04d0dcptdjmluqvdx9k3",
        },
        {
            "policy_id": "1e349c9bdea19fd6c147626a5260bc44b71635f398b67c59881df209",
            "asset_name": "7eae28af2208be856f7a119668ae52a49b73725e326dc16579dcc373",
            "asset_fingerprint": "asset1aqrdypg669jgazruv5ah07nuyqe0wxjhe2el6f",
        },
        {
            "policy_id": "7eae28af2208be856f7a119668ae52a49b73725e326dc16579dcc373",
            "asset_name": "1e349c9bdea19fd6c147626a5260bc44b71635f398b67c59881df209",
            "asset_fingerprint": "asset17jd78wukhtrnmjh3fngzasxm8rck0l2r4hhyyt",
        },
        {
            "policy_id": "7eae28af2208be856f7a119668ae52a49b73725e326dc16579dcc373",
            "asset_name": "0000000000000000000000000000000000000000000000000000000000000000",
            "asset_fingerprint": "asset1pkpwyknlvul7az0xx8czhl60pyel45rpje4z8w",
        },
    ],
)
def test_encode_asset(asset, input_types):
    if isinstance(input_types[0], bytes):
        policy_id = bytes.fromhex(asset["policy_id"])
        asset_name = bytes.fromhex(asset["asset_name"])
    elif isinstance(input_types[0], str):
        policy_id = asset["policy_id"]
        asset_name = asset["asset_name"]

    if isinstance(input_types[0], ScriptHash):
        policy_id = ScriptHash(policy_id)
        asset_name = AssetName(asset_name)

    fingerprint = encode_asset(
        policy_id=asset["policy_id"], asset_name=asset["asset_name"]
    )

    assert fingerprint == asset["asset_fingerprint"]
