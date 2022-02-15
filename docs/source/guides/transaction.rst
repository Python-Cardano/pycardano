===========
Transaction
===========

Cardano transactions are usually involved with three child components, transaction input(s), transaction output(s), and
transaction fee. There are two approaches of creating transactions in PyCardano. The first one is to provide child
components explicitly, which is also referred as creating "raw transactions". The second one is to use a transaction
builder, which is usually more user-friendly.

Below are two examples that generates the same transaction using different approaches. The transaction is simply sending
100000 ADA to ourselves, and paying the network fees.


---------------
Raw transaction
---------------

Step 1

Define Tx input::

    >>> from pycardano import (
    ...     PaymentSigningKey,
    ...     PaymentVerificationKey,
    ...     Transaction,
    ...     TransactionBody,
    ...     TransactionInput,
    ...     TransactionOutput,
    ...     TransactionWitnessSet,
    ...     VerificationKeyWitness,
    ... )
    >>> # Assume the UTxO is sitting at index 0 of tx 732bfd67e66be8e8288349fcaaa2294973ef6271cc189a239bb431275401b8e5
    >>> tx_id = "732bfd67e66be8e8288349fcaaa2294973ef6271cc189a239bb431275401b8e5"
    >>> tx_in = TransactionInput.from_primitive([tx_id, 0])


Step 2

Define Tx output. Suppose we have total of 900000000000 lovelace, and we need to pay 165897 as network fee, then
we will get 799999834103 as change::

    >>> address = "addr_test1vrm9x2zsux7va6w892g38tvchnzahvcd9tykqf3ygnmwtaqyfg52x"

    >>> # Define two transaction outputs, the first one is the amount we want to send, the second one is the change.
    >>> output1 = TransactionOutput.from_primitive([address, 100000000000])
    >>> output2 = TransactionOutput.from_primitive([address, 799999834103])

Step 3

Create a transaction body from the input and outputs defined above and add transaction fee::

    >>> tx_body = TransactionBody(inputs=[tx_in], outputs=[output1, output2], fee=165897)


Step 4

Sign the transaction body hash and create a complete transaction::

    >>> sk = PaymentSigningKey.load("path/to/payment.skey")

    >>> # Derive a verification key from the signing key
    >>> vk = PaymentVerificationKey.from_signing_key(sk)

    >>> # Sign the transaction body hash
    >>> signature = sk.sign(tx_body.hash())

    >>> # Add verification key and the signature to the witness set
    >>> vk_witnesses = [VerificationKeyWitness(vk, signature)]

    >>> # Create final signed transaction
    >>> signed_tx = Transaction(tx_body, TransactionWitnessSet(vkey_witnesses=vk_witnesses))


A complete example could be found `here <https://github.com/cffls/pycardano/blob/main/examples/raw_transaction.py>`_.

Notice that, to create a transaction, we need to know which transaction input to use, the amount of changes to return
to the sender, and the amount of fee to pay to the network, which is possible to calculate, but requiring
additional efforts. Instead, we can use a
`transaction builder <../api/pycardano.transaction.html#pycardano.txbuilder.TransactionBuilder>`_
to help us autofill in these information.


-------------------
Transaction builder
-------------------

Step 1

To use a transaction builder, we first need to create a chain context, so the builder can read protocol parameters and
search proper transaction inputs to use. Currently, the available chain context is
`BlockFrostChainContext <api/pycardano.backend.base.html#pycardano.backend.blockfrost.BlockFrostChainContext>`_ ::

    >>> from pycardano import BlockFrostChainContext, Network
    >>> network = Network.TESTNET
    >>> context = BlockFrostChainContext("your_blockfrost_project_id", network)


Step 2

Read signing key into the program and generate its corresponding verification key::

    >>> from pycardano import PaymentSigningKey, PaymentVerificationKey, Address
    >>> sk = PaymentSigningKey.load("path/to/payment.skey")
    >>> vk = PaymentVerificationKey.from_signing_key(sk)
    >>> address = Address(pvk.hash(), svk.hash(), network)


Step 3

Create a transaction builder from chain context::

    >>> builder = TransactionBuilder(context)


Step 4

Tell the builder that transaction input will come from our own address::

    >>> builder.add_input_address(address)

Step 5

Specify output amount::

    >>> builder.add_output(TransactionOutput.from_primitive([address, 100000000000]))


Step 6

Create the transaction body using transaction builder::

    >>> tx_body = builder.build(change_address=address)

Step 7

Sign the transaction body hash and create a complete transaction (same as the step 4 in raw transaction example)::

    >>> # Sign the transaction body hash
    >>> signature = sk.sign(tx_body.hash())

    >>> # Add verification key and the signature to the witness set
    >>> vk_witnesses = [VerificationKeyWitness(vk, signature)]

    >>> # Create final signed transaction
    >>> signed_tx = Transaction(tx_body, TransactionWitnessSet(vkey_witnesses=vk_witnesses))


By using transaction builder, we no longer need to specify which UTxO to use as transaction input or calculate
transaction fee, because they are taken care by the transaction builder.

A more complex example of using transaction builder could be found
in this `Github example <https://github.com/cffls/pycardano/blob/main/examples/tx_builder.py>`_.

----------------------
Transaction submission
----------------------

Once we have a signed transaction, it could be submitted to the network. The easiest way to do so is through a chain
context::

    >>> context.submit_tx(signed_tx.to_cbor())

