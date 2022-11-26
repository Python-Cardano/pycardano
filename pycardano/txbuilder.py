from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field, fields
from typing import Dict, List, Optional, Set, Tuple, Union

from pycardano.address import Address, AddressType
from pycardano.backend.base import ChainContext
from pycardano.certificate import (
    Certificate,
    StakeCredential,
    StakeDelegation,
    StakeDeregistration,
    StakeRegistration,
)
from pycardano.coinselection import (
    LargestFirstSelector,
    RandomImproveMultiAsset,
    UTxOSelector,
)
from pycardano.exception import (
    InsufficientUTxOBalanceException,
    InvalidArgumentException,
    InvalidTransactionException,
    TransactionBuilderException,
    UTxOSelectionException,
)
from pycardano.hash import DatumHash, ScriptDataHash, ScriptHash, VerificationKeyHash
from pycardano.key import ExtendedSigningKey, SigningKey, VerificationKey
from pycardano.logging import logger
from pycardano.metadata import AuxiliaryData
from pycardano.nativescript import NativeScript, ScriptAll, ScriptAny, ScriptPubkey
from pycardano.plutus import (
    PLUTUS_V1_COST_MODEL,
    PLUTUS_V2_COST_MODEL,
    CostModels,
    Datum,
    ExecutionUnits,
    PlutusV1Script,
    PlutusV2Script,
    Redeemer,
    RedeemerTag,
    datum_hash,
    script_hash,
)
from pycardano.transaction import (
    Asset,
    AssetName,
    MultiAsset,
    Transaction,
    TransactionBody,
    TransactionInput,
    TransactionOutput,
    UTxO,
    Value,
    Withdrawals,
)
from pycardano.utils import fee, max_tx_fee, min_lovelace_post_alonzo, script_data_hash
from pycardano.witness import TransactionWitnessSet, VerificationKeyWitness

__all__ = ["TransactionBuilder"]

FAKE_VKEY = VerificationKey.from_primitive(
    bytes.fromhex("5797dc2cc919dfec0bb849551ebdf30d96e5cbe0f33f734a87fe826db30f7ef9")
)

# Ed25519 signature of a 32-bytes message (TX hash) will have length of 64
FAKE_TX_SIGNATURE = bytes.fromhex(
    "577ccb5b487b64e396b0976c6f71558e52e44ad254db7d06dfb79843e5441a5d763dd42a"
    "dcf5e8805d70373722ebbce62a58e3f30dd4560b9a898b8ceeab6a03"
)


