import pytest

from pycardano.exception import DeserializeException
from pycardano.network import Network


def test_from_primitive_invalid_primitive_input():
    value = "a string value"
    with pytest.raises(DeserializeException):
        Network.from_primitive(value)


def test_from_primitive_testnet():
    testnet_value = 0
    network = Network.from_primitive(testnet_value)
    assert network.value == testnet_value


def test_from_primitive_mainnet():
    mainnet_value = 1
    network = Network.from_primitive(mainnet_value)
    assert network.value == mainnet_value


def test_to_primitive_testnet():
    network = Network(0)
    assert network.to_primitive() == 0


def test_to_primitive_mainnet():
    network = Network(1)
    assert network.to_primitive() == 1
