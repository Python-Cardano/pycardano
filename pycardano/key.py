"""Cryptographic keys that could be used in address generation and transaction signing."""

from __future__ import annotations

import json
import os

from nacl.bindings import crypto_sign_PUBLICKEYBYTES, crypto_sign_SEEDBYTES
from nacl.encoding import RawEncoder
from nacl.hash import blake2b
from nacl.public import PrivateKey
from nacl.signing import SigningKey as NACLSigningKey

from pycardano.exception import InvalidKeyTypeException
from pycardano.hash import VERIFICATION_KEY_HASH_SIZE, VerificationKeyHash
from pycardano.serialization import CBORSerializable

__all__ = [
    "Key",
    "VerificationKey",
    "SigningKey",
    "PaymentSigningKey",
    "PaymentVerificationKey",
    "PaymentKeyPair",
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
    def from_primitive(cls, value: bytes) -> Key:
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


class VerificationKey(Key):

    SIZE = crypto_sign_PUBLICKEYBYTES

    def hash(self) -> VerificationKeyHash:
        """Compute a blake2b hash from the key

        Args:
            hash_size: Size of the hash output in bytes.

        Returns:
            VerificationKeyHash: Hash output in bytes.
        """
        return VerificationKeyHash(
            blake2b(self.payload, VERIFICATION_KEY_HASH_SIZE, encoder=RawEncoder)
        )

    @classmethod
    def from_signing_key(cls, key: SigningKey) -> VerificationKey:
        verification_key = NACLSigningKey(bytes(key)).verify_key
        return cls(bytes(verification_key))


class SigningKey(Key):

    SIZE = crypto_sign_SEEDBYTES

    def sign(self, data: bytes) -> bytes:
        signed_message = NACLSigningKey(self.payload).sign(data)
        return signed_message.signature

    @classmethod
    def generate(cls) -> SigningKey:
        signing_key = PrivateKey.generate()
        return cls(bytes(signing_key))


class PaymentSigningKey(SigningKey):
    KEY_TYPE = "PaymentSigningKeyShelley_ed25519"
    DESCRIPTION = "Payment Verification Key"


class PaymentVerificationKey(VerificationKey):
    KEY_TYPE = "PaymentVerificationKeyShelley_ed25519"
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
    DESCRIPTION = "Stake Verification Key"


class StakeVerificationKey(VerificationKey):
    KEY_TYPE = "StakeVerificationKeyShelley_ed25519"
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
