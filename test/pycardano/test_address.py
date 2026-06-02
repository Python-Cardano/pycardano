import os
import tempfile

import pytest

from pycardano.address import Address, AddressType, PointerAddress
from pycardano.exception import (
    DecodingException,
    DeserializeException,
    InvalidAddressInputException,
)
from pycardano.hash import (
    SCRIPT_HASH_SIZE,
    VERIFICATION_KEY_HASH_SIZE,
    ScriptHash,
    VerificationKeyHash,
)
from pycardano.key import PaymentVerificationKey
from pycardano.network import Network


def test_payment_addr():
    vk = PaymentVerificationKey.from_json("""{
        "type": "GenesisUTxOVerificationKey_ed25519",
        "description": "Genesis Initial UTxO Verification Key",
        "cborHex": "58208be8339e9f3addfa6810d59e2f072f85e64d4c024c087e0d24f8317c6544f62f"
    }""")
    assert (
        Address(vk.hash(), network=Network.TESTNET).encode()
        == "addr_test1vr2p8st5t5cxqglyjky7vk98k7jtfhdpvhl4e97cezuhn0cqcexl7"
    )


def test_to_primitive_pointer_addr():
    assert PointerAddress(1, 2, 3).to_primitive() == b"\x01\x02\x03"


def test_from_primitive_pointer_addr():
    assert PointerAddress.from_primitive(
        b"\x01\x02\x03"
    ) == PointerAddress.from_primitive(b"\x01\x02\x03")


def test_from_primitive_invalid_value_pointer_addr():
    with pytest.raises(DecodingException):
        PointerAddress.decode(data=b"\x01\x02")

    with pytest.raises(DeserializeException):
        PointerAddress.from_primitive(1)

    with pytest.raises(DeserializeException):
        PointerAddress.from_primitive([])

    with pytest.raises(DeserializeException):
        PointerAddress.from_primitive({})


def test_equality_pointer_addr():
    assert PointerAddress(1, 2, 3) == PointerAddress(1, 2, 3)


def test_inequality_different_values_pointer_addr():
    assert PointerAddress(1, 2, 3) != PointerAddress(4, 5, 6)


def test_inequality_not_pointer_addr():
    assert PointerAddress(1, 2, 3) != (1, 2, 3)


def test_inequality_null_pointer_addr():
    assert PointerAddress(1, 2, 3) != None


def test_self_equality_pointer_addr():
    assert PointerAddress(1, 2, 3) == PointerAddress(1, 2, 3)


def test_from_primitive_invalid_value_addr():
    with pytest.raises(DeserializeException):
        Address.from_primitive(1)

    with pytest.raises(DeserializeException):
        Address.from_primitive([])

    with pytest.raises(DeserializeException):
        Address.from_primitive({})


def test_key_script_addr():
    address = Address(
        VerificationKeyHash(b"1" * VERIFICATION_KEY_HASH_SIZE),
        ScriptHash(b"1" * SCRIPT_HASH_SIZE),
    )
    assert address.address_type == AddressType.KEY_SCRIPT


def test_script_key_addr():
    address = Address(
        ScriptHash(b"1" * SCRIPT_HASH_SIZE),
        VerificationKeyHash(b"1" * VERIFICATION_KEY_HASH_SIZE),
    )
    assert address.address_type == AddressType.SCRIPT_KEY


def test_script_point_addr():
    address = Address(ScriptHash(b"1" * SCRIPT_HASH_SIZE), PointerAddress(1, 2, 3))
    assert address.address_type == AddressType.SCRIPT_POINTER


def test_none_script_hash_addr():
    address = Address(None, ScriptHash(b"1" * SCRIPT_HASH_SIZE))
    assert address.address_type == AddressType.NONE_SCRIPT


def test_invalid_combination_unhandled_types_addr():
    class UnknownType:
        pass

    with pytest.raises(InvalidAddressInputException):
        Address(UnknownType(), UnknownType())


def test_equality_same_values_addr():
    a1 = Address(
        VerificationKeyHash(b"1" * VERIFICATION_KEY_HASH_SIZE),
        ScriptHash(b"1" * SCRIPT_HASH_SIZE),
    )
    a2 = Address(
        VerificationKeyHash(b"1" * VERIFICATION_KEY_HASH_SIZE),
        ScriptHash(b"1" * SCRIPT_HASH_SIZE),
    )
    assert a1 == a2


def test_inequality_not_address_addr():
    a1 = Address(
        VerificationKeyHash(b"1" * VERIFICATION_KEY_HASH_SIZE),
        ScriptHash(b"1" * SCRIPT_HASH_SIZE),
    )
    not_address = (1, 2, 3)
    assert a1 != not_address


def test_from_primitive_address_type_key_script_addr():
    header = AddressType.KEY_SCRIPT.value << 4
    payment = b"\x01" * VERIFICATION_KEY_HASH_SIZE
    staking = b"\x02" * SCRIPT_HASH_SIZE
    value = bytes([header]) + payment + staking

    address = Address.from_primitive(value)

    assert isinstance(address.payment_part, VerificationKeyHash)

    assert isinstance(address.staking_part, ScriptHash)


def test_from_primitive_type_verification_key_hash_addr():
    header = AddressType.KEY_POINTER.value << 4
    payment = b"\x01" * VERIFICATION_KEY_HASH_SIZE
    staking = b"\x01\x02\x03"
    value = bytes([header]) + payment + staking

    address = Address.from_primitive(value)

    assert isinstance(address.payment_part, VerificationKeyHash)

    assert isinstance(address.staking_part, PointerAddress)


def test_from_primitive_staking_script_hash_addr():
    header = AddressType.SCRIPT_KEY.value << 4
    payment = b"\x01" * SCRIPT_HASH_SIZE
    staking = b"\x02" * VERIFICATION_KEY_HASH_SIZE
    value = bytes([header]) + payment + staking

    address = Address.from_primitive(value)

    assert isinstance(address.payment_part, ScriptHash)

    assert isinstance(address.staking_part, VerificationKeyHash)


def test_from_primitive_payment_script_hash_addr():
    header = AddressType.SCRIPT_POINTER.value << 4
    payment = b"\x01" * SCRIPT_HASH_SIZE
    staking = b"\x01\x02\x03"
    value = bytes([header]) + payment + staking

    address = Address.from_primitive(value)

    assert isinstance(address.payment_part, ScriptHash)


def test_from_primitive_type_none_addr():
    header = AddressType.NONE_SCRIPT.value << 4
    payment = b"\x01" * 14
    staking = b"\x02" * 14
    value = bytes([header]) + payment + staking

    address = Address.from_primitive(value)

    assert address.payment_part is None

    assert isinstance(address.staking_part, ScriptHash)


def test_from_primitive_invalid_type_addr():
    header = AddressType.BYRON.value << 4
    payment = b"\x01" * 14
    staking = b"\x02" * 14
    value = bytes([header]) + payment + staking

    with pytest.raises(DeserializeException):
        Address.from_primitive(value)


def test_save_load_address():
    address_string = "addr_test1vr2p8st5t5cxqglyjky7vk98k7jtfhdpvhl4e97cezuhn0cqcexl7"
    address = Address.from_primitive(address_string)

    # On Windows, NamedTemporaryFile keeps the file locked while open, so
    # save() cannot open it for writing. Use delete=False and close the handle
    # first, then clean up manually afterward.
    with tempfile.NamedTemporaryFile(delete=False) as f:
        tmp_path = f.name
    try:
        address.save(tmp_path)
        loaded_address = Address.load(tmp_path)
        assert address == loaded_address
    finally:
        os.unlink(tmp_path)
