import pathlib

from pycardano.wallet import Ada, Lovelace, Wallet, TokenPolicy

import pytest


def test_amount():
    """Check that the Ada / Lovelace math works as expected."""

    assert Ada(1).as_lovelace() == Lovelace(1000000)
    assert Lovelace(1).as_ada() == Ada(0.000001)
    assert Ada(1).as_ada() == Ada(1)
    assert Lovelace(1).as_lovelace() == Lovelace(1)
    assert Ada(1) + Ada(1) == Ada(2)
    assert Ada(1) - Ada(1) == Ada(0)
    assert Lovelace(1) + Lovelace(1) == Lovelace(2)
    assert Lovelace(1) - Lovelace(1) == Lovelace(0)
    assert Lovelace(1) + Ada(1) == Lovelace(1000001)
    assert Lovelace(1000001) - Ada(1) == Lovelace(1)
    assert Ada(1) + Lovelace(1) == Ada(1.000001)
    assert Ada(1) - Lovelace(1) == Ada(0.999999)
    assert Ada(1) == Ada(1)
    assert Lovelace(1) == Lovelace(1)
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
    assert Ada(1) * 2 == Ada(2)
    assert Lovelace(1) * 2 == Lovelace(2)
    assert Ada(1) / 2 == Ada(0.5)
    assert Ada(1) / 2 == Lovelace(500000)
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


def test_lovelace_integer():
    """Check that the Lovelace class only accepts integer values."""

    with pytest.raises(TypeError):
        Lovelace(5.5)


def test_wallet():

    wallet = Wallet(
        name="payment",
        keys_dir=str(pathlib.Path(__file__).parent / "../resources/keys"),
    )

    assert (
        str(wallet.address)
        == "addr1q8xrqjtlfluk9axpmjj5enh0uw0cduwhz7txsqyl36m3uk2g9z3d4kaf0j5l6rxunxt43x28pssehhqds2x05mwld45s399sr7"
    )

    assert (
        wallet.sign_data("pycardano rocks", mode="payment")
        == ("84584da301276761646472657373581d61cc30497f4ff962f4c1dca54cceefe39f86f1"
            "d7179668009f8eb71e590458205797dc2cc919dfec0bb849551ebdf30d96e5cbe0f33f"
            "734a87fe826db30f7ef9a166686173686564f44f707963617264616e6f20726f636b73"
            "58402beecd6dba2f7f73d0d72abd5cc43829173a069afa2a29eff72d65049b092bc80c"
            "571569e8a7c26354cd1d38b5fcdc3d7a3b6955d2211106824ba02c33ba220f"
        )
    )

