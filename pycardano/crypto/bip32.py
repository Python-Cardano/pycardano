"""
BIP32 implemented on curve ED25519
Paper: https://github.com/LedgerHQ/orakolo/blob/master/papers/Ed25519_BIP%20Final.pdf
This is a modified version of https://github.com/johnoliverdriscoll/py-edhd/blob/master/src/edhd/__init__.py

"""

from __future__ import annotations

import hashlib

from nacl import bindings


class BIP32ED25519PrivateKey:
    def __init__(self, private_key: bytes, chain_code: bytes):
        self.private_key = private_key
        self.left = self.private_key[:32]
        self.right = self.private_key[32:]
        self.chain_code = chain_code
        self.public_key = bindings.crypto_scalarmult_ed25519_base_noclamp(self.left)

    def sign(self, message: bytes) -> bytes:
        r = bindings.crypto_core_ed25519_scalar_reduce(
            hashlib.sha512(self.right + message).digest(),
        )
        R = bindings.crypto_scalarmult_ed25519_base_noclamp(r)
        hram = bindings.crypto_core_ed25519_scalar_reduce(
            hashlib.sha512(R + self.public_key + message).digest(),
        )
        S = bindings.crypto_core_ed25519_scalar_add(
            bindings.crypto_core_ed25519_scalar_mul(hram, self.left),
            r,
        )
        return R + S


class BIP32ED25519PublicKey:
    def __init__(self, public_key: bytes, chain_code: bytes):
        self.public_key = public_key
        self.chain_code = chain_code

    @classmethod
    def from_private_key(
        cls, private_key: BIP32ED25519PrivateKey
    ) -> BIP32ED25519PublicKey:
        return cls(private_key.public_key, private_key.chain_code)

    def verify(self, signature, message):
        return bindings.crypto_sign_open(signature + message, self.public_key)
