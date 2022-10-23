import datetime
import pathlib
from test.pycardano.util import (
    FixedBlockFrostChainContext,
    blockfrost_context,
    chain_context,
)
from unittest.mock import patch

import pytest

from pycardano.address import Address
from pycardano.nativescript import ScriptAll, ScriptPubkey
from pycardano.wallet import (
    Ada,
    Lovelace,
    MetadataFormattingException,
    Token,
    TokenPolicy,
    Wallet,
)


def test_load_wallet():

    w = Wallet(
        name="payment",
        keys_dir=str(pathlib.Path(__file__).parent / "../resources/keys"),
        context="null",
    )

    assert w.address == Address.from_primitive(
        "addr1q8xrqjtlfluk9axpmjj5enh0uw0cduwhz7txsqyl36m3uk2g9z3d4kaf0j5l6rxunxt43x28pssehhqds2x05mwld45s399sr7"
    )
    assert w.payment_address == Address.from_primitive(
        "addr1v8xrqjtlfluk9axpmjj5enh0uw0cduwhz7txsqyl36m3ukgqdsn8w"
    )
    assert w.stake_address == Address.from_primitive(
        "stake1u9yz3gk6mw5he20apnwfn96cn9rscgvmmsxc9r86dh0k66ghyrkpw"
    )


WALLET = Wallet(
    name="payment",
    keys_dir=str(pathlib.Path(__file__).parent / "../resources/keys"),
    context="null",
)


def test_amount():
    """Check that the Ada / Lovelace math works as expected."""

    assert Ada(1).as_lovelace() == Lovelace(1000000)
    assert Lovelace(1).as_ada() == Ada(0.000001)
    assert Ada(1).as_ada() == Ada(1)
    assert Lovelace(1).as_lovelace() == Lovelace(1)
    assert Ada(1) == Ada(1)
    assert Lovelace(1) == Lovelace(1)
    assert Lovelace(1) == 1
    assert Ada(1) != Ada(2)
    assert Lovelace(1) != Lovelace(2)
    assert Ada(1) < Ada(2)
    assert Lovelace(1) < Lovelace(2)
    assert Ada(2) > Ada(1)
    assert Lovelace(2) > Lovelace(1)
    assert Ada(1) <= Ada(1)
    assert Lovelace(1) <= Lovelace(1)
    assert Ada(1) >= Ada(1)
    assert Lovelace(1) >= Lovelace(1)
    assert Ada(1) <= Ada(2)
    assert Lovelace(1) <= Lovelace(2)
    assert Ada(2) >= Ada(1)
    assert Lovelace(2) >= Lovelace(1)
    assert str(Ada(1)) == "1"
    assert str(Lovelace(1)) == "1"
    assert bool(Ada(1)) == True
    assert bool(Lovelace(1)) == True
    assert bool(Ada(0)) == False
    assert bool(Lovelace(0)) == False
    assert sum([Ada(3), Ada(5), Ada(7)]) == Ada(15)
    assert sum([Lovelace(500000), Ada(5)]) == Lovelace(5500000)
    assert abs(Ada(-1)) == Ada(1)
    assert abs(Lovelace(-1)) == Lovelace(1)
    assert Lovelace(1) != Lovelace(2)
    assert Lovelace(1) != 2
    assert Lovelace(2) > 1
    assert Lovelace(1) < 2
    assert Lovelace(1) >= 1
    assert Lovelace(2) <= 2
    assert -Lovelace(5) == Lovelace(-5)
    assert -Ada(5) == Ada(-5)
    assert round(Ada(5.66)) == Ada(6)

    with pytest.raises(TypeError):
        Lovelace(500) == "500"

    with pytest.raises(TypeError):
        Lovelace(1) != "1"

    with pytest.raises(TypeError):
        Lovelace(1) < "2"

    with pytest.raises(TypeError):
        Lovelace(1) > "2"

    with pytest.raises(TypeError):
        Lovelace(1) <= "2"

    with pytest.raises(TypeError):
        Lovelace(1) >= "2"

    assert int(Lovelace(100)) == 100
    assert int(Ada(100)) == 100
    assert hash(Lovelace(100)) == hash((100, "lovelace"))
    assert hash(Ada(100)) == hash((100, "ada"))


