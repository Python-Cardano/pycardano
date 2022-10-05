"""
This module contains algorithms that select UTxOs from a parent list to satisfy some output constraints.
"""

import random
from typing import Iterable, List, Optional, Tuple

from pycardano.address import Address
from pycardano.backend.base import ChainContext
from pycardano.exception import (
    InputUTxODepletedException,
    InsufficientUTxOBalanceException,
    MaxInputCountExceededException,
    UTxOSelectionException,
)
from pycardano.transaction import TransactionOutput, UTxO, Value
from pycardano.utils import max_tx_fee, min_lovelace_post_alonzo

__all__ = ["UTxOSelector", "LargestFirstSelector", "RandomImproveMultiAsset"]

_FAKE_ADDR = Address.from_primitive(
    "addr1q8m9x2zsux7va6w892g38tvchnzahvcd9tykqf3ygnmwta8k2v59pcduem5uw253zwke30x9mwes62kfvqnzg38kuh6q966kg7"
)


class UTxOSelector:
    """UTxOSelector defines an interface through which a subset of UTxOs should be selected from a parent set
    with a selection strategy and given constraints.
    """

    def select(
        self,
        utxos: List[UTxO],
        outputs: List[TransactionOutput],
        context: ChainContext,
        max_input_count: int = None,
        include_max_fee: bool = True,
        respect_min_utxo: bool = True,
    ) -> Tuple[List[UTxO], Value]:
        """From an input list of UTxOs, select a subset of UTxOs whose sum (including ADA and multi-assets)
        is equal to or larger than the sum of a set of outputs.

        Args:
            utxos (List[UTxO]): A list of UTxO to select from.
            outputs (List[TransactionOutput]): A list of transaction outputs which the selected set should satisfy.
            context (ChainContext): A chain context where protocol parameters could be retrieved.
            max_input_count (int): Max number of input UTxOs to select.
            include_max_fee (bool): Have selected UTxOs to cover transaction fee. Defaults to True. If disabled,
                there is a possibility that selected UTxO are not able to cover the fee of the transaction.
            respect_min_utxo (bool): Respect minimum amount of ADA required to hold a multi-asset bundle in the change.
                Defaults to True. If disabled, the selection will not add addition amount of ADA to change even
                when the amount is too small to hold a multi-asset bundle.

        Returns:
            Tuple[List[UTxO], Value]: A tuple containing:

                selected (List[UTxO]): A list of selected UTxOs.

                changes (Value): Change amount to be returned.

        Raises:
            InsufficientUTxOBalanceException: When total value of input UTxO is less than requested outputs.
            MaxInputCountExceededException: When number of selected UTxOs exceeds `max_input_count`.
            InputUTxODepletedException: When the algorithm has depleted input UTxOs but selection should continue.
            UTxOSelectionException: When selection fails for reasons besides the three above.
        """
        raise NotImplementedError()


class LargestFirstSelector(UTxOSelector):
    """
    Largest first selection algorithm as specified in
    https://github.com/cardano-foundation/CIPs/tree/master/CIP-0002#largest-first.

    This implementation adds transaction fee into consideration.
    """

    def select(
        self,
        utxos: List[UTxO],
        outputs: List[TransactionOutput],
        context: ChainContext,
        max_input_count: Optional[int] = None,
        include_max_fee: Optional[bool] = True,
        respect_min_utxo: Optional[bool] = True,
    ) -> Tuple[List[UTxO], Value]:

        available: List[UTxO] = sorted(utxos, key=lambda utxo: utxo.output.lovelace)
        max_fee = max_tx_fee(context) if include_max_fee else 0
        total_requested = Value(max_fee)
        for o in outputs:
            total_requested += o.amount

        selected = []
        selected_amount = Value()

        while not total_requested <= selected_amount:
            if not available:
                raise InsufficientUTxOBalanceException("UTxO Balance insufficient!")
            to_add = available.pop()
            selected.append(to_add)
            selected_amount += to_add.output.amount

            if max_input_count and len(selected) > max_input_count:
                raise MaxInputCountExceededException(
                    f"Max input count: {max_input_count} exceeded!"
                )

        if respect_min_utxo:
            change = selected_amount - total_requested
            min_change_amount = min_lovelace_post_alonzo(
                TransactionOutput(_FAKE_ADDR, change), context
            )

            if change.coin < min_change_amount:
                additional, _ = self.select(
                    available,
                    [TransactionOutput(None, min_change_amount - change.coin)],
                    context,
                    max_input_count - len(selected) if max_input_count else None,
                    include_max_fee=False,
                    respect_min_utxo=False,
                )
                for u in additional:
                    selected.append(u)
                    selected_amount += u.output.amount

        return selected, selected_amount - total_requested


