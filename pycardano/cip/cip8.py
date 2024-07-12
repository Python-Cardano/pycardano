from typing import Optional, Union

from cbor2 import CBORTag, dumps
from cose.algorithms import EdDSA
from cose.headers import KID, Algorithm
from cose.keys import CoseKey
from cose.keys.curves import Ed25519
from cose.keys.keyops import SignOp, VerifyOp
from cose.keys.keyparam import KpAlg, KpKeyOps, KpKty, OKPKpCurve, OKPKpD, OKPKpX
from cose.keys.keytype import KtyOKP
from cose.messages import CoseMessage, Sign1Message

from pycardano.address import Address
from pycardano.crypto import BIP32ED25519PublicKey
from pycardano.key import (
    ExtendedSigningKey,
    ExtendedVerificationKey,
    PaymentVerificationKey,
    SigningKey,
    StakeExtendedSigningKey,
    StakeSigningKey,
    StakeVerificationKey,
)
from pycardano.network import Network

__all__ = ["sign", "verify"]


def sign(
    message: str,
    signing_key: Union[ExtendedSigningKey, SigningKey],
    attach_cose_key: bool = False,
    network: Network = Network.MAINNET,
) -> Union[str, dict]:
    """Sign an arbitrary message with a payment or stake key following CIP-0008.
    Note that a stake key passed in must be of type StakeSigningKey or
    StakeExtendedSigningKey to be detected.

    Args:
        message (str): Message to be signed
        signing_key (SigningKey): Key which is used to sign the message
        attach_cose_key (bool): Whether or not to attach the Cose key to the output
        network (Network): Network to use for the address generation

    Returns:
        Union[str, dict]: A hex-encoded string containing the signed message and verification key.
        In the case of attach_cose_key=True, a dict containing the signed message and Cose key.
    """

    # derive the verification key
    verification_key = signing_key.to_verification_key()
    if isinstance(verification_key, ExtendedVerificationKey):
        verification_key = verification_key.to_non_extended()

    if isinstance(signing_key, StakeSigningKey) or isinstance(
        signing_key, StakeExtendedSigningKey
    ):
        address = Address(
            payment_part=None, staking_part=verification_key.hash(), network=network
        )
    else:
        address = Address(
            payment_part=verification_key.hash(), staking_part=None, network=network
        )

    # create the message object, attach verification key to the header
    msg = Sign1Message(
        phdr={
            Algorithm: EdDSA,
            "address": address.to_primitive(),
        },
        payload=message.encode("utf-8"),
    )

    msg.uhdr = {"hashed": False}

    if not attach_cose_key:
        msg.phdr[KID] = verification_key.to_primitive()

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

    if isinstance(signing_key, ExtendedSigningKey):
        _message = [
            msg.phdr_encoded,
            msg.uhdr_encoded,
            msg.payload,
            signing_key.sign(msg._sig_structure),
        ]

        encoded = dumps(
            CBORTag(msg.cbor_tag, _message), default=msg._custom_cbor_encoder
        )

    else:
        encoded = msg.encode()

    # turn the enocded message into a hex string and remove the first byte
    # which is always "d2"
    signed_message = encoded.hex()[2:]

    if attach_cose_key:
        key_to_return = {
            KpKty: KtyOKP,
            KpAlg: EdDSA,
            OKPKpCurve: Ed25519,
            OKPKpX: verification_key.payload,  # public key
        }

        signed_message = {  # type: ignore
            "signature": signed_message,
            "key": CoseKey.from_dict(key_to_return).encode().hex(),
        }

    return signed_message


def verify(
    signed_message: Union[str, dict],
    attach_cose_key: Optional[bool] = None,
) -> dict:
    """Verify the signature of a COSESign1 message and decode its contents following CIP-0008.
    Supports messages signed by browser wallets or `Message.sign()`.

    Args:
        signed_message (Union[str, dict]): Message to be verified
        attach_cose_key (Optional[bool]): Whether or not the Cose key is included with the signed_message.
            This method will try to determine this automatically if not specified.
            Usually if `signed_message` is a dict, this should be true.

    Returns:
        dict: A dict containing whether or not the message is verified, the message contents,
        and an Address which was used to sign the message.
    """

    if attach_cose_key is None:
        # try to determine automatically if the verification key is included in the header
        if isinstance(signed_message, dict):
            attach_cose_key = True
        else:
            attach_cose_key = False

    if attach_cose_key:
        # The cose key is attached as a dict object which contains the verification key
        # the headers of the signature are emtpy
        assert isinstance(
            signed_message, dict
        ), "signed_message must be a dict if attach_cose_key is True"
        key = signed_message.get("key")
        signed_message = signed_message.get("signature")  # type: ignore

    else:
        key = ""  # key will be extracted later from the payload headers

    # Add back the "D2" header byte and decode
    assert isinstance(
        signed_message, str
    ), "signed_message must be a hex string at this point"
    decoded_message = CoseMessage.decode(bytes.fromhex("d2" + signed_message))

    # generate/extract the cose key
    if not attach_cose_key:
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
        # i,e key is sent separately
        assert isinstance(
            key, str
        ), "key must be a hex string if attach_cose_key is True"
        cose_key = CoseKey.decode(bytes.fromhex(key))
        verification_key = cose_key[OKPKpX]

    # attach the key to the decoded message
    decoded_message.key = cose_key

    if len(verification_key) > 32:
        vk = BIP32ED25519PublicKey(
            public_key=verification_key[:32], chain_code=verification_key[32:]
        )
        vk.verify(
            signature=decoded_message.signature, message=decoded_message._sig_structure
        )
        signature_verified = True
    else:
        signature_verified = decoded_message.verify_signature()

    message = decoded_message.payload.decode("utf-8")

    signing_address = Address.from_primitive(decoded_message.phdr["address"])

    # check that the address attached matches the
    # one of the verification keys used to sign the message

    if signing_address.payment_part is not None:
        addresses_match = (
            signing_address.payment_part
            == PaymentVerificationKey.from_primitive(verification_key).hash()
        )
    else:
        addresses_match = (
            signing_address.staking_part
            == StakeVerificationKey.from_primitive(verification_key).hash()
        )

    verified = signature_verified & addresses_match

    return {
        "verified": verified,
        "message": message,
        "signing_address": signing_address,
    }