def test_lovelace_integer():
    """Check that the Lovelace class only accepts integer values."""

    with pytest.raises(TypeError):
        Lovelace(5.5)


def test_amount_math():
    """Check that the mathematical properties of Ada and Lovelace are consistent"""

    assert Ada(1) + Ada(1) == Ada(2)
    assert Ada(1) - Ada(1) == Ada(0)
    assert Ada(1) + 1 == Ada(2)
    assert Ada(2) - 1 == Ada(1)
    assert 1 + Ada(1) == Ada(2)
    assert 2 - Ada(1) == Ada(1)
    assert Lovelace(1) + Lovelace(1) == Lovelace(2)
    assert Lovelace(1) - Lovelace(1) == Lovelace(0)
    assert Lovelace(1) + 1 == Lovelace(2)
    assert Lovelace(2) - 1 == Lovelace(1)
    assert Lovelace(1) + Ada(1) == Lovelace(1000001)
    assert Lovelace(1000001) - Ada(1) == Lovelace(1)
    assert Ada(1) + Lovelace(1) == Ada(1.000001)
    assert Ada(1) - Lovelace(1) == Ada(0.999999)
    assert Ada(5) * Ada(2) == Ada(10)
    assert Ada(1) * 2 == Ada(2)
    assert 2 * Ada(1) == Ada(2)
    assert Lovelace(1) * 2 == Lovelace(2)
    assert Ada(6) / Ada(3) == Ada(2)
    assert Ada(1) / 2 == Ada(0.5)
    assert 1 / Ada(2) == Ada(0.5)
    assert Ada(1) / 2 == Lovelace(500000)
    assert Ada(5) // Ada(2) == Ada(2)
    assert Ada(5) // 2 == Ada(2)
    assert 5 // Ada(2) == Ada(2)

    assert sum([Ada(1), Ada(2)]) == Ada(3)
    assert sum([Ada(1), 2]) == Ada(3)
    assert sum([Ada(2), Lovelace(500000)]) == Ada(2.5)

    with pytest.raises(TypeError):
        Ada(1) + "1"

    with pytest.raises(TypeError):
        "1" + Ada(1)

    with pytest.raises(TypeError):
        Ada(2) - "1"

    with pytest.raises(TypeError):
        "1" - Ada(2)

    with pytest.raises(TypeError):
        Ada(2) * "2"

    with pytest.raises(TypeError):
        Ada(2) / "4"

    with pytest.raises(TypeError):
        Ada(2) // "4"

    with pytest.raises(TypeError):
        "2" * Ada(2)

    with pytest.raises(TypeError):
        "4" / Ada(2)

    with pytest.raises(TypeError):
        "4" // Ada(2)

    with pytest.raises(TypeError):
        sum([Ada(1), "2"])


def test_wallet_sign_data():

    assert (
        str(WALLET.address)
        == "addr1q8xrqjtlfluk9axpmjj5enh0uw0cduwhz7txsqyl36m3uk2g9z3d4kaf0j5l6rxunxt43x28pssehhqds2x05mwld45s399sr7"
    )

    assert WALLET.sign_data("pycardano rocks", mode="payment") == (
        "84584da301276761646472657373581d61cc30497f4ff962f4c1dca54cceefe39f86f1"
        "d7179668009f8eb71e590458205797dc2cc919dfec0bb849551ebdf30d96e5cbe0f33f"
        "734a87fe826db30f7ef9a166686173686564f44f707963617264616e6f20726f636b73"
        "58402beecd6dba2f7f73d0d72abd5cc43829173a069afa2a29eff72d65049b092bc80c"
        "571569e8a7c26354cd1d38b5fcdc3d7a3b6955d2211106824ba02c33ba220f"
    )


