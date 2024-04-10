===============
Smart Contracts
===============

Smart Contracts on Cardano allow us to incorporate expressive logics to determine when a particular UTxO can be spent.
The official language to write Contracts is Plutus, which is why we will often refer to "Plutus Scripts" and "Plutus binarys".
However, many `many different languages <https://aiken-lang.org/ecosystem-overview#the-alternatives>`_ are emerging
that aim to make the development of contracts more accesible.
In this tutorial, we will focus on  `opshin <https://github.com/OpShin/opshin>`_,
a Smart Contract language based on python.
In order to understand how Smart Contracts work on Cardanos eUTxO model we need to understand a couple of concepts.

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

    >>> from pycardano import PlutusData, Unit
    >>> empty_datum = Unit()
    >>> empty_datum.to_cbor().hex()
    'd87980'

Sample datum with int, bytes, List and hashmap inputs::

    >>> # Create sample datum
    >>> from typing import List, Dict
    >>> from dataclasses import dataclass
    >>> @dataclass
    ... class MyDatum(PlutusData):
    ...     CONSTR_ID = 1
    ...     a: int
    ...     b: bytes
    ...     c: List[int]
    ...     d: Dict[int, bytes]

    >>> datum = MyDatum(123, b"1234", [4, 5, 6], {1: b"1", 2: b"2"})
    >>> datum.to_cbor().hex()
    'd87a9f187b443132333483040506a2014131024132ff'

You can also wrap `PlutusData` within `PlutusData`::

    >>> @dataclass
    ... class InclusionDatum(PlutusData):
    ...     CONSTR_ID = 1
    ...     beneficiary: bytes
    ...     deadline: int
    ...     other_data: MyDatum

    >>> key_hash = bytes.fromhex("c2ff616e11299d9094ce0a7eb5b7284b705147a822f4ffbd471f971a")
    >>> deadline = 1643235300000
    >>> other_datum = MyDatum(123, b"1234", [4, 5, 6], {1: b"1", 2: b"2"})
    >>> include_datum = InclusionDatum(key_hash, deadline, other_datum)
    >>> include_datum.to_cbor().hex()
    'd87a9f581cc2ff616e11299d9094ce0a7eb5b7284b705147a822f4ffbd471f971a1b0000017e9874d2a0d8668218829f187b44313233349f040506ffa2014131024132ffff'

