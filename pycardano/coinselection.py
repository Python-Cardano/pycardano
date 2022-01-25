"""
This module contains algorithms that select UTxOs from a parent list to satisfy some output constraints.
"""

from typing import List, Tuple

from pycardano.backend.base import ChainContext
from pycardano.exception import UTxOSelectionException
from pycardano.transaction import UTxO, TransactionOutput, FullMultiAsset
from pycardano.utils import max_tx_fee


class UTxOSelector:
    """UTxOSelector defines an interface through which a subset of UTxOs should be selected from a parent set
        with a selection strategy and given constraints.
    """

    def select(self,
               utxos: List[UTxO],
               outputs: List[TransactionOutput],
               context: ChainContext,
               max_input_count: int = None,
               include_max_fee: bool = True
               ) -> Tuple[List[UTxO], List[FullMultiAsset]]:
        """From an input list of UTxOs, select a subset of UTxOs whose sum (including ADA and multi-assets)
            is equal to or larger than the sum of a set of outputs.

        Args:
            utxos (List[UTxO]): A list of UTxO to select from.
            outputs (List[TransactionOutput]): A list of transaction outputs which the selected set should satisfy.
            context (ChainContext): A chain context where protocol parameters could be retrieved.
            max_input_count (int): Max number of input UTxOs to select.
            include_max_fee (bool): Have selected UTxOs to cover transaction fee. Defaults to True. If disabled,
                there is a possibility that selected UTxO are not able to cover the fee of the transaction.

        Returns:
            Tuple[List[UTxO], List[FullMultiAsset]]: A tuple containing:
                selected (List[UTxO]): A list of selected UTxOs.
                changes (List[FullMultiAsset]): A list of assets as changes to be returned.

        Raises:
            UTxOSelectionException: When it is impossible to select a satisfying set of UTxOs.
        """
        raise NotImplementedError()


class LargestFirstSelector(UTxOSelector):
    """
    Largest first selection algorithm as specified in
        https://github.com/cardano-foundation/CIPs/tree/master/CIP-0002#largest-first.

    This implementation adds transaction fee into consideration.
    """

    def select(self,
               utxos: List[UTxO],
               outputs: List[TransactionOutput],
               context: ChainContext,
               max_input_count: int = None,
               include_max_fee: bool = True
               ) -> Tuple[List[UTxO], List[FullMultiAsset]]:

        available: List[UTxO] = sorted(utxos, key=lambda utxo: utxo.output.lovelace)
        max_fee = max_tx_fee(context) if include_max_fee else 0
        total_requested = FullMultiAsset(max_fee)
        for o in outputs:
            total_requested += o.amount

        selected = []
        selected_amount = FullMultiAsset()

        while not total_requested <= selected_amount:
            if not available:
                raise UTxOSelectionException("UTxO Balance insufficient!")
            to_add = available.pop()
            selected.append(to_add)
            selected_amount += to_add.output.amount

            if max_input_count and len(selected) > max_input_count:
                raise UTxOSelectionException(f"Max input count: {max_input_count} exceeded!")

        changes = [selected_amount - total_requested]

        return selected, changes