def test_policy(chain_context):

    policy_dir = pathlib.Path(__file__).parent / "../resources/policy"

    script_filepath = policy_dir / f"testToken.script"
    if script_filepath.exists():
        script_filepath.unlink()

    # remove policy file if it exists
    if script_filepath.exists():
        script_filepath.unlink()

    policy = TokenPolicy(name="testToken", policy_dir=str(policy_dir))

    policy.generate_minting_policy(signers=WALLET)

    script = ScriptAll([ScriptPubkey(WALLET.verification_key.hash())])

    assert (
        policy.policy_id == "6b0cb18696ccd4de1dcd9664c31ed6e98f7a4a1ff647855fef1e0831"
    )
    assert policy.policy == script
    assert policy.script == script
    assert policy.required_signatures == [WALLET.verification_key.hash()]

    # load from dictionary
    policy_dict = {
        "type": "all",
        "scripts": [
            {
                "type": "sig",
                "keyHash": "cc30497f4ff962f4c1dca54cceefe39f86f1d7179668009f8eb71e59",
            }
        ],
    }

    # also test new policy directory
    second_policy_dir = pathlib.Path(__file__).parent / "../resources/policy_two"
    second_script_filepath = second_policy_dir / f"testToken.script"
    if second_script_filepath.exists():
        second_script_filepath.unlink()

    from_dict = TokenPolicy(
        name="testTokenDict", policy=policy_dict, policy_dir=str(second_policy_dir)
    )

    assert policy.policy == from_dict.policy

    # test a policy for a token for which we don't have the private key
    third_policy_dir = pathlib.Path(__file__).parent / "../resources/policy_three"
    their_policy = TokenPolicy(
        name="notOurs",
        policy="6b0cb18696ccd4de1dcd9664c31ed6e98f7a4a1ff647855fef1e0831",
        policy_dir=third_policy_dir,
    )
    assert their_policy.policy_id == policy.policy_id
    assert their_policy.id == policy.id

    # try loading an already existing policy
    reloaded_policy = TokenPolicy(name="testToken", policy_dir=str(policy_dir))
    assert reloaded_policy.policy == policy.policy

    # try to generate a policy with a name that already exists
    with pytest.raises(FileExistsError):
        reloaded_policy.generate_minting_policy(signers=WALLET)

    with pytest.raises(AttributeError):
        temp_policy = TokenPolicy(
            name="noContext",
            policy_dir=str(policy_dir),
        )
        temp_policy.generate_minting_policy(
            signers=WALLET, expiration=datetime.datetime.now()
        )

    # test policy with expiration
    exp_filepath = policy_dir / f"expiring.script"
    if exp_filepath.exists():
        exp_filepath.unlink()

    exp_policy = TokenPolicy(name="expiring", policy_dir=str(policy_dir))
    exp_policy.generate_minting_policy(signers=WALLET, expiration=2600)
    assert exp_policy.expiration_slot == 2600
    with patch(
        "pycardano.wallet.get_now", return_value=datetime.datetime(2022, 1, 1, 0, 0, 0)
    ):
        assert exp_policy.get_expiration_timestamp(
            context=chain_context
        ) == datetime.datetime(2022, 1, 1, 0, 10, 0)
        assert exp_policy.is_expired(context=chain_context) == False

    # reinitialize the policy with a datetime
    if exp_filepath.exists():
        exp_filepath.unlink()

    # with timezone
    exp_policy = TokenPolicy(name="expiring", policy_dir=str(policy_dir))
    with patch(
        "pycardano.wallet.get_now",
        return_value=datetime.datetime(
            2022, 1, 1, 0, 0, 0, tzinfo=datetime.timezone.utc
        ),
    ):
        exp_policy.generate_minting_policy(
            signers=WALLET,
            expiration=datetime.datetime(
                2022, 1, 1, 0, 10, 0, tzinfo=datetime.timezone.utc
            ),
            context=chain_context,
        )
        assert exp_policy.get_expiration_timestamp(
            context=chain_context
        ) == datetime.datetime(2022, 1, 1, 0, 10, 0, tzinfo=datetime.timezone.utc)

    # without timezone (UTC)
    if exp_filepath.exists():
        exp_filepath.unlink()

    exp_policy = TokenPolicy(name="expiring", policy_dir=str(policy_dir))
    with patch(
        "pycardano.wallet.get_now",
        return_value=datetime.datetime(2022, 1, 1, 0, 0, 0),
    ):
        exp_policy.generate_minting_policy(
            signers=WALLET,
            expiration=datetime.datetime(2022, 1, 1, 0, 10, 0),
            context=chain_context,
        )
        assert exp_policy.get_expiration_timestamp(
            context=chain_context
        ) == datetime.datetime(2022, 1, 1, 0, 10, 0)

    # test address as signer
    if exp_filepath.exists():
        exp_filepath.unlink()

    address_signer = TokenPolicy(name="expiring", policy_dir=str(policy_dir))
    address_signer.generate_minting_policy(signers=WALLET.address)

    # with bad expiration date
    if exp_filepath.exists():
        exp_filepath.unlink()

    exp_policy = TokenPolicy(name="expiring", policy_dir=str(policy_dir))
    with pytest.raises(TypeError):
        exp_policy.generate_minting_policy(signers=WALLET, expiration=2000.5)

    # test bad signer
    if exp_filepath.exists():
        exp_filepath.unlink()

    bad_signer = TokenPolicy(name="expiring", policy_dir=str(policy_dir))
    with pytest.raises(TypeError):
        bad_signer.generate_minting_policy(signers="addr1q")

    # cleanup
    if script_filepath.exists():
        script_filepath.unlink()

    if second_script_filepath.exists():
        second_script_filepath.unlink()

    if exp_filepath.exists():
        exp_filepath.unlink()

    if policy_dir.exists():
        policy_dir.rmdir()

    if second_policy_dir.exists():
        second_policy_dir.rmdir()

    if third_policy_dir.exists():
        second_policy_dir.rmdir()


