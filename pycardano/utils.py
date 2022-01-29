"""A collection of utility functions."""

from typing import Union

from pycardano.backend.base import ChainContext
from pycardano.hash import SCRIPT_HASH_SIZE
from pycardano.transaction import MultiAsset, FullMultiAsset


def max_tx_fee(context: ChainContext) -> int:
    """Calculate the maximum possible transaction fee based on protocol parameters.

    Args:
        context (ChainContext): A chain context.

    Returns:
        int: Maximum possible tx fee in lovelace.
    """
    return context.protocol_param.max_tx_size * context.protocol_param.min_fee_coefficient + \
        context.protocol_param.min_fee_constant + \
        int(context.protocol_param.max_tx_ex_mem * context.protocol_param.price_mem) + \
        int(context.protocol_param.max_tx_ex_steps * context.protocol_param.price_step)


def bundle_size(multi_asset: MultiAsset) -> int:
    """Calculate size of a multi-asset in words. (1 word = 8 bytes)

    Args:
        multi_asset (MultiAsset): Input multi asset.

    Returns:
        int: Number of words.
    """
    num_policies = len(multi_asset)
    num_assets = 0
    total_asset_name_len = 0

    # Only unique asset names are counted
    # see GitHub issue: https://github.com/Emurgo/cardano-serialization-lib/issues/194
    unique_assets = set()
    for p in multi_asset:
        num_assets += len(multi_asset[p])
        for n in multi_asset[p]:
            if n.payload not in unique_assets:
                unique_assets.add(n.payload)
                total_asset_name_len += len(n.payload)

    byte_len = num_assets * 12 + total_asset_name_len + num_policies * SCRIPT_HASH_SIZE
    return 6 + (byte_len + 7) // 8


def min_lovelace(amount: Union[int, FullMultiAsset], context: ChainContext, has_datum: bool = False) -> int:
    """Calculate minimum lovelace a transaction output needs to hold.

    More info could be found in
    `this <https://github.com/input-output-hk/cardano-ledger/blob/master/doc/explanations/min-utxo-alonzo.rst>`_ page.

    Args:
        amount (Union[int, FullMultiAsset]): Amount from a transaction output.
        context (ChainContext): A chain context.
        has_datum (bool): Whether the transaction output contains datum hash.

    Returns:
        int: Minimum required lovelace amount for this transaction output.
    """
    if isinstance(amount, int):
        return context.protocol_param.min_utxo

    b_size = bundle_size(amount.multi_asset)
    utxo_entry_size = 27
    data_hash_size = 10 if has_datum else 0
    finalized_size = utxo_entry_size + b_size + data_hash_size

    return finalized_size * context.protocol_param.coins_per_utxo_word
