========================
Instance/Object creation
========================

In PyCardano, most components and data structures are embedded in Python classes. To construct an instance, we need to
start from its child components, and build everything from bottom up.

For example, we need to create an instance of
`TransactionId <../api/pycardano.hash.html#pycardano.hash.TransactionId>`_
before creating a `TransactionInput <../api/pycardano.transaction.html#pycardano.transaction.TransactionInput>`_.
Similarly, we need to provide an instance of
`Address <../api/pycardano.address.html#pycardano.address.Address>`_
before creating a `TransactionOutput <../api/pycardano.transaction.html#pycardano.transaction.TransactionOutput>`_::

    >>> from pycardano import Address, TransactionId, TransactionInput, TransactionOutput
    >>> tx_id_hex = "732bfd67e66be8e8288349fcaaa2294973ef6271cc189a239bb431275401b8e5"
    >>> tx_id = TransactionId(bytes.fromhex(tx_id_hex))
    >>> tx_in = TransactionInput(tx_id, 0)
    >>> tx_in
    {'index': 0,
     'transaction_id': TransactionId(hex='732bfd67e66be8e8288349fcaaa2294973ef6271cc189a239bb431275401b8e5')}
    >>> addr = Address.decode(
    ...     "addr_test1vrm9x2zsux7va6w892g38tvchnzahvcd9tykqf3ygnmwtaqyfg52x"
    ... )
    >>> tx_out = TransactionOutput(addr, 100000000000)
    >>> tx_out
    {'address': addr_test1vrm9x2zsux7va6w892g38tvchnzahvcd9tykqf3ygnmwtaqyfg52x,
     'amount': 100000000000,
     'datum_hash': None}


Another example is native asset::

    >>> from pycardano import Asset, AssetName, MultiAsset, ScriptHash
    >>> # Create an asset container
    >>> my_asset = Asset()

    >>> # Create names for our assets
    >>> nft1 = AssetName(b"MY_NFT_1")
    >>> nft2 = AssetName(b"MY_NFT_2")

    >>> # Put assets into the asset container with a quantity of 1
    >>> my_asset[nft1] = 1
    >>> my_asset[nft2] = 1

    >>> # Create a MultiAsset container
    >>> my_nft = MultiAsset()

    >>> # Create a policy id
    >>> policy_id = ScriptHash(bytes.fromhex("9c83e0e86689ae56c0753c9a1714980e6b7603bca12530b0e19b0dae"))

    >>> # Put assets into MultiAsset container.
    >>> my_nft[policy_id] = my_asset
    >>> my_nft
    {ScriptHash(hex='9c83e0e86689ae56c0753c9a1714980e6b7603bca12530b0e19b0dae'): {AssetName(b'MY_NFT_1'): 1, AssetName(b'MY_NFT_2'): 2}}


It is rather verbose and tedious to build an instance from ground up. To solve this problem, PyCardano provides an
alternative way of constructing instances: directly constructing an instance from Python primitive types. Because
Python is quite concise in terms of creating dictionary and list literals, we can simplify instance construction by
leveraging this Python feature.

Example of creating an equivalent ``TransactionInput`` and ``TransactionOutput`` from above::

    >>> from pycardano import Address, TransactionId, TransactionInput, TransactionOutput
    >>> tx_in = TransactionInput.from_primitive(
    ...     [bytes.fromhex("732bfd67e66be8e8288349fcaaa2294973ef6271cc189a239bb431275401b8e5"), 0])
    >>> tx_in
        {'index': 0,
         'transaction_id': TransactionId(hex='732bfd67e66be8e8288349fcaaa2294973ef6271cc189a239bb431275401b8e5')}

    >>> tx_out = TransactionOutput.from_primitive(
    ...     ["addr_test1vrm9x2zsux7va6w892g38tvchnzahvcd9tykqf3ygnmwtaqyfg52x", 100000000000])
    >>> tx_out
    {'address': addr_test1vrm9x2zsux7va6w892g38tvchnzahvcd9tykqf3ygnmwtaqyfg52x,
     'amount': 100000000000,
     'datum_hash': None}


Example of creating an equivalent ``MultiAsset`` from above::

    >>> my_nft_alternative = MultiAsset.from_primitive(
    ...     {
    ...         bytes.fromhex("9c83e0e86689ae56c0753c9a1714980e6b7603bca12530b0e19b0dae"): {
    ...             b"MY_NFT_1": 1,
    ...             b"MY_NFT_2": 1
    ...         }
    ...     }
    ... )

    >>> my_nft_alternative
    {ScriptHash(hex='9c83e0e86689ae56c0753c9a1714980e6b7603bca12530b0e19b0dae'): {AssetName(b'MY_NFT_1'): 1, AssetName(b'MY_NFT_2'): 1}}


All child classes of `CBORSerializable <../api/pycardano.serialization.html#pycardano.serialization.CBORSerializable>`_
has a class method
`from_primitive <../api/pycardano.serialization.html#pycardano.serialization.CBORSerializable.from_primitive>`_ that takes
a `Primitive <../api/pycardano.serialization.html#pycardano.serialization.Primitive>`_ as input, which is usually a list
or dictionary. It is not hard to tell that creating an instance using primitives is much more concise and easier than
building it from ground up.

.. note::
    The opposite operation of ``from_primitive`` is
    `to_primitive <../api/pycardano.serialization.html#pycardano.serialization.CBORSerializable.to_primitive>`_, which
    is often used in debugging and internal logic of `serialization <serialization.html>`_.