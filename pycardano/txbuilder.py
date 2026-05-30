from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field, fields
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from pycardano import RedeemerMap
from pycardano.address import Address, AddressType
from pycardano.backend.base import ChainContext
from pycardano.certificate import (
    Certificate,
    PoolRegistration,
    PoolRetirement,
    RegDRepCert,
    StakeAndVoteDelegation,
    StakeCredential,
    StakeDelegation,
    StakeDeregistration,
    StakeDeregistrationConway,
    StakeRegistration,
    StakeRegistrationAndDelegation,
    StakeRegistrationAndDelegationAndVoteDelegation,
    StakeRegistrationAndVoteDelegation,
    StakeRegistrationConway,
    VoteDelegation,
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
from pycardano.governance import (
    Anchor,
    GovAction,
    GovActionId,
    GovActionIdToVotingProcedure,
    ProposalProcedure,
    Vote,
    Voter,
    VotingProcedure,
    VotingProcedures,
)
from pycardano.hash import DatumHash, ScriptDataHash, ScriptHash, VerificationKeyHash
from pycardano.key import ExtendedSigningKey, SigningKey, VerificationKey
from pycardano.logging import log_state, logger
from pycardano.metadata import AuxiliaryData
from pycardano.nativescript import NativeScript, ScriptAll, ScriptAny, ScriptPubkey
from pycardano.plutus import (
    CostModels,
    Datum,
    ExecutionUnits,
    PlutusScript,
    PlutusV1Script,
    PlutusV2Script,
    PlutusV3Script,
    Redeemer,
    RedeemerKey,
    Redeemers,
    RedeemerTag,
    RedeemerValue,
    ScriptType,
    datum_hash,
    script_hash,
)
from pycardano.serialization import NonEmptyOrderedSet, OrderedSet
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
        default_factory=lambda: [LargestFirstSelector(), RandomImproveMultiAsset()]
    )

    execution_memory_buffer: float = 0.2
    """Additional amount of execution memory (in ratio) that will be on top of estimation"""

    execution_step_buffer: float = 0.2
    """Additional amount of execution step (in ratio) that will be added on top of estimation"""

    fee_buffer: Optional[int] = field(default=None)
    """Additional amount of fee (in lovelace) that will be added on top of estimation."""

    ttl: Optional[int] = field(default=None)

    validity_start: Optional[int] = field(default=None)

    auxiliary_data: Optional[AuxiliaryData] = field(default=None)

    native_scripts: Optional[List[NativeScript]] = field(default=None)

    mint: Optional[MultiAsset] = field(default=None)

    required_signers: Optional[List[VerificationKeyHash]] = field(default=None)

    collaterals: NonEmptyOrderedSet[UTxO] = field(
        default_factory=lambda: NonEmptyOrderedSet[UTxO]()
    )

    certificates: Optional[List[Certificate]] = field(default=None)

    withdrawals: Optional[Withdrawals] = field(default=None)

    reference_inputs: Set[Union[UTxO, TransactionInput]] = field(
        init=False, default_factory=lambda: set()
    )

    witness_override: Optional[int] = field(default=None)

    initial_stake_pool_registration: Optional[bool] = field(default=False)

    use_redeemer_map: Optional[bool] = field(default=True)
    """Whether to serialize redeemers as a map or a list. Default is True."""

    voting_procedures: Optional[VotingProcedures] = field(init=False, default=None)

    proposal_procedures: Optional[NonEmptyOrderedSet[ProposalProcedure]] = field(
        init=False, default=None
    )

    current_treasury_value: Optional[int] = field(init=False, default=None)

    donation: Optional[int] = field(init=False, default=None)

    _inputs: List[UTxO] = field(init=False, default_factory=lambda: [])

    _potential_inputs: List[UTxO] = field(init=False, default_factory=lambda: [])

    _excluded_inputs: List[UTxO] = field(init=False, default_factory=lambda: [])

    _input_addresses: List[Union[Address, str]] = field(
        init=False, default_factory=lambda: []
    )

    _outputs: List[TransactionOutput] = field(init=False, default_factory=lambda: [])

    _fee: int = field(init=False, default=0)

    _datums: Dict[DatumHash, Datum] = field(init=False, default_factory=lambda: {})

    _collateral_return: Optional[TransactionOutput] = field(init=False, default=None)

    collateral_return_threshold: int = 1_000_000
    """The minimum amount of lovelace above which
    the remaining collateral (total_collateral_amount - actually_used_amount) will be returned."""

    _total_collateral: Optional[int] = field(init=False, default=None)

    _inputs_to_redeemers: Dict[UTxO, Redeemer] = field(
        init=False, default_factory=lambda: {}
    )

    _minting_script_to_redeemers: List[Tuple[ScriptType, Optional[Redeemer]]] = field(
        init=False, default_factory=lambda: []
    )

    _withdrawal_script_to_redeemers: List[Tuple[ScriptType, Optional[Redeemer]]] = (
        field(init=False, default_factory=lambda: [])
    )

    _certificate_script_to_redeemers: List[Tuple[ScriptType, Optional[Redeemer]]] = (
        field(init=False, default_factory=lambda: [])
    )

    _inputs_to_scripts: Dict[UTxO, ScriptType] = field(
        init=False, default_factory=lambda: {}
    )

    _reference_scripts: List[Union[NativeScript, PlutusScript]] = field(
        init=False, default_factory=lambda: []
    )

    _should_estimate_execution_units: Optional[bool] = field(init=False, default=None)

    def add_input(self, utxo: UTxO) -> TransactionBuilder:
        """Add a specific UTxO to transaction's inputs.

        Args:
            utxo (UTxO): UTxO to be added.

        Returns:
            TransactionBuilder: Current transaction builder.
        """
        self.inputs.append(utxo)
        if utxo.output.script:
            self._reference_scripts.append(utxo.output.script)
        return self

    def _consolidate_redeemer(self, redeemer):
        if self._should_estimate_execution_units is None:
            if redeemer.ex_units:
                self._should_estimate_execution_units = False
            else:
                self._should_estimate_execution_units = True
                redeemer.ex_units = ExecutionUnits(0, 0)
        else:
            if not self._should_estimate_execution_units and not redeemer.ex_units:
                raise InvalidArgumentException(
                    f"All redeemers need to provide execution units if the firstly "
                    f"added redeemer specifies execution units. \n"
                    f"Added redeemers: {self._redeemer_list} \n"
                    f"New redeemer: {redeemer}"
                )
            if self._should_estimate_execution_units:
                if redeemer.ex_units:
                    raise InvalidArgumentException(
                        f"No redeemer should provide execution units if the firstly "
                        f"added redeemer didn't provide execution units. \n"
                        f"Added redeemers: {self._redeemer_list} \n"
                        f"New redeemer: {redeemer}"
                    )
                else:
                    redeemer.ex_units = ExecutionUnits(0, 0)

    def add_script_input(
        self,
        utxo: UTxO,
        script: Optional[Union[UTxO, NativeScript, PlutusScript]] = None,
        datum: Optional[Datum] = None,
        redeemer: Optional[Redeemer] = None,
    ) -> TransactionBuilder:
        """Add a script UTxO to transaction's inputs.

        Args:
            utxo (UTxO): Script UTxO to be added.
            script (Optional[Union[UTxO, NativeScript, PlutusScript]]):
                A plutus script.
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

        if (
            utxo.output.datum_hash
            and datum is not None
            and utxo.output.datum_hash != datum_hash(datum)
        ):
            raise InvalidArgumentException(
                f"Datum hash in transaction output is {utxo.output.datum_hash}, "
                f"but actual datum hash from input datum is {datum_hash(datum)}."
            )
        if (
            datum is not None
            and utxo.output.datum_hash is None
            and utxo.output.datum is not None
        ):
            raise InvalidArgumentException(
                f"Inline Datum found in transaction output {utxo.input}, "
                "so attaching a Datum to the transaction input manually is not allowed."
            )

        if datum is not None:
            self.datums[datum_hash(datum)] = datum

        if redeemer:
            if redeemer.tag is not None and redeemer.tag != RedeemerTag.SPEND:
                raise InvalidArgumentException(
                    f"Expect the redeemer tag's type to be {RedeemerTag.SPEND}, "
                    f"but got {redeemer.tag} instead."
                )
            redeemer.tag = RedeemerTag.SPEND
            self._consolidate_redeemer(redeemer)
            self._inputs_to_redeemers[utxo] = redeemer

        input_script_hash = utxo.output.address.payment_part

        # collect potential scripts to fulfill the input
        candidate_scripts: List[
            Tuple[
                Union[NativeScript, PlutusScript],
                Optional[UTxO],
            ]
        ] = []
        if utxo.output.script:
            candidate_scripts.append((utxo.output.script, utxo))
        elif not script:
            for i in self.context.utxos(utxo.output.address):
                if i.output.script:
                    candidate_scripts.append((i.output.script, i))
        elif isinstance(script, UTxO):
            if script.output.script is None:
                raise InvalidArgumentException(
                    f"Expect the output of the reference UTxO {utxo}"
                    " to have a script, but got None instead."
                )
            candidate_scripts.append((script.output.script, script))
        else:
            candidate_scripts.append((script, None))

        found_valid_script = False
        for candidate_script, candidate_utxo in candidate_scripts:
            if script_hash(candidate_script) != input_script_hash:
                continue

            found_valid_script = True
            self._inputs_to_scripts[utxo] = candidate_script

            if candidate_utxo is not None and candidate_utxo != utxo:
                self.reference_inputs.add(candidate_utxo)
                self._reference_scripts.append(candidate_script)
            break
        if not found_valid_script:
            raise InvalidArgumentException(
                f"Cannot find a valid script to fulfill the input UTxO: {utxo.input}."
                "Supplied scripts do not match the payment part of the input address."
            )

        self.inputs.append(utxo)
        return self

    def add_minting_script(
        self,
        script: Union[UTxO, NativeScript, PlutusScript],
        redeemer: Optional[Redeemer] = None,
    ) -> TransactionBuilder:
        """Add a minting script along with its datum and redeemer to this transaction.

        Args:
            script (Union[UTxO, PlutusScript): A plutus script.
            redeemer (Optional[Redeemer]): A plutus redeemer to unlock the UTxO.

        Returns:
            TransactionBuilder: Current transaction builder.
        """
        if redeemer:
            if redeemer.tag is not None and redeemer.tag != RedeemerTag.MINT:
                raise InvalidArgumentException(
                    f"Expect the redeemer tag's type to be {RedeemerTag.MINT}, "
                    f"but got {redeemer.tag} instead."
                )
            redeemer.tag = RedeemerTag.MINT
            self._consolidate_redeemer(redeemer)

        if isinstance(script, UTxO):
            assert script.output.script is not None
            self._minting_script_to_redeemers.append((script.output.script, redeemer))
            self.reference_inputs.add(script)
            self._reference_scripts.append(script.output.script)
        else:
            self._minting_script_to_redeemers.append((script, redeemer))
        return self

    def add_withdrawal_script(
        self,
        script: Union[UTxO, NativeScript, PlutusScript],
        redeemer: Optional[Redeemer] = None,
    ) -> TransactionBuilder:
        """Add a withdrawal script along with its redeemer to this transaction.

        Args:
            script (Union[UTxO, PlutusScript]): A plutus script.
            redeemer (Optional[Redeemer]): A plutus redeemer to unlock the UTxO.

        Returns:
            TransactionBuilder: Current transaction builder.
        """
        if redeemer:
            if redeemer.tag is not None and redeemer.tag != RedeemerTag.WITHDRAWAL:
                raise InvalidArgumentException(
                    f"Expect the redeemer tag's type to be {RedeemerTag.WITHDRAWAL}, "
                    f"but got {redeemer.tag} instead."
                )
            redeemer.tag = RedeemerTag.WITHDRAWAL
            self._consolidate_redeemer(redeemer)

        if isinstance(script, UTxO):
            assert script.output.script is not None
            self._withdrawal_script_to_redeemers.append(
                (script.output.script, redeemer)
            )
            self.reference_inputs.add(script)
            self._reference_scripts.append(script.output.script)
        else:
            self._withdrawal_script_to_redeemers.append((script, redeemer))
        return self

    def add_certificate_script(
        self,
        script: Union[UTxO, NativeScript, PlutusScript],
        redeemer: Optional[Redeemer] = None,
    ) -> TransactionBuilder:
        """Add a certificate script along with its redeemer to this transaction.
        WARNING: The order of operations matters.
        The index of the redeemer will be set to the index of the last certificate added.

        Args:
            script (Union[UTxO, PlutusScript]): A plutus script.
            redeemer (Optional[Redeemer]): A plutus redeemer to unlock the UTxO.

        Returns:
            TransactionBuilder: Current transaction builder.
        """
        if redeemer:
            if redeemer.tag is not None and redeemer.tag != RedeemerTag.CERTIFICATE:
                raise InvalidArgumentException(
                    f"Expect the redeemer tag's type to be {RedeemerTag.CERTIFICATE}, "
                    f"but got {redeemer.tag} instead."
                )
            assert self.certificates is not None and len(self.certificates) >= 1, (
                "self.certificates is None. redeemer.index needs to be set to the index of the corresponding"
                "certificate (defaulting to the last certificate) however no certificates could be found"
            )
            redeemer.index = len(self.certificates) - 1
            redeemer.tag = RedeemerTag.CERTIFICATE
            self._consolidate_redeemer(redeemer)

        if isinstance(script, UTxO):
            assert script.output.script is not None
            self._certificate_script_to_redeemers.append(
                (script.output.script, redeemer)
            )
            self.reference_inputs.add(script)
            self._reference_scripts.append(script.output.script)
        else:
            self._certificate_script_to_redeemers.append((script, redeemer))
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
        if datum is not None:
            tx_out.datum_hash = datum_hash(datum)
        self.outputs.append(tx_out)
        if datum is not None and add_datum_to_witness:
            self.datums[datum_hash(datum)] = datum
        return self

    @property
    def inputs(self) -> List[UTxO]:
        return self._inputs

    @property
    def potential_inputs(self) -> List[UTxO]:
        return self._potential_inputs

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
    def all_scripts(self) -> List[ScriptType]:
        scripts: Dict[ScriptHash, ScriptType] = {}
        s: ScriptType

        if self.native_scripts:
            for s in self.native_scripts:
                scripts[script_hash(s)] = s

        for s in self._inputs_to_scripts.values():
            scripts[script_hash(s)] = s

        for s, _ in self._minting_script_to_redeemers:
            scripts[script_hash(s)] = s

        for s, _ in self._withdrawal_script_to_redeemers:
            scripts[script_hash(s)] = s

        for s, _ in self._certificate_script_to_redeemers:
            scripts[script_hash(s)] = s

        return list(scripts.values())

    @property
    def scripts(self) -> List[ScriptType]:
        scripts: Dict[ScriptHash, ScriptType] = {
            script_hash(s): s for s in self.all_scripts
        }
        s: ScriptType

        for s in self._reference_scripts:
            if script_hash(s) in scripts:
                scripts.pop(script_hash(s))

        return list(scripts.values())

    @property
    def datums(self) -> Dict[DatumHash, Datum]:
        return self._datums

    @property
    def _redeemer_list(self) -> List[Redeemer]:
        return (
            [r for r in self._inputs_to_redeemers.values() if r is not None]
            + [r for _, r in self._minting_script_to_redeemers if r is not None]
            + [r for _, r in self._withdrawal_script_to_redeemers if r is not None]
            + [r for _, r in self._certificate_script_to_redeemers if r is not None]
        )

    def redeemers(self) -> Redeemers:
        redeemer_list = self._redeemer_list

        # We have to serialize redeemers as a map if there are no redeemers
        if self.use_redeemer_map or not redeemer_list:
            redeemers = RedeemerMap()
            for r in redeemer_list:
                if r.tag is None:
                    raise InvalidArgumentException(
                        f"Redeemer tag is not set. Redeemer: {r}"
                    )
                if r.ex_units is None:
                    raise InvalidArgumentException(
                        f"Execution units are not set. Redeemer: {r}"
                    )
                k = RedeemerKey(r.tag, r.index)
                v = RedeemerValue(r.data, r.ex_units)
                redeemers[k] = v
            return redeemers
        else:
            return redeemer_list

    @property
    def script_data_hash(self) -> Optional[ScriptDataHash]:
        if self.datums or self._redeemer_list:
            cost_models = {}
            for s in self.all_scripts:
                version = -1
                if isinstance(s, PlutusScript):
                    version = s.version
                elif type(s) is bytes:
                    version = 1
                if version != -1:
                    cost_models[version - 1] = (
                        self.context.protocol_param.cost_models.get(
                            f"PlutusV{version}", {}
                        )
                    )
            return script_data_hash(
                self.redeemers(),
                NonEmptyOrderedSet(list(self.datums.values())),
                CostModels(cost_models),
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
        provided.coin -= self._get_total_proposal_deposit()
        provided.multi_asset.filter(
            lambda p, n, v: p in requested.multi_asset and n in requested.multi_asset[p]
        )
        if (
            provided.coin < requested.coin
            or requested.multi_asset > provided.multi_asset
        ):
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
            lovelace_change = Value(change.coin)
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

        return len(attempt_amount.to_cbor()) > max_val_size

    def _pack_tokens_for_change(
        self,
        change_address: Optional[Address],
        change_estimator: Value,
        max_val_size: int,
    ) -> List[MultiAsset]:
        multi_asset_arr = []
        base_coin = Value(coin=change_estimator.coin)
        change_address = change_address or Address(FAKE_VKEY.hash())
        output = TransactionOutput(change_address, base_coin)

        # iteratively add tokens to output
        for policy_id, assets in change_estimator.multi_asset.items():
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

            if len(updated_amount.to_cbor()) > max_val_size:
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
        for i in self.inputs + list(self.collaterals):
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
                    cert,
                    (
                        StakeRegistration,
                        StakeDeregistration,
                        StakeDelegation,
                        StakeRegistrationConway,
                        StakeDeregistrationConway,
                        VoteDelegation,
                        StakeAndVoteDelegation,
                        StakeRegistrationAndDelegation,
                        StakeRegistrationAndVoteDelegation,
                        StakeRegistrationAndDelegationAndVoteDelegation,
                    ),
                ):
                    _check_and_add_vkey(cert.stake_credential)
                elif isinstance(cert, RegDRepCert):
                    _check_and_add_vkey(cert.drep_credential)
                elif isinstance(cert, PoolRegistration):
                    results.add(cert.pool_params.operator)
                elif isinstance(cert, PoolRetirement):
                    results.add(cert.pool_keyhash)
        return results

    def _vote_vkey_hashes(self) -> Set[VerificationKeyHash]:
        results = set()

        if self.voting_procedures:
            for voter in self.voting_procedures:
                if isinstance(voter.credential, VerificationKeyHash):
                    results.add(voter.credential)
        return results

    def _get_total_key_deposit(self):
        stake_registration_certs = set()
        stake_registration_certs_with_explicit_deposit = set()
        stake_pool_registration_certs = set()

        protocol_params = self.context.protocol_param

        if self.certificates:
            for cert in self.certificates:
                if isinstance(cert, StakeRegistration):
                    stake_registration_certs.add(cert.stake_credential.credential)
                elif isinstance(
                    cert,
                    (
                        RegDRepCert,
                        StakeRegistrationConway,
                        StakeRegistrationAndDelegation,
                        StakeRegistrationAndVoteDelegation,
                        StakeRegistrationAndDelegationAndVoteDelegation,
                    ),
                ):
                    stake_registration_certs_with_explicit_deposit.add(cert.coin)
                elif (
                    isinstance(cert, PoolRegistration)
                    and self.initial_stake_pool_registration
                ):
                    stake_pool_registration_certs.add(cert.pool_params.operator)

        stake_registration_deposit = protocol_params.key_deposit * len(
            stake_registration_certs
        ) + sum(stake_registration_certs_with_explicit_deposit)
        stake_pool_registration_deposit = protocol_params.pool_deposit * len(
            stake_pool_registration_certs
        )
        return stake_registration_deposit + stake_pool_registration_deposit

    def _get_total_proposal_deposit(self):
        proposal_deposit = 0
        if self.proposal_procedures:
            for proposal in self.proposal_procedures:
                proposal_deposit += proposal.deposit
        return proposal_deposit

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
        #
        # There is no way to determine certificate index here

        if self.mint:
            sorted_mint_policies = sorted(self.mint.keys(), key=lambda x: x.to_cbor())
        else:
            sorted_mint_policies = []
        if self.withdrawals:
            sorted_withdrawals = sorted(self.withdrawals.keys())
        else:
            sorted_withdrawals = []

        for i, utxo in enumerate(self.inputs):
            if (
                utxo in self._inputs_to_redeemers
                and self._inputs_to_redeemers[utxo].tag == RedeemerTag.SPEND
            ):
                self._inputs_to_redeemers[utxo].index = i

        for script, redeemer in self._minting_script_to_redeemers:
            if redeemer is not None:
                redeemer.index = sorted_mint_policies.index(script_hash(script))

        for script, redeemer in self._withdrawal_script_to_redeemers:
            if redeemer is not None:
                script_staking_credential = Address(
                    staking_part=script_hash(script), network=self.context.network
                )
                redeemer.index = sorted_withdrawals.index(
                    script_staking_credential.to_primitive()
                )

        self._redeemer_list.sort(key=lambda r: r.index)

    def _build_tx_body(self) -> TransactionBody:
        tx_body = TransactionBody(
            OrderedSet([i.input for i in self.inputs]),
            self.outputs,
            fee=self.fee,
            ttl=self.ttl,
            mint=self.mint,
            auxiliary_data_hash=(
                self.auxiliary_data.hash() if self.auxiliary_data else None
            ),
            script_data_hash=self.script_data_hash,
            required_signers=(
                NonEmptyOrderedSet(self.required_signers)
                if self.required_signers
                else None
            ),
            validity_start=self.validity_start,
            collateral=(
                NonEmptyOrderedSet([c.input for c in self.collaterals])
                if self.collaterals
                else None
            ),
            certificates=self.certificates,
            withdraws=self.withdrawals,
            collateral_return=self._collateral_return,
            total_collateral=self._total_collateral,
            reference_inputs=(
                NonEmptyOrderedSet(
                    [
                        i.input if isinstance(i, UTxO) else i
                        for i in self.reference_inputs
                    ]
                )
                if self.reference_inputs
                else None
            ),
            # Add new governance fields
            voting_procedures=(
                self.voting_procedures if self.voting_procedures else None
            ),
            proposal_procedures=(
                self.proposal_procedures if self.proposal_procedures else None
            ),
            current_treasury_value=(
                self.current_treasury_value if self.current_treasury_value else None
            ),
            donation=self.donation if self.donation else None,
        )
        return tx_body

    def _build_required_vkeys(self) -> Set[VerificationKeyHash]:
        vkey_hashes = self._input_vkey_hashes()
        vkey_hashes.update(self._required_signer_vkey_hashes())
        vkey_hashes.update(self._native_scripts_vkey_hashes())
        vkey_hashes.update(self._certificate_vkey_hashes())
        vkey_hashes.update(self._withdrawal_vkey_hashes())
        vkey_hashes.update(self._vote_vkey_hashes())
        return vkey_hashes

    def _witness_count(self) -> int:
        return self.witness_override or len(self._build_required_vkeys())

    def _build_fake_vkey_witnesses(self) -> NonEmptyOrderedSet[VerificationKeyWitness]:
        witnesses = []
        for i in range(self._witness_count()):
            # Convert index to 32 bytes and use AND operation to create unique keys
            i_bytes = i.to_bytes(32, "big")
            unique_vkey = VerificationKey.from_primitive(
                bytes(
                    x & y
                    for x, y in zip(
                        bytes.fromhex(
                            "5797dc2cc919dfec0bb849551ebdf30d96e5cbe0f33f734a87fe826db30f7ef9"
                        ),
                        i_bytes,
                    )
                )
            )
            unique_sig = bytes(
                x & y
                for x, y in zip(
                    bytes.fromhex(
                        "577ccb5b487b64e396b0976c6f71558e52e44ad254db7d06dfb79843e5441a5d"
                        "763dd42adcf5e8805d70373722ebbce62a58e3f30dd4560b9a898b8ceeab6a03"
                    ),
                    i_bytes + i_bytes,  # 64 bytes for signature
                )
            )
            witnesses.append(VerificationKeyWitness(unique_vkey, unique_sig))
        return NonEmptyOrderedSet(witnesses)

    def _build_fake_witness_set(self) -> TransactionWitnessSet:
        witness_set = self.build_witness_set()
        if self._witness_count() > 0:
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
        size = len(tx.to_cbor())
        if size > self.context.protocol_param.max_tx_size:
            raise InvalidTransactionException(
                f"Transaction size ({size}) exceeds the max limit "
                f"({self.context.protocol_param.max_tx_size}). Please try reducing the "
                f"number of inputs or outputs."
            )

        return tx

    def build_witness_set(
        self, remove_dup_script: bool = False
    ) -> TransactionWitnessSet:
        """Build a transaction witness set, excluding verification key witnesses.
        This function is especially useful when the transaction involves Plutus scripts.

        Args:
            remove_dup_script (bool): Whether to remove scripts, that are already attached to inputs,
             from the witness set.

        Returns:
            TransactionWitnessSet: A transaction witness set without verification key witnesses.
        """

        native_scripts: NonEmptyOrderedSet[NativeScript] = NonEmptyOrderedSet()
        plutus_v1_scripts: NonEmptyOrderedSet[PlutusV1Script] = NonEmptyOrderedSet()
        plutus_v2_scripts: NonEmptyOrderedSet[PlutusV2Script] = NonEmptyOrderedSet()
        plutus_v3_scripts: NonEmptyOrderedSet[PlutusV3Script] = NonEmptyOrderedSet()
        plutus_data: NonEmptyOrderedSet[Any] = NonEmptyOrderedSet()

        input_scripts = (
            {
                script_hash(i.output.script)
                for i in self.inputs
                if i.output.script is not None
            }
            if remove_dup_script
            else {}
        )

        for datum in self.datums.values():
            plutus_data.append(datum)

        for script in self.scripts:
            if script_hash(script) not in input_scripts:
                if isinstance(script, NativeScript):
                    native_scripts.append(script)
                elif isinstance(script, PlutusV1Script):
                    plutus_v1_scripts.append(script)
                elif type(script) is bytes:
                    plutus_v1_scripts.append(PlutusV1Script(script))
                elif isinstance(script, PlutusV2Script):
                    plutus_v2_scripts.append(script)
                elif isinstance(script, PlutusV3Script):
                    plutus_v3_scripts.append(script)
                else:
                    raise InvalidArgumentException(
                        f"Unsupported script type: {type(script)}"
                    )

        witness_set = TransactionWitnessSet(
            native_scripts=native_scripts if native_scripts else None,
            plutus_v1_script=plutus_v1_scripts if plutus_v1_scripts else None,
            plutus_v2_script=plutus_v2_scripts if plutus_v2_scripts else None,
            plutus_v3_script=plutus_v3_scripts if plutus_v3_scripts else None,
            redeemer=self.redeemers() if self._redeemer_list else None,
            plutus_data=plutus_data if plutus_data else None,
        )
        witness_set.convert_to_latest_spec()
        return witness_set

    def _ensure_no_input_exclusion_conflict(self):
        intersection = set(self.inputs).intersection(set(self.excluded_inputs))
        if intersection:
            raise TransactionBuilderException(
                f"Found common UTxOs between UTxO inputs and UTxO excluded_inputs: "
                f"{intersection}."
            )

    def _ref_script_size(self):
        ref_script_size = 0
        for s in self._reference_scripts:
            if isinstance(s, NativeScript):
                ref_script_size += len(s.to_cbor())
            else:
                ref_script_size += len(s)
        return ref_script_size

    def _estimate_fee(self):
        plutus_execution_units = ExecutionUnits(0, 0)
        for redeemer in self._redeemer_list:
            plutus_execution_units += redeemer.ex_units

        estimated_fee = fee(
            self.context,
            len(self._build_full_fake_tx().to_cbor()),
            plutus_execution_units.steps,
            plutus_execution_units.mem,
            self._ref_script_size(),
        )
        if self.fee_buffer is not None:
            estimated_fee += self.fee_buffer

        return estimated_fee

    @log_state
    def build(
        self,
        change_address: Optional[Address] = None,
        merge_change: Optional[bool] = False,
        collateral_change_address: Optional[Address] = None,
        auto_validity_start_offset: Optional[int] = None,
        auto_ttl_offset: Optional[int] = None,
        auto_required_signers: Optional[bool] = None,
    ) -> TransactionBody:
        """Build a transaction body from all constraints set through the builder.

        Args:
            change_address (Optional[Address]): Address to which changes will be returned. If not provided, the
                transaction body will likely be unbalanced (sum of inputs is greater than the sum of outputs).
            merge_change (Optional[bool]): If the change address match one of the transaction output, the change amount
                will be directly added to that transaction output, instead of being added as a separate output.
            collateral_change_address (Optional[Address]): Address to which collateral changes will be returned.
            auto_validity_start_offset (Optional[int]): Automatically set the validity start interval of the transaction
                to the current slot number + the given offset (default -1000).
                A manually set validity start will always take precedence.
            auto_ttl_offset (Optional[int]): Automatically set the validity end interval (ttl) of the transaction
                to the current slot number + the given offset (default 10_000).
                A manually set ttl will always take precedence.
            auto_required_signers (Optional[bool]): Automatically add all pubkeyhashes of transaction inputs
                to required signatories (default only for Smart Contract transactions).
                Manually set required signers will always take precedence.

        Returns:
            TransactionBody: A transaction body.
        """
        self._ensure_no_input_exclusion_conflict()

        # only automatically set the validity interval and required signers if scripts are involved
        is_smart = bool(self.all_scripts)

        # Automatically set the validity range to a tight value around transaction creation
        if (
            is_smart or auto_validity_start_offset is not None
        ) and self.validity_start is None:
            last_slot = self.context.last_block_slot
            # If None is provided, the default value is -1000
            if auto_validity_start_offset is None:
                auto_validity_start_offset = -1000
            self.validity_start = max(0, last_slot + auto_validity_start_offset)

        if (is_smart or auto_ttl_offset is not None) and self.ttl is None:
            last_slot = self.context.last_block_slot
            # If None is provided, the default value is 10_000
            if auto_ttl_offset is None:
                auto_ttl_offset = 10_000
            self.ttl = max(0, last_slot + auto_ttl_offset)

        selected_utxos = []
        selected_amount = Value()
        for i in self.inputs:
            selected_utxos.append(i)
            selected_amount += i.output.amount

        if self.mint:
            # Add positive minted amounts to the selected amount (=source)
            for pid, m in self.mint.items():
                for tkn, am in m.items():
                    if am > 0:
                        selected_amount += Value(
                            multi_asset=MultiAsset({pid: Asset({tkn: am})})
                        )

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
        selected_amount.coin -= self._get_total_proposal_deposit()

        requested_amount = Value()
        for o in self.outputs:
            requested_amount += o.amount

        if self.mint:
            # Add negative minted amounts to the requested amount (=sink)
            for pid, m in self.mint.items():
                for tkn, am in m.items():
                    if am < 0:
                        requested_amount += Value(
                            multi_asset=MultiAsset({pid: Asset({tkn: -am})})
                        )

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

        remaining = trimmed_selected_amount - requested_amount
        remaining.multi_asset = remaining.multi_asset.filter(lambda p, n, v: v > 0)
        remaining.coin = max(0, remaining.coin)

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

        # Create a set of all seen utxos in addition to other utxo lists.
        # We need this set to avoid adding the same utxo twice.
        # The reason of not turning all utxo lists into sets is that we want to keep the order of utxos and make
        # utxo selection deterministic.
        seen_utxos = set(selected_utxos)

        # When there are positive coin or native asset quantity in unfulfilled Value
        if Value() < unfulfilled_amount:
            additional_utxo_pool = []
            additional_amount = Value()

            for utxo in self.potential_inputs:
                additional_amount += utxo.output.amount
                seen_utxos.add(utxo)
                additional_utxo_pool.append(utxo)

            for address in self.input_addresses:
                for utxo in self.context.utxos(address):
                    if (
                        utxo not in seen_utxos
                        and utxo not in self.excluded_inputs
                        and utxo.output.script is None
                    ):
                        additional_utxo_pool.append(utxo)
                        additional_amount += utxo.output.amount
                        seen_utxos.add(utxo)

            for index, selector in enumerate(self.utxo_selectors):
                try:
                    selected, _ = selector.select(
                        additional_utxo_pool,
                        [
                            TransactionOutput(
                                Address(FAKE_VKEY.hash()), unfulfilled_amount
                            )
                        ],
                        self.context,
                        include_max_fee=False,
                        respect_min_utxo=not can_merge_change,
                        existing_amount=remaining,
                    )

                    for s in selected:
                        selected_amount += s.output.amount
                        selected_utxos.append(s)
                    break

                except UTxOSelectionException as e:
                    if index < len(self.utxo_selectors) - 1:
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

        # Automatically set the required signers for smart transactions
        if (
            is_smart and auto_required_signers is not False
        ) and self.required_signers is None:
            # Collect all signatories from explicitly defined
            # transaction inputs and collateral inputs, and input addresses
            self.required_signers = list(self._input_vkey_hashes())

        self._set_redeemer_index()

        self._set_collateral_return(collateral_change_address or change_address)

        self._update_execution_units(
            change_address, merge_change, collateral_change_address
        )

        self._add_change_and_fee(change_address, merge_change=merge_change)

        tx_body = self._build_tx_body()

        return tx_body

    def _should_add_collateral_return(self, collateral_return: Value) -> bool:
        """Check if it is necessary to add a collateral return output.

        Args:
            collateral_return (Value): The potential collateral return amount.

        Returns:
            bool: True if a collateral return output should be added, False otherwise.
        """
        return (
            collateral_return.coin > max(self.collateral_return_threshold, 1_000_000)
            or collateral_return.multi_asset.count(lambda p, n, v: v > 0) > 0
        )

    def _set_collateral_return(self, collateral_return_address: Optional[Address]):
        """Calculate and set the change returned from the collateral inputs.

        Args:
            collateral_return_address (Address): Address to which the collateral change will be returned.
        """
        witnesses = self._build_fake_witness_set()

        # Make sure there is at least one script input
        if (
            not witnesses.plutus_v1_script
            and not witnesses.plutus_v2_script
            and not witnesses.plutus_v3_script
            and not self._reference_scripts
        ):
            return

        if not collateral_return_address:
            return

        collateral_amount = (
            max_tx_fee(context=self.context, ref_script_size=self._ref_script_size())
            * self.context.protocol_param.collateral_percent
            // 100
        )

        if not self.collaterals:
            tmp_val = Value()

            def _add_collateral_input(cur_total, candidate_inputs):
                cur_collateral_return = cur_total - collateral_amount

                while (
                    cur_total.coin < collateral_amount
                    or self._should_add_collateral_return(cur_collateral_return)
                    and 0
                    <= cur_collateral_return.coin
                    < min_lovelace_post_alonzo(
                        TransactionOutput(
                            collateral_return_address, cur_collateral_return
                        ),
                        self.context,
                    )
                ) and candidate_inputs:
                    candidate = candidate_inputs.pop()
                    if (
                        not candidate.output.address.address_type.name.startswith(
                            "SCRIPT"
                        )
                        and candidate.output.amount.coin > 2000000
                        and candidate not in self.collaterals
                    ):
                        self.collaterals.append(candidate)
                        cur_total += candidate.output.amount
                        cur_collateral_return = cur_total - collateral_amount

            sorted_inputs = sorted(
                self.inputs.copy(),
                key=lambda i: (len(i.output.to_cbor_hex()), -i.output.amount.coin),
            )
            _add_collateral_input(tmp_val, sorted_inputs)

            if tmp_val.coin < collateral_amount:
                sorted_inputs = sorted(
                    self.potential_inputs,
                    key=lambda i: (len(i.output.to_cbor_hex()), -i.output.amount.coin),
                )
                _add_collateral_input(tmp_val, sorted_inputs)

            if tmp_val.coin < collateral_amount:
                sorted_inputs = sorted(
                    self.context.utxos(collateral_return_address),
                    key=lambda i: (len(i.output.to_cbor_hex()), -i.output.amount.coin),
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

            if not self._should_add_collateral_return(return_amount):
                return  # No need to return collateral if the remaining amount is too small

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
        merge_change: Optional[bool] = False,
        collateral_change_address: Optional[Address] = None,
    ):
        if self._should_estimate_execution_units:
            estimated_execution_units = self._estimate_execution_units(
                change_address, merge_change, collateral_change_address
            )
            for r in self._redeemer_list:
                assert (
                    r.tag is not None
                ), "Expected tag of redeemer to be set, but found None"
                tagname = r.tag.name.lower()
                key = f"{tagname}:{r.index}"
                if (
                    key not in estimated_execution_units
                    or estimated_execution_units[key] is None
                ):
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
        merge_change: Optional[bool] = False,
        collateral_change_address: Optional[Address] = None,
    ) -> Dict[str, ExecutionUnits]:
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

        return self.context.evaluate_tx(tx)

    def build_and_sign(
        self,
        signing_keys: List[Union[SigningKey, ExtendedSigningKey]],
        change_address: Optional[Address] = None,
        merge_change: Optional[bool] = False,
        collateral_change_address: Optional[Address] = None,
        auto_validity_start_offset: Optional[int] = None,
        auto_ttl_offset: Optional[int] = None,
        auto_required_signers: Optional[bool] = None,
        force_skeys: Optional[bool] = False,
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
            auto_validity_start_offset (Optional[int]): Automatically set the validity start interval of the transaction
                to the current slot number + the given offset (default -1000).
                A manually set validity start will always take precedence.
            auto_ttl_offset (Optional[int]): Automatically set the validity end interval (ttl) of the transaction
                to the current slot number + the given offset (default 10_000).
                A manually set ttl will always take precedence.
            auto_required_signers (Optional[bool]): Automatically add all pubkeyhashes of transaction inputs
                and the given signers to required signatories (default only for Smart Contract transactions).
                Manually set required signers will always take precedence.
            force_skeys (Optional[bool]): Whether to force the use of signing keys for signing the transaction.
                Default is False, which means that provided signing keys will only be used to sign the transaction if
                they are actually required by the transaction. This is useful to reduce tx fees by not including
                unnecessary signatures. If set to True, all provided signing keys will be used to sign the transaction.

        Returns:
            Transaction: A signed transaction.
        """
        # The given signers should be required signers if they weren't added yet
        if auto_required_signers and self.scripts and not self.required_signers:
            # Collect all signatories from explicitly defined
            # transaction inputs and collateral inputs, and input addresses
            self.required_signers = [
                s.to_verification_key().hash() for s in signing_keys
            ]

        tx_body = self.build(
            change_address=change_address,
            merge_change=merge_change,
            collateral_change_address=collateral_change_address,
            auto_validity_start_offset=auto_validity_start_offset,
            auto_ttl_offset=auto_ttl_offset,
            auto_required_signers=auto_required_signers,
        )
        witness_set = self.build_witness_set(True)
        witness_set.vkey_witnesses = NonEmptyOrderedSet()

        required_vkeys = self._build_required_vkeys()

        for signing_key in set(signing_keys):
            vkey_hash = signing_key.to_verification_key().hash()
            if not force_skeys and vkey_hash not in required_vkeys:
                logger.warning(
                    f"Verification key hash {vkey_hash} is not required for this tx."
                )
                continue
            signature = signing_key.sign(tx_body.hash())
            witness_set.vkey_witnesses.append(
                VerificationKeyWitness(signing_key.to_verification_key(), signature)
            )

        if len(witness_set.vkey_witnesses) == 0:
            witness_set.vkey_witnesses = None

        return Transaction(tx_body, witness_set, auxiliary_data=self.auxiliary_data)

    # Add helper methods for governance operations
    def add_vote(
        self,
        voter: Voter,
        gov_action_id: GovActionId,
        vote: Vote,
        anchor: Optional[Anchor] = None,
    ) -> TransactionBuilder:
        """Add a vote to the transaction.

        Args:
            voter: The voter casting the vote
            gov_action_id: The ID of the governance action being voted on
            vote: The vote being cast (YES/NO/ABSTAIN)
            anchor: Optional metadata about the vote

        Returns:
            self: The transaction builder instance
        """
        if self.voting_procedures is None:
            self.voting_procedures = VotingProcedures()

        # Initialize the inner map if this is the first vote for this voter
        if voter not in self.voting_procedures:
            self.voting_procedures[voter] = GovActionIdToVotingProcedure()

        # Add the voting procedure for this specific governance action
        self.voting_procedures[voter][gov_action_id] = VotingProcedure(vote, anchor)

        return self

    def add_proposal(
        self,
        deposit: int,
        reward_account: bytes,
        gov_action: GovAction,
        anchor: Anchor,
    ) -> TransactionBuilder:
        """Add a governance proposal to the transaction.

        Args:
            deposit: The deposit amount required for the proposal
            reward_account: The reward account for the proposal
            gov_action: The governance action being proposed
            anchor: Metadata about the proposal

        Returns:
            self: The transaction builder instance
        """
        if self.proposal_procedures is None:
            self.proposal_procedures = NonEmptyOrderedSet()

        self.proposal_procedures.append(
            ProposalProcedure(
                deposit=deposit,
                reward_account=reward_account,
                gov_action=gov_action,
                anchor=anchor,
            )
        )
        return self

    def add_treasury_donation(self, amount: int) -> TransactionBuilder:
        """Add a donation to the treasury.

        Args:
            amount: The amount to donate (must be positive)

        Returns:
            self: The transaction builder instance
        """
        if amount <= 0:
            raise ValueError("Treasury donation amount must be positive")
        self.donation = amount
        return self
