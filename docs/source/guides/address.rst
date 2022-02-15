================
Keys & Addresses
================

----
Keys
----

The most common keys in Cardano are payment key and stake key.
They are both `Ed25519 <https://ed25519.cr.yp.to/>`_ keys.

Payment key is usually used to sign transactions that involve funds transfers, while stake key
is usually used to sign transactions that involve staking-related activities, e.g. stake address registration,
delegation. PyCardano provides APIs to create, save, and loads payment keys and stake keys.

New payment keys and stake keys could be generated using class method
`generate <../api/pycardano.key.html#pycardano.key.SigningKey.generate>`_. Their corresponding
verification (public) key could be created using class method
`from_signing_key <../api/pycardano.key.html#pycardano.key.VerificationKey.from_signing_key>`_::

    >>> from pycardano import PaymentSigningKey, StakeSigningKey, PaymentVerificationKey, StakeVerificationKey
     
    >>> payment_signing_key = PaymentSigningKey.generate()
    >>> payment_verification_key = PaymentVerificationKey.from_signing_key(payment_signing_key)

    >>> stake_signing_key = StakeSigningKey.generate()
    >>> stake_verification_key = StakeVerificationKey.from_signing_key(stake_signing_key)


Alternatively, a key pair (signing key + verification key) could be generated together::

    >>> from pycardano import PaymentKeyPair, StakeKeyPair

    >>> payment_key_pair = PaymentKeyPair.generate()
    >>> payment_signing_key = payment_key_pair.signing_key
    >>> payment_verification_key = payment_key_pair.verification_key

    >>> stake_key_pair = StakeKeyPair.generate()
    >>> stake_signing_key = stake_key_pair.signing_key
    >>> stake_verification_key = stake_key_pair.verification_key


A key could be saved to and loaded from a file::

    >>> # Save
    >>> payment_signing_key.save("payment.skey")
    >>> payment_verification_key.save("payment.vkey")

    >>> # Load
    >>> payment_signing_key = payment_signing_key.load("payment.skey")
    >>> payment_verification_key = payment_verification_key.load("payment.vkey")

Signing keys can sign messages (in bytes)::

    >>> message = b"Hello world!"
    >>> payment_signing_key.signing_key.sign(b"Hello world!")
    b'\xf1N\x96\x05\xe8[\xa3"g5\x95\x80\xca\x88\x93&\xefD\xc3\x9fXj{\xaf\x01mna\xa92+z\x08\x9d\x1eG\x9fN\xc2\xb8\xb1\xab\xbf\xee\xf7\xa6\x08\x87\xfa\xeb\x9bGW\xba\xb7\xd8\xb2\xbb\xe0\x9c"\x0b\xe0\x07'

This guide only covers address keys. There is another category of keys called "Node keys".
You can learn more about keys `here <https://docs.cardano.org/core-concepts/cardano-keys>`_.

---------
Addresses
---------

Cardano addresses (after Shelley era) are derived from blake2b-256 hash of verification (public) keys.
For more information, please read `cardano addresses <https://docs.cardano.org/core-concepts/cardano-addresses>`_ in
Cardano's official doc.

Addresses also depends on the network type, either mainnet or testnet. Therefore, network type should be specified
when creating an address.

Base address is the most commonly used address type. It is generated from a payment verification key and
a stake verification key::

    >>> from pycardano import Address, Network

    >>> base_address = Address(payment_part=payment_verification_key.hash(),
    ...                        staking_part=stake_verification_key.hash(),
    ...                        network=Network.TESTNET)

    >>> base_address
    "addr_test1vr2p8st5t5cxqglyjky7vk98k7jtfhdpvhl4e97cezuhn0cqcexl7"

An address object could also be created from an address string directly::

    >>> address = Address.from_primitive("addr_test1vr2p8st5t5cxqglyjky7vk98k7jtfhdpvhl4e97cezuhn0cqcexl7")


An enterprise address does not have staking functionalities, it is created from a payment verification key only::

    >>> enterprise_address = Address(payment_part=payment_verification_key.hash(),
    ...                              network=Network.TESTNET)


A stake address does not have payment functionalities, it is created from a stake verification key only::

    >>> stake_address = Address(staking_part=payment_verification_key.hash(),
    ...                         network=Network.TESTNET)

