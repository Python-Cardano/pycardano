import json
import os
import tempfile

from pycardano import (
    PaymentSigningKey,
    PaymentVerificationKey,
    Transaction,
    TransactionWitnessSet,
    Unit,
    VerificationKeyWitness,
)


def test_witness_save_load():
    sk = PaymentSigningKey.generate()
    vk = PaymentVerificationKey.from_signing_key(sk)
    witness = VerificationKeyWitness(
        vkey=vk,
        signature=sk.sign(b"test"),
    )

    with tempfile.NamedTemporaryFile(delete=False) as f:
        tmp_path = f.name
    try:
        witness.save(tmp_path)
        loaded_witness = VerificationKeyWitness.load(tmp_path)
        assert witness == loaded_witness

        assert witness != vk
    finally:
        os.unlink(tmp_path)


def test_redeemer_decode():
    witness = TransactionWitnessSet(plutus_data=[Unit()])
    encoded = witness.to_cbor()
    decoded = TransactionWitnessSet.from_cbor(encoded)
    assert isinstance(decoded.plutus_data, list)
