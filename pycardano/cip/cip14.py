from typing import Union

from nacl.encoding import RawEncoder
from nacl.hash import blake2b
from pycardano.crypto.bech32 import encode


def encode_asset(policy_id: Union[bytes, str], asset_name: Union[bytes, str]) -> str:
    """Implementation of CIP14 asset fingerprinting

    This function encodes the asset policy and name into an asset fingerprint, which is
    bech32 compliant.

    For more information:
    https://developers.cardano.org/docs/governance/cardano-improvement-proposals/cip-0014/

    Args:
        policy_id: The asset policy as `bytes` or a hex `str`
        asset_name: The asset name as `bytes` or a hex `str`
    """
    if isinstance(policy_id, str):
        policy_id = bytes.fromhex(policy_id)

    if isinstance(asset_name, str):
        asset_name = bytes.fromhex(asset_name)

    asset_hash = blake2b(
        policy_id + asset_name,
        digest_size=20,
        encoder=RawEncoder,
    )

    return encode("asset", asset_hash)
