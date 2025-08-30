import json
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

    with tempfile.NamedTemporaryFile() as f:
        witness.save(f.name)
        loaded_witness = VerificationKeyWitness.load(f.name)
        assert witness == loaded_witness

        assert witness != vk


def test_redeemer_decode():
    witness = TransactionWitnessSet(plutus_data=[Unit()])
    encoded = witness.to_cbor()
    decoded = TransactionWitnessSet.from_cbor(encoded)
    assert isinstance(decoded.plutus_data, list)
