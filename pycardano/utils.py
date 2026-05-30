"""A collection of utility functions."""

from __future__ import annotations

import math
import sys
from typing import Dict, List, Optional, Tuple, Union

from nacl.encoding import RawEncoder
from nacl.hash import blake2b

from pycardano.backend.base import ChainContext
from pycardano.cbor import cbor2
from pycardano.hash import SCRIPT_DATA_HASH_SIZE, SCRIPT_HASH_SIZE, ScriptDataHash
from pycardano.plutus import COST_MODELS, CostModels, Datum, RedeemerMap, Redeemers
from pycardano.serialization import NonEmptyOrderedSet, default_encoder
from pycardano.transaction import MultiAsset, TransactionOutput, Value

__all__ = [
    "fee",
    "max_tx_fee",
    "bundle_size",
    "min_lovelace",
    "min_lovelace_pre_alonzo",
    "min_lovelace_post_alonzo",
    "script_data_hash",
    "tiered_reference_script_fee",
    "greater_than_version",
]


def tiered_reference_script_fee(context: ChainContext, scripts_size: int) -> int:
    """Calculate fee for reference scripts.

    Args:
        context (ChainContext): A chain context.
        scripts_size (int): Size of reference scripts in bytes.

    Returns:
        int: Fee for reference scripts.

    Raises:
        ValueError: If scripts size exceeds maximum allowed size
    """
    if (
        context.protocol_param.maximum_reference_scripts_size is None
        or context.protocol_param.min_fee_reference_scripts is None
    ):
        return 0

    max_size = context.protocol_param.maximum_reference_scripts_size["bytes"]
    if scripts_size > max_size:
        raise ValueError(
            f"Reference scripts size: {scripts_size} exceeds maximum allowed size ({max_size})."
        )

    total = 0.0
    if scripts_size:
        b = context.protocol_param.min_fee_reference_scripts["base"]
        r = math.ceil(context.protocol_param.min_fee_reference_scripts["range"])
        m = context.protocol_param.min_fee_reference_scripts["multiplier"]

        while scripts_size > r:
            total += b * r
            scripts_size = scripts_size - r
            b = b * m

        total += b * scripts_size

    return math.ceil(total)


def fee(
    context: ChainContext,
    length: int,
    exec_steps: int = 0,
    max_mem_unit: int = 0,
    ref_script_size: int = 0,
) -> int:
    """Calculate fee based on the length of a transaction's CBOR bytes and script execution.

    Args:
        context (ChainContext): A chain context.
        length (int): The length of CBOR bytes, which could usually be derived
            by `len(tx.to_cbor())`.
        exec_steps (int): Number of execution steps run by plutus scripts in the transaction.
        max_mem_unit (int): Max numer of memory units run by plutus scripts in the transaction.
        ref_script_size (int): Size of referenced scripts in the transaction.

    Return:
        int: Minimum acceptable transaction fee.
    """
    return int(
        math.ceil(length * context.protocol_param.min_fee_coefficient)
        + math.ceil(context.protocol_param.min_fee_constant)
        + math.ceil(exec_steps * context.protocol_param.price_step)
        + math.ceil(max_mem_unit * context.protocol_param.price_mem)
        + tiered_reference_script_fee(context, ref_script_size)
    )


def max_tx_fee(context: ChainContext, ref_script_size: int = 0) -> int:
    """Calculate the maximum possible transaction fee based on protocol parameters.

    Args:
        context (ChainContext): A chain context.
        ref_script_size (int): Size of reference scripts in the transaction.

    Returns:
        int: Maximum possible tx fee in lovelace.
    """
    return fee(
        context,
        context.protocol_param.max_tx_size,
        context.protocol_param.max_tx_ex_steps,
        context.protocol_param.max_tx_ex_mem,
        ref_script_size,
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
    context: ChainContext,
    output: Optional[TransactionOutput] = None,
    amount: Optional[Union[int, Value]] = None,
    has_datum: bool = False,
) -> int:
    """Calculate minimum lovelace a transaction output needs to hold.

    More info could be found in
    `this <https://github.com/input-output-hk/cardano-ledger/blob/master/doc/explanations/min-utxo-alonzo.rst>`_ page.

    Args:
        context (ChainContext): A chain context.
        output (TransactionOutput): A transaction output (for post-alonzo transactions).
        amount (Union[int, Value]): Amount from a transaction output (for pre-alonzo transactions).
        has_datum (bool): Whether the transaction output contains datum hash (for pre-alonzo transactions).

    Returns:
        int: Minimum required lovelace amount for this transaction output.
    """
    if output:
        return min_lovelace_post_alonzo(output, context)
    else:
        return min_lovelace_pre_alonzo(amount, context, has_datum)


def min_lovelace_pre_alonzo(
    amount: Union[int, Value, None], context: ChainContext, has_datum: bool = False
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
    if amount is None or isinstance(amount, int) or not amount.multi_asset:
        return context.protocol_param.min_utxo or 1_000_000

    b_size = bundle_size(amount.multi_asset)
    utxo_entry_size = 27
    data_hash_size = 10 if has_datum else 0
    finalized_size = utxo_entry_size + b_size + data_hash_size

    return finalized_size * context.protocol_param.coins_per_utxo_word


def min_lovelace_post_alonzo(output: TransactionOutput, context: ChainContext) -> int:
    """Calculate minimum lovelace a transaction output needs to hold post alonzo.

    This implementation is copied from the original Haskell implementation:
    https://github.com/input-output-hk/cardano-ledger/blob/eb053066c1d3bb51fb05978eeeab88afc0b049b2/eras/babbage/impl/src/Cardano/Ledger/Babbage/Rules/Utxo.hs#L242-L265

    Args:
        output (TransactionOutput): A transaction output.
        context (ChainContext): A chain context.

    Returns:
        int: Minimum required lovelace amount for this transaction output.
    """
    constant_overhead = 160

    amt = output.amount

    # If the amount of ADA is 0, a default value of 1 ADA will be used
    if amt.coin == 0:
        amt.coin = 1000000

    # Make sure we are using post-alonzo output
    tmp_out = TransactionOutput(
        output.address,
        output.amount,
        output.datum_hash,
        output.datum,
        output.script,
        True,
    )

    return (
        constant_overhead + len(tmp_out.to_cbor())
    ) * context.protocol_param.coins_per_utxo_byte


def script_data_hash(
    redeemers: Optional[Redeemers] = None,
    datums: Optional[Union[List[Datum], NonEmptyOrderedSet[Datum]]] = None,
    cost_models: Optional[Union[CostModels, Dict]] = None,
) -> ScriptDataHash:
    """Calculate plutus script data hash

    Args:
        redeemers (Optional[Redeemers]): Redeemers to include.
        datums (Optional[Union[List[Datum], NonEmptyOrderedSet[Datum]]]): Datums to include.
        cost_models (Optional[CostModels]): Cost models.

    Returns:
        ScriptDataHash: Plutus script data hash
    """
    if redeemers is None:
        redeemers = RedeemerMap()
        cost_models = {}
    elif len(redeemers) == 0:
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


def greater_than_version(version: Tuple[int, int]) -> bool:
    """Check if the current Python version is greater than or equal to the specified version

    Args:
        version (Tuple[int, int]): Tuple of major and minor version

    Returns:
        True if the current Python version is greater than or equal to the specified version
    """
    return sys.version_info >= version
