import tempfile

from pycardano import (
    PaymentKeyPair,
    PaymentSigningKey,
    PaymentVerificationKey,
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
