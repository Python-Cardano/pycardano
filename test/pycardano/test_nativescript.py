import pytest

from pycardano.exception import InvalidArgumentException
from pycardano.key import VerificationKey
from pycardano.nativescript import ScriptPubkey, ScriptAll, ScriptAny, ScriptNofK, InvalidBefore, InvalidHereAfter
from test.pycardano.util import check_two_way_cbor

"""The following ground truths of script hashes (policy ID) are generated from cardano-cli."""


def test_pubkey():
    vk = VerificationKey.from_cbor("58206443a101bdb948366fc87369336224595d36d8b0eee5602cba8b81a024e58473")
    script = ScriptPubkey(key_hash=vk.hash())
    assert "88d1bd864d184909138e772d5b71b312113a985590fb551e8b35f50c" == str(script.hash())
    check_two_way_cbor(script)


def test_alter_script_type_number_with_exception():
    with pytest.raises(InvalidArgumentException):
        vk = VerificationKey.from_cbor("58206443a101bdb948366fc87369336224595d36d8b0eee5602cba8b81a024e58473")
        script = ScriptPubkey(key_hash=vk.hash(), TYPE=3)


def test_script_all():
    vk1 = VerificationKey.from_cbor("58206443a101bdb948366fc87369336224595d36d8b0eee5602cba8b81a024e58473")
    vk2 = VerificationKey.from_cbor("58206443a101bdb948366fc87369336224595d36d8b0eee5602cba8b81a024e58475")
    spk1 = ScriptPubkey(key_hash=vk1.hash())
    spk2 = ScriptPubkey(key_hash=vk2.hash())
    before = InvalidHereAfter(123456789)
    after = InvalidBefore(123456780)
    script = ScriptAll([before, after, spk1, spk2])

    assert "ec8b7d1dd0b124e8333d3fa8d818f6eac068231a287554e9ceae490e" == str(script.hash())
    check_two_way_cbor(script)


def test_script_any():
    vk1 = VerificationKey.from_cbor("58206443a101bdb948366fc87369336224595d36d8b0eee5602cba8b81a024e58473")
    vk2 = VerificationKey.from_cbor("58206443a101bdb948366fc87369336224595d36d8b0eee5602cba8b81a024e58475")
    spk1 = ScriptPubkey(key_hash=vk1.hash())
    spk2 = ScriptPubkey(key_hash=vk2.hash())
    before = InvalidHereAfter(123456789)
    after = InvalidBefore(123456780)
    script = ScriptAny([before, after, spk1, spk2])

    assert "2cca2c35ff880760b34e42c87172125d2bad18d8bcf42e209298648b" == str(script.hash())
    check_two_way_cbor(script)


def test_script_nofk():
    vk1 = VerificationKey.from_cbor("58206443a101bdb948366fc87369336224595d36d8b0eee5602cba8b81a024e58473")
    vk2 = VerificationKey.from_cbor("58206443a101bdb948366fc87369336224595d36d8b0eee5602cba8b81a024e58475")
    spk1 = ScriptPubkey(key_hash=vk1.hash())
    spk2 = ScriptPubkey(key_hash=vk2.hash())
    before = InvalidHereAfter(123456789)
    after = InvalidBefore(123456780)
    script = ScriptNofK(2, [before, after, spk1, spk2])

    assert "088a24a57345f12db09c6eddac2e88edf281bf766e66a98ff1045c0d" == str(script.hash())
    check_two_way_cbor(script)
