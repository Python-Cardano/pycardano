"""Cryptographic keys that could be used in address generation and transaction signing."""

from __future__ import annotations

import json
import os
from typing import Type

from nacl.encoding import RawEncoder
from nacl.hash import blake2b
from nacl.public import PrivateKey
from nacl.signing import SigningKey as NACLSigningKey

from pycardano.crypto.bip32 import BIP32ED25519PrivateKey, HDWallet
from pycardano.exception import InvalidKeyTypeException
from pycardano.hash import VERIFICATION_KEY_HASH_SIZE, VerificationKeyHash
from pycardano.serialization import CBORSerializable, limit_primitive_type

__all__ = [
    "Key",
    "ExtendedSigningKey",
    "ExtendedVerificationKey",
    "VerificationKey",
    "SigningKey",
    "PaymentExtendedSigningKey",
    "PaymentExtendedVerificationKey",
    "PaymentSigningKey",
    "PaymentVerificationKey",
    "PaymentKeyPair",
    "StakeExtendedSigningKey",
    "StakeExtendedVerificationKey",
    "StakeSigningKey",
    "StakeVerificationKey",
    "StakeKeyPair",
]


class Key(CBORSerializable):
    """A class that holds a cryptographic key and some metadata. e.g. signing key, verification key."""

    KEY_TYPE = ""
    DESCRIPTION = ""

    def __init__(self, payload: bytes, key_type: str = None, description: str = None):
        self._payload = payload
        self._key_type = key_type or self.KEY_TYPE
        self._description = description or self.KEY_TYPE

    @property
    def payload(self) -> bytes:
        return self._payload

    @property
    def key_type(self) -> str:
        return self._key_type

    @property
    def description(self) -> str:
        return self._description

    def to_primitive(self) -> bytes:
        return self.payload

    @classmethod
    @limit_primitive_type(bytes)
    def from_primitive(cls: Type["Key"], value: bytes) -> Key:
        return cls(value)

    def to_json(self) -> str:
        """Serialize the key to JSON.

        The json output has three fields: "type", "description", and "cborHex".

        Returns:
            str: JSON representation of the key.
        """
        return json.dumps(
            {
                "type": self.key_type,
                "description": self.description,
                "cborHex": self.to_cbor(),
            }
        )

    @classmethod
    def from_json(cls, data: str, validate_type=False) -> Key:
        """Restore a key from a JSON string.

        Args:
            data (str): JSON string.
            validate_type (bool): Checks whether the type specified in json object is the same
                as the class's default type.

        Returns:
            Key: The key restored from JSON.

        Raises:
            InvalidKeyTypeException: When `validate_type=True` and the type in json is not equal to the default type
                of the Key class used.
        """
        obj = json.loads(data)

        if validate_type and obj["type"] != cls.KEY_TYPE:
            raise InvalidKeyTypeException(
                f"Expect key type: {cls.KEY_TYPE}, got {obj['type']} instead."
            )

        return cls(
            cls.from_cbor(obj["cborHex"]).payload,
            key_type=obj["type"],
            description=obj["description"],
        )

    def save(self, path: str):
        if os.path.isfile(path):
            if os.stat(path).st_size > 0:
                raise IOError(f"File {path} already exists!")
        with open(path, "w") as f:
            f.write(self.to_json())

    @classmethod
    def load(cls, path: str):
        with open(path) as f:
            return cls.from_json(f.read())

    def __bytes__(self):
        return self.payload

    def __eq__(self, other):
        if not isinstance(other, Key):
            return False
        else:
            return (
                self.payload == other.payload
                and self.description == other.description
                and self.key_type == other.key_type
            )

    def __repr__(self) -> str:
        return self.to_json()


class SigningKey(Key):
    def sign(self, data: bytes) -> bytes:
        signed_message = NACLSigningKey(self.payload).sign(data)
        return signed_message.signature

    def to_verification_key(self) -> VerificationKey:
        verification_key = NACLSigningKey(self.payload).verify_key
        return VerificationKey(
            bytes(verification_key),
            self.key_type.replace("Signing", "Verification"),
            self.description.replace("Signing", "Verification"),
        )

    @classmethod
    def generate(cls) -> SigningKey:
        signing_key = PrivateKey.generate()
        return cls(bytes(signing_key))


class VerificationKey(Key):
    def hash(self) -> VerificationKeyHash:
        """Compute a blake2b hash from the key

        Returns:
            VerificationKeyHash: Hash output in bytes.
        """
        return VerificationKeyHash(
            blake2b(self.payload, VERIFICATION_KEY_HASH_SIZE, encoder=RawEncoder)
        )

    @classmethod
    def from_signing_key(cls, key: SigningKey) -> VerificationKey:
        return key.to_verification_key()


