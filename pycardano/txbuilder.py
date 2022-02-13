from __future__ import annotations

from typing import List, Optional, Set, Union

from pycardano.address import Address
from pycardano.backend.base import ChainContext
from pycardano.coinselection import (
    LargestFirstSelector,
    RandomImproveMultiAsset,
    UTxOSelector,
)
from pycardano.exception import InvalidTransactionException, UTxOSelectionException
from pycardano.hash import VerificationKeyHash
from pycardano.key import VerificationKey
from pycardano.logging import logger
from pycardano.metadata import AuxiliaryData
from pycardano.nativescript import NativeScript, ScriptAll, ScriptAny, ScriptPubkey
from pycardano.transaction import (
    MultiAsset,
    Transaction,
    TransactionBody,
    TransactionOutput,
    UTxO,
    Value,
)
from pycardano.utils import fee, max_tx_fee
from pycardano.witness import TransactionWitnessSet, VerificationKeyWitness

__all__ = ["TransactionBuilder"]


FAKE_VKEY = VerificationKey.from_primitive(
    bytes.fromhex(
        "58205e750db9facf42b15594790e3ac882e" "d5254eb214a744353a2e24e4e65b8ceb4"
    )
)

# Ed25519 signature of a 32-bytes message (TX hash) will have length of 64
FAKE_TX_SIGNATURE = bytes.fromhex(
    "7a40e127815e62595e8de6fdeac6dd0346b8dbb0275dca5f244b8107cff"
    "e9f9fd8de14b60c3fdc3409e70618d8681afb63b69a107eb1af15f8ef49edb4494001"
)


