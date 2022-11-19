"""
BIP32 implemented on curve ED25519
Paper: https://github.com/LedgerHQ/orakolo/blob/master/papers/Ed25519_BIP%20Final.pdf
This is a modified version of https://github.com/johnoliverdriscoll/py-edhd/blob/master/src/edhd/__init__.py

"""

from __future__ import annotations

import hashlib
import hmac
import unicodedata
from binascii import hexlify, unhexlify
from typing import Optional, Tuple

from mnemonic import Mnemonic
from nacl import bindings

from pycardano.logging import logger

__all__ = ["BIP32ED25519PrivateKey", "BIP32ED25519PublicKey", "HDWallet"]


SUPPORTED_MNEMONIC_LANGS = {
    "english",
    "french",
    "italian",
    "japanese",
    "chinese_simplified",
    "chinese_traditional",
    "korean",
    "spanish",
}


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


def _Fk(message, secret):
    return hmac.new(secret, message, hashlib.sha512).digest()


class HDWallet:
    """
    Hierarchical Deterministic Wallet for Cardano
    """

    def __init__(
        self,
        root_xprivate_key: bytes,
        root_public_key: bytes,
        root_chain_code: bytes,
        xprivate_key: bytes,
        public_key: bytes,
        chain_code: bytes,
        path: str = "m",
        seed: Optional[bytes] = None,
        mnemonic: Optional[str] = None,
        passphrase: Optional[str] = None,
        entropy: Optional[str] = None,
    ):
        self._root_xprivate_key = root_xprivate_key
        self._root_public_key = root_public_key
        self._root_chain_code = root_chain_code

        self._xprivate_key = xprivate_key
        self._public_key = public_key
        self._chain_code = chain_code

        self._path = path

        self._seed = seed
        self._mnemonic = mnemonic
        self._passphrase = passphrase
        self._entropy = entropy

    @classmethod
    def from_seed(
        cls,
        seed: str,
        entropy: Optional[str] = None,
        passphrase: Optional[str] = None,
        mnemonic: Optional[str] = None,
    ) -> HDWallet:
        """
        Create an HDWallet instance from master key.

        Args:
            seed: Master key of 96 bytes from seed hex string.
            entropy: Entropy hex string, default to ``None``.
            passphrase: Mnemonic passphrase or password, default to ``None``.
            mnemonic: Mnemonic words, default to ``None``.

        Returns:
            HDWallet -- Hierarchical Deterministic Wallet instance.
        """

        seed_converted = bytearray(bytes.fromhex(seed))
        seed_modified = cls._tweak_bits(seed_converted)

        kL, c = seed_modified[:32], seed_modified[64:]

        # root public key
        A = bindings.crypto_scalarmult_ed25519_base_noclamp(kL)

        return cls(
            root_xprivate_key=seed_modified[:64],
            root_public_key=A,
            root_chain_code=c,
            xprivate_key=seed_modified[:64],
            public_key=A,
            chain_code=c,
            seed=seed_modified,
            mnemonic=mnemonic,
            passphrase=passphrase,
            entropy=entropy,
        )

    @classmethod
    def from_mnemonic(cls, mnemonic: str, passphrase: str = "") -> HDWallet:
        """
        Create master key and HDWallet from Mnemonic words.

        Args:
            mnemonic: Mnemonic words.
            passphrase: Mnemonic passphrase or password, default to ``None``.

        Returns:
            HDWallet -- Hierarchical Deterministic Wallet instance.
        """

        if not cls.is_mnemonic(mnemonic=mnemonic):
            raise ValueError("Invalid mnemonic words.")

        mnemonic = unicodedata.normalize("NFKD", mnemonic)
        entropy = Mnemonic(language="english").to_entropy(words=mnemonic)
        seed = cls._generate_seed(passphrase, entropy)

        return cls.from_seed(
            seed=hexlify(seed).decode(),
            mnemonic=mnemonic,
            entropy=hexlify(entropy).decode("utf-8"),
            passphrase=passphrase,
        )

    @classmethod
    def from_entropy(cls, entropy: str, passphrase: str = "") -> HDWallet:
        """
        Create master key and HDWallet from Mnemonic words.

        Args:
            entropy: Entropy hex string.
            passphrase: Mnemonic passphrase or password, default to ``None``.

        Returns:
            HDWallet -- Hierarchical Deterministic Wallet instance.
        """

        if not cls.is_entropy(entropy):
            raise ValueError("Invalid entropy")

        seed = cls._generate_seed(passphrase, bytearray.fromhex(entropy))
        return cls.from_seed(seed=hexlify(seed).decode(), entropy=entropy)

    @classmethod
    def _generate_seed(cls, passphrase: str, entropy: bytearray) -> bytearray:
        return bytearray(
            hashlib.pbkdf2_hmac(
                "sha512",
                password=passphrase.encode(),
                salt=entropy,
                iterations=4096,
                dklen=96,
            )
        )

    @classmethod
    def _tweak_bits(cls, seed: bytearray) -> bytes:
        """
        Modify seed based on Icarus master node derivation scheme.

        The process follows
        `CIP-0003#Wallet Key Generation <https://github.com/cardano-foundation/CIPs/tree/master/CIP-0003>`_.

        Process:
            - clear the lowest 3 bits
            - clear the highest 3 bits
            - set the highest second bit

        Args:
            seed: Seed in bytearray

        Returns:
            modified seed in bytes.
        """
        seed[0] &= 0b11111000
        seed[31] &= 0b00011111
        seed[31] |= 0b01000000

        return bytes(seed)

    def _copy_hdwallet(self):
        """
        Create a new instance of HDWallet
        """

        return HDWallet(
            root_xprivate_key=self._root_xprivate_key,
            root_public_key=self._root_public_key,
            root_chain_code=self._root_chain_code,
            xprivate_key=self._xprivate_key,
            public_key=self._public_key,
            chain_code=self._chain_code,
            path=self._path,
            seed=self._seed,
            mnemonic=self._mnemonic,
            passphrase=self._passphrase,
            entropy=self._entropy,
        )

    def derive_from_path(self, path: str, private: bool = True) -> HDWallet:
        """
        Derive keys from a path following CIP-1852 specifications.

        Args:
            path: Derivation path for the key generation.
            private: whether to derive private child keys or public child keys.

        Returns:
            HDWallet instance with keys derived

        Examples:
            >>> mnemonic_words = "test walk nut penalty hip pave soap entry language right filter choice"
            >>> hdwallet = HDWallet.from_mnemonic(mnemonic_words)
            >>> child_hdwallet = hdwallet.derive_from_path("m/1852'/1815'/0'/0/0")
            >>> child_hdwallet.public_key.hex()
            '73fea80d424276ad0978d4fe5310e8bc2d485f5f6bb3bf87612989f112ad5a7d'
        """

        if path[:2] != "m/":
            raise ValueError(
                'Bad path, please insert like this type of path "m/0\'/0"! '
            )

        derived_hdwallet = self._copy_hdwallet()
        for index in path.lstrip("m/").split("/"):
            if index.endswith("'"):
                derived_hdwallet = derived_hdwallet.derive(
                    int(index[:-1]), private=private, hardened=True
                )
            else:
                derived_hdwallet = derived_hdwallet.derive(
                    int(index), private=private, hardened=False
                )

        return derived_hdwallet

    def derive(
        self,
        index: int,
        private: bool = True,
        hardened: bool = False,
    ) -> HDWallet:
        """
        Returns a new HDWallet derived from given index.

        Args:
            index: Derivation index.
            private: whether to derive private child keys or public child keys.
            hardened: whether to derive hardened address. Default to False.

        Returns:
            HDWallet instance with keys derived

        Examples:
            >>> mnemonic_words = "test walk nut penalty hip pave soap entry language right filter choice"
            >>> hdwallet = HDWallet.from_mnemonic(mnemonic_words)
            >>> hdwallet = hdwallet.derive(1852, hardened=True)
            >>> hdwallet = hdwallet.derive(1815, hardened=True)
            >>> hdwallet = hdwallet.derive(0, hardened=True)
            >>> hdwallet = hdwallet.derive(0)
            >>> hdwallet = hdwallet.derive(0)
            >>> hdwallet.public_key.hex()
            '73fea80d424276ad0978d4fe5310e8bc2d485f5f6bb3bf87612989f112ad5a7d'
        """

        if not isinstance(index, int):
            raise ValueError("Bad index, Please import only integer number!")

        if not self._root_xprivate_key and not self._root_public_key:
            raise ValueError("Missing root keys. Can't do derivation.")

        if hardened:
            index += 2**31

        if private:
            private_node = (
                self._xprivate_key[:32],
                self._xprivate_key[32:],
                self._public_key,
                self._chain_code,
                self._path,
            )
            return self._derive_private_child_key_by_index(private_node, index)

        public_node = (
            self._public_key,
            self._chain_code,
            self._path,
        )
        return self._derive_public_child_key_by_index(public_node, index)

    def _derive_private_child_key_by_index(
        self, private_pnode: Tuple[bytes, bytes, bytes, bytes, str], index: int
    ) -> HDWallet:
        """
        Derive private child keys from parent node.

        PROCESS:
          1. encode i 4-bytes little endian, il = encode_U32LE(i)
          2. if i is less than 2^31
               - compute Z   = HMAC-SHA512(key=c, Data=0x02 | A | il )
               - compute c_  = HMAC-SHA512(key=c, Data=0x03 | A | il )
             else
               - compute Z   = HMAC-SHA512(key=c, Data=0x00 | kL | kR | il )
               - compute c_  = HMAC-SHA512(key=c, Data=0x01 | kL | kR | il )
          3. ci = lowest_32bytes(c_)
          4. set ZL = highest_28bytes(Z)
             set ZR = lowest_32bytes(Z)
          5. compute kL_i:
                zl_  = LEBytes_to_int(ZL)
                kL_  = LEBytes_to_int(kL)
                kLi_ = zl_*8 + kL_
                if kLi_ % order == 0: child does not exist
                kL_i = int_to_LEBytes(kLi_)
          6. compute kR_i
                zr_  = LEBytes_to_int(ZR)
                kR_  = LEBytes_to_int(kR)
                kRi_ = (zr_ + kRn_) % 2^256
                kR_i = int_to_LEBytes(kRi_)
          7. compute A
                A = kLi_.G
          8. return ((kL_i,kR_i), A_i, c)

        Args:
            private_pnode: ((kLP,kRP), AP, cP). (kLP,kRP) is 64 bytes parent private eddsa key,
                AP is 32 btyes parent public key, cP is 32 btyes parent chain code.
            index: child index to compute (hardened if >= 0x80000000)

        Returns:
            HDWallet with child node derived.

        """
        # unpack argument
        (kLP, kRP, AP, cP, path) = private_pnode
        assert 0 <= index < 2**32

        i_bytes = index.to_bytes(4, "little")

        # compute Z,c
        if index < 2**31:
            # regular child
            Z = _Fk(b"\x02" + AP + i_bytes, cP)
            c = _Fk(b"\x03" + AP + i_bytes, cP)[32:]
        else:
            # harderned child
            Z = _Fk(b"\x00" + (kLP + kRP) + i_bytes, cP)
            c = _Fk(b"\x01" + (kLP + kRP) + i_bytes, cP)[32:]

        ZL, ZR = Z[:28], Z[32:]

        # compute KLi
        kLn = int.from_bytes(ZL, "little") * 8 + int.from_bytes(kLP, "little")

        # compute KRi
        kRn = (int.from_bytes(ZR, "little") + int.from_bytes(kRP, "little")) % 2**256

        kL = kLn.to_bytes(32, "little")
        kR = kRn.to_bytes(32, "little")

        # compue Ai
        A = bindings.crypto_scalarmult_ed25519_base_noclamp(kL)

        # compute path
        path += "/" + str(index)

        derived_hdwallet = HDWallet(
            root_xprivate_key=self._root_xprivate_key,
            root_public_key=self._root_public_key,
            root_chain_code=self._root_chain_code,
            xprivate_key=kL + kR,
            public_key=A,
            chain_code=c,
            path=path,
            seed=self._seed,
            mnemonic=self._mnemonic,
            passphrase=self._passphrase,
            entropy=self._entropy,
        )

        return derived_hdwallet

    def _derive_public_child_key_by_index(
        self, public_pnode: Tuple[bytes, bytes, str], index: int
    ) -> HDWallet:
        """
        Derive public child keys from parent node.

        Args:
            public_pnode: (AP, cP). AP is 32 btyes parent public key, cP is 32 btyes parent chain code.
            index: child index to compute (hardened if >= 0x80000000)

        Returns:
            HDWallet with child node derived.
        """
        # unpack argument
        (AP, cP, path) = public_pnode
        assert 0 <= index < 2**32

        i_bytes = index.to_bytes(4, "little")

        # compute Z,c
        if index < 2**31:
            # regular child
            Z = _Fk(b"\x02" + AP + i_bytes, cP)
            c = _Fk(b"\x03" + AP + i_bytes, cP)[32:]
        else:
            # can't derive hardened child from public keys
            raise ValueError("Cannot derive hardened index with public key")

        ZL = Z[:28]

        # compute ZLi
        ZLint = int.from_bytes(ZL, "little")

        # compue Ai
        A = bindings.crypto_core_ed25519_add(
            AP,
            bindings.crypto_scalarmult_ed25519_base_noclamp(
                (8 * ZLint).to_bytes(32, "little")
            ),
        )

        # compute path
        path += "/" + str(index)

        derived_hdwallet = HDWallet(
            root_xprivate_key=self._root_xprivate_key,
            root_public_key=self._root_public_key,
            root_chain_code=self._root_chain_code,
            xprivate_key=self._xprivate_key,
            public_key=A,
            chain_code=c,
            path=path,
            seed=self._seed,
            mnemonic=self._mnemonic,
            passphrase=self._passphrase,
            entropy=self._entropy,
        )

        return derived_hdwallet

    @property
    def root_xprivate_key(self):
        return self._root_xprivate_key

    @property
    def root_public_key(self):
        return self._root_public_key

    @property
    def root_chain_code(self):
        return self._root_chain_code

    @property
    def xprivate_key(self):
        return self._xprivate_key

    @property
    def public_key(self):
        return self._public_key

    @property
    def chain_code(self):
        return self._chain_code

    @staticmethod
    def generate_mnemonic(language: str = "english", strength: int = 256) -> str:
        """
        Generate mnemonic words.

        Args:
            language (str): language for the mnemonic words.
            strength (int): length of the mnemoic words. Valid values are 128/160/192/224/256.

        Returns:
            mnemonic (str): mnemonic words.
        """

        if language and language not in SUPPORTED_MNEMONIC_LANGS:
            raise ValueError(
                "invalid language, use only this options english, french, "
                "italian, spanish, chinese_simplified, chinese_traditional, japanese or korean languages."
            )
        if strength not in [128, 160, 192, 224, 256]:
            raise ValueError(
                "Strength should be one of the following "
                "[128, 160, 192, 224, 256], but it is not (%d)." % strength
            )

        return Mnemonic(language=language).generate(strength=strength)

    @staticmethod
    def is_mnemonic(mnemonic: str, language: Optional[str] = None) -> bool:
        """
        Check if mnemonic words are valid.

        Args:
            mnemonic (str): Mnemonic words in string format.
            language (Optional[str]): Mnemonic language, default to None.

        Returns:
            bool. Whether the input mnemonic words is valid.
        """

        if language and language not in SUPPORTED_MNEMONIC_LANGS:
            raise ValueError(
                "invalid language, use only this options english, french, "
                "italian, spanish, chinese_simplified, chinese_traditional, japanese or korean languages."
            )
        try:
            mnemonic = unicodedata.normalize("NFKD", mnemonic)
            if language:
                return Mnemonic(language=language).check(mnemonic=mnemonic)

            for _language in SUPPORTED_MNEMONIC_LANGS:
                if Mnemonic(language=_language).check(mnemonic=mnemonic) is True:
                    return True
        except ValueError:
            logger.warning(
                "The input mnemonic words are not valid. Words should be in string format seperated by space."
            )
        return False

    @staticmethod
    def is_entropy(entropy: str) -> bool:
        """
        Check entropy hex string.

        Args:
            entropy: entropy converted from mnemonic words.

        Returns:
            bool. Whether entropy is valid or not.
        """

        try:
            return len(unhexlify(entropy)) in [16, 20, 24, 28, 32]
        except ValueError:
            logger.warning("The input entropy is not valid.")
            return False
