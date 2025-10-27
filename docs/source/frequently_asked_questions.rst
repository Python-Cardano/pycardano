===
FAQ
===

What is PyCardano?
------------------

PyCardano is a standalone Cardano client written in Python. The library is able to create and sign transactions
without depending on third-party Cardano serialization tools, making it a light-weight library that is easy and fast to set up in all kinds of environments.

Where can I find some examples?
-------------------------------
You can find some examples in the `examples <https://github.com/Python-Cardano/pycardano/tree/main/examples>`_ directory. There is also a collection of examples under `awesome-pycardano <https://github.com/B3nac/awesome-pycardano>`_.


What is a transaction builder?
-------------------------------

A transaction builder is a class that helps you build and sign transactions. It provides a user-friendly interface that automatically handles transaction inputs, outputs, fees, and other details based on the context you provide.

Here is an example::

    >>> # Create a transaction builder with a chain context
    >>> builder = TransactionBuilder(context)
    >>> 
    >>> # Add inputs from an address
    >>> builder.add_input_address(address)
    >>> 
    >>> # Add an output - sending 100 ADA to a recipient
    >>> recipient = Address.from_primitive("addr_test1vrm9x2zsux7va6w892g38tvchnzahvcd9tykqf3ygnmwtaqyfg52x")
    >>> builder.add_output(TransactionOutput(recipient, Value.from_primitive([100_000_000])))
    >>> 
    >>> # Build, sign, and submit
    >>> signed_tx = builder.build_and_sign([payment_signing_key], change_address=address)
    >>> context.submit_tx(signed_tx)


.. note::

   The transaction builder in PyCardano is **stateful**. It maintains an internal state for the transaction under construction. Once you use it to build a transaction, that instance cannot be reused to build another transaction. If you need to create multiple transactions, instantiate a new transaction builder for each transaction or create a copy of the builder.




How do I burn a token?
----------------------

To burn a token, create a transaction that mints a negative amount of the token.

Here is an example::

    >>> # Set up the transaction builder with the address containing the tokens
    >>> builder = TransactionBuilder(context)
    >>> builder.add_input_address(address)
    >>> 
    >>> # Add the native script (policy) that governs the token
    >>> native_script = ScriptAll([pub_key_policy, must_before_slot])
    >>> builder.native_scripts = [native_script]
    >>> 
    >>> # Mint negative amount to burn tokens
    >>> policy_id = bytes.fromhex("57fca08abbaddee36da742a839f7d83a7e1d2419f1507fcbf3916522")
    >>> builder.mint = MultiAsset.from_primitive({policy_id: {b"Token1": -100}})
    >>> 
    >>> # Build, sign, and submit
    >>> signed_tx = builder.build_and_sign([payment_signing_key], change_address=address)
    >>> context.submit_tx(signed_tx)

.. note::

   The negative amount in the ``mint`` field indicates burning. To burn 100 tokens, use ``-100``.


Why does a decoded transaction have a different hash than the original transaction?
------------------------------------------------------------------------------------

When you decode a transaction from CBOR using ``Transaction.from_cbor()`` and then re-encode it with ``to_cbor()``, you may notice that the resulting CBOR bytes (and therefore the transaction hash) are different from the original. This is due to non-deterministic CBOR encoding behavior in the C implementation of the ``cbor2`` library.

**Root Cause**

PyCardano uses `cbor2 <https://github.com/agronholm/cbor2/tree/master>`_ for CBOR encoding and decoding. The library has two implementations:

- **C implementation** (default): Faster but less deterministic
- **Pure Python implementation**: Slightly slower but produces consistent, deterministic encodings

The C implementation does not guarantee that the order and structure of certain CBOR elements (such as map keys, array elements, or encoding choices for indefinite vs definite length arrays) will be preserved during deserialization and re-serialization. This can cause:

- **Transaction input order changes** - resulting in a different transaction hash and invalidating signatures (see `issue #311 <https://github.com/Python-Cardano/pycardano/issues/311>`_)
- **Plutus data encoding changes** - altering datum hashes and breaking script validation (see `issue #466 <https://github.com/Python-Cardano/pycardano/issues/466>`_)

**Solution**

Use the **pure Python implementation** of cbor2, which provides deterministic encoding. PyCardano provides a convenience script to ensure the pure Python implementation is installed:

.. code-block:: bash

   ./ensure_pure_cbor2.sh

Or manually install it with:

.. code-block:: bash

   pip uninstall -y cbor2
   pip install --no-binary cbor2 cbor2

**Best Practices**

- Always use the pure Python cbor2 implementation when working with pre-signed transactions or Plutus scripts
- Avoid decoding and re-encoding signed transactions unless absolutely necessary
- Test serialization round-trips if working with complex transactions
- Keep the original CBOR bytes when you need to preserve the exact transaction structure