class TransactionBuilder:
    """A class builder that makes it easy to build a transaction.

    Args:
        context (ChainContext): A chain context.
        utxo_selectors (Optional[List[UTxOSelector]]): A list of UTxOSelectors that will select input UTxOs.
    """

    def __init__(
        self, context: ChainContext, utxo_selectors: Optional[List[UTxOSelector]] = None
    ):
        self.context = context
        self._inputs = []
        self._input_addresses = []
        self._outputs = []
        self._fee = 0
        self._ttl = None
        self._validity_start = None
        self._auxiliary_data = None
        self._native_scripts = None
        self._mint = None

        if utxo_selectors:
            self.utxo_selectors = utxo_selectors
        else:
            self.utxo_selectors = [RandomImproveMultiAsset(), LargestFirstSelector()]

    def add_input(self, utxo: UTxO) -> TransactionBuilder:
        self.inputs.append(utxo)
        return self

    def add_input_address(self, address: Union[Address, str]) -> TransactionBuilder:
        self.input_addresses.append(address)
        return self

    def add_output(self, tx_out: TransactionOutput):
        self.outputs.append(tx_out)
        return self

    @property
    def inputs(self) -> List[UTxO]:
        return self._inputs

    @property
    def input_addresses(self) -> List[Union[Address, str]]:
        return self._input_addresses

    @property
    def outputs(self) -> List[TransactionOutput]:
        return self._outputs

    @property
    def fee(self) -> int:
        return self._fee

    @fee.setter
    def fee(self, fee: int):
        self._fee = fee

    @property
    def ttl(self) -> int:
        return self._ttl

    @ttl.setter
    def ttl(self, ttl: int):
        self._ttl = ttl

    @property
    def mint(self) -> MultiAsset:
        return self._mint

    @mint.setter
    def mint(self, mint: MultiAsset):
        self._mint = mint

    @property
    def auxiliary_data(self) -> AuxiliaryData:
        return self._auxiliary_data

    @auxiliary_data.setter
    def auxiliary_data(self, data: AuxiliaryData):
        self._auxiliary_data = data

    @property
    def native_scripts(self) -> List[NativeScript]:
        return self._native_scripts

    @native_scripts.setter
    def native_scripts(self, scripts: List[NativeScript]):
        self._native_scripts = scripts

    @property
    def validity_start(self):
        return self._validity_start

    @validity_start.setter
    def validity_start(self, validity_start: int):
        self._validity_start = validity_start

    def _calc_change(self, fees, inputs, outputs, address) -> List[TransactionOutput]:
        requested = Value(fees)
        for o in outputs:
            requested += o.amount

        provided = Value()
        for i in inputs:
            provided += i.output.amount
        if self.mint:
            provided.multi_asset += self.mint

        change = provided - requested

        # Remove any asset that has 0 quantity
        if change.multi_asset:
            change.multi_asset = change.multi_asset.filter(lambda p, n, v: v > 0)

        # If we end up with no multi asset, simply use coin value as change
        if not change.multi_asset:
            change = change.coin

        # TODO: Split change if the bundle size exceeds the max utxo size.
        # Currently, there is only one change (UTxO) being returned. This is a native solution, it will fail
        # when there are too many native tokens attached to the change.
        return [TransactionOutput(address, change)]

    def _add_change_and_fee(
        self, change_address: Optional[Address]
    ) -> TransactionBuilder:
        original_outputs = self.outputs[:]
        if change_address:
            # Set fee to max
            self.fee = max_tx_fee(self.context)
            changes = self._calc_change(
                self.fee, self.inputs, self.outputs, change_address
            )
            self._outputs += changes

        self.fee = fee(self.context, len(self._build_full_fake_tx().to_cbor("bytes")))

        if change_address:
            self._outputs = original_outputs
            changes = self._calc_change(
                self.fee, self.inputs, self.outputs, change_address
            )
            self._outputs += changes

        return self

    def _input_vkey_hashes(self) -> Set[VerificationKeyHash]:
        results = set()
        for i in self.inputs:
            if isinstance(i.output.address.payment_part, VerificationKeyHash):
                results.add(i.output.address.payment_part)
        return results

    def _native_scripts_vkey_hashes(self) -> Set[VerificationKeyHash]:
        results = set()

        def _dfs(script: NativeScript):
            tmp = set()
            if isinstance(script, ScriptPubkey):
                tmp.add(script.key_hash)
            elif isinstance(script, (ScriptAll, ScriptAny)):
                for s in script.native_scripts:
                    tmp.update(_dfs(s))
            return tmp

        if self.native_scripts:
            for script in self.native_scripts:
                results.update(_dfs(script))

        return results

    def _build_tx_body(self) -> TransactionBody:
        tx_body = TransactionBody(
            [i.input for i in self.inputs],
            self.outputs,
            fee=self.fee,
            ttl=self.ttl,
            mint=self.mint,
            auxiliary_data_hash=self.auxiliary_data.hash()
            if self.auxiliary_data
            else None,
            validity_start=self.validity_start,
        )
        return tx_body

    def _build_fake_vkey_witnesses(self) -> List[VerificationKeyWitness]:
        vkey_hashes = self._input_vkey_hashes()
        vkey_hashes.update(self._native_scripts_vkey_hashes())
        return [
            VerificationKeyWitness(FAKE_VKEY, FAKE_TX_SIGNATURE) for _ in vkey_hashes
        ]

    def _build_fake_witness_set(self) -> TransactionWitnessSet:
        return TransactionWitnessSet(
            vkey_witnesses=self._build_fake_vkey_witnesses(),
            native_scripts=self.native_scripts,
        )

    def _build_full_fake_tx(self) -> Transaction:
        tx_body = self._build_tx_body()
        witness = self._build_fake_witness_set()
        tx = Transaction(tx_body, witness, True, self.auxiliary_data)
        size = len(tx.to_cbor("bytes"))
        if size > self.context.protocol_param.max_tx_size:
            raise InvalidTransactionException(
                f"Transaction size ({size}) exceeds the max limit "
                f"({self.context.protocol_param.max_tx_size}). Please try reducing the "
                f"number of inputs or outputs."
            )
        return tx

    def build(self, change_address: Optional[Address] = None) -> TransactionBody:
        """Build a transaction body from all constraints set through the builder.

        Args:
            change_address (Optional[Address]): Address to which changes will be returned. If not provided, the
                transaction body will likely be unbalanced (sum of inputs is greater than the sum of outputs).

        Returns:
            A transaction body.
        """
        selected_utxos = []
        selected_amount = Value()
        for i in self.inputs:
            selected_utxos.append(i)
            selected_amount += i.output.amount
        if self.mint:
            selected_amount.multi_asset += self.mint

        requested_amount = Value()
        for o in self.outputs:
            requested_amount += o.amount

        # Trim off assets that are not requested because they will be returned as changes eventually.
        trimmed_selected_amount = Value(
            selected_amount.coin,
            selected_amount.multi_asset.filter(
                lambda p, n, v: p in requested_amount.multi_asset
                and n in requested_amount.multi_asset[p]
            ),
        )

        unfulfilled_amount = requested_amount - trimmed_selected_amount
        unfulfilled_amount.coin = max(0, unfulfilled_amount.coin)
        # Clean up all non-positive assets
        unfulfilled_amount.multi_asset = unfulfilled_amount.multi_asset.filter(
            lambda p, n, v: v > 0
        )

        # When there are positive coin or native asset quantity in unfulfilled Value
        if Value() < unfulfilled_amount:
            additional_utxo_pool = []
            for address in self.input_addresses:
                for utxo in self.context.utxos(str(address)):
                    if utxo not in selected_utxos:
                        additional_utxo_pool.append(utxo)

            for i, selector in enumerate(self.utxo_selectors):
                try:
                    selected, _ = selector.select(
                        additional_utxo_pool,
                        [TransactionOutput(None, unfulfilled_amount)],
                        self.context,
                    )
                    for s in selected:
                        selected_amount += s.output.amount
                        selected_utxos.append(s)

                    break

                except UTxOSelectionException as e:
                    if i < len(self.utxo_selectors) - 1:
                        logger.info(e)
                        logger.info(f"{selector} failed. Trying next selector.")
                    else:
                        raise UTxOSelectionException("All UTxO selectors failed.")

        selected_utxos.sort(
            key=lambda utxo: (str(utxo.input.transaction_id), utxo.input.index)
        )

        self.inputs[:] = selected_utxos[:]

        self._add_change_and_fee(change_address)

        tx_body = self._build_tx_body()

        return tx_body
