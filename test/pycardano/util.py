from pycardano.serialization import CBORSerializable


def check_two_way_cbor(serializable: CBORSerializable):
    restored = serializable.from_cborhex(serializable.to_cborhex())
    assert restored == serializable
