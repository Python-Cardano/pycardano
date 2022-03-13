from __future__ import annotations

from copy import deepcopy
from typing import List, Optional, Set, Union

from pycardano.address import Address
from pycardano.backend.base import ChainContext
from pycardano.coinselection import (
    LargestFirstSelector,
    RandomImproveMultiAsset,
    UTxOSelector,
)
from pycardano.exception import (
    InsufficientUTxOBalanceException,
    InvalidTransactionException,
    UTxOSelectionException,
)
from pycardano.hash import ScriptHash, VerificationKeyHash
from pycardano.key import VerificationKey
from pycardano.logging import logger
from pycardano.metadata import AuxiliaryData
from pycardano.nativescript import NativeScript, ScriptAll, ScriptAny, ScriptPubkey
from pycardano.transaction import (
    Asset,
    AssetName,
    MultiAsset,
    Transaction,
    TransactionBody,
    TransactionOutput,
    UTxO,
    Value,
)
from pycardano.utils import fee, max_tx_fee, min_lovelace
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
        self._required_signers = None

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

    @property
    def required_signers(self) -> List[VerificationKeyHash]:
        return self._required_signers

    @required_signers.setter
    def required_signers(self, signers: List[VerificationKeyHash]):
        self._required_signers = signers

    def _calc_change(self, fees, inputs, outputs, address) -> List[TransactionOutput]:
        requested = Value(fees)
        for o in outputs:
            requested += o.amount

        provided = Value()
        for i in inputs:
            provided += i.output.amount
        if self.mint:
            provided.multi_asset += self.mint

        if not requested < provided:
            raise InvalidTransactionException(
                f"The input UTxOs cannot cover the transaction outputs and tx fee. \n"
                f"Inputs: {inputs} \n"
                f"Outputs: {outputs} \n"
                f"fee: {fees}"
            )

        change = provided - requested
        if change.coin < 0:
            # We assign max fee for now to ensure enough balance regardless of splits condition
            # We can implement a more precise fee logic and requirements later
            raise InsufficientUTxOBalanceException("Not enough ADA to cover fees")

        # Remove any asset that has 0 quantity
        if change.multi_asset:
            change.multi_asset = change.multi_asset.filter(lambda p, n, v: v > 0)

        change_output_arr = []

        # when there is only ADA left, simply use remaining coin value as change
        if not change.multi_asset:
            lovelace_change = change.coin
            change_output_arr.append(TransactionOutput(address, lovelace_change))

        # If there are multi asset in the change
        if change.multi_asset:
            # Split assets if size exceeds limits
            multi_asset_arr = self._pack_tokens_for_change(
                address, change, self.context.protocol_param.max_val_size
            )

            # Include minimum lovelace into each token output except for the last one
            for i, multi_asset in enumerate(multi_asset_arr):
                # Combine remainder of provided ADA with last MultiAsset for output
                # There may be rare cases where adding ADA causes size exceeds limit
                # We will revisit if it becomes an issue
                if i == len(multi_asset_arr) - 1:
                    change_value = Value(change.coin, multi_asset)
                else:
                    change_value = Value(0, multi_asset)
                    change_value.coin = min_lovelace(change_value, self.context)
                change_output_arr.append(TransactionOutput(address, change_value))
                change -= change_value
                # Remove assets with 0 quantity
                change.multi_asset = change.multi_asset.filter(lambda p, n, v: v > 0)

        return change_output_arr

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

    def _adding_asset_make_output_overflow(
        self,
        output: TransactionOutput,
        current_assets: Asset,
        policy_id: ScriptHash,
        add_asset_name: AssetName,
        add_asset_val: int,
        max_val_size: int,
    ) -> bool:
        """Check if adding the asset will make output exceed maximum size limit

        Args:
            output (TransactionOutput): current output
            current_assets (Asset): current Assets to be included in output
            policy_id (ScriptHash): policy id containing the MultiAsset
            asset_to_add (Asset): Asset to add to current MultiAsset to check size limit

        """
        attempt_assets = deepcopy(current_assets)
        attempt_assets += Asset({add_asset_name: add_asset_val})
        attempt_multi_asset = MultiAsset({policy_id: attempt_assets})

        new_amount = Value(0, attempt_multi_asset)
        current_amount = deepcopy(output.amount)
        attempt_amount = new_amount + current_amount

        # Calculate minimum ada requirements for more precise value size
        required_lovelace = min_lovelace(attempt_amount, self.context)
        attempt_amount.coin = required_lovelace

        return len(attempt_amount.to_cbor("bytes")) > max_val_size

    def _pack_tokens_for_change(
        self,
        change_address: Optional[Address],
        change_estimator: Value,
        max_val_size: int,
        ) -> List[MultiAsset]:
        multi_asset_arr = []
        base_coin = Value(coin=change_estimator.coin)
        output = TransactionOutput(change_address, base_coin)

        # iteratively add tokens to output
        for (policy_id, assets) in change_estimator.multi_asset.items():
            temp_multi_asset = MultiAsset()
            temp_value = Value(coin=0)
            temp_assets = Asset()
            old_amount = deepcopy(output.amount)
            for asset_name, asset_value in assets.items():
                if self._adding_asset_make_output_overflow(
                    output,
                    temp_assets,
                    policy_id,
                    asset_name,
                    asset_value,
                    max_val_size,
                ):
                    # Insert current assets as one group
                    temp_multi_asset += MultiAsset({policy_id: temp_multi_asset})
                    temp_value.multi_asset = temp_multi_asset
                    output.amount += temp_value
                    multi_asset_arr.append(output.amount.multi_asset)

                    # Create a new output
                    base_coin = Value(coin=0)
                    output = TransactionOutput(change_address, base_coin)

                    # Continue building output from where we stopped
                    old_amount = output.amount.copy()
                    temp_multi_asset = MultiAsset()
                    temp_value = Value()
                    temp_assets = Asset()

                temp_assets += Asset({asset_name: asset_value})

            # Assess assets in buffer
            temp_multi_asset += MultiAsset({policy_id: temp_assets})
            temp_value.multi_asset = temp_multi_asset
            output.amount += temp_value

            # Calculate min lovelace required for more precise size
            updated_amount = deepcopy(output.amount)
            required_lovelace = min_lovelace(updated_amount, self.context)
            updated_amount.coin = required_lovelace

            if len(updated_amount.to_cbor("bytes")) > max_val_size:
                output.amount = old_amount
                break

            multi_asset_arr.append(output.amount.multi_asset)

        return multi_asset_arr

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
            required_signers=self.required_signers,
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
