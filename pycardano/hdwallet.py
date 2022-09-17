import hashlib
import hmac
import unicodedata
from binascii import hexlify, unhexlify
from typing import Optional, Union

from ecpy.curves import Curve
from mnemonic import Mnemonic


def _Fk(message, secret):
    return hmac.new(secret, message, hashlib.sha512).digest()


class HDWallet:
    """
    Hierarchical Deterministic Wallet for Cardano
    """

    def __int__(self):
        self._seed: Optional[bytes] = None
        self._mnemonic: Optional[str] = None
        self._passphrase: Optional[str] = None
        self._entropy: Optional[str] = None

        self._root_xprivate_key: Optional[tuple] = None
        self._root_public_key: Optional[bytes] = None
        self._root_chain_code: Optional[bytes] = None
        self._xprivate_key: Optional[tuple] = None
        self._public_key: Optional[bytes] = None
        self._chain_code: Optional[bytes] = None
        self._path: str = "m"
        self._depth: int = 0
        self._index: int = 0

    def from_seed(self, seed: str) -> "HDWallet":
        """
        Create an HDWallet instance from master key.

        Args:
            seed: Master key of 96 bytes from seed hex string.

        Returns:
            HDWallet -- Hierarchical Deterministic Wallet instance.
        """

        seed = bytearray(bytes.fromhex(seed))
        seed_modified = self._tweak_bits(seed)
        self._seed = seed_modified

        kL, kR, c = seed_modified[:32], seed_modified[32:64], seed_modified[64:]

        # root public key
        cv25519 = Curve.get_curve("Ed25519")
        k_scalar = int.from_bytes(bytes(kL), "little")
        P = k_scalar * cv25519.generator
        A = cv25519.encode_point(P)

        # set root keys and parent keys
        self._root_xprivate_key = self._xprivate_key = (kL, kR)
        self._root_public_key = self._public_key = A
        self._root_chain_code = self._chain_code = c

        return self

    def from_mnemonic(
        self, mnemonic: Union[str, list], passphrase: str = ""
    ) -> "HDWallet":
        """
        Create master key and HDWallet from Mnemonic words.

        Args:
            mnemonic: Mnemonic words.
            passphrase: Mnemonic passphrase or password, default to ``None``.

        Returns:
            HDWallet -- Hierarchical Deterministic Wallet instance.
        """

        if not self.is_mnemonic(mnemonic=mnemonic):
            raise ValueError("Invalid mnemonic words.")

        self._mnemonic = unicodedata.normalize("NFKD", mnemonic)
        self._passphrase = str(passphrase) if passphrase else ""

        entropy = Mnemonic(language="english").to_entropy(words=mnemonic)
        self._entropy = hexlify(entropy).decode()

        seed = bytearray(
            hashlib.pbkdf2_hmac(
                "sha512",
                password=passphrase.encode(),
                salt=entropy,
                iterations=4096,
                dklen=96,
            )
        )

        return self.from_seed(seed=hexlify(seed).decode())

    def from_entropy(self, entropy: str, passphrase: str = None) -> "HDWallet":
        """
        Create master key and HDWallet from Mnemonic words.

        Args:
            entropy: Entropy hex string.
            passphrase: Mnemonic passphrase or password, default to ``None``.

        Returns:
            HDWallet -- Hierarchical Deterministic Wallet instance.
        """

        if not self.is_entropy(entropy):
            raise ValueError("Invalid entropy")

        self._entropy = entropy

        seed = bytearray(
            hashlib.pbkdf2_hmac(
                "sha512", password=passphrase, salt=entropy, iterations=4096, dklen=96
            )
        )
        return self.from_seed(seed=hexlify(seed).decode())

    def _tweak_bits(self, seed: bytearray) -> bytearray:
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
            modified bytearray seed.
        """
        seed[0] &= 0b11111000
        seed[31] &= 0b00011111
        seed[31] |= 0b01000000

        return seed

    def derive_from_path(self, path: str, private: bool = True) -> "HDWallet":
        """
        Derive keys from a path following CIP-1852 specifications.

        Args:
            path: Derivation path for the key generation.
            private: whether to derive private child keys or public child keys.

        Returns:
            HDWallet instance with keys derived

        Examples:
            >>> mnemonic_words = "test walk nut penalty hip pave soap entry language right filter choice"
            >>> hdwallet = HDWallet().from_mnemonic(mnemonic_words)
            >>> hdwallet.derive_from_path("m/1852'/1815'/0'/0/0")
            >>> hdwallet.public_key
            '73fea80d424276ad0978d4fe5310e8bc2d485f5f6bb3bf87612989f112ad5a7d'
        """

        if path[:2] != "m/":
            raise ValueError(
                'Bad path, please insert like this type of path "m/0\'/0"! '
            )

        for index in path.lstrip("m/").split("/"):
            if index.endswith("'"):
                self.derive_from_index(int(index[:-1]), private=private, hardened=True)
            else:
                self.derive_from_index(int(index), private=private, hardened=False)

    def derive_from_index(
        self, index: int, private: bool = True, hardened: bool = False
    ) -> "HDWallet":
        """
        Derive keys from index.

        Args:
            index: Derivation index.
            private: whether to derive private child keys or public child keys.
            hardened: whether to derive hardened address. Default to False.

        Returns:
            HDWallet instance with keys derived

        Examples:
            >>> mnemonic_words = "test walk nut penalty hip pave soap entry language right filter choice"
            >>> hdwallet = HDWallet().from_mnemonic(mnemonic_words)
            >>> hdwallet.derive_from_index(index=1852, hardened=True)
            >>> hdwallet.derive_from_index(index=1815, hardened=True)
            >>> hdwallet.derive_from_index(index=0, hardened=True)
            >>> hdwallet.derive_from_index(index=0)
            >>> hdwallet.derive_from_index(index=0)
            >>> hdwallet.public_key
            '73fea80d424276ad0978d4fe5310e8bc2d485f5f6bb3bf87612989f112ad5a7d'
        """

        if not isinstance(index, int):
            raise ValueError("Bad index, Please import only integer number!")

        if not self._root_xprivate_key and not self._root_public_key:
            raise ValueError("Missing root keys. Can't do derivation.")

        if hardened:
            index += 2**31

        # derive private child key
        if private:
            node = (self._xprivate_key, self._public_key, self._chain_code)
            self._derive_private_child_key_by_index(node, index)
        # derive public child key
        else:
            node = (self._public_key, self._chain_code)
            self._derive_public_child_key_by_index(node, index)

    def _derive_private_child_key_by_index(
        self, private_pnode: ((bytes, bytes), bytes, bytes), index: int
    ) -> Optional["HDWallet"]:
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

        if not private_pnode:
            return None

        # unpack argument
        ((kLP, kRP), AP, cP) = private_pnode
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
        cv25519 = Curve.get_curve("Ed25519")
        k_scalar = int.from_bytes(kL, "little")
        P = k_scalar * cv25519.generator
        A = cv25519.encode_point(P)

        self._xprivate_key = (kL, kR)
        self._public_key = A
        self._chain_code = c

        return self

    def _derive_public_child_key_by_index(
        self, public_pnode: (bytes, bytes), index: int
    ) -> Optional["HDWallet"]:
        """
        Derive public child keys from parent node.

        Args:
            public_pnode: (AP, cP). AP is 32 btyes parent public key, cP is 32 btyes parent chain code.
            index: child index to compute (hardened if >= 0x80000000)

        Returns:
            HDWallet with child node derived.
        """

        if not public_pnode:
            return None

        # unpack argument
        (AP, cP) = public_pnode
        assert 0 <= index < 2**32

        i_bytes = index.to_bytes(4, "little")

        # compute Z,c
        if index < 2**31:
            # regular child
            Z = _Fk(b"\x02" + AP + i_bytes, cP)
            c = _Fk(b"\x03" + AP + i_bytes, cP)[32:]
        else:
            # can't derive hardened child from public keys
            return None

        ZL = Z[:28]

        # compute ZLi
        ZLint = int.from_bytes(ZL, "little")
        ZLint_x_8 = 8 * ZLint

        # compue Ai
        cv25519 = Curve.get_curve("Ed25519")
        P = ZLint_x_8 * cv25519.generator
        Q = cv25519.decode_point(AP)
        PQ = P + Q
        A = cv25519.encode_point(PQ)

        self._public_key = A
        self._chain_code = c

        return self

    @property
    def root_xprivate_key(self):
        return (self._root_xprivate_key[0].hex(), self._root_xprivate_key[1].hex())

    @property
    def root_public_key(self):
        return None if not self._root_public_key else self._root_public_key.hex()

    @property
    def root_chain_code(self):
        return None if not self._root_chain_code else self._root_chain_code.hex()

    @property
    def xprivate_key(self):
        return (
            (None, None)
            if not self._xprivate_key
            else (self._xprivate_key[0].hex(), self._xprivate_key[1].hex())
        )

    @property
    def public_key(self):
        return None if not self._public_key else self._public_key.hex()

    @property
    def chain_code(self):
        return None if not self._chain_code else self._chain_code.hex()

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

        if language and language not in [
            "english",
            "french",
            "italian",
            "japanese",
            "chinese_simplified",
            "chinese_traditional",
            "korean",
            "spanish",
        ]:
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

        if language and language not in [
            "english",
            "french",
            "italian",
            "japanese",
            "chinese_simplified",
            "chinese_traditional",
            "korean",
            "spanish",
        ]:
            raise ValueError(
                "invalid language, use only this options english, french, "
                "italian, spanish, chinese_simplified, chinese_traditional, japanese or korean languages."
            )
        try:
            mnemonic = unicodedata.normalize("NFKD", mnemonic)
            if language is None:
                for _language in [
                    "english",
                    "french",
                    "italian",
                    "chinese_simplified",
                    "chinese_traditional",
                    "japanese",
                    "korean",
                    "spanish",
                ]:
                    valid = False
                    if Mnemonic(language=_language).check(mnemonic=mnemonic) is True:
                        valid = True
                        break
                return valid
            else:
                return Mnemonic(language=language).check(mnemonic=mnemonic)
        except ValueError:
            print("The input mnemonic words are not valid. Words should be in string format seperated by space.")

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
            print("The input entropy is not valid.")
