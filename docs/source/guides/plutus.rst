======
Plutus
======

Plutus is the native language to write smart contract on Cardano's extended UTxO model (EUTxO). It allows us to incorporate expressive logics to determine when a particular UTxO can be spent.
To learn more about EUTxO and its advantages, you can refer to the `Cardano docs <https://docs.cardano.org/plutus/eutxo-explainer>`_ or the `class notes <https://plutus-pioneer-program.readthedocs.io/en/latest/pioneer/week1.html>`_ from Plutus pioneer program (PPP).
To learn how Plutus enables logic creation, we need to understand a couple key concepts:

* **Plutus script**: the smart contract that acts as the validator of the transaction. By evaluating the inputs from someone who wants to spend the UTxO, they either approve or deny it (by returning either True or False). The script is compiled into Plutus Core binary and sits on-chain.
* **Script address**: the hash of the Plutus script binary. They hold UTxOs like typical public key address, but every time a transaction tries to consume the UTxOs on this address, the Plutus script generated this address will be executed by evaluating the input of the transaction, namely datum, redeemer and script context. The transaction is only valid if the script returns True.
* **Datum**: the datum is a piece of information associated with a UTxO. When someone sends fund to script address, he or she attaches the hash of the datum to "lock" the fund. When someone tries to consume the UTxO, he or she needs to provide datum whose hash matches the attached datum hash and redeemer that meets the conditions specified by the Plutus script to "unlock" the fund.
* **Redeemer**: the redeemer shares the same data format as datum, but is a separate input. It includes datum, along with other information such as types of actions to take with the target UTxO and computational resources to reserve. Redeemer value is attached to the input transaction to unlock funds from a script and is used by the script to validate the transaction.
* **Script context**: The script context provides information about the pending transaction, along with which input triggered the validation.

--------------------------------
Datum and Redeemer Serialization
--------------------------------
To calculate the hash of a datum, we can leverage the helper class `PlutusData`. `PlutusData` can serialize itself into a CBOR format, which can be interpreted as a data structure in Plutus scripts. Wrapping datum in PlutusData class will reduce the complexity of serialization and deserialization tremendously. It supports data type of int, bytes, List and hashmap. Below are some examples on how to construct some arbitrary datums.

Empty datum::

    >>> empty_datum = PlutusData()
    >>> empty_datum.to_cbor()
    'd87980'

Sample datum with int, bytes, List and hashmap inputs::

    >>> # Create sample datum
    >>> @dataclass
    ... class MyDatum(PlutusData):
    ...     CONSTR_ID = 1
    ...     a: int
    ...     b: bytes
    ...     c: IndefiniteList
    ...     d: dict

    >>> datum = MyDatum(123, b"1234", IndefiniteList([4, 5, 6]), {1: b"1", 2: b"2"})
    >>> datum.to_cbor()
    'd87a9f187b43333231ff'

You can also wrap `PlutusData` within `PlutusData`::

    >>> @dataclass
    ... class InclusionDatum(PlutusData):
    ...     CONSTR_ID = 1
    ...     beneficiary: bytes
    ...     deadline: int
    ...     other_data: MyDatum

    >>> key_hash = bytes.fromhex("c2ff616e11299d9094ce0a7eb5b7284b705147a822f4ffbd471f971a")
    >>> deadline = 1643235300000
    >>> other_datum = MyDatum(123, b"1234", IndefiniteList([4, 5, 6]), {1: b"1", 2: b"2"})
    >>> include_datum = InclusionDatum(key_hash, deadline, other_datum)
    >>> include_datum.to_cbor()
    'd87a9f581cc2ff616e11299d9094ce0a7eb5b7284b705147a822f4ffbd471f971a1b0000017e9874d2a0d8668218829f187b44313233349f040506ffa2014131024132ffff'

