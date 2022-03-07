from test.pycardano.util import check_two_way_cbor

import pytest

from pycardano.exception import InvalidArgumentException
from pycardano.key import VerificationKey
from pycardano.nativescript import (
    InvalidBefore,
    InvalidHereAfter,
    ScriptAll,
    ScriptAny,
    ScriptNofK,
    ScriptPubkey,
)
from pycardano.transaction import Transaction

"""The following ground truths of script hashes (policy ID) are generated from cardano-cli."""


def test_pubkey():
    vk = VerificationKey.from_cbor(
        "58206443a101bdb948366fc87369336224595d36d8b0eee5602cba8b81a024e58473"
    )
    script = ScriptPubkey(key_hash=vk.hash())
    assert "88d1bd864d184909138e772d5b71b312113a985590fb551e8b35f50c" == str(
        script.hash()
    )
    check_two_way_cbor(script)


def test_script_all():
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

    assert "ec8b7d1dd0b124e8333d3fa8d818f6eac068231a287554e9ceae490e" == str(
        script.hash()
    )
    check_two_way_cbor(script)

    vk1 = VerificationKey.from_cbor(
        "5820f6b367e63d0478e2aa7f99c6b1998dcd746484c37e754a993c3720d8ecf39b03"
    )
    spk1 = ScriptPubkey(key_hash=vk1.hash())
    before = InvalidHereAfter(80059041)
    script = ScriptAll([spk1, before])
    assert "b9ef27af6a13e3f779bf77c1f624966068b2464ea92b59e8d26fa19b" == str(
        script.hash()
    )


def test_script_any():
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
    script = ScriptAny([before, after, spk1, spk2])

    assert "2cca2c35ff880760b34e42c87172125d2bad18d8bcf42e209298648b" == str(
        script.hash()
    )
    check_two_way_cbor(script)


def test_script_nofk():
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
    script = ScriptNofK(2, [before, after, spk1, spk2])

    assert "088a24a57345f12db09c6eddac2e88edf281bf766e66a98ff1045c0d" == str(
        script.hash()
    )
    check_two_way_cbor(script)


def test_full_tx():
    cbor = (
        "84a60081825820b35a4ba9ef3ce21adcd6879d08553642224304704d206c74d3ffb3e6eed3ca28000d80018182581d60cc304"
        "97f4ff962f4c1dca54cceefe39f86f1d7179668009f8eb71e598200a1581c50ab3393739cfa524cbe554c88d13bd41a356794"
        "0af6bbf780a5854ba24f5365636f6e6454657374746f6b656e1a009896804954657374746f6b656e1a00989680021a000493e"
        "00e8009a1581c50ab3393739cfa524cbe554c88d13bd41a3567940af6bbf780a5854ba24f5365636f6e6454657374746f6b65"
        "6e1a009896804954657374746f6b656e1a00989680a200828258206443a101bdb948366fc87369336224595d36d8b0eee5602"
        "cba8b81a024e584735840b0e25a64e88c14d81b840979af2fe79246a34aa9c62b5f03bcae2ff4af0ba0c80872f3e7702a9184"
        "6e4b4c73eabb25af91064d9cdebce4bad6246a51460b890b8258205797dc2cc919dfec0bb849551ebdf30d96e5cbe0f33f734"
        "a87fe826db30f7ef95840d4fefcc897e8271f9639a02b4df91f68f4b16335569492a2df531e7974e57ae5778d8cf943981f86"
        "3bdf4542029664d54143d150de277304fd3cb1eb7ed29d04018182018382051a075bcd158200581c9139e5c0a42f0f2389634"
        "c3dd18dc621f5594c5ba825d9a8883c66278200581c835600a2be276a18a4bebf0225d728f090f724f4c0acd591d066fa6ff5f6"
    )

    tx = Transaction.from_cbor(cbor)

    vk1 = VerificationKey.from_cbor(
        "58206443a101bdb948366fc87369336224595d36d8b0eee5602cba8b81a024e58473"
    )
    vk2 = VerificationKey.from_cbor(
        "58206443a101bdb948366fc87369336224595d36d8b0eee5602cba8b81a024e58475"
    )
    spk1 = ScriptPubkey(key_hash=vk1.hash())
    spk2 = ScriptPubkey(key_hash=vk2.hash())
    before = InvalidHereAfter(123456789)
    script = ScriptAll([before, spk1, spk2])

    assert tx.transaction_witness_set.native_scripts[0] == script