def test_token():

    script = ScriptAll([ScriptPubkey(WALLET.verification_key.hash())])

    policy = TokenPolicy(name="testToken", policy=script)

    token = Token(policy=policy, name="testToken", amount=1)
    token_hex = Token(policy=policy, hex_name="74657374546f6b656e", amount=1)

    assert token == token_hex
    assert token.hex_name == "74657374546f6b656e"
    assert token.bytes_name == b"testToken"
    assert token.policy_id == "6b0cb18696ccd4de1dcd9664c31ed6e98f7a4a1ff647855fef1e0831"
    assert str(token) == "testToken"

    # test token errors
    with pytest.raises(TypeError):
        Token(policy=policy, name="badToken", amount="1")


def test_metadata():

    script = ScriptAll([ScriptPubkey(WALLET.verification_key.hash())])

    policy = TokenPolicy(name="testToken", policy=script)

    metadata = {
        "key_1": "value_1",
        "key_2": ["value_2_1", "value_2_2"],
        "key_3": {"key_3_1": "value_3_1"},
    }

    _ = Token(policy=policy, name="testToken", amount=1, metadata=metadata)

    # test bad metadata

    long_key = {"a" * 100: "so_long"}
    long_value = {"so_long": "a" * 100}
    long_string = "a" * 100
    unserializable = {"unserializable": lambda x: x}

    with pytest.raises(MetadataFormattingException):
        _ = Token(policy=policy, name="testToken", amount=1, metadata=long_key)

    with pytest.raises(MetadataFormattingException):
        _ = Token(policy=policy, name="testToken", amount=1, metadata=long_value)

    with pytest.raises(MetadataFormattingException):
        _ = Token(policy=policy, name="testToken", amount=1, metadata=long_string)

    with pytest.raises(MetadataFormattingException):
        _ = Token(policy=policy, name="testToken", amount=1, metadata=unserializable)