class ExtendedSigningKey(Key):
    def sign(self, data: bytes) -> bytes:
        private_key = BIP32ED25519PrivateKey(self.payload[:64], self.payload[96:])
        return private_key.sign(data)

    def to_verification_key(self) -> ExtendedVerificationKey:
        return ExtendedVerificationKey(
            self.payload[64:],
            self.key_type.replace("Signing", "Verification"),
            self.description.replace("Signing", "Verification"),
        )

    @classmethod
    def from_hdwallet(cls, hdwallet: HDWallet) -> ExtendedSigningKey:
        if hdwallet.xprivate_key is None or hdwallet.chain_code is None:
            raise InvalidKeyTypeException(
                "The hdwallet doesn't contain extended private key or chain code info."
            )

        return cls(
            payload=hdwallet.xprivate_key + hdwallet.public_key + hdwallet.chain_code,
            key_type="PaymentExtendedSigningKeyShelley_ed25519_bip32",
            description="Payment Signing Key",
        )


class ExtendedVerificationKey(Key):
    def hash(self) -> VerificationKeyHash:
        """Compute a blake2b hash from the key, excluding chain code

        Returns:
            VerificationKeyHash: Hash output in bytes.
        """
        return self.to_non_extended().hash()

    @classmethod
    def from_signing_key(cls, key: ExtendedSigningKey) -> ExtendedVerificationKey:
        return key.to_verification_key()

    def to_non_extended(self) -> VerificationKey:
        """Get the 32-byte verification with chain code trimmed off

        Returns:
            VerificationKey: 32-byte verification with chain code trimmed off
        """
        return VerificationKey(self.payload[:32])


class PaymentSigningKey(SigningKey):
    KEY_TYPE = "PaymentSigningKeyShelley_ed25519"
    DESCRIPTION = "Payment Signing Key"


class PaymentVerificationKey(VerificationKey):
    KEY_TYPE = "PaymentVerificationKeyShelley_ed25519"
    DESCRIPTION = "Payment Verification Key"


class PaymentExtendedSigningKey(ExtendedSigningKey):
    KEY_TYPE = "PaymentExtendedSigningKeyShelley_ed25519_bip32"
    DESCRIPTION = "Payment Signing Key"


class PaymentExtendedVerificationKey(ExtendedVerificationKey):
    KEY_TYPE = "PaymentExtendedVerificationKeyShelley_ed25519_bip32"
    DESCRIPTION = "Payment Verification Key"


class PaymentKeyPair:
    def __init__(
        self, signing_key: PaymentSigningKey, verification_key: PaymentVerificationKey
    ):
        self.signing_key = signing_key
        self.verification_key = verification_key

    @classmethod
    def generate(cls) -> PaymentKeyPair:
        signing_key = PaymentSigningKey.generate()
        return cls.from_signing_key(signing_key)

    @classmethod
    def from_signing_key(cls, signing_key: PaymentSigningKey) -> PaymentKeyPair:
        return cls(signing_key, PaymentVerificationKey.from_signing_key(signing_key))

    def __eq__(self, other):
        if isinstance(other, PaymentKeyPair):
            return (
                other.signing_key == self.signing_key
                and other.verification_key == self.verification_key
            )


class StakeSigningKey(SigningKey):
    KEY_TYPE = "StakeSigningKeyShelley_ed25519"
    DESCRIPTION = "Stake Signing Key"


class StakeVerificationKey(VerificationKey):
    KEY_TYPE = "StakeVerificationKeyShelley_ed25519"
    DESCRIPTION = "Stake Verification Key"


class StakeExtendedSigningKey(ExtendedSigningKey):
    KEY_TYPE = "StakeExtendedSigningKeyShelley_ed25519_bip32"
    DESCRIPTION = "Stake Signing Key"


class StakeExtendedVerificationKey(ExtendedVerificationKey):
    KEY_TYPE = "StakeExtendedVerificationKeyShelley_ed25519_bip32"
    DESCRIPTION = "Stake Verification Key"


class StakeKeyPair:
    def __init__(
        self, signing_key: StakeSigningKey, verification_key: StakeVerificationKey
    ):
        self.signing_key = signing_key
        self.verification_key = verification_key

    @classmethod
    def generate(cls) -> StakeKeyPair:
        signing_key = StakeSigningKey.generate()
        return cls.from_signing_key(signing_key)

    @classmethod
    def from_signing_key(cls, signing_key: StakeSigningKey) -> StakeKeyPair:
        return cls(signing_key, StakeVerificationKey.from_signing_key(signing_key))