`PlutusData` supports conversion from/to JSON format, which
is easier to read and write. The above could be convered to JSON like this::

    >>> encoded_json = include_datum.to_json(separators=(",", ":")

Similarly, redeemer can be serialized like following::

    >>> data = MyDatum(123, b"234", IndefiniteList([]), {1: b"1", 2: b"2"})
    >>> redeemer = Redeemer(data, ExecutionUnits(1000000, 1000000))
    >>> redeemer.to_cbor().hex()
    '840000d8668218829f187b433233349fffa2014131024132ff821a000f42401a000f4240'

--------------------------------
Datum Deserialization
--------------------------------

Deserialization of PlutusData generally has two different paths, based on whether you know the structure of the Plutus Datum you are trying to deserialize or not.
If you know the structure in advance, subclass the `PlutusData` type and configure it to match the data type that you expect to receive. If the datatype does not match, the deserialization will throw an Exception! So make sure that the data really follows the format that you expect.::

    >>> # Create sample datum
    >>> from typing import List, Dict
    >>> @dataclass
    ... class MyDatum(PlutusData):
    ...     CONSTR_ID = 1
    ...     a: int
    ...     b: bytes
    ...     c: List[int]
    ...     d: Dict[int, bytes]

    >>> MyDatum.from_cbor(bytes.fromhex('d87a9f187b443132333483040506a2014131024132ff'))
    MyDatum(a=123, b=b'1234', c=[4, 5, 6], d={1: b'1', 2: b'2'})
    >>> # The Inclusion Datum will not be correctly deserialized
    >>> MyDatum.from_cbor(bytes.fromhex('d87a9f581cc2ff616e11299d9094ce0a7eb5b7284b705147a822f4ffbd471f971a1b0000017e9874d2a0d8668218829f187b44313233349f040506ffa2014131024132ffff'))
    DeserializeException(f"Cannot deserialize object: \n{v}\n to type {t}.")
    pycardano.exception.DeserializeException: Cannot deserialize object:
    b'\xc2\xffan\x11)\x9d\x90\x94\xce\n~\xb5\xb7(KpQG\xa8"\xf4\xff\xbdG\x1f\x97\x1a'
     to type <class 'int'>.

If you do not know the structure of the Datum in advance, use `RawPlutusDatum.from_cbor`.
As you can see, this will not tell you anything about the `meaning` of specific fields, CBOR Tags etc - this is because the meaning are not stored on chain. In the CBOR, just the types are known and hence restoring a raw datum will return to you just the types.::

    >>> from pycardano import RawPlutusData
    >>> RawPlutusData.from_cbor(bytes.fromhex("d87a9f187b443132333483040506a2014131024132ff"))
    RawPlutusData(data=CBORTag(122, [123, b'1234', [4, 5, 6], {1: b'1', 2: b'2'}]))

Note that there are specific fields you may need.
 * **Builtin**: If you don't know the structure of a datum inside a PlutusDatum. It will be decoded as RawPlutusDatum.
 * **IndefiniteList**: A list that is in theory unbounded. This may be required by the Cardano node in case a list has more than 64 elements.
 * **ByteString**: Similarly to IndefiniteList, this denotes a `bytes` element that may be longer than 64 bytes and correctly encodes it in CBOR so that the result is accepted by the Cardano node.


-----------------------
Example - Gift Contract
-----------------------

We demonstrate how these concepts come into play using a simple example from `opshin <https://github.com/ImperatorLang/opshin>`_.
A user can lock funds together with a public key hash.
The contract will make sure that only the owner of the matching private key can redeem the gift.

We will first compile the contract locally. For this, you will need to have installed python3.8.

Step 1

Open a file called ``gift.py`` and fill it with the following code:::

    from opshin.prelude import *

    @dataclass()
    class CancelDatum(PlutusData):
        pubkeyhash: bytes


    def validator(datum: CancelDatum, redeemer: None, context: ScriptContext) -> None:
        sig_present = False
        for s in context.tx_info.signatories:
            if datum.pubkeyhash == s:
                sig_present = True
        assert sig_present


Step 2

Install the python package ``opshin``. We can then build the contract.

.. code:: bash

    $ python3.8 -m venv venv
    $ source venv/bin/activate
    $ pip install opshin
    $ opshin build gift.py

This is it! You will now find all relevant artifacts for proceeding in the folder ``gift/``.

Step 3

Back into the python console.
Similar to `Transaction guide <../guides/transaction.html>`_, we build a chain context using `BlockFrostChainContext <../api/pycardano.backend.base.html#pycardano.backend.blockfrost.BlockFrostChainContext>`_::

    >>> from blockfrost import ApiUrls
    >>> from pycardano import BlockFrostChainContext
    >>> context = BlockFrostChainContext("your_blockfrost_project_id", base_url=ApiUrls.preprod.value)

Step 4

Create script address::

    >>> import cbor2
    >>> from pycardano import (
    ...     Address,
    ...     PaymentVerificationKey,
    ...     PaymentSigningKey,
    ...     plutus_script_hash,
    ...     Transaction,
    ...     TransactionBuilder,
    ...     TransactionOutput,
    ...     PlutusData,
    ...     Redeemer,
    ...     PlutusV2Script,
    ...     Network,
    ...     datum_hash,
    ... )

    >>> # This artifact was generated in step 2
    >>> with open("gift/script.cbor", "r") as f:
    >>>     script_hex = f.read()
    >>> gift_script = PlutusV2Script(bytes.fromhex(script_hex))

    >>> script_hash = plutus_script_hash(gift_script)
    >>> network = Network.TESTNET
    >>> script_address = Address(script_hash, network=network)

Step 5

Giver/Locker sends funds to script address.
We will attach the public key hash of a receiver address as datum to the utxo.
Note that we will just use the datatype defined in the contract, as it also uses ``PlutusData``.

::

    >>> payment_vkey = PaymentVerificationKey.load("path/to/payment.vkey")
    >>> payment_skey = PaymentSigningKey.load("path/to/payment.skey")
    >>> giver_address = Address(payment_vkey.hash(), network=network)

    >>> payment_vkey_2 = PaymentVerificationKey.load("path/to/payment2.vkey")
    >>> payment_skey_2 = PaymentSigningKey.load("path/to/payment2.skey")
    >>> taker_address = Address(payment_vkey_2.hash(), network=network)

    >>> builder = TransactionBuilder(context)
    >>> builder.add_input_address(giver_address)

    >>> from gift import CancelDatum
    >>> datum = CancelDatum(payment_vkey_2.hash().to_primitive())
    >>> builder.add_output(
    >>>     TransactionOutput(script_address, 50000000, datum_hash=datum_hash(datum))
    >>> )

Build, sign and submit the transaction:

   >>> signed_tx = builder.build_and_sign([payment_skey], giver_address)
   >>> context.submit_tx(signed_tx.to_cbor_hex())

Step 6

Taker/Unlocker sends transaction to consume funds. Here we specify the redeemer tag as spend and pass in no special redeemer, as it is being ignored by the contract.::

    >>> redeemer = Redeemer(PlutusData())  # The plutus equivalent of None

    >>> utxo_to_spend = context.utxos(str(script_address))[0]

    >>> builder = TransactionBuilder(context)

Add info on the UTxO to spend, Plutus script, actual datum and the redeemer. Specify funds amount to take::

    >>> builder.add_script_input(utxo_to_spend, gift_script, datum, redeemer)
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

    >>> signed_tx = builder.build_and_sign([payment_skey_2], taker_address)


Uh oh! That failed. We forgot to add the taker as a `required` signer, so that the contract knows
that they will sign the transaction::

    >>> builder.required_signers = [payment_vkey_2.hash()]

Now lets try to resubmit this::

    >>> signed_tx = builder.build_and_sign([payment_skey_2], taker_address)

    >>> context.submit_tx(signed_tx.to_cbor_hex())

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
    >>>     TransactionOutput(script_address, 50000000, script=gift_script)
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
    >>> signed_tx = builder.build_and_sign([payment_skey], taker_address)

Again, with the same example, we show that you can send funds to script address with inline datums directly::

    >>> builder = TransactionBuilder(context)
    >>> builder.add_input_address(giver_address)
    >>> datum = 42
    >>> builder.add_output(
    >>>     TransactionOutput(script_address, 50000000, datum=datum, script=gift_script)
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
    >>> signed_tx = builder.build_and_sign([payment_skey], taker_address)