`PlutusData` supports conversion from/to JSON format, which
is easier to read and write. The above could be convered to JSON like this::

    >>> encoded_json = include_datum.to_json(separators=(",", ":")

Similarly, redeemer can be serialized like following::

    >>> data = MyDatum(123, b"234", IndefiniteList([]), {1: b"1", 2: b"2"})
    >>> redeemer = MyRedeemer(RedeemerTag.SPEND, data, ExecutionUnits(1000000, 1000000))
    >>> redeemer.to_cbor()
    '840000d8668218829f187b433233349fffa2014131024132ff821a000f42401a000f4240'

------------------
Example - FortyTwo
------------------

We demonstrate how these concepts come into play using a simple example from PPP - FortyTwo. The original script in haskell can be found here `here <https://github.com/input-output-hk/plutus-pioneer-program/blob/28559d379df8b66c06d8fbd1e2a43f6a8351382a/code/week02/src/Week02/Typed.hs>`_. Using PyCardano, we will show one can send and lock funds at a script address, and how someone else with the correct redeemer value can unlock and receive the funds.

Step 1

Similar to `Transaction guide <../guides/transaction.html>`_, we build a chain context using `BlockFrostChainContext <../api/pycardano.backend.base.html#pycardano.backend.blockfrost.BlockFrostChainContext>`_::

    >>> from pycardano import BlockFrostChainContext, Network
    >>> network = Network.TESTNET
    >>> context = BlockFrostChainContext("your_blockfrost_project_id", network)

Step 2

Create script address::

    >>> import cbor2
    >>> from pycardano import (
    ...     Address,
    ...     PaymentVerificationKey,
    ...     PaymentSigningKey,
    ...     plutus_script_hash,
    ...     Transaction,
    ...     TransactionBuilder,
    ...     PlutusData,
    ...     Redeemer,
    ... )

    >>> # Assuming the hexadecimal file of the script exists at your local path
    >>> with open("path/to/fortytwo.plutus", "r") as f:
    >>>     script_hex = f.read()
    >>>     forty_two_script = cbor2.loads(bytes.fromhex(script_hex))

    >>> script_hash = plutus_script_hash(forty_two_script)
    >>> script_address = Address(script_hash, network=network)

Step 3

Giver/Locker sends funds to script address::

    >>> payment_vkey = PaymentVerificationKey.load("path/to/payment.vkey")
    >>> payment_skey = PaymentSigningKey.load("path/to/payment.skey")
    >>> giver_address = Address(payment_vkey.hash(), network=network)

    >>> builder = TransactionBuilder(context)
    >>> builder.add_input_address(giver_address)

    >>> datum = PlutusData()  # A Unit type "()" in Haskell
    >>> builder.add_output(
    >>>     TransactionOutput(script_address, 50000000, datum_hash=datum_hash(datum))
    >>> )

Build, sign and submit the transaction:

    >>> signed_tx = builder.build_and_sign([payment_skey], giver_address)
    >>> context.submit_tx(signed_tx.to_cbor())

Step 4

Taker/Unlocker sends transaction to consume funds. Here we specify the redeemer tag as spend and pass in the redeemer value of 42. If the redeemer value is anything else, the validator will fail and funds won't be retrieved::

    >>> redeemer = Redeemer(RedeemerTag.SPEND, 42)

    >>> utxo_to_spend = context.utxos(str(script_address))[0]
    >>> extended_payment_vkey = PaymentVerificationKey.load("path/to/extended_payment.vkey")
    >>> extended_payment_skey = PaymentSigningKey.load("path/to/extended_payment.skey")
    >>> taker_address = Address(extended_payment_vkey.hash(), network=network)

    >>> builder = TransactionBuilder(context)

Add info on the UTxO to spend, Plutus script, actual datum and the redeemer. Specify funds amount to take::

    >>> builder.add_script_input(utxo_to_spend, forty_two_script, datum, redeemer)
    >>> take_output = TransactionOutput(taker_address, 25123456)
    >>> builder.add_output(take_output)

Taker/Unlocker provides collateral. Collateral has been introduced in Alonzo transactions to cover the cost of the validating node executing a failing script. In this scenario, the provided UTXO is consumed instead of the fees. A UTXO provided for collateral must only have ada, no other native assets::

    >>> non_nft_utxo = None
    >>> for utxo in context.utxos(str(taker_address)):
    >>>     # multi_asset should be empty for collateral utxo
    >>>     if not utxo.output.amount.multi_asset:
    >>>         non_nft_utxo = utxo
    >>>         break

    >>> builder.collaterals.append(non_nft_utxo)

    >>> signed_tx = builder.build_and_sign([self.extended_payment_skey], taker_address)

    >>> chain_context.submit_tx(signed_tx.to_cbor())

The funds locked in script address is successfully retrieved to the taker address.

-------------
Vasil Upgrade
-------------
As part of the Basho phase of Cardano roadmap, the Vasil upgrade brings new capabilities on Plutus, namely reference inputs, inline datums, reference scripts, collateral output and Plutus V2 primitives.

- **Reference inputs** (`CIP-31 <https://cips.cardano.org/cips/cip31/>`_): This upgrade enables data sharing on-chain. Previously, datums were carried in transaction outputs; they stored and provided access to information on the blockchain. However, to access information in this datum, one had to spend the output that the datum was attached to. This required the re-creation of a spent output. The addition of reference inputs now allows developers to look at the datum without extra steps. This facilitates access to information stored on the blockchain without the need for spending and re-creating UTXOs. This can be useful for oracles and other use cases where state need to be inspected.

- **Inline datums** (`CIP-32 <https://cips.cardano.org/cips/cip32/>`_): Transaction datums were previously attached to outputs as hashes. With the implementation of inline datums, developers can now create scripts and attach datums directly to outputs instead of using their hashes. This simplifies how datums are used – a user can see the actual datum rather than supply it to match the given hash.

- **Reference scripts** (`CIP-33 <https://cips.cardano.org/cips/cip33/>`_): In Alonzo, when spending an output locked within a Plutus script, one had to include the script in the spending transaction. This increased the size of the script and caused certain delays in its processing. The reference scripts upgrade allows developers to reference a script without including it in each transaction. This significantly reduces transaction size, improves throughput, and reduces script execution costs (since the script only needs to be paid for once).

- **Explicit collateral output** (`CIP-40 <https://cips.cardano.org/cips/cip40/>`_): Transactions that call Plutus smart contracts are required to put up collateral to cover the potential cost of smart contract execution failure. If contract execution fails during phase 2 validation, all the funds stored in the chose UTXO for the collateral will be lost. After Vasil, user can specify a change address for the script collateral. If the script fails phase-2 validation, only the collateral amount will be taken, and the remaining funds will be sent to the change address.

- **Plutus V2 scripts**: The Vasil upgrade includes a new cost model that's lower than before, and developers will be able to see redeemers for all inputs rather than just the one being passed to the currently executing script.

Using the same FortyTwo example, now in Vasil, we show how reference scripts can be used. Reference script exists at a particular transaction output, and it can be used to witness UTxO at the corresponding script address::

    >>> builder = TransactionBuilder(context)
    >>> builder.add_input_address(giver_address)
    >>> datum = 42
    >>> # Include scripts in the script address
    >>> builder.add_output(
    >>>     TransactionOutput(script_address, 50000000, script=forty_two_script)
    >>> )

With reference script, actual script doesn't need to be included in the transaction anymore in order to spend UTxO sitting at script address::

    >>> utxo_to_spend = None
    >>> # Spend the utxo that has datum/datum hash but no script
    >>> for utxo in chain_context.utxos(str(script_address)):
    >>>     if not utxo.output.script and (
    >>>        utxo.output.datum_hash == datum_hash(datum)
    >>>         or utxo.output.datum == datum
    >>>     ):
    >>>         utxo_to_spend = utxo
    >>>         break

    >>> builder = TransactionBuilder(context)
    >>> builder.add_script_input(utxo_to_spend, datum=datum, redeemer=redeemer)
    >>> take_output = TransactionOutput(taker_address, 25123456)
    >>> builder.add_output(take_output)
    >>> signed_tx = builder.build_and_sign([extended_payment_skey], taker_address)

Again, with the same example, we show that you can send funds to script address with inline datums directly::

    >>> builder = TransactionBuilder(context)
    >>> builder.add_input_address(giver_address)
    >>> datum = 42
    >>> builder.add_output(
    >>>     TransactionOutput(script_address, 50000000, datum=datum, script=forty_two_script)
    >>> )

With inline datum, we no longer have to include a datum within our transaction for our plutus spending scripts. Instead we can specify the transaction output where our datum exists to be used in conjunction with our Plutus spending script. This reduces the overall size of our transaction::

    >>> utxo_to_spend = None
    >>> # Speed the utxo that has both inline script and inline datum
    >>> for utxo in chain_context.utxos(str(script_address)):
    >>>     if utxo.output.datum and utxo.output.script:
    >>>         utxo_to_spend = utxo
    >>>         break

    >>> builder = TransactionBuilder(context)
    >>> builder.add_script_input(utxo_to_spend, redeemer=redeemer)
    >>> take_output = TransactionOutput(taker_address, 25123456)
    >>> builder.add_output(take_output)
    >>> signed_tx = builder.build_and_sign([extended_payment_skey], taker_address)