class RandomImproveMultiAsset(UTxOSelector):
    """Random-improve selection algorithm as specified in
    https://github.com/cardano-foundation/CIPs/tree/master/CIP-0002#random-improve.

    Because the original algorithm does not take multi-assets into consideration, this implementation is slightly
    different from the algorithm. The main modification is that it merges all requested transaction outputs into one,
    including all native assets, and then treat each merged native asset as an individual transaction output request.

    This idea is inspired by Nami wallet: https://github.com/Berry-Pool/nami-wallet/blob/main/src/lib/coinSelection.js

    .. Note::
        Although this implementation is similar to the original Random-improve algorithm, and it is being used by some
        wallets, there are no substantial evidences or proofs showing that this implementation will still be able to
        correctly optimize UTxO selection based on
        `three heuristics <https://github.com/cardano-foundation/CIPs/tree/master/CIP-0002#motivating-principles>`_
        mentioned in the doc.
    """

    def __init__(self, random_generator: Optional[Iterable[int]] = None):
        self.random_generator = iter(random_generator) if random_generator else None

    def _get_next_random(self, utxos: List[UTxO]) -> Tuple[int, UTxO]:
        if not utxos:
            raise InputUTxODepletedException("Input UTxOs depleted!")
        if self.random_generator:
            i = next(self.random_generator, None)
            if i is None:
                raise UTxOSelectionException("Random generator depleted!")
            elif i > len(utxos):
                raise UTxOSelectionException(f"Random index: {i} out of range!")
        else:
            i = random.randint(0, len(utxos) - 1)
        return i, utxos[i]

    def _random_select_subset(
        self,
        amount: Value,
        remaining: List[UTxO],
        selected: List[UTxO],
        selected_amount: Value,
    ):
        while not amount <= selected_amount:
            if not remaining:
                raise InputUTxODepletedException("Input UTxOs depleted!")
            i, to_add = self._get_next_random(remaining)
            selected.append(to_add)
            selected_amount += to_add.output.amount
            remaining.pop(i)

    @staticmethod
    def _split_by_asset(value: Value) -> List[Value]:
        # Extract ADA
        assets = [Value(value.coin)]

        # Extract native assets
        for policy_id in value.multi_asset:
            for asset_name in value.multi_asset[policy_id]:
                assets.append(
                    Value.from_primitive(
                        [
                            0,
                            {
                                policy_id.payload: {
                                    asset_name.payload: value.multi_asset[policy_id][
                                        asset_name
                                    ]
                                }
                            },
                        ]
                    )
                )

        return assets

    @staticmethod
    def _get_single_asset_val(value: Value) -> int:
        if value.coin:
            return value.coin
        else:
            return list(list(value.multi_asset.values())[0].values())[0]

    @staticmethod
    def _find_diff_by_former(a: Value, b: Value) -> int:
        """The first argument contains only one asset. Find the absolute difference between this asset and
        the corresponding value of the same asset in the second argument"""
        if a.coin:
            return a.coin - b.coin
        else:
            policy_id = list(a.multi_asset.keys())[0]
            asset_name = list(a.multi_asset[policy_id].keys())[0]
            return (
                a.multi_asset[policy_id][asset_name]
                - b.multi_asset[policy_id][asset_name]
            )

    def _improve(
        self,
        selected: List[UTxO],
        selected_amount: Value,
        remaining: List[UTxO],
        ideal: Value,
        upper_bound: Value,
        max_input_count: int,
    ):
        if not remaining or self._find_diff_by_former(ideal, selected_amount) <= 0:
            # In case where there is no remaining UTxOs or we already selected more than ideal,
            # we cannot improve by randomly adding more UTxOs, therefore return immediate.
            return
        if max_input_count and len(selected) > max_input_count:
            raise MaxInputCountExceededException(
                f"Max input count: {max_input_count} exceeded!"
            )

        i, to_add = self._get_next_random(remaining)
        if (
            abs(
                self._find_diff_by_former(ideal, selected_amount + to_add.output.amount)
            )
            < abs(self._find_diff_by_former(ideal, selected_amount))
            and self._find_diff_by_former(
                upper_bound, selected_amount + to_add.output.amount
            )
            >= 0
        ):
            selected.append(to_add)
            selected_amount += to_add.output.amount

        self._improve(
            selected,
            selected_amount,
            remaining[:i] + remaining[i + 1 :],
            ideal,
            upper_bound,
            max_input_count,
        )

    def select(
        self,
        utxos: List[UTxO],
        outputs: List[TransactionOutput],
        context: ChainContext,
        max_input_count: int = None,
        include_max_fee: bool = True,
        respect_min_utxo: bool = True,
    ) -> Tuple[List[UTxO], Value]:
        # Shallow copy the list
        remaining = list(utxos)
        max_fee = max_tx_fee(context) if include_max_fee else 0
        request_sum = Value(max_fee)
        for o in outputs:
            request_sum += o.amount

        assets = self._split_by_asset(request_sum)
        request_sorted = sorted(assets, key=self._get_single_asset_val, reverse=True)

        # Phase 1 - random select
        selected = []
        selected_amount = Value()
        for r in request_sorted:
            self._random_select_subset(r, remaining, selected, selected_amount)
            if max_input_count and len(selected) > max_input_count:
                raise MaxInputCountExceededException(
                    f"Max input count: {max_input_count} exceeded!"
                )

        # Phase 2 - improve current selection
        for request in reversed(request_sorted):
            ideal = request + request
            upper_bound = ideal + request
            num_selected_before = len(selected)
            try:
                self._improve(
                    selected,
                    selected_amount,
                    list(remaining),
                    ideal,
                    upper_bound,
                    max_input_count,
                )
            except UTxOSelectionException:
                pass
            new_selected = selected[num_selected_before:]
            remaining = [utxo for utxo in remaining if utxo not in new_selected]

        if respect_min_utxo:
            change = selected_amount - request_sum
            min_change_amount = min_lovelace_post_alonzo(
                TransactionOutput(_FAKE_ADDR, change), context
            )

            if change.coin < min_change_amount:
                additional, _ = self.select(
                    remaining,
                    [TransactionOutput(None, min_change_amount - change.coin)],
                    context,
                    max_input_count - len(selected) if max_input_count else None,
                    include_max_fee=False,
                    respect_min_utxo=False,
                )
                for u in additional:
                    selected.append(u)
                    selected_amount += u.output.amount

        return selected, selected_amount - request_sum
