"""A collection of utility functions."""

from __future__ import annotations

from typing import List, Optional, Union

import cbor2
from nacl.encoding import RawEncoder
from nacl.hash import blake2b

from pycardano.backend.base import ChainContext
from pycardano.hash import SCRIPT_DATA_HASH_SIZE, SCRIPT_HASH_SIZE, ScriptDataHash
from pycardano.plutus import COST_MODELS, CostModels, Datum, Redeemer
from pycardano.serialization import default_encoder
from pycardano.transaction import MultiAsset, Value

__all__ = ["fee", "max_tx_fee", "bundle_size", "min_lovelace", "script_data_hash"]


def fee(
    context: ChainContext,
    length: int,
    exec_steps: Optional[int] = 0,
    max_mem_unit: Optional[int] = 0,
) -> int:
    """Calculate fee based on the length of a transaction's CBOR bytes and script execution.

    Args:
        context (ChainConext): A chain context.
        length (int): The length of CBOR bytes, which could usually be derived
            by `len(tx.to_cbor("bytes"))`.
        exec_steps (Optional[int]): Number of execution steps run by plutus scripts in the transaction.
        max_mem_unit (Optional[int]): Max numer of memory units run by plutus scripts in the transaction.

    Return:
        int: Minimum acceptable transaction fee.
    """
    return (
        int(length * context.protocol_param.min_fee_coefficient)
        + int(context.protocol_param.min_fee_constant)
        + int(exec_steps * context.protocol_param.price_step)
        + int(max_mem_unit * context.protocol_param.price_mem)
    )


def max_tx_fee(context: ChainContext) -> int:
    """Calculate the maximum possible transaction fee based on protocol parameters.

    Args:
        context (ChainContext): A chain context.

    Returns:
        int: Maximum possible tx fee in lovelace.
    """
    return fee(
        context,
        context.protocol_param.max_tx_size,
        context.protocol_param.max_tx_ex_steps,
        context.protocol_param.max_tx_ex_mem,
    )


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


def min_lovelace(
    amount: Union[int, Value], context: ChainContext, has_datum: bool = False
) -> int:
    """Calculate minimum lovelace a transaction output needs to hold.

    More info could be found in
    `this <https://github.com/input-output-hk/cardano-ledger/blob/master/doc/explanations/min-utxo-alonzo.rst>`_ page.

    Args:
        amount (Union[int, Value]): Amount from a transaction output.
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


def script_data_hash(
    redeemers: List[Redeemer],
    datums: List[Datum],
    cost_models: Optional[CostModels] = None,
) -> ScriptDataHash:
    """Calculate plutus script data hash

    Args:
        redeemers (List[Redeemer]): Redeemers to include.
        datums (List[Datum]): Datums to include.
        cost_models (Optional[CostModels]): Cost models.

    Returns:
        ScriptDataHash: Plutus script data hash
    """
    if not redeemers:
        cost_models = {}
    elif not cost_models:
        cost_models = COST_MODELS

    redeemer_bytes = cbor2.dumps(redeemers, default=default_encoder)
    if datums:
        datum_bytes = cbor2.dumps(datums, default=default_encoder)
    else:
        datum_bytes = b""
    cost_models_bytes = cbor2.dumps(cost_models, default=default_encoder)

    return ScriptDataHash(
        blake2b(
            redeemer_bytes + datum_bytes + cost_models_bytes,
            SCRIPT_DATA_HASH_SIZE,
            encoder=RawEncoder,
        )
    )
