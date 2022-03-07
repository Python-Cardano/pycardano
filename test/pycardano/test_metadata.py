from test.pycardano.util import check_two_way_cbor

import pytest
from cbor2 import CBORTag

from pycardano.exception import InvalidArgumentException
from pycardano.key import VerificationKey
from pycardano.metadata import (
    AlonzoMetadata,
    AuxiliaryData,
    Metadata,
    ShellayMarryMetadata,
)
from pycardano.nativescript import (
    InvalidBefore,
    InvalidHereAfter,
    ScriptAll,
    ScriptPubkey,
)

M_PRIMITIVE = {123: {"test": b"123", 2: 3, 3: [1, 2, {(1, 2, 3): "token"}]}}


def generate_script():
    vk1 = VerificationKey.from_cbor(
        "58206443a101bdb948366fc87369336224595d36d8b0eee5602cba8b81a024e58473"
    )
    vk2 = VerificationKey.from_cbor(
        "58206443a101bdb948366fc87369336224595d36d8b0eee5602cba8b81a024e58475"
    )
    spk1 = ScriptPubkey(key_hash=vk1.hash())
    spk2 = ScriptPubkey(key_hash=vk2.hash())
    before = InvalidHereAfter(123456789)
    after = InvalidBefore(123456780)
    script = ScriptAll([before, after, spk1, spk2])
    return script


def test_metadata():
    m = Metadata(M_PRIMITIVE)
    check_two_way_cbor(m)
    assert M_PRIMITIVE == m.to_primitive()


def test_shelley_marry_metadata():
    script = generate_script()
    m = Metadata(M_PRIMITIVE)

    shelley_marry_m = ShellayMarryMetadata(m, [script])

    check_two_way_cbor(shelley_marry_m)

    assert [m.to_primitive(), [script.to_primitive()]] == shelley_marry_m.to_primitive()


def test_alonzo_metadata():
    script = generate_script()
    m = Metadata(M_PRIMITIVE)
    plutus_scripts = [b"fake_script"]

    alonzo_m = AlonzoMetadata(m, [script], plutus_scripts)

    check_two_way_cbor(alonzo_m)

    assert (
        CBORTag(
            AlonzoMetadata.TAG,
            {0: m.to_primitive(), 1: [script.to_primitive()], 2: plutus_scripts},
        )
        == alonzo_m.to_primitive()
    )


def test_auxiliary_data():
    script = generate_script()
    plutus_scripts = [b"fake_script"]

    m = Metadata(M_PRIMITIVE)
    shelley_marry_m = ShellayMarryMetadata(m, [script])
    alonzo_m = AlonzoMetadata(m, [script], plutus_scripts)

    check_two_way_cbor(AuxiliaryData(m))
    check_two_way_cbor(AuxiliaryData(shelley_marry_m))
    check_two_way_cbor(AuxiliaryData(alonzo_m))


def test_axuiliary_data_hash():
    data = {
        721: {
            "{policy_id}": {
                "{policy_name}": {
                    "description": "<optional>",
                    "image": "<required>",
                    "location": {
                        "arweave": "<optional>",
                        "https": "<optional>",
                        "ipfs": "<required>",
                    },
                    "name": "<required>",
                    "sha256": "<required>",
                    "type": "<required>",
                }
            }
        }
    }

    aux_data = AuxiliaryData(AlonzoMetadata(metadata=Metadata(data)))
    assert "592a2df0e091566969b3044626faa8023dabe6f39c78f33bed9e105e55159221" == str(
        aux_data.hash()
    )


def test_metadata_invalid_type():
    data = {"abc": "abc"}
    with pytest.raises(InvalidArgumentException):
        Metadata(data)

    data = {123: {"1": set()}}
    with pytest.raises(InvalidArgumentException):
        Metadata(data)


def test_metadata_valid_size():
    data = {
        123: {"1": bytes(Metadata.MAX_ITEM_SIZE), "2": "1" * Metadata.MAX_ITEM_SIZE}
    }
    Metadata(data)


def test_metadata_invalid_size():
    data = {123: {"1": bytes(Metadata.MAX_ITEM_SIZE + 1)}}

    with pytest.raises(InvalidArgumentException):
        Metadata(data)

    data = {123: {"1": "1" * (Metadata.MAX_ITEM_SIZE + 1)}}

    with pytest.raises(InvalidArgumentException):
        Metadata(data)
