import pytest

from pycardano.cip.cip102 import (
    CIP102RoyaltyTokenName,
    InvalidCIP102Token,
    RoyaltyInfo,
    RoyaltyRecipient,
    RoyaltyRecipientNoMinFee,
    RoyaltyRecipientSomeMinFee,
    calculate_royalty,
    fee_from_chain,
    fee_to_chain,
)
from pycardano.cip.cip67 import InvalidCIP67Token
from pycardano.plutus import PlutusData, Unit


def assert_roundtrip(obj: PlutusData) -> None:
    serialized = obj.to_cbor_hex()
    deserialized = obj.__class__.from_cbor(serialized)
    reserialized = deserialized.to_cbor_hex()
    assert serialized == reserialized


# ── Token name ──────────────────────────────────────────────────────────────

class TestCIP102RoyaltyTokenName:
    def test_from_postfix_none(self):
        token = CIP102RoyaltyTokenName.from_postfix()
        assert token.label == 500
        assert token.postfix is None
        # Spec hex: 001f4d70526f79616c7479
        assert token.payload.hex() == "001f4d70526f79616c7479"

    @pytest.mark.parametrize("postfix", [1, 2, 10])
    def test_from_postfix_int(self, postfix):
        token = CIP102RoyaltyTokenName.from_postfix(postfix)
        assert token.label == 500
        assert token.postfix == postfix
        # payload ends with "Royalty{postfix}"
        assert token.payload[4:] == f"Royalty{postfix}".encode()

    def test_roundtrip_from_hex(self):
        token = CIP102RoyaltyTokenName.from_postfix(3)
        reconstructed = CIP102RoyaltyTokenName(token.payload)
        assert reconstructed.payload == token.payload
        assert reconstructed.postfix == 3

    def test_invalid_label(self):
        # label 222 (user NFT) — wrong label, fails checksum first
        with pytest.raises((InvalidCIP102Token, InvalidCIP67Token)):
            CIP102RoyaltyTokenName("000de1404d794e4654")

    def test_invalid_payload(self):
        # Build a valid CIP-67 token with label 500 but wrong payload
        from crc8 import crc8
        label_bytes = (500 << 4).to_bytes(3, "big")
        label_nibbles_for_crc = label_bytes.hex()[1:5]  # "01f4"
        checksum = crc8(bytes.fromhex(label_nibbles_for_crc)).hexdigest()
        prefix = "0" + label_nibbles_for_crc + checksum + "0"
        wrong_payload = b"NotRoyalty".hex()
        with pytest.raises(InvalidCIP102Token):
            CIP102RoyaltyTokenName(prefix + wrong_payload)

    def test_spec_hex_roundtrip(self):
        """The base royalty token hex from the CIP spec must be accepted."""
        spec_hex = "001f4d70526f79616c7479"
        token = CIP102RoyaltyTokenName(spec_hex)
        assert token.label == 500
        assert token.postfix is None


# ── Fee helpers ──────────────────────────────────────────────────────────────

class TestFeeHelpers:
    @pytest.mark.parametrize("pct,expected_chain_fee", [
        (0.016, 625),   # 1.6%
        (0.02, 500),    # 2.0%
        (0.025, 400),   # 2.5%
        (0.05, 200),    # 5%
        (0.10, 100),    # 10%
    ])
    def test_fee_to_chain(self, pct, expected_chain_fee):
        assert fee_to_chain(pct) == expected_chain_fee

    @pytest.mark.parametrize("chain_fee,expected_pct", [
        (625, 0.016),
        (500, 0.02),
        (200, 0.05),
    ])
    def test_fee_from_chain(self, chain_fee, expected_pct):
        assert abs(fee_from_chain(chain_fee) - expected_pct) < 1e-9

    def test_fee_roundtrip(self):
        for pct in [0.01, 0.016, 0.02, 0.05, 0.1]:
            chain = fee_to_chain(pct)
            back = fee_from_chain(chain)
            # Floating-point round-trip may not be exact, but close enough
            assert abs(back - pct) < 0.001