@dataclass
class TransactionBuilder:
    """A class builder that makes it easy to build a transaction."""

    context: ChainContext

    utxo_selectors: List[UTxOSelector] = field(
        default_factory=lambda: [RandomImproveMultiAsset(), LargestFirstSelector()]
    )

    execution_memory_buffer: float = 0.2
    """Additional amount of execution memory (in ratio) that will be on top of estimation"""

    execution_step_buffer: float = 0.2
    """Additional amount of execution step (in ratio) that will be added on top of estimation"""

    ttl: int = field(default=None)

    validity_start: int = field(default=None)

    auxiliary_data: AuxiliaryData = field(default=None)

    native_scripts: List[NativeScript] = field(default=None)

    mint: MultiAsset = field(default=None)

    required_signers: List[VerificationKeyHash] = field(default=None)

    collaterals: List[UTxO] = field(default_factory=lambda: [])

    certificates: List[Certificate] = field(default=None)

    withdrawals: Withdrawals = field(default=None)

    reference_inputs: Set[TransactionInput] = field(
        init=False, default_factory=lambda: set()
    )

    _inputs: List[UTxO] = field(init=False, default_factory=lambda: [])

    _excluded_inputs: List[UTxO] = field(init=False, default_factory=lambda: [])

    _input_addresses: List[Address] = field(init=False, default_factory=lambda: [])

    _outputs: List[TransactionOutput] = field(init=False, default_factory=lambda: [])

    _fee: int = field(init=False, default=0)

    _datums: Dict[DatumHash, Datum] = field(init=False, default_factory=lambda: {})

    _collateral_return: TransactionOutput = field(init=False, default=None)

    _total_collateral: int = field(init=False, default=None)

    _inputs_to_redeemers: Dict[UTxO, Redeemer] = field(
        init=False, default_factory=lambda: {}
    )

    _minting_script_to_redeemers: List[Tuple[bytes, Redeemer]] = field(
        init=False, default_factory=lambda: []
    )

    _inputs_to_scripts: Dict[UTxO, bytes] = field(
        init=False, default_factory=lambda: {}
    )

    _reference_scripts: List[
        Union[NativeScript, PlutusV1Script, PlutusV2Script]
    ] = field(init=False, default_factory=lambda: [])

    _should_estimate_execution_units: bool = field(init=False, default=None)

    def add_input(self, utxo: UTxO) -> TransactionBuilder:
        """Add a specific UTxO to transaction's inputs.

        Args:
            utxo (UTxO): UTxO to be added.

        Returns:
            TransactionBuilder: Current transaction builder.
        """
        self.inputs.append(utxo)
        return self

    def _consolidate_redeemer(self, redeemer):
        if self._should_estimate_execution_units is None:
            if redeemer.ex_units:
                self._should_estimate_execution_units = False
            else:
                self._should_estimate_execution_units = True
                redeemer.ex_units = ExecutionUnits(0, 0)
        else:
            if not self._should_estimate_execution_units and redeemer.ex_units is None:
                raise InvalidArgumentException(
                    f"All redeemers need to provide execution units if the firstly "
                    f"added redeemer specifies execution units. \n"
                    f"Added redeemers: {self.redeemers} \n"
                    f"New redeemer: {redeemer}"
                )
            if self._should_estimate_execution_units:
                if redeemer.ex_units is not None:
                    raise InvalidArgumentException(
                        f"No redeemer should provide execution units if the firstly "
                        f"added redeemer didn't provide execution units. \n"
                        f"Added redeemers: {self.redeemers} \n"
                        f"New redeemer: {redeemer}"
                    )
                else:
                    redeemer.ex_units = ExecutionUnits(0, 0)

    def add_script_input(
        self,
        utxo: UTxO,
        script: Optional[
            Union[UTxO, NativeScript, PlutusV1Script, PlutusV2Script]
        ] = None,
        datum: Optional[Datum] = None,
        redeemer: Optional[Redeemer] = None,
    ) -> TransactionBuilder:
        """Add a script UTxO to transaction's inputs.

        Args:
            utxo (UTxO): Script UTxO to be added.
            script (Optional[Union[UTxO, NativeScript, PlutusV1Script, PlutusV2Script]]): A plutus script.
                If not provided, the script will be inferred from the input UTxO (first arg of this method).
                The script can also be a specific UTxO whose output contains an inline script.
            datum (Optional[Datum]): A plutus datum to unlock the UTxO.
            redeemer (Optional[Redeemer]): A plutus redeemer to unlock the UTxO.

        Returns:
            TransactionBuilder: Current transaction builder.
        """
        if not utxo.output.address.address_type.name.startswith("SCRIPT"):
            raise InvalidArgumentException(
                f"Expect the output address of utxo to be script type, "
                f"but got {utxo.output.address.address_type} instead."
            )
        if utxo.output.datum_hash and utxo.output.datum_hash != datum_hash(datum):
            raise InvalidArgumentException(
                f"Datum hash in transaction output is {utxo.output.datum_hash}, "
                f"but actual datum hash from input datum is {datum_hash(datum)}."
            )

        if datum:
            self.datums[datum_hash(datum)] = datum

        if redeemer:
            self._consolidate_redeemer(redeemer)
            self._inputs_to_redeemers[utxo] = redeemer

        if utxo.output.script:
            self._inputs_to_scripts[utxo] = utxo.output.script
            self.reference_inputs.add(utxo.input)
            self._reference_scripts.append(utxo.output.script)
        elif not script:
            for i in self.context.utxos(str(utxo.output.address)):
                if i.output.script:
                    self._inputs_to_scripts[utxo] = i.output.script
                    self.reference_inputs.add(i.input)
                    self._reference_scripts.append(i.output.script)
                    break
        elif isinstance(script, UTxO):
            self._inputs_to_scripts[utxo] = script.output.script
            self.reference_inputs.add(script.input)
            self._reference_scripts.append(script.output.script)
        else:
            self._inputs_to_scripts[utxo] = script

        self.inputs.append(utxo)
        return self

    def add_minting_script(
        self,
        script: Union[UTxO, NativeScript, PlutusV1Script, PlutusV2Script],
        redeemer: Optional[Redeemer] = None,
    ) -> TransactionBuilder:
        """Add a minting script along with its datum and redeemer to this transaction.

        Args:
            script (Union[UTxO, PlutusV1Script, PlutusV2Script]): A plutus script.
            redeemer (Optional[Redeemer]): A plutus redeemer to unlock the UTxO.

        Returns:
            TransactionBuilder: Current transaction builder.
        """
        if redeemer:
            if redeemer.tag != RedeemerTag.MINT:
                raise InvalidArgumentException(
                    f"Expect the redeemer tag's type to be {RedeemerTag.MINT}, "
                    f"but got {redeemer.tag} instead."
                )
            self._consolidate_redeemer(redeemer)

        if isinstance(script, UTxO):
            self._minting_script_to_redeemers.append((script.output.script, redeemer))
            self.reference_inputs.add(script.input)
            self._reference_scripts.append(script.output.script)
        else:
            self._minting_script_to_redeemers.append((script, redeemer))
        return self

    def add_input_address(self, address: Union[Address, str]) -> TransactionBuilder:
        """Add an address to transaction's input address.
        Unlike :meth:`add_input`, which deterministically adds a UTxO to the transaction's inputs, `add_input_address`
        will not immediately select any UTxO when called. Instead, it will delegate UTxO selection to
        :class:`UTxOSelector`s of the builder when :meth:`build` is called.

        Args:
            address (Union[Address, str]): Address to be added.

        Returns:
            TransactionBuilder: The current transaction builder.
        """
        self.input_addresses.append(address)
        return self

    def add_output(
        self,
        tx_out: TransactionOutput,
        datum: Optional[Datum] = None,
        add_datum_to_witness: bool = False,
    ) -> TransactionBuilder:
        """Add a transaction output.

        Args:
            tx_out (TransactionOutput): The transaction output to be added.
            datum (Datum): Attach a datum hash to this transaction output.
            add_datum_to_witness (bool): Optionally add the actual datum to transaction witness set. Defaults to False.

        Returns:
            TransactionBuilder: Current transaction builder.
        """
        if datum:
            tx_out.datum_hash = datum_hash(datum)
        self.outputs.append(tx_out)
        if add_datum_to_witness:
            self.datums[datum_hash(datum)] = datum
        return self

    @property
    def inputs(self) -> List[UTxO]:
        return self._inputs

    @property
    def excluded_inputs(self) -> List[UTxO]:
        return self._excluded_inputs

    @excluded_inputs.setter
    def excluded_inputs(self, excluded_inputs: List[UTxO]):
        self._excluded_inputs = excluded_inputs

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
    def all_scripts(self) -> List[bytes]:
        scripts = {}

        if self.native_scripts:
            for s in self.native_scripts:
                scripts[script_hash(s)] = s

        for s in self._inputs_to_scripts.values():
            scripts[script_hash(s)] = s

        for s, _ in self._minting_script_to_redeemers:
            scripts[script_hash(s)] = s

        return list(scripts.values())

    @property
    def scripts(self) -> List[bytes]:
        scripts = {script_hash(s): s for s in self.all_scripts}

        for s in self._reference_scripts:
            if script_hash(s) in scripts:
                scripts.pop(script_hash(s))

        return list(scripts.values())

    @property
    def datums(self) -> Dict[DatumHash, Datum]:
        return self._datums

    @property
    def redeemers(self) -> List[Redeemer]:
        return list(self._inputs_to_redeemers.values()) + [
            r for _, r in self._minting_script_to_redeemers
        ]

    @property
    def script_data_hash(self) -> Optional[ScriptDataHash]:
        if self.datums or self.redeemers:
            cost_models = {}
            for s in self.all_scripts:
                if isinstance(s, PlutusV1Script) or type(s) == bytes:
                    cost_models[0] = (
                        self.context.protocol_param.cost_models.get("PlutusV1")
                        or PLUTUS_V1_COST_MODEL
                    )
                if isinstance(s, PlutusV2Script):
                    cost_models[1] = (
                        self.context.protocol_param.cost_models.get("PlutusV2")
                        or PLUTUS_V2_COST_MODEL
                    )
            return script_data_hash(
                self.redeemers, list(self.datums.values()), CostModels(cost_models)
            )
        else:
            return None

    def _calc_change(
        self, fees, inputs, outputs, address, precise_fee=False, respect_min_utxo=True
    ) -> List[TransactionOutput]:
        requested = Value(fees)
        for o in outputs:
            requested += o.amount

        provided = Value()
        for i in inputs:
            provided += i.output.amount
        if self.mint:
            provided.multi_asset += self.mint
        if self.withdrawals:
            for v in self.withdrawals.values():
                provided.coin += v

        provided.coin -= self._get_total_key_deposit()

        if not requested < provided:
            raise InvalidTransactionException(
                f"The input UTxOs cannot cover the transaction outputs and tx fee. \n"
                f"Inputs: {inputs} \n"
                f"Outputs: {outputs} \n"
                f"fee: {fees}"
            )

        change = provided - requested

        # Remove any asset that has 0 quantity
        if change.multi_asset:
            change.multi_asset = change.multi_asset.filter(lambda p, n, v: v > 0)

        change_output_arr = []

        # when there is only ADA left, simply use remaining coin value as change
        if not change.multi_asset:
            if respect_min_utxo and change.coin < min_lovelace_post_alonzo(
                TransactionOutput(address, change), self.context
            ):
                raise InsufficientUTxOBalanceException(
                    f"Not enough ADA left for change: {change.coin} but needs "
                    f"{min_lovelace_post_alonzo(TransactionOutput(address, change), self.context)}"
                )
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
                if respect_min_utxo and change.coin < min_lovelace_post_alonzo(
                    TransactionOutput(address, Value(0, multi_asset)), self.context
                ):
                    raise InsufficientUTxOBalanceException(
                        "Not enough ADA left to cover non-ADA assets in a change address"
                    )

                if i == len(multi_asset_arr) - 1:
                    # Include all ada in last output
                    change_value = Value(change.coin, multi_asset)
                else:
                    change_value = Value(0, multi_asset)
                    change_value.coin = min_lovelace_post_alonzo(
                        TransactionOutput(address, change_value), self.context
                    )

                change_output_arr.append(TransactionOutput(address, change_value))
                change -= change_value
                change.multi_asset = change.multi_asset.filter(lambda p, n, v: v > 0)

        return change_output_arr

    def _add_change_and_fee(
        self,
        change_address: Optional[Address],
        merge_change: Optional[bool] = False,
    ) -> TransactionBuilder:
        original_outputs = deepcopy(self.outputs)
        change_output_index = None

        def _merge_changes(changes):
            if change_output_index is not None and len(changes) == 1:
                # Add the leftover change to the TransactionOutput containing the change address
                self._outputs[change_output_index].amount = (
                    changes[0].amount + self._outputs[change_output_index].amount
                )
                # if we enforce that TransactionOutputs must use Values for `amount`, we can use += here

            else:
                self._outputs += changes

        if change_address:

            if merge_change:

                for idx, output in enumerate(original_outputs):

                    # Find any transaction outputs which already contain the change address
                    if change_address == output.address:
                        if change_output_index is None or output.lovelace == 0:
                            change_output_index = idx

            # Set fee to max
            self.fee = self._estimate_fee()
            changes = self._calc_change(
                self.fee,
                self.inputs,
                self.outputs,
                change_address,
                precise_fee=True,
                respect_min_utxo=not merge_change,
            )

            _merge_changes(changes)

        # With changes included, we can estimate the fee more precisely
        self.fee = self._estimate_fee()

        if change_address:
            self._outputs = original_outputs
            changes = self._calc_change(
                self.fee,
                self.inputs,
                self.outputs,
                change_address,
                precise_fee=True,
                respect_min_utxo=not merge_change,
            )

            _merge_changes(changes)

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
            output (TransactionOutput): Current output
            current_assets (Asset): Current Assets to be included in output
            policy_id (ScriptHash): Policy id containing the MultiAsset
            add_asset_name (AssetName): Name of asset to add to current MultiAsset
            add_asset_val (int): Value of asset to add to current MultiAsset
            max_val_size (int): maximum size limit for output

        Returns:
            bool: whether adding asset will make output greater than maximum size limit
        """
        attempt_assets = deepcopy(current_assets)
        attempt_assets += Asset({add_asset_name: add_asset_val})
        attempt_multi_asset = MultiAsset({policy_id: attempt_assets})

        new_amount = Value(0, attempt_multi_asset)
        current_amount = deepcopy(output.amount)
        attempt_amount = new_amount + current_amount

        # Calculate minimum ada requirements for more precise value size
        required_lovelace = min_lovelace_post_alonzo(
            TransactionOutput(output.address, attempt_amount), self.context
        )
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
                    # Insert current assets as one group if current assets isn't null
                    # This handles edge case when first Asset from next policy will cause overflow
                    if temp_assets:
                        temp_multi_asset += MultiAsset({policy_id: temp_assets})
                        temp_value.multi_asset = temp_multi_asset
                        output.amount += temp_value
                    multi_asset_arr.append(output.amount.multi_asset)

                    # Create a new output
                    base_coin = Value(coin=0)
                    output = TransactionOutput(change_address, base_coin)

                    # Continue building output from where we stopped
                    old_amount = deepcopy(output.amount)
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
            required_lovelace = min_lovelace_post_alonzo(
                TransactionOutput(change_address, updated_amount), self.context
            )
            updated_amount.coin = required_lovelace

            if len(updated_amount.to_cbor("bytes")) > max_val_size:
                output.amount = old_amount
                break

        multi_asset_arr.append(output.amount.multi_asset)
        # Remove records where MultiAsset is null due to overflow of adding
        # items at the beginning of next policy to previous policy MultiAssets
        return multi_asset_arr

    def _required_signer_vkey_hashes(self) -> Set[VerificationKeyHash]:
        return set(self.required_signers) if self.required_signers else set()

    def _input_vkey_hashes(self) -> Set[VerificationKeyHash]:
        results = set()
        for i in self.inputs + self.collaterals:
            if isinstance(i.output.address.payment_part, VerificationKeyHash):
                results.add(i.output.address.payment_part)
        return results

    def _certificate_vkey_hashes(self) -> Set[VerificationKeyHash]:

        results = set()

        def _check_and_add_vkey(stake_credential: StakeCredential):
            if isinstance(stake_credential.credential, VerificationKeyHash):
                results.add(stake_credential.credential)

        if self.certificates:
            for cert in self.certificates:
                if isinstance(
                    cert, (StakeRegistration, StakeDeregistration, StakeDelegation)
                ):
                    _check_and_add_vkey(cert.stake_credential)
        return results

    def _get_total_key_deposit(self):
        results = set()
        if self.certificates:
            for cert in self.certificates:
                if isinstance(cert, StakeRegistration):
                    results.add(cert.stake_credential.credential)
        return self.context.protocol_param.key_deposit * len(results)

    def _withdrawal_vkey_hashes(self) -> Set[VerificationKeyHash]:

        results = set()

        if self.withdrawals:
            for k in self.withdrawals:
                address = Address.from_primitive(k)
                if address.address_type == AddressType.NONE_KEY:
                    results.add(address.staking_part)

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

    def _set_redeemer_index(self):
        # Set redeemers' index according to section 4.1 in
        # https://hydra.iohk.io/build/13099856/download/1/alonzo-changes.pdf

        if self.mint:
            sorted_mint_policies = sorted(
                self.mint.keys(), key=lambda x: x.to_cbor("bytes")
            )
        else:
            sorted_mint_policies = []

        for i, utxo in enumerate(self.inputs):
            if (
                utxo in self._inputs_to_redeemers
                and self._inputs_to_redeemers[utxo].tag == RedeemerTag.SPEND
            ):
                self._inputs_to_redeemers[utxo].index = i
            elif (
                utxo in self._inputs_to_redeemers
                and self._inputs_to_redeemers[utxo].tag == RedeemerTag.MINT
            ):
                redeemer = self._inputs_to_redeemers[utxo]
                redeemer.index = sorted_mint_policies.index(
                    script_hash(self._inputs_to_scripts[utxo])
                )

        for script, redeemer in self._minting_script_to_redeemers:
            redeemer.index = sorted_mint_policies.index(script_hash(script))

        self.redeemers.sort(key=lambda r: r.index)

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
            script_data_hash=self.script_data_hash,
            required_signers=self.required_signers,
            validity_start=self.validity_start,
            collateral=[c.input for c in self.collaterals]
            if self.collaterals
            else None,
            certificates=self.certificates,
            withdraws=self.withdrawals,
            collateral_return=self._collateral_return,
            total_collateral=self._total_collateral,
            reference_inputs=list(self.reference_inputs) or None,
        )
        return tx_body

    def _build_fake_vkey_witnesses(self) -> List[VerificationKeyWitness]:
        vkey_hashes = self._input_vkey_hashes()
        vkey_hashes.update(self._required_signer_vkey_hashes())
        vkey_hashes.update(self._native_scripts_vkey_hashes())
        vkey_hashes.update(self._certificate_vkey_hashes())
        vkey_hashes.update(self._withdrawal_vkey_hashes())
        return [
            VerificationKeyWitness(FAKE_VKEY, FAKE_TX_SIGNATURE) for _ in vkey_hashes
        ]

    def _build_fake_witness_set(self) -> TransactionWitnessSet:
        witness_set = self.build_witness_set()
        witness_set.vkey_witnesses = self._build_fake_vkey_witnesses()
        return witness_set

    def _build_full_fake_tx(self) -> Transaction:
        tx_body = self._build_tx_body()

        if tx_body.fee == 0:
            # When fee is not specified, we will use max possible fee to fill in the fee field.
            # This will make sure the size of fee field itself is taken into account during fee estimation.
            tx_body.fee = max_tx_fee(self.context)

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

    def build_witness_set(self) -> TransactionWitnessSet:
        """Build a transaction witness set, excluding verification key witnesses.
        This function is especially useful when the transaction involves Plutus scripts.

        Returns:
            TransactionWitnessSet: A transaction witness set without verification key witnesses.
        """

        native_scripts = []
        plutus_v1_scripts = []
        plutus_v2_scripts = []

        for script in self.scripts:
            if isinstance(script, NativeScript):
                native_scripts.append(script)
            elif isinstance(script, PlutusV1Script) or type(script) is bytes:
                plutus_v1_scripts.append(script)
            elif isinstance(script, PlutusV2Script):
                plutus_v2_scripts.append(script)
            else:
                raise InvalidArgumentException(
                    f"Unsupported script type: {type(script)}"
                )

        return TransactionWitnessSet(
            native_scripts=native_scripts if native_scripts else None,
            plutus_v1_script=plutus_v1_scripts if plutus_v1_scripts else None,
            plutus_v2_script=plutus_v2_scripts if plutus_v2_scripts else None,
            redeemer=self.redeemers if self.redeemers else None,
            plutus_data=list(self.datums.values()) if self.datums else None,
        )

    def _ensure_no_input_exclusion_conflict(self):
        intersection = set(self.inputs).intersection(set(self.excluded_inputs))
        if intersection:
            raise TransactionBuilderException(
                f"Found common UTxOs between UTxO inputs and UTxO excluded_inputs: "
                f"{intersection}."
            )

    def _estimate_fee(self):
        plutus_execution_units = ExecutionUnits(0, 0)
        for redeemer in self.redeemers:
            plutus_execution_units += redeemer.ex_units

        estimated_fee = fee(
            self.context,
            len(self._build_full_fake_tx().to_cbor("bytes")),
            plutus_execution_units.steps,
            plutus_execution_units.mem,
        )

        return estimated_fee

    def build(
        self,
        change_address: Optional[Address] = None,
        merge_change: Optional[bool] = False,
        collateral_change_address: Optional[Address] = None,
    ) -> TransactionBody:
        """Build a transaction body from all constraints set through the builder.

        Args:
            change_address (Optional[Address]): Address to which changes will be returned. If not provided, the
                transaction body will likely be unbalanced (sum of inputs is greater than the sum of outputs).
            merge_change (Optional[bool]): If the change address match one of the transaction output, the change amount
                will be directly added to that transaction output, instead of being added as a separate output.
            collateral_change_address (Optional[Address]): Address to which collateral changes will be returned.

        Returns:
            TransactionBody: A transaction body.
        """
        self._ensure_no_input_exclusion_conflict()
        selected_utxos = []
        selected_amount = Value()
        for i in self.inputs:
            selected_utxos.append(i)
            selected_amount += i.output.amount

        if self.mint:
            selected_amount.multi_asset += self.mint

        if self.withdrawals:
            for v in self.withdrawals.values():
                selected_amount.coin += v

        can_merge_change = False
        if merge_change:
            for o in self.outputs:
                if o.address == change_address:
                    can_merge_change = True
                    break

        selected_amount.coin -= self._get_total_key_deposit()

        requested_amount = Value()
        for o in self.outputs:
            requested_amount += o.amount

        # Include min fees associated as part of requested amount
        requested_amount += self._estimate_fee()

        # Trim off assets that are not requested because they will be returned as changes eventually.
        trimmed_selected_amount = Value(
            selected_amount.coin,
            selected_amount.multi_asset.filter(
                lambda p, n, v: p in requested_amount.multi_asset
                and n in requested_amount.multi_asset[p]
            ),
        )

        unfulfilled_amount = requested_amount - trimmed_selected_amount

        if change_address is not None and not can_merge_change:
            # If change address is provided and remainder is smaller than minimum ADA required in change,
            # we need to select additional UTxOs available from the address
            if unfulfilled_amount.coin < 0:
                unfulfilled_amount.coin = max(
                    0,
                    unfulfilled_amount.coin
                    + min_lovelace_post_alonzo(
                        TransactionOutput(
                            change_address, selected_amount - trimmed_selected_amount
                        ),
                        self.context,
                    ),
                )
        else:
            unfulfilled_amount.coin = max(0, unfulfilled_amount.coin)

        # Clean up all non-positive assets
        unfulfilled_amount.multi_asset = unfulfilled_amount.multi_asset.filter(
            lambda p, n, v: v > 0
        )

        # When there are positive coin or native asset quantity in unfulfilled Value
        if Value() < unfulfilled_amount:
            additional_utxo_pool = []
            additional_amount = Value()
            for address in self.input_addresses:
                for utxo in self.context.utxos(str(address)):
                    if (
                        utxo not in selected_utxos
                        and utxo not in self.excluded_inputs
                        and not utxo.output.datum_hash  # UTxO with datum should be added by using `add_script_input`
                        and not utxo.output.datum
                        and not utxo.output.script
                    ):
                        additional_utxo_pool.append(utxo)
                        additional_amount += utxo.output.amount

            for i, selector in enumerate(self.utxo_selectors):
                try:
                    selected, _ = selector.select(
                        additional_utxo_pool,
                        [TransactionOutput(None, unfulfilled_amount)],
                        self.context,
                        include_max_fee=False,
                        respect_min_utxo=not can_merge_change,
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
                        trimmed_additional_amount = Value(
                            additional_amount.coin,
                            additional_amount.multi_asset.filter(
                                lambda p, n, v: p in requested_amount.multi_asset
                                and n in requested_amount.multi_asset[p]
                            ),
                        )
                        diff = (
                            requested_amount
                            - trimmed_selected_amount
                            - trimmed_additional_amount
                        )
                        diff.multi_asset = diff.multi_asset.filter(
                            lambda p, n, v: v > 0
                        )
                        raise UTxOSelectionException(
                            f"All UTxO selectors failed.\n"
                            f"Requested output:\n {requested_amount} \n"
                            f"Pre-selected inputs:\n {selected_amount} \n"
                            f"Additional UTxO pool:\n {additional_utxo_pool} \n"
                            f"Unfulfilled amount:\n {diff}"
                        )

        selected_utxos.sort(
            key=lambda utxo: (str(utxo.input.transaction_id), utxo.input.index)
        )

        self.inputs[:] = selected_utxos[:]

        self._set_redeemer_index()

        self._set_collateral_return(collateral_change_address or change_address)

        self._update_execution_units(
            change_address, merge_change, collateral_change_address
        )

        self._add_change_and_fee(change_address, merge_change=merge_change)

        tx_body = self._build_tx_body()

        return tx_body

    def _set_collateral_return(self, collateral_return_address: Address):
        """Calculate and set the change returned from the collateral inputs.

        Args:
            collateral_return_address (Address): Address to which the collateral change will be returned.
        """
        witnesses = self._build_fake_witness_set()

        # Make sure there is at least one script input
        if (
            not witnesses.plutus_v1_script
            and not witnesses.plutus_v2_script
            and not self._reference_scripts
        ):
            return

        if not collateral_return_address:
            return

        collateral_amount = (
            max_tx_fee(context=self.context)
            * self.context.protocol_param.collateral_percent
            // 100
        )

        if not self.collaterals:
            tmp_val = Value()

            def _add_collateral_input(cur_total, candidate_inputs):
                while cur_total.coin < collateral_amount and candidate_inputs:
                    candidate = candidate_inputs.pop()
                    if (
                        not candidate.output.address.address_type.name.startswith(
                            "SCRIPT"
                        )
                        and candidate.output.amount.coin > 2000000
                    ):
                        self.collaterals.append(candidate)
                        cur_total += candidate.output.amount

            sorted_inputs = sorted(
                self.inputs.copy(),
                key=lambda i: (len(i.output.to_cbor()), -i.output.amount.coin),
            )
            _add_collateral_input(tmp_val, sorted_inputs)

            if tmp_val.coin < collateral_amount:
                sorted_inputs = sorted(
                    self.context.utxos(str(collateral_return_address)),
                    key=lambda i: (len(i.output.to_cbor()), -i.output.amount.coin),
                )
                _add_collateral_input(tmp_val, sorted_inputs)

        total_input = Value()

        for utxo in self.collaterals:
            total_input += utxo.output.amount

        if collateral_amount > total_input.coin:
            raise ValueError(
                f"Minimum collateral amount {collateral_amount} is greater than total "
                f"provided collateral inputs {total_input}"
            )
        else:
            return_amount = total_input - collateral_amount
            min_lovelace_val = min_lovelace_post_alonzo(
                TransactionOutput(collateral_return_address, return_amount),
                self.context,
            )
            if min_lovelace_val > return_amount.coin:
                raise ValueError(
                    f"Minimum lovelace amount for collateral return {min_lovelace_val} is "
                    f"greater than collateral change {return_amount.coin}. Please provide more collateral inputs."
                )
            else:
                self._collateral_return = TransactionOutput(
                    collateral_return_address, total_input - collateral_amount
                )
                self._total_collateral = collateral_amount

    def _update_execution_units(
        self,
        change_address: Optional[Address] = None,
        merge_change: bool = False,
        collateral_change_address: Optional[Address] = None,
    ):
        if self._should_estimate_execution_units:
            estimated_execution_units = self._estimate_execution_units(
                change_address, merge_change, collateral_change_address
            )
            for r in self.redeemers:
                key = f"{r.tag.name.lower()}:{r.index}"
                if key not in estimated_execution_units:
                    raise TransactionBuilderException(
                        f"Cannot find execution unit for redeemer: {r} "
                        f"in estimated execution units: {estimated_execution_units}"
                    )
                r.ex_units = estimated_execution_units[key]
                r.ex_units.mem = int(
                    r.ex_units.mem * (1 + self.execution_memory_buffer)
                )
                r.ex_units.steps = int(
                    r.ex_units.steps * (1 + self.execution_step_buffer)
                )

    def _estimate_execution_units(
        self,
        change_address: Optional[Address] = None,
        merge_change: bool = False,
        collateral_change_address: Optional[Address] = None,
    ):
        # Create a deep copy of current builder, so we won't mess up current builder's internal states
        tmp_builder = TransactionBuilder(self.context)
        for f in fields(self):
            if f.name not in ("context",):
                setattr(tmp_builder, f.name, deepcopy(getattr(self, f.name)))
        tmp_builder._should_estimate_execution_units = False
        self._should_estimate_execution_units = False
        tx_body = tmp_builder.build(
            change_address, merge_change, collateral_change_address
        )
        witness_set = tmp_builder._build_fake_witness_set()
        tx = Transaction(
            tx_body, witness_set, auxiliary_data=tmp_builder.auxiliary_data
        )

        return self.context.evaluate_tx(tx.to_cbor())

    def build_and_sign(
        self,
        signing_keys: List[Union[SigningKey, ExtendedSigningKey]],
        change_address: Optional[Address] = None,
        merge_change: Optional[bool] = False,
        collateral_change_address: Optional[Address] = None,
    ) -> Transaction:
        """Build a transaction body from all constraints set through the builder and sign the transaction with
        provided signing keys.

        Args:
            signing_keys (List[Union[SigningKey, ExtendedSigningKey]]): A list of signing keys that will be used to
                sign the transaction.
            change_address (Optional[Address]): Address to which changes will be returned. If not provided, the
                transaction body will likely be unbalanced (sum of inputs is greater than the sum of outputs).
            merge_change (Optional[bool]): If the change address match one of the transaction output, the change amount
                will be directly added to that transaction output, instead of being added as a separate output.
            collateral_change_address (Optional[Address]): Address to which collateral changes will be returned.

        Returns:
            Transaction: A signed transaction.
        """

        tx_body = self.build(
            change_address=change_address,
            merge_change=merge_change,
            collateral_change_address=collateral_change_address,
        )
        witness_set = self.build_witness_set()
        witness_set.vkey_witnesses = []

        for signing_key in signing_keys:
            signature = signing_key.sign(tx_body.hash())
            witness_set.vkey_witnesses.append(
                VerificationKeyWitness(signing_key.to_verification_key(), signature)
            )

        return Transaction(tx_body, witness_set, auxiliary_data=self.auxiliary_data)
