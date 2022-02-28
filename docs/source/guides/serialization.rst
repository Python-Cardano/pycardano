=============
Serialization
=============


Cardano uses Concise Binary Object Representation (`CBOR <https://cbor.io/>`_) to
store on-chain data. Reading and writing data from/to blockchain requires serialization and deserialization of CBOR
binaries.

A core feature PyCardano provides is serialization. It can serialize Python objects into CBOR bytes and deserialize
CBOR bytes back to Python objects. Most Classes in PyCardano are child class of
`CBORSerializable <../api/pycardano.serialization.html#pycardano.serialization.CBORSerializable>`_, which provides two
CBOR-related methods. `to_cbor <../api/pycardano.serialization.html#pycardano.serialization.CBORSerializable.to_cbor>`_
generates CBOR bytes from an instance, and
`from_cbor <../api/pycardano.serialization.html#pycardano.serialization.CBORSerializable.from_cbor>`_ restore an instance.

Examples::

    >>> from pycardano import (TransactionBody,
    ...                        TransactionInput,
    ...                        TransactionId,
    ...                        TransactionOutput)
    >>> 
    >>> tx_id_hex = "732bfd67e66be8e8288349fcaaa2294973ef6271cc189a239bb431275401b8e5"
    >>> tx_in = TransactionInput(TransactionId(bytes.fromhex(tx_id_hex)), 0)
    >>> addr = Address.decode(
    ...     "addr_test1vrm9x2zsux7va6w892g38tvchnzahvcd9tykqf3ygnmwtaqyfg52x"
    ... )
    >>> output1 = TransactionOutput(addr, 100000000000)
    >>> output2 = TransactionOutput(addr, 799999834103)
    >>> fee = 165897
    >>> tx_body = TransactionBody(
    ...     inputs=[tx_in],
    ...     outputs=[output1, output2],
    ...     fee=fee
    ... )
    >>> cbor_hex = tx_body.to_cbor()
    a50081825820732bfd67e66be8e8288349fcaaa2294973ef6271cc189a239bb431275401b8e500018282581d60f6532850e1bccee9c72a9113ad98bcc5dbb30d2ac960262444f6e5f41b000000174876e80082581d60f6532850e1bccee9c72a9113ad98bcc5dbb30d2ac960262444f6e5f41b000000ba43b4b7f7021a000288090d800e80

    >>> restored_tx_body = TransactionBody.from_cbor(cbor_hex)
    >>> assert tx_body == restored_tx_body

    >>> restored_tx_body
    {'auxiliary_data_hash': None,
    'certificates': None,
    'collateral': [],
    'fee': 165897,
    'inputs': [{'index': 0,
    'transaction_id': TransactionId(hex='732bfd67e66be8e8288349fcaaa2294973ef6271cc189a239bb431275401b8e5')}],
    'mint': None,
    'network_id': None,
    'outputs': [{'address': addr_test1vrm9x2zsux7va6w892g38tvchnzahvcd9tykqf3ygnmwtaqyfg52x,
    'amount': 100000000000,
    'datum_hash': None},
                {'address': addr_test1vrm9x2zsux7va6w892g38tvchnzahvcd9tykqf3ygnmwtaqyfg52x,
    'amount': 799999834103,
    'datum_hash': None}],
    'required_signers': [],
    'script_data_hash': None,
    'ttl': None,
    'update': None,
    'validity_start': None,
    'withdraws': None}
