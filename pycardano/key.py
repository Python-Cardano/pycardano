"""Cryptographic keys that could be used in address generation and transaction signing."""

from __future__ import annotations

import binascii
import json
import os
from typing import Optional, Union

from cose.algorithms import EdDSA
from cose.headers import KID, Algorithm
from cose.keys import CoseKey
from cose.keys.curves import Ed25519
from cose.keys.keyops import SignOp, VerifyOp
from cose.keys.keyparam import KpAlg, KpKeyOps, KpKty, OKPKpCurve, OKPKpD, OKPKpX
from cose.keys.keytype import KtyOKP
from cose.messages import CoseMessage, Sign1Message
from nacl.encoding import RawEncoder
from nacl.hash import blake2b
from nacl.public import PrivateKey
from nacl.signing import SigningKey as NACLSigningKey

from pycardano.address import Address
from pycardano.crypto.bip32 import BIP32ED25519PrivateKey
from pycardano.exception import InvalidKeyTypeException
from pycardano.hash import VERIFICATION_KEY_HASH_SIZE, VerificationKeyHash
from pycardano.serialization import CBORSerializable

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


class Message:
    def __init__(
        self,
        message: Optional[str] = None,
        signed_message: Optional[Union[str, dict]] = None,
    ):

        if not message and not signed_message:
            raise TypeError("Please provide either `message` or `signed_message`.")

        self.message = message
        self.signed_message = signed_message
        self.verified = None

        self.signature_verified = None
        self.signing_address = None
        self.addresses_match = None

    def sign(
        self,
        signing_key: SigningKey,
        verification_key: VerificationKey,
        cose_key_separate: bool = False,
    ):

        # create the message object, attach verification key to the header

        msg = Sign1Message(
            phdr={Algorithm: EdDSA, "address": verification_key.to_primitive()},
            payload=self.message.encode("utf-8"),
        )

        if cose_key_separate:
            msg.phdr[KID] = verification_key.payload

        # build the CoseSign1 signing key from a dictionary
        cose_key = {
            KpKty: KtyOKP,
            OKPKpCurve: Ed25519,
            KpKeyOps: [SignOp, VerifyOp],
            OKPKpD: signing_key.payload,  # private key
            OKPKpX: verification_key.payload,  # public key
        }

        cose_key = CoseKey.from_dict(cose_key)
        msg.key = cose_key  # attach the key to the message

        msg.uhdr = {"hashed": False}

        encoded = msg.encode()

        # turn the enocded message into a hex string and remove the first byte
        # which is always "d2"
        signed_message = binascii.hexlify(encoded).decode("utf-8")[2:]

        if cose_key_separate:
            key_to_return = {
                KpKty: KtyOKP,
                KpAlg: EdDSA,
                OKPKpCurve: Ed25519,
                OKPKpX: verification_key.payload,  # public key
            }

            signed_message = {
                "signature": signed_message,
                "key": binascii.hexlify(CoseKey.from_dict(key_to_return).encode()),
            }

        self.signed_message = signed_message

        return signed_message

    def verify(self, cose_key_separate: Optional[bool] = None):
        """
        Verify the signature of a COSESign1 message and decode.
        Supports messages signed by browser wallets or `Message.sign()`.
        Parameters:
                self.signed_payload (str): A hex-encoded string or dict
        Returns :
                verified (bool): If the signature is verified
                addresses_match (bool): Whether the address provided belongs to the verification key used to sign the message
                message (str): The contents of the signed message
                address (pycardano.Address): The address to which the signing keys belong
            Note: Both `verified` and `address_match` should be True.
        """

        if not self.signed_message:
            raise ValueError(
                "Set `Message.signed_message` before attempting verification."
            )

        if cose_key_separate is None:
            # try to determine automatically if the verification key is included in the header
            if isinstance(self.signed_message, dict):
                cose_key_separate = True
            else:
                cose_key_separate = False

        if cose_key_separate:
            # The cose key is attached as a dict object which contains the verification key
            # the headers of the signature are emtpy
            key = self.signed_message.get("key")
            signed_message = self.signed_message.get("signature")

        else:
            key = ""  # key will be extracted later from the payload headers
            signed_message = self.signed_message

        # Add back the "D2" header byte and decode
        decoded_message = CoseMessage.decode(binascii.unhexlify("d2" + signed_message))

        # generate/extract the cose key
        if not cose_key_separate:

            # get the verification key from the headers
            verification_key = decoded_message.phdr[KID]

            # generate the COSE key
            cose_key = {
                KpKty: KtyOKP,
                OKPKpCurve: Ed25519,
                KpKeyOps: [SignOp, VerifyOp],
                OKPKpX: verification_key,  # public key
            }

            cose_key = CoseKey.from_dict(cose_key)

        else:
            # i,e key is attached to header
            cose_key = CoseKey.decode(binascii.unhexlify(key))
            verification_key = cose_key[OKPKpX]

        # attach the key to the decoded message
        decoded_message.key = cose_key

        self.signature_verified = decoded_message.verify_signature()

        self.message = decoded_message.payload.decode("utf-8")

        self.signing_address = Address.from_primitive(decoded_message.phdr["address"])

        # check that the address atatched in the headers matches the one of the verification key used to sign the message
        self.addresses_match = (
            self.signing_address.payment_part
            == PaymentVerificationKey.from_primitive(verification_key).hash()
        )

        self.verified = self.signature_verified & self.addresses_match

        return self.verified