class TestCalculateRoyalty:
    def test_basic(self):
        # 1.6% of 100 ADA (100_000_000 lovelace)
        assert calculate_royalty(625, 100_000_000) == 1_600_000

    def test_max_fee_clamps(self):
        # Without max: 2% of 1000 ADA = 20 ADA; max set to 5 ADA
        result = calculate_royalty(500, 1_000_000_000, max_fee=5_000_000)
        assert result == 5_000_000

    def test_min_fee_floor(self):
        # 2% of 1 ADA = 0.02 ADA (20000 lovelace); min set to 1 ADA
        result = calculate_royalty(500, 1_000_000, min_fee=1_000_000)
        assert result == 1_000_000

    def test_no_clamps(self):
        result = calculate_royalty(500, 100_000_000, min_fee=None, max_fee=None)
        assert result == 2_000_000

    def test_both_clamps(self):
        # min=1, max=3 ADA; 2% of 100 ADA = 2 ADA → within bounds
        result = calculate_royalty(500, 100_000_000, min_fee=1_000_000, max_fee=3_000_000)
        assert result == 2_000_000


# ── RoyaltyRecipient ─────────────────────────────────────────────────────────

# Dummy Plutus address bytes — arbitrary 58-byte enterprise address encoding
_DUMMY_ADDR = bytes(29)


class TestRoyaltyRecipient:
    def test_new_no_fees(self):
        r = RoyaltyRecipient.new(address=_DUMMY_ADDR, fee=625)
        assert r.fee == 625
        assert isinstance(r.min_fee, RoyaltyRecipientNoMinFee)
        assert isinstance(r.max_fee, RoyaltyRecipientNoMinFee)

    def test_new_with_fees(self):
        r = RoyaltyRecipient.new(address=_DUMMY_ADDR, fee=500, min_fee=1_000_000, max_fee=5_000_000)
        assert isinstance(r.min_fee, RoyaltyRecipientSomeMinFee)
        assert r.min_fee.value == 1_000_000
        assert isinstance(r.max_fee, RoyaltyRecipientSomeMinFee)
        assert r.max_fee.value == 5_000_000

    def test_roundtrip_no_fees(self):
        r = RoyaltyRecipient.new(address=_DUMMY_ADDR, fee=625)
        assert_roundtrip(r)

    def test_roundtrip_with_fees(self):
        r = RoyaltyRecipient.new(address=_DUMMY_ADDR, fee=500, min_fee=1_000_000, max_fee=10_000_000)
        assert_roundtrip(r)


# ── RoyaltyInfo ──────────────────────────────────────────────────────────────

class TestRoyaltyInfo:
    def test_single_recipient_v1(self):
        r = RoyaltyRecipient.new(address=_DUMMY_ADDR, fee=625)
        info = RoyaltyInfo(recipients=[r], version=1, extra=Unit())
        assert info.version == 1
        assert len(info.recipients) == 1
        assert_roundtrip(info)

    def test_multiple_recipients_v2(self):
        r1 = RoyaltyRecipient.new(address=_DUMMY_ADDR, fee=625)
        r2 = RoyaltyRecipient.new(address=_DUMMY_ADDR, fee=500, min_fee=500_000)
        info = RoyaltyInfo(recipients=[r1, r2], version=2, extra=Unit())
        assert info.version == 2
        assert len(info.recipients) == 2
        assert_roundtrip(info)

    def test_cbor_hex_is_string(self):
        r = RoyaltyRecipient.new(address=_DUMMY_ADDR, fee=625)
        info = RoyaltyInfo(recipients=[r], version=1, extra=Unit())
        cbor_hex = info.to_cbor_hex()
        assert isinstance(cbor_hex, str)
        assert len(cbor_hex) > 0
