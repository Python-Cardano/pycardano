from pycardano.serialization import CBORSerializable


def check_two_way_cbor(serializable: CBORSerializable):
    restored = serializable.from_cbor(serializable.to_cbor())
    assert restored == serializable
