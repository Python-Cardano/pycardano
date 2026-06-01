from dataclasses import dataclass
from typing import Any, List, Optional, Union

from cbor2 import CBORTag

from pycardano.cip.cip67 import CIP67TokenName, InvalidCIP67Token
from pycardano.hash import ScriptHash, VerificationKeyHash
from pycardano.plutus import PlutusData, Unit, Primitive
from pycardano.serialization import IndefiniteList
from pycardano.transaction import AssetName


ROYALTY_TOKEN_LABEL = 500
ROYALTY_TOKEN_PAYLOAD = b"Royalty"


class InvalidCIP102Token(Exception):
    pass


class CIP102RoyaltyTokenName(CIP67TokenName):
    """Generates a CIP-102 royalty token name from an input postfix.

    The royalty token name is a CIP-67 encoded token name with label ``500`` and
    payload ``"Royalty"`` followed by an optional integer postfix.

    For more information on CIP-102:
    https://github.com/cardano-foundation/CIPs/tree/master/CIP-0102

    Args:
        data: The token name as bytes, str, or AssetName
    """

    def __init__(self, data: Union[bytes, str, AssetName]):
        super().__init__(data)

        if self.label != ROYALTY_TOKEN_LABEL:
            raise InvalidCIP102Token(
                f"Royalty token must have label {ROYALTY_TOKEN_LABEL}, "
                f"got {self.label}."
            )

        if not self.payload[4:].startswith(ROYALTY_TOKEN_PAYLOAD):
            raise InvalidCIP102Token(
                f"Royalty token payload must start with 'Royalty', "
                f"got {self.payload[4:]}."
            )

    @classmethod
    def from_postfix(cls, postfix: Optional[int] = None) -> "CIP102RoyaltyTokenName":
        """Create a royalty token name with an optional integer postfix.

        Args:
            postfix: Optional integer postfix to distinguish multiple royalty tokens
                under the same policy ID (version 2). If ``None``, creates the
                base ``(500)Royalty`` token for version 1.

        Returns:
            CIP102RoyaltyTokenName: The constructed royalty token name.

        Example:
            CIP102RoyaltyTokenName.from_postfix()        # (500)Royalty
            CIP102RoyaltyTokenName.from_postfix(1)       # (500)Royalty1
            CIP102RoyaltyTokenName.from_postfix(2)       # (500)Royalty2
        """
        from crc8 import crc8

        label = ROYALTY_TOKEN_LABEL
        # CIP-67 stores the label in the upper 12 bits of the first 3 bytes.
        # data[1:5] (nibbles 1-4) are the CRC8 input, matching the validator.
        label_bytes = (label << 4).to_bytes(3, "big")  # 3 bytes with label in upper 12 bits
        label_nibbles_for_crc = label_bytes.hex()[1:5]  # e.g. "01f4" for label 500
        checksum = crc8(bytes.fromhex(label_nibbles_for_crc)).hexdigest()
        prefix = "0" + label_nibbles_for_crc + checksum + "0"  # 8 hex chars = 4 bytes

        payload = ROYALTY_TOKEN_PAYLOAD
        if postfix is not None:
            payload = payload + str(postfix).encode()

        token_hex = prefix + payload.hex()
        return cls(token_hex)

    @property
    def postfix(self) -> Optional[int]:
        """Return the integer postfix of this royalty token, or ``None`` if absent."""
        suffix = self.payload[4 + len(ROYALTY_TOKEN_PAYLOAD) :]
        if not suffix:
            return None
        try:
            return int(suffix.decode())
        except (ValueError, UnicodeDecodeError):
            return None


@dataclass
class RoyaltyRecipientSomeMinFee(PlutusData):
    """Plutus representation of ``optional_big_int`` when a value is present (``#6.121([big_int])``)."""

    CONSTR_ID = 0
    value: int


@dataclass
class RoyaltyRecipientNoMinFee(PlutusData):
    """Plutus representation of ``optional_big_int`` when no value is present (``#6.122([])``).

    Maps to constructor 1 in Plutus alternate constructor encoding.
    """

    CONSTR_ID = 1


def _make_optional_big_int(value: Optional[int]) -> PlutusData:
    """Build the ``optional_big_int`` Plutus representation.

    Args:
        value: An integer value, or ``None`` for the empty case.

    Returns:
        ``RoyaltyRecipientSomeMinFee(value)`` if value is set,
        ``RoyaltyRecipientNoMinFee()`` if ``None``.
    """
    if value is not None:
        return RoyaltyRecipientSomeMinFee(value)
    return RoyaltyRecipientNoMinFee()


@dataclass
class RoyaltyRecipient(PlutusData):
    """A single royalty recipient as specified in the CIP-102 datum.

    Encodes as ``#6.121([address, fee, min_fee, max_fee])`` in CBOR/Plutus.

    The ``address`` field stores the raw Plutus address bytes as produced by
    :meth:`pycardano.address.Address.to_primitive`, matching the Plutus ledger
    address definition.

    Args:
        address: Plutus address bytes (payment credential + optional staking credential).
        fee: Variable fee as integer denominator. The royalty percentage is
            ``10 / fee`` (e.g., fee=625 → 1.6%).
        min_fee: Optional minimum royalty fee in lovelace.
        max_fee: Optional maximum royalty fee in lovelace.

    For fee calculations see :mod:`pycardano.cip.cip102` module-level helpers.
    """

    CONSTR_ID = 0

    address: bytes
    fee: int
    min_fee: Union[RoyaltyRecipientSomeMinFee, RoyaltyRecipientNoMinFee]
    max_fee: Union[RoyaltyRecipientSomeMinFee, RoyaltyRecipientNoMinFee]

    @classmethod
    def new(
        cls,
        address: bytes,
        fee: int,
        min_fee: Optional[int] = None,
        max_fee: Optional[int] = None,
    ) -> "RoyaltyRecipient":
        """Construct a royalty recipient with optional min/max fee.

        Args:
            address: Plutus address bytes.
            fee: On-chain fee denominator (``floor(10 / pct)``).
            min_fee: Minimum royalty in lovelace, or ``None``.
            max_fee: Maximum royalty in lovelace, or ``None``.

        Returns:
            RoyaltyRecipient: The constructed recipient.
        """
        return cls(
            address=address,
            fee=fee,
            min_fee=_make_optional_big_int(min_fee),
            max_fee=_make_optional_big_int(max_fee),
        )


@dataclass
class RoyaltyInfo(PlutusData):
    """The CIP-102 royalty datum.

    Encodes as ``#6.121([royalty_recipients, version, extra])`` in CBOR/Plutus,
    suitable for use as an inline datum on the royalty token UTxO.

    For more information on CIP-102:
    https://github.com/cardano-foundation/CIPs/tree/master/CIP-0102

    Args:
        recipients: List of :class:`RoyaltyRecipient` objects.
        version: Datum version. Use ``1`` for a single ``(500)Royalty`` token;
            use ``2`` when postfixed royalty tokens are involved.
        extra: Required extra field. Pass :class:`pycardano.plutus.Unit` for empty.

    Example:
        from pycardano.plutus import Unit
        recipient = RoyaltyRecipient.new(address=bytes(29), fee=625)
        datum = RoyaltyInfo(recipients=[recipient], version=1, extra=Unit())
        cbor_hex = datum.to_cbor_hex()
    """

    CONSTR_ID = 0

    recipients: List[RoyaltyRecipient]
    version: int
    extra: Any

    def __post_init__(self):
        # Deliberately does not call super().__post_init__() to allow Any-typed
        # extra field (same pattern as CIP68Datum).
        pass

    def to_shallow_primitive(self) -> CBORTag:
        """Serialize to CBOR, wrapping the ``extra`` field appropriately."""
        primitives: Primitive = super().to_shallow_primitive()
        if isinstance(primitives, CBORTag):
            value = primitives.value
            if value:
                extra = value[2]
                if isinstance(extra, Unit):
                    extra = CBORTag(121, IndefiniteList([]))
                elif isinstance(extra, CBORTag):
                    extra = CBORTag(extra.tag, IndefiniteList(extra.value))
                recipients = value[0]
                value = [recipients, value[1], extra]
        return CBORTag(121, value)


def fee_to_chain(pct: float) -> int:
    """Convert a royalty percentage to the on-chain integer denominator.

    The on-chain fee is stored as ``floor(10 / pct)`` (integer division with
    precision 10), so that ``pct = 10 / fee``.

    Args:
        pct: Royalty percentage as a decimal (e.g., ``0.016`` for 1.6%).

    Returns:
        int: The on-chain fee denominator.

    Example:
        >>> fee_to_chain(0.016)
        625
    """
    import math

    return math.floor(10 / pct)


def fee_from_chain(chain_fee: int) -> float:
    """Convert an on-chain fee denominator back to a royalty percentage.

    Args:
        chain_fee: The on-chain integer denominator stored in the royalty datum.

    Returns:
        float: The royalty percentage (e.g., ``0.016`` for 1.6%).

    Example:
        >>> fee_from_chain(625)
        0.016
    """
    return 10 / chain_fee


def calculate_royalty(
    chain_fee: int,
    sale_price: int,
    min_fee: Optional[int] = None,
    max_fee: Optional[int] = None,
) -> int:
    """Calculate the royalty amount for a given sale price.

    Applies the CIP-102 formula::

        max(min_fee, min(max_fee, (10 * sale_price) // chain_fee))

    Args:
        chain_fee: On-chain fee denominator from the royalty datum.
        sale_price: Sale price in the same monetary unit as the royalty.
        min_fee: Optional minimum fee. If ``None``, no lower bound is applied.
        max_fee: Optional maximum fee. If ``None``, no upper bound is applied.

    Returns:
        int: Calculated royalty amount.

    Example:
        >>> calculate_royalty(625, 100_000_000)  # 1.6% of 100 ADA
        1600000
    """
    amount = (10 * sale_price) // chain_fee
    if max_fee is not None:
        amount = min(amount, max_fee)
    if min_fee is not None:
        amount = max(amount, min_fee)
    return amount
