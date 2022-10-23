import datetime
import json
import operator
from dataclasses import dataclass, field
from functools import wraps
from os import getenv
from pathlib import Path
from time import sleep
from typing import List, Literal, Optional, Union

from blockfrost import ApiError

from pycardano.address import Address
from pycardano.backend.base import ChainContext
from pycardano.backend.blockfrost import BlockFrostChainContext
from pycardano.certificate import StakeCredential, StakeDelegation, StakeRegistration
from pycardano.cip.cip8 import sign
from pycardano.exception import PyCardanoException
from pycardano.hash import PoolKeyHash, ScriptHash, TransactionId
from pycardano.key import (
    PaymentKeyPair,
    PaymentSigningKey,
    PaymentVerificationKey,
    SigningKey,
    StakeKeyPair,
    VerificationKey,
)
from pycardano.logging import logger
from pycardano.metadata import AlonzoMetadata, AuxiliaryData, Metadata
from pycardano.nativescript import (
    InvalidHereAfter,
    NativeScript,
    ScriptAll,
    ScriptPubkey,
)
from pycardano.network import Network
from pycardano.transaction import (
    Asset,
    AssetName,
    MultiAsset,
    TransactionOutput,
    UTxO,
    Value,
    Withdrawals,
)
from pycardano.txbuilder import TransactionBuilder
from pycardano.utils import min_lovelace


# function wrappers
def blockfrost_only(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if isinstance(kwargs.get("context"), BlockFrostChainContext) or isinstance(
            args[1], BlockFrostChainContext
        ):
            func(*args, **kwargs)
        else:
            raise TypeError(
                f"Function {func.__name__} is only available for context of type BlockFrostChainContext."
            )

    return wrapper


@dataclass(frozen=True)
class Amount:
    """Base class for Cardano currency amounts."""

    _amount: Union[float, int]
    _amount_type: str = "lovelace"

    def __post_init__(self):

        if self._amount_type == "lovelace":
            self._lovelace = int(self._amount)
            self._ada = self._amount / 1000000
        else:
            self._lovelace = int(self._amount * 1000000)
            self._ada = self._amount

        self._amount_dict = {"lovelace": self._lovelace, "ada": self._ada}

    @property
    def amount(self):
        """Encodes the contained amount."""

        if self._amount_type == "lovelace":
            return self.lovelace
        else:
            return self.ada

    @property
    def lovelace(self):
        """Returns the lovelace amount"""
        return self._lovelace

    @property
    def ada(self):
        """Returns the ada amount"""
        return self._ada

    def __eq__(self, other):
        if isinstance(other, (int, float)):
            return self.amount == other
        elif isinstance(other, Amount):
            return self.lovelace == other.lovelace
        else:
            raise TypeError("Must compare with a number or another Cardano amount")

    def __ne__(self, other):
        if isinstance(other, (int, float)):
            return self.amount != other
        elif isinstance(other, Amount):
            return self.lovelace != other.lovelace
        else:
            raise TypeError("Must compare with a number or another Cardano amount")

    def __gt__(self, other):
        if isinstance(other, (int, float)):
            return self.amount > other
        elif isinstance(other, Amount):
            return self.lovelace > other.lovelace
        else:
            raise TypeError("Must compare with a number or another Cardano amount")

    def __lt__(self, other):
        if isinstance(other, (int, float)):
            return self.amount < other
        elif isinstance(other, Amount):
            return self.lovelace < other.lovelace
        else:
            raise TypeError("Must compare with a number or another Cardano amount")

    def __ge__(self, other):
        if isinstance(other, (int, float)):
            return self.amount >= other
        elif isinstance(other, Amount):
            return self.lovelace >= other.lovelace
        else:
            raise TypeError("Must compare with a number or another Cardano amount")

    def __le__(self, other):
        if isinstance(other, (int, float)):
            return self.amount <= other
        elif isinstance(other, Amount):
            return self.lovelace <= other.lovelace
        else:
            raise TypeError("Must compare with a number or another Cardano amount")

    def __int__(self):
        return int(self.amount)

    def __str__(self):
        return str(self.amount)

    def __hash__(self):
        return hash((self._amount, self._amount_type))

    def __bool__(self):
        return bool(self._amount)

    def __getitem__(self, key):
        return self._amount_dict[key]

    # Math
    def __add__(self, other):
        if isinstance(other, (int, float)):
            return self.__class__(self.amount + other)
        elif isinstance(other, Amount):
            return self.__class__(self.amount + other[self._amount_type])
        else:
            raise TypeError("Must compute with a number or another Cardano amount")

    def __radd__(self, other):
        if isinstance(other, (int, float)):
            return self.__class__(self.amount + other)
        else:
            raise TypeError("Must compute with a number or another Cardano amount")

    def __sub__(self, other):
        if isinstance(other, (int, float)):
            return self.__class__(self.amount - other)
        elif isinstance(other, Amount):
            return self.__class__(self.amount - other[self._amount_type])
        else:
            raise TypeError("Must compute with a number or another Cardano amount")

    def __rsub__(self, other):
        if isinstance(other, (int, float)):
            return self.__class__(other - self.amount)
        else:
            raise TypeError("Must compute with a number or another Cardano amount")

    def __mul__(self, other):
        if isinstance(other, (int, float)):
            return self.__class__(self.amount * other)
        elif isinstance(other, Amount):
            return self.__class__(self.amount * other[self._amount_type])
        else:
            raise TypeError("Must compute with a number or another Cardano amount")

    def __rmul__(self, other):
        if isinstance(other, (int, float)):
            return self.__class__(self.amount * other)
        else:
            raise TypeError("Must compute with a number or another Cardano amount")

    def __truediv__(self, other):
        if isinstance(other, (int, float)):
            return self.__class__(self.amount / other)
        elif isinstance(other, Amount):
            return self.__class__(self.amount / other[self._amount_type])
        else:
            raise TypeError("Must compute with a number or another Cardano amount")

    def __floordiv__(self, other):
        if isinstance(other, (int, float)):
            return self.__class__(self.amount // other)
        elif isinstance(other, Amount):
            return self.__class__(self.amount // other[self._amount_type])
        else:
            raise TypeError("Must compute with a number or another Cardano amount")

    def __rtruediv__(self, other):
        if isinstance(other, (int, float)):
            return self.__class__(other / self.amount)
        else:
            raise TypeError("Must compute with a number or another Cardano amount")

    def __rfloordiv__(self, other):
        if isinstance(other, (int, float)):
            return self.__class__(other // self.amount)
        else:
            raise TypeError("Must compute with a number or another Cardano amount")

    def __neg__(self):
        return self.__class__(-self.amount)

    def __abs__(self):
        return self.__class__(abs(self.amount))

    def __round__(self):
        return self.__class__(round(self.amount))


class Lovelace(Amount):
    """Stores an amount of Lovelace and automatically handles most currency math."""

    def __init__(self, amount: int = 0):

        if not isinstance(amount, int):
            raise TypeError("Lovelace must be an integer.")

        super().__init__(amount, "lovelace")

    def __repr__(self):
        return f"Lovelace({self.lovelace})"

    def as_lovelace(self):
        """Returns a copy."""
        return Lovelace(self.lovelace)

    def as_ada(self):
        """Converts the Lovelace to an Ada class."""
        return Ada(self.ada)


class Ada(Amount):
    """Stores an amount of Ada and automatically handles most currency math."""

    def __init__(self, amount: Union[int, float] = 0):
        super().__init__(amount, "ada")

    def __repr__(self):
        return f"Ada({self.ada})"

    def as_lovelace(self):
        """Converts the Ada to a Lovelace class."""
        return Lovelace(self.lovelace)

    def as_ada(self):
        """Returns a copy."""
        return Ada(self.ada)


@dataclass(unsafe_hash=True)
class TokenPolicy:
    """Class for the creation and management of fungible and non-fungible token policies.

    Args:
        name (str): The name of the token policy, used for saving and loading keys.
        policy (Optional[Union[NativeScript, dict, str]]): Direct provide a policy to use.
        policy_dir (Optional[Union[str, Path]]): The directory to save and load the policy from.
    """

    name: str
    policy: Optional[Union[NativeScript, dict, str]] = field(repr=False, default=None)
    policy_dir: Optional[Union[str, Path]] = field(
        repr=False, default=Path("./priv/policies")
    )

    def __post_init__(self):

        # streamline inputs
        if isinstance(self.policy_dir, str):
            self.policy_dir = Path(self.policy_dir)

        # if native script is directly provide, stop there
        if self.policy:
            if isinstance(self.policy, dict):
                self.policy = NativeScript.from_dict(self.policy)
        else:
            if not self.policy_dir.exists():
                self.policy_dir.mkdir(parents=True, exist_ok=True)

            # look for the policy
            if Path(self.policy_dir / f"{self.name}.script").exists():
                with open(
                    Path(self.policy_dir / f"{self.name}.script"), "r"
                ) as policy_file:
                    self.policy = NativeScript.from_dict(json.load(policy_file))

    @property
    def policy_id(self):

        if not isinstance(self.policy, str):
            return str(self.policy.hash())
        else:
            return self.policy

    @property
    def id(self):
        return self.policy_id

    @property
    def script(self):
        return self.policy

    @property
    def expiration_slot(self):
        """Get the expiration slot for a simple minting policy,
        like one generated by generate_minting_policy
        """

        if not isinstance(self.policy, str):
            scripts = getattr(self.policy, "native_scripts", None)

            if scripts:
                for script in scripts:
                    if script._TYPE == 5:
                        return script.after

    @property
    def required_signatures(self):
        """List the public key hashes of all required signers"""

        required_signatures = []

        if not isinstance(self.policy, str):
            scripts = getattr(self.policy, "native_scripts", None)

            if scripts:
                for script in scripts:
                    if script._TYPE == 0:
                        required_signatures.append(script.key_hash)

        return required_signatures

    def get_expiration_timestamp(self, context: ChainContext):
        """Get the expiration timestamp for a simple minting policy,
        like one generated by generate_minting_policy
        """

        if self.expiration_slot:
            seconds_diff = self.expiration_slot - context.last_block_slot

            return datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(
                seconds=seconds_diff
            )

    def is_expired(self, context: ChainContext):
        """Get the expiration timestamp for a simple minting policy,
        like one generated by generate_minting_policy
        """

        if self.expiration_slot:
            seconds_diff = self.expiration_slot - context.last_block_slot

            return seconds_diff < 0

    def generate_minting_policy(
        self,
        signers: Union["Wallet", Address, List["Wallet"], List[Address]],
        expiration: Optional[Union[datetime.datetime, int]] = None,
        context: Optional[ChainContext] = None,
    ):
        """Generate a minting policy for the given signers with an optional expiration.
        Policy is generated with CIP-25 in mind.

        Args:
            signers (Union[Wallet, Address, List[Wallet], List[Address]]): The signer(s) of the policy.
            expiration (Optional[Union[datetime.datetime, int]]): The expiration of the policy.
                If given as a datetime, it will be roughly converted to a slot.
            context (Optional[ChainContext]): A context is needed to estimate the expiration slot from a datetime.
        """

        script_filepath = Path(self.policy_dir / f"{self.name}.script")

        if script_filepath.exists() or self.policy:
            raise FileExistsError(f"Policy named {self.name} already exists")

        if isinstance(expiration, datetime.datetime) and not context:
            raise AttributeError(
                "If input expiration is provided as a datetime, please also provide a context."
            )

        # get pub key hashes
        if not isinstance(signers, list):
            signers = [signers]

        pub_keys = [ScriptPubkey(self._get_pub_key_hash(signer)) for signer in signers]

        # calculate when to lock
        if expiration:
            if isinstance(expiration, int):  # assume this is directly the block no.
                must_before_slot = InvalidHereAfter(expiration)
            elif isinstance(expiration, datetime.datetime):
                if expiration.tzinfo:
                    time_until_expiration = expiration - datetime.datetime.now(
                        datetime.timezone.utc
                    )
                else:
                    time_until_expiration = expiration - datetime.datetime.now()

                last_block_slot = context.last_block_slot

                must_before_slot = InvalidHereAfter(
                    last_block_slot + int(time_until_expiration.total_seconds())
                )
            else:
                must_before_slot = None

            # noinspection PyTypeChecker
            policy = ScriptAll(pub_keys + [must_before_slot])

        else:
            policy = ScriptAll(pub_keys)

        # save policy to file
        with open(script_filepath, "w") as script_file:
            json.dump(policy.to_dict(), script_file, indent=4)

        self.policy = policy

    @staticmethod
    def _get_pub_key_hash(signer: Union["Wallet", Address]):

        if hasattr(signer, "verification_key"):
            return signer.verification_key.hash()
        elif isinstance(signer, Address):
            return str(signer.payment_part)
        else:
            raise TypeError("Input signer must be of type Wallet or Address.")


@dataclass(unsafe_hash=True)
class Token:
    """Class that represents a token with an attached policy and amount.

    Attributes:
        policy (Union[NativeScript, TokenPolicy]): The policy of the token.
            The policy need not necessarily be owned by the user.
        amount (int): The amount of tokens.
        name (str): The name of the token. Either the name or the hex name should be provided.
        hex_name (str): The name of the token as a hex string.
        metadata (dict): The metadata attached to the token
    """

    policy: Union[NativeScript, TokenPolicy]
    amount: int
    name: Optional[str] = field(default="")
    hex_name: Optional[str] = field(default="")
    metadata: Optional[dict] = field(default_factory=dict, compare=False)

    def __post_init__(self):

        if not isinstance(self.amount, int):
            raise TypeError("Expected token amount to be of type: integer.")

        if self.hex_name:
            if isinstance(self.hex_name, str):
                self.name = bytes.fromhex(self.hex_name).decode("utf-8")

        elif isinstance(self.name, str):
            self.hex_name = bytes(self.name.encode("utf-8")).hex()

        self._check_metadata(to_check=self.metadata, top_level=True)

    def __str__(self):
        return self.name

    def _check_metadata(
        self, to_check: Union[dict, list, str], top_level: bool = False
    ):
        """Screen the input metadata for potential issues.
        Used recursively to check inside all dicts and lists of the metadata.
        Use top_level=True only for the full metadata dictionary in order to check that
        it is JSON serializable.
        """

        if isinstance(to_check, dict):
            for key, value in to_check.items():

                if len(str(key)) > 64:
                    raise MetadataFormattingException(
                        f"Metadata key is too long (> 64 characters): {key}\nConsider splitting into an array of "
                        f"shorter strings. "
                    )

                if isinstance(value, dict) or isinstance(value, list):
                    self._check_metadata(to_check=value)

                elif len(str(value)) > 64:
                    raise MetadataFormattingException(
                        f"Metadata field is too long (> 64 characters): {key}: {value}\nConsider splitting into an "
                        f"array of shorter strings. "
                    )

        elif isinstance(to_check, list):

            for item in to_check:
                self._check_metadata(to_check=item)

        elif isinstance(to_check, str):
            if len(to_check) > 64:
                raise MetadataFormattingException(
                    f"Metadata field is too long (> 64 characters): {to_check}\nConsider splitting into an array of "
                    f"shorter strings. "
                )

        if top_level:
            try:
                json.dumps(to_check)
            except TypeError as e:
                raise MetadataFormattingException(f"Cannot format metadata: {e}")

    @property
    def bytes_name(self):
        return bytes(self.name.encode("utf-8"))

    @property
    def policy_id(self):
        return self.policy.policy_id

    @blockfrost_only
    def get_on_chain_metadata(self, context: ChainContext) -> dict:
        """Get the on-chain metadata of the token.

        Args:
            context (ChainContext): A chain context is necessary to fetch the on-chain metadata.
                Only BlockFrost chain context is supported at the moment.

        Returns:
            dict: The on-chain metadata of the token.

        """

        try:
            metadata = context.api.asset(
                self.policy.id + self.hex_name
            ).onchain_metadata.to_dict()
        except ApiError as e:
            logger.error(
                f"Could not get on-chain data, likely this asset has not been minted yet\n Blockfrost Error: {e}"
            )
            metadata = {}

        self.metadata = metadata
        return metadata


@dataclass(unsafe_hash=True)
class Output:
    """Represents the output of a transaction.

    Attributes:
        address (Union[Wallet, Address, str]): The address of receiver of this output.
        amount (Union[Lovelace, Ada, int]): The amount of Lovelace (or Ada) being sent to the address.
            Should generally satisfy the minimum ADA requirement for any attached tokens.
        tokens (Optional[Union[Token, List[Token]]]): Token or list of Tokens to be sent to the address.
            Amount of each token to send should be defined in each Token object.

    """

    address: Union["Wallet", Address, str]
    amount: Union[Lovelace, Ada, int]
    tokens: Optional[Union[Token, List[Token]]] = field(default_factory=list)

    def __post_init__(self):

        if (
            not isinstance(self.amount, Ada)
            and not isinstance(self.amount, Lovelace)
            and not isinstance(self.amount, int)
        ):
            raise TypeError(
                "Please provide amount as either `Ada(amount)` or `Lovelace(amount)`.",
                "Otherwise provide lovelace as an integer.",
            )

        if isinstance(self.amount, int):
            self.amount = Lovelace(self.amount)

        if self.tokens:
            if not isinstance(self.tokens, list):
                self.tokens = [self.tokens]

        if isinstance(self.address, str):
            self.address = Address.from_primitive(self.address)

        elif isinstance(self.address, Wallet):
            self.address = self.address.address


@dataclass
class Wallet:
    """Create or load a wallet for which you own the keys or will later create them.
    NOTE: BlockFrost Chain Context can be automatically loaded by setting the following environment variables:
        `BLOCKFROST_ID_MAINNET` for mainnet
        `BLOCKFROST_ID_PREPROD` for preprod
        `BLOCKFROST_ID_PREVIEW` for preview
    Otherwise, a custom Chain Context can be provided when necessary.

    Currently you can already:
    - Generate keys
    - Load keys
    - Fetch utxos
    - Send ada
    - Send specific UTxOs
    - Get senders of all UTxOs
    - Get metadata for all held tokens
    - Get utxo block times and sort utxos
    - Mint / Burn tokens
    - Automatically load in token polices where wallet is a signer
    - Automatically create BlockFrost Chain Context (mainnet, preprod, and preview)
    - Attach messages to transactions
    - Sign messages
    - Add custom metadata fields
    - Multi-output transactions
    - Register wallet
    - Stake wallet
    - Withdraw rewards
    - Generate fully manual transactions that can do any / all of the above

    Future additions (TODO list):
    - Add tests
    - Add examples
    - Create and sign multi-sig transactions
    - Interaction with native scripts
    - Interaction with plutus scripts
    - Load wallets with mnemonic phrase

    Attributes:
        name (str): The name of the wallet. This is required and keys will be
            automatically generated and saved with this name. If the wallet already exists in keys_dir,
            it will be loaded automatically.
        address (Optional[Union[Address, str]]): Optionally provide an address to use as a wallet
            without signing capabilities.
        keys_dir (Optional[Union[str, Path]]): Directory in which to save the keys. Defaults to "./priv".
        use_stake (Optional[bool]): Whether to use a stake address for this wallet. Defaults to True.
        network (Optional[str, Network]): The network to use for the wallet.
            Can pick from "mainnet", "preview", "preprod". Defaults to "mainnet".
            BlockFrost Chain Context will be automatically loaded for this network if
            the API key is set in the environment variables.

    """

    name: str
    address: Optional[Union[Address, str]] = None
    keys_dir: Optional[Union[str, Path]] = field(repr=False, default=Path("./priv"))
    use_stake: Optional[bool] = field(repr=False, default=True)
    network: Optional[Literal["mainnet", "preview", "preprod"]] = "mainnet"

    # generally added later upon initialization
    lovelace: Optional[Lovelace] = field(repr=False, default=Lovelace(0))
    ada: Optional[Ada] = field(repr=True, default=Ada(0))
    signing_key: Optional[SigningKey] = field(repr=False, default=None)
    verification_key: Optional[VerificationKey] = field(repr=False, default=None)
    uxtos: Optional[list] = field(repr=False, default_factory=list)
    context: Optional[BlockFrostChainContext] = field(repr=False, default=None)

    def __post_init__(self):

        # convert address into pycardano format
        if isinstance(self.address, str):
            self.address = Address.from_primitive(self.address)

        if isinstance(self.keys_dir, str):
            self.keys_dir = Path(self.keys_dir)

        if self.network == "preprod":
            self._network = Network.TESTNET
        elif self.network == "preview":
            self._network = Network.TESTNET
        else:
            self._network = Network.MAINNET

        # if not address was provided, get keys
        if not self.address:
            self._load_or_create_key_pair(stake=self.use_stake)
        # otherwise derive the network from the address provided
        else:
            # check that the given address matches the desired network
            if self._network:
                if self.address.network != self._network:
                    raise ValueError(
                        f"{self._network} does not match the network of the provided address."
                    )

            self._network = self.address.network
            self.signing_key = None
            self.verification_key = None
            self.stake_signing_key = None
            self.stake_verification_key = None

        # try to automatically create blockfrost context
        if not self.context:
            if self.network.lower() == "mainnet" and getenv("BLOCKFROST_ID_MAINNET"):
                self.context = BlockFrostChainContext(
                    getenv("BLOCKFROST_ID_MAINNET"), network=Network.MAINNET
                )
            elif self.network.lower() == "preprod" and getenv("BLOCKFROST_ID_PREPROD"):
                self.context = BlockFrostChainContext(
                    getenv("BLOCKFROST_ID_PREPROD"),
                    network=Network.TESTNET,
                    base_url="https://cardano-preprod.blockfrost.io/api",
                )
            elif self.network.lower() == "preview" and getenv("BLOCKFROST_ID_PREVIEW"):
                self.context = BlockFrostChainContext(
                    getenv("BLOCKFROST_ID_PREVIEW"),
                    network=Network.TESTNET,
                    base_url="https://cardano-preview.blockfrost.io/api",
                )

        logger.info(self.__repr__())

    @property
    def payment_address(self):

        return Address(payment_part=self.address.payment_part, network=self._network)

    @property
    def stake_address(self):

        if self.stake_signing_key or self.address.staking_part:
            return Address(
                staking_part=self.address.staking_part, network=self._network
            )
        else:
            return None

    @property
    def verification_key_hash(self):
        return str(self.address.payment_part)

    @property
    def stake_verification_key_hash(self):
        return str(self.address.staking_part)

    @property
    def tokens(self):
        return self._token_list

    @property
    def tokens_dict(self):
        return self._token_dict

    @property
    def stake_info(self):
        account_info = get_stake_info(self.stake_address, self.context)
        if not account_info:
            logger.warn("Stake address is not registered yet.")
        return account_info

    @property
    def pool_id(self):
        account_info = get_stake_info(self.stake_address, self.context)
        if account_info.get("pool_id"):
            return account_info.get("pool_id")
        else:
            logger.warn("Stake address is not registered yet.")
            return None

    @property
    def withdrawable_amount(self):
        account_info = get_stake_info(self.stake_address, self.context)
        if account_info.get("withdrawable_amount"):
            return Lovelace(int(account_info.get("withdrawable_amount")))
        else:
            logger.warn("Stake address is not registered yet.")
            return Lovelace(0)

    def _load_or_create_key_pair(self, stake=True):
        """Look for a key pair in the keys directory. If not found, create a new key pair."""

        if not self.keys_dir.exists():
            self.keys_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Creating directory {self.keys_dir}.")

        skey_path = self.keys_dir / f"{self.name}.skey"
        vkey_path = self.keys_dir / f"{self.name}.vkey"
        stake_skey_path = self.keys_dir / f"{self.name}.stake.skey"
        stake_vkey_path = self.keys_dir / f"{self.name}.stake.vkey"

        stake_skey = None
        stake_vkey = None

        if skey_path.exists():
            skey = PaymentSigningKey.load(str(skey_path))
            vkey = PaymentVerificationKey.from_signing_key(skey)

            if stake and stake_skey_path.exists():
                stake_skey = PaymentSigningKey.load(str(stake_skey_path))
                stake_vkey = PaymentVerificationKey.from_signing_key(stake_skey)

            logger.info(f"Wallet {self.name} found.")

        else:
            key_pair = PaymentKeyPair.generate()
            key_pair.signing_key.save(str(skey_path))
            key_pair.verification_key.save(str(vkey_path))
            skey = key_pair.signing_key
            vkey = key_pair.verification_key

            logger.info(f"New wallet {self.name} created in {self.keys_dir}.")

        if stake and not stake_skey_path.exists():
            stake_key_pair = StakeKeyPair.generate()
            stake_key_pair.signing_key.save(str(stake_skey_path))
            stake_key_pair.verification_key.save(str(stake_vkey_path))
            stake_skey = stake_key_pair.signing_key
            stake_vkey = stake_key_pair.verification_key
        elif not stake:
            stake_skey_path = None
            stake_vkey_path = None

        self.signing_key = skey
        self.verification_key = vkey
        self.signing_key_path = skey_path
        self.verification_key_path = vkey_path

        self.stake_signing_key = stake_skey
        self.stake_verification_key = stake_vkey
        self.stake_signing_key_path = stake_skey_path
        self.stake_verification_key_path = stake_vkey_path

        if stake:
            self.address = Address(
                vkey.hash(), stake_vkey.hash(), network=self._network
            )
        else:
            self.address = Address(vkey.hash(), network=self._network)

    def _find_context(self, context: Optional[ChainContext] = None):
        """Helper function to ensure that a context is always provided when needed.
        By default, will return `self.context` unless a context variable has been specifically specified.
        """

        if not context and not self.context:
            raise TypeError("Please pass `context` or set Wallet.context.")
        elif not self.context:
            return context
        else:
            return self.context

    def _get_tokens(self):
        """Gather up all tokens across all UTxOs."""

        # loop through the utxos and sum up all tokens
        tokens = {}

        for utxo in self.utxos:

            for script_hash, assets in utxo.output.amount.multi_asset.items():

                policy_id = str(script_hash)

                for asset, amount in assets.items():

                    asset_name = asset.to_primitive().decode("utf-8")

                    if not tokens.get(policy_id):
                        tokens[policy_id] = {}

                    if not tokens[policy_id].get(asset_name):
                        tokens[policy_id][asset_name] = amount
                    else:
                        current_amount = tokens[policy_id][asset_name]
                        tokens[policy_id][asset_name] = current_amount + amount

        # Convert asset dictionary into Tokens
        # find all policies in which the wallet is a signer
        my_policies = {}
        if self.verification_key:
            my_policies = {
                policy.id: policy
                for policy in get_all_policies(self.keys_dir / "policies")
                if self.verification_key.hash() in policy.required_signatures
            }

        token_list = []
        for policy_id, assets in tokens.items():
            for asset, amount in assets.items():
                if policy_id in my_policies.keys():
                    token_list.append(
                        Token(my_policies[policy_id], amount=amount, name=asset)
                    )
                else:
                    token_list.append(
                        Token(
                            TokenPolicy(name=policy_id[:8], policy=policy_id),
                            amount=amount,
                            name=asset,
                        )
                    )

        self._token_dict = tokens
        self._token_list = token_list

    def sync(self, context: Optional[ChainContext] = None):
        """Query the blockchain for all UTxOs associated with this wallet.

        Args:
            context (Optional[ChainContext]): The context to use for the query. Defaults to the wallet's context.

        """

        context = self._find_context(context)

        try:
            self.utxos = context.utxos(str(self.address))
        except Exception as e:
            logger.warning(
                f"Error getting UTxOs. Address has likely not transacted yet. Details: {e}"
            )
            self.utxos = []

        # calculate total ada
        if self.utxos:

            self.lovelace = Lovelace(
                sum([utxo.output.amount.coin for utxo in self.utxos])
            )
            self.ada = self.lovelace.as_ada()

            # add up all the tokens
            self._get_tokens()

            logger.info(
                f"Wallet {self.name} has {len(self.utxos)} UTxOs containing a total of {self.ada} ₳."
            )

        else:
            logger.info(f"Wallet {self.name} has no UTxOs.")

            self.lovelace = Lovelace(0)
            self.ada = Ada(0)

    def get_utxo_creators(self, context: Optional[ChainContext] = None):
        """Get a list of all addresses that created each of the UTxOs in the wallet.

        Args:
            context (Optional[ChainContext]): The context to use for the query. Defaults to the wallet's context.
        """

        context = self._find_context(context)

        for utxo in self.utxos:
            utxo.creator = get_utxo_creator(utxo, context)

    def get_utxo_block_times(self, context: Optional[ChainContext] = None):
        """Get a list of the creation block number for each UTxO in the wallet.

        Args:
            context (Optional[ChainContext]): The context to use for the query. Defaults to the wallet's context.
        """

        context = self._find_context(context)

        for utxo in self.utxos:
            utxo.block_time = get_utxo_block_time(utxo, context)

        self.sort_utxos()

    def sort_utxos(self, by="block_time"):
        """Sort the UTxOs in the wallet by the specified field.

        Args:
            by (str): The field by which to sort UTxOs. Defaults to "block_time".
        """

        if self.utxos:
            if hasattr(self.utxos[0], by):
                self.utxos.sort(key=operator.attrgetter(by))
            else:
                logger.warn(f"Not all utxos have the attribute `{by}`.")

    def get_token_metadata(self, context: Optional[ChainContext] = None):
        """Fetch the on-chain metadata for each token in the wallet.

        Args:
            context (Optional[ChainContext]): The context to use for the query. Defaults to the wallet's context.
        """

        context = self._find_context(context)

        for token in self.tokens:
            token.get_on_chain_metadata(context)

    def sign_data(
        self,
        message: str,
        mode: Literal["payment", "stake"] = "payment",
        attach_cose_key=False,
    ) -> Union[str, dict]:
        """Sign a message with the wallet's private payment or stake keys following CIP-8.
        NOTE: CIP-8 is not yet finalized so this could be changed in the future.

        Args:
            message (str): The message to sign.
            mode (Optional[Literal["payment", "stake"]]): The keys to use for signing. Defaults to "payment".
            attach_cose_key (bool): Whether to attach the COSE key to the signature. Defaults to False.
                At the moment, Eternl currently does not attach the COSE key, while Nami does.

        Returns:
            Union[str, dict]: The signature. If attach_cose_key is True,
                the signature is a dictionary with the signature and the COSE key.
        """

        if mode == "payment":
            signing_key = self.signing_key
        elif mode == "stake":
            if self.stake_signing_key:
                signing_key = self.stake_signing_key
            else:
                raise TypeError(f"Wallet {self.name} does not have stake credentials.")
        else:
            raise TypeError(
                f"Data signing mode must be `payment` or `stake`, not {mode}."
            )

        return sign(
            message,
            signing_key,
            attach_cose_key=attach_cose_key,
            network=self._network,
        )

    def send_ada(
        self,
        to: Union[str, Address],
        amount: Union[Ada, Lovelace],
        utxos: Optional[Union[UTxO, List[UTxO]]] = None,
        **kwargs,
    ) -> str:
        """Create a simple transaction in which Ada is sent to a single recipient.


        Args:
            to (Union[str, Address]): The address to which to send the Ada.
            amount (Union[Ada, Lovelace]): The amount of Ada to send.
            utxos (Optional[Union[UTxO, List[UTxO]]]): The UTxOs to use for the transaction.
                By default all wallet UTxOs are considered.
            message (Optional[Union[str, List[str]]]): Optional message to include in the transaction (CIP-20).
            await_confirmation (Optional[bool]): Whether to wait for the transaction to be confirmed. Defaults to False.
            context (Optional[ChainContext]): The context to use for the query. Defaults to the wallet's context.

        Returns:
            str: The transaction ID.
        """

        # streamline inputs, use either specific utxos or all wallet utxos
        if utxos:
            if isinstance(utxos, UTxO):
                inputs = [utxos]
            else:
                inputs = utxos
        else:
            inputs = [self]

        return self.transact(inputs=inputs, outputs=[Output(to, amount)], **kwargs)

    def send_utxo(
        self, to: Union[str, Address], utxos: Union[UTxO, List[UTxO]], **kwargs
    ) -> str:
        """Send all of the contents (ADA and tokens) of specified UTxO(s) to a single recipient.

        Args:
            to (Union[str, Address]): The address to which to send the UTxO contents.
            utxos (Optional[Union[UTxO, List[UTxO]]]): The UTxO(s) to use for the transaction.

        Returns:
            str: The transaction ID.
        """

        return self.transact(inputs=utxos, change_address=to, **kwargs)

    def empty_wallet(
        self,
        to: Union[str, Address],
        **kwargs,
    ) -> str:

        """Send all of the contents (ADA and tokens) of the wallet to a single recipient.
        The current wallet will be left completely empty

        Args:
            to (Union[str, Address]): The address to which to send the entire contents of the wallet.

        Returns:
            str: The transaction ID.
        """

        return self.transact(inputs=self.utxos, change_address=to, **kwargs)

    def delegate(
        self,
        pool_hash: Union[PoolKeyHash, str],
        register: Optional[bool] = True,
        amount: Optional[Union[Ada, Lovelace]] = Lovelace(2000000),
        utxos: Optional[Union[UTxO, List[UTxO]]] = None,
        **kwargs,
    ) -> str:
        """Delegate the current wallet to a pool.

        Args:
            pool_hash (Union[PoolKeyHash, str]): The hash of the pool to which to delegate.
            register (Optional[bool]): Whether to register the pool with the network. Defaults to True.
                If True, this will skip registration if the wallet is already registered.
            amount (Optional[Union[Ada, Lovelace]]): The amount of Ada to attach to the delegation transaction.
                Defaults to 2 Ada.
            await_confirmation (Optional[bool]): Whether to wait for the transaction to be confirmed. Defaults to False.
            context (Optional[ChainContext]): The context to use for the query. Defaults to the wallet's context.

        Returns:
            str: The transaction ID.
        """

        # streamline inputs
        if not self.stake_address:
            raise ValueError("This wallet does not have staking keys.")

        # streamline inputs, use either specific utxos or all wallet utxos
        if utxos:
            if isinstance(utxos, UTxO):
                inputs = [utxos]
            else:
                inputs = utxos
        else:
            inputs = [self]

        # check registration, do not register if already registered
        active = self.stake_info.get("active")
        if register:
            register = not active
        elif not active:
            raise ValueError(
                "Cannot delegate to a pool. This wallet is not yet registered. Try again with register=True."
            )

        return self.transact(
            inputs=inputs,
            outputs=Output(self, amount),
            stake_registration=register,
            delegations=pool_hash,
            **kwargs,
        )

    def withdraw_rewards(
        self,
        withdrawal_amount: Optional[Union[Ada, Lovelace]] = None,
        output_amount: Optional[Union[Ada, Lovelace]] = Lovelace(1000000),
        **kwargs,
    ) -> str:
        """Withdraw staking rewards.

        Args:
            withdrawal_amount (Optional[Union[Ada, Lovelace]]): The amount of Ada to withdraw.
                If not set, defaults to the entire rewards balance.
            output_amount (Optional[Union[Ada, Lovelace]]): Amount of ADA to attach to the withdrawal transaction.
                Defaults to 1 ADA which is generally a safe minimum amount to use.
            await_confirmation (Optional[bool]): Whether to wait for the transaction to be confirmed. Defaults to False.
            context (Optional[ChainContext]): The context to use for the query. Defaults to the wallet's context.

        Returns:
            str: The transaction ID.
        """

        # streamline inputs
        if not self.stake_address:
            raise ValueError("This wallet does not have staking keys.")

        if not withdrawal_amount:
            # automatically detect rewards:
            withdrawal_amount = self.withdrawable_amount

        if not withdrawal_amount:
            raise ValueError("No rewards to withdraw.")

        return self.transact(
            inputs=[self],
            outputs=Output(self, output_amount),
            withdrawals={self: withdrawal_amount},
            **kwargs,
        )

    def mint_tokens(
        self,
        to: Union[str, Address],
        mints: Union[Token, List[Token]],
        amount: Optional[Union[Ada, Lovelace]] = None,
        utxos: Optional[Union[UTxO, List[UTxO]]] = None,
        **kwargs,
    ):
        """Mints (or burns) tokens of a policy owned by a user wallet. To attach metadata,
        set it in Token class directly.

        Burn tokens by setting Token class amount to a negative value or using burn_tokens directly.

        Args:
            to (Union[str, Address]): The address to which to send the newly minted tokens.
            mints (Union[Token, List[Token]]): The token(s) to mint/burn.
                Set metadata and quantity directly in the Token class.
            amount (Optional[Union[Ada, Lovelace]]): The amount of Ada to attach to the transaction.
                If not set, the minimum amount will be calculated automatically.
            utxos (Optional[Union[UTxO, List[UTxO]]]): The UTxO(s) to use as inputs.
                If not set, the wallet will be queried for the latest UTxO set.

        Returns:
            str: The transaction ID.
        """

        if amount and not issubclass(amount.__class__, Amount):
            raise TypeError(
                "Please provide amount as either `Ada(amount)` or `Lovelace(amount)`."
            )

        if not amount:
            amount = Lovelace(0)

        # streamline inputs, use either specific utxos or all wallet utxos
        if utxos:
            if isinstance(utxos, UTxO):
                inputs = [utxos]
            else:
                inputs = utxos
        else:
            inputs = [self]

        return self.transact(
            inputs=inputs,
            outputs=Output(to, amount, tokens=mints),
            mints=mints,
            **kwargs,
        )

    def burn_tokens(
        self,
        tokens: Union[Token, List[Token]],
        amount: Optional[Union[Ada, Lovelace]] = None,
        utxos: Optional[Union[UTxO, List[UTxO]]] = None,
        **kwargs,
    ):
        """Burns tokens of a policy owned by a user wallet.
        Same as mint_tokens but automatically sets Token class amount to a negative value.

        Args:
            to (Union[str, Address]): The address to which to send the newly minted tokens.
            mints (Union[Token, List[Token]]): The token(s) to mint/burn.
                Set metadata and quantity directly in the Token class.
            amount (Optional[Union[Ada, Lovelace]]): The amount of Ada to attach to the transaction.
                If not provided, the minimum amount will be calculated automatically.
            utxos (Optional[Union[UTxO, List[UTxO]]]): The UTxO(s) to use as inputs.
                If not set, the wallet will be queried for the latest UTxO set.

        Returns:
            str: The transaction ID.
        """

        if amount and not issubclass(amount.__class__, Amount):
            raise TypeError(
                "Please provide amount as either `Ada(amount)` or `Lovelace(amount)`."
            )

        if not amount:
            # attach 1 ADA to burn transactions
            amount = Ada(1)

        # streamline inputs, use either specific utxos or all wallet utxos
        if utxos:
            if isinstance(utxos, UTxO):
                inputs = [utxos]
            else:
                inputs = utxos
        else:
            inputs = [self]

        if not isinstance(tokens, list):
            tokens = [tokens]

        # set token values to negative
        for token in tokens:
            token.amount = -abs(token.amount)

        return self.transact(
            inputs=inputs,
            outputs=Output(self, amount, tokens=tokens),
            mints=tokens,
            **kwargs,
        )

    def transact(
        self,
        inputs: Union[
            "Wallet",
            Address,
            UTxO,
            str,
            List["Wallet"],
            List[Address],
            List[UTxO],
            List[str],
        ],
        outputs: Optional[Union[Output, List[Output]]] = None,
        mints: Optional[Union[Token, List[Token]]] = None,
        signers: Optional[
            Union["Wallet", List["Wallet"], SigningKey, List[SigningKey]]
        ] = None,
        stake_registration: Optional[
            Union[
                bool, "Wallet", Address, str, List[Address], List["Wallet"], List[str]
            ]
        ] = None,
        delegations: Optional[Union[str, dict, PoolKeyHash]] = None,
        withdrawals: Optional[Union[bool, dict]] = None,
        change_address: Optional[Union["Wallet", Address, str]] = None,
        merge_change: Optional[bool] = True,
        message: Optional[Union[str, List[str]]] = None,
        other_metadata=None,
        submit: Optional[bool] = True,
        await_confirmation: Optional[bool] = False,
        context: Optional[ChainContext] = None,
    ) -> str:
        """
        Construct fully manual transactions.

        Args:
            inputs (Union[Wallet, Address, UTxO, str, List[Wallet], List[Address], List[UTxO], List[str]]):
                Inputs to the transaction. If wallets or addresses are provided, they will be queried for UTxOs.
            outputs (Union[Output, List[Output]]): Outputs of the transaction using the Output class.
                Can specify any number of recipients, ADA amounts, and native tokens.
            mints (Union[Token, List[Token]]): The token(s) to mint/burn. Set metadata and quantity here.
            signers (Union[Wallet, List[Wallet], SigningKey, List[SigningKey]]): The wallets
                or keys with which to sign the transaction.
            stake_registration (Union[bool, Wallet, Address, str, List[Address], List["Wallet"], List[str]]):
                Wallets or addresses to register.
            delegations (Union[str, dict, PoolKeyHash]): The hash of the pool to delegate to.
                To delegate to multiple wallets, provide a dict of the form {wallet/address: PoolHash}.
            withdrawals (Union[bool, dict]): Set the rewards to withdraw. Set to True to withdraw
                all rewards from the current wallet. To withdraw a specific amount from one or more wallets,
                provide a dict of {wallet/address: Amount}, where Amount is an amount of Lovelace(), Ada().
                Use True or "all" to withdraw all available rewards from each specified wallet.
            change_address (Union["Wallet", Address, str]): The wallet or address to send change to.
            merge_change (bool): Whether to merge change into any Output whose address matches the change_address.
                True by default.
            message (Union[str, List[str]]): A message to include in the transaction.
            other_metadata (dict): Any other metadata to include in the transaction.
            submit (bool): Whether to submit the transaction to the network. Defaults to True.
                If False, return the signed transaction CBOR.
            await_confirmation (bool): Whether to wait for the transaction to be confirmed. Defaults to False.
            context (ChainContext): The context to use for the transaction. Defaults to the default context.

        Returns:
            str: The transaction ID if submit is True, otherwise the signed transaction CBOR.
        """

        # streamline inputs
        context = self._find_context(context)

        if not isinstance(inputs, list):
            inputs = [inputs]

        if outputs and not isinstance(outputs, list):
            outputs = [outputs]

        if mints and not isinstance(mints, list):
            mints = [mints]
        elif not mints:
            mints = []

        if (
            stake_registration
            and not isinstance(stake_registration, list)
            and not isinstance(stake_registration, bool)
        ):
            stake_registration = [stake_registration]
        elif not stake_registration:
            stake_registration = []

        if signers and not isinstance(signers, list):
            signers = [signers]
        elif not signers:
            signers = []

        if not change_address:
            change_address = self.address
        else:
            if isinstance(change_address, str):
                change_address = Address.from_primitive(change_address)
            elif not isinstance(change_address, Address):
                change_address = change_address.address

        if other_metadata is None:
            other_metadata = {}

        all_metadata = {}

        # sort out mints
        mints_dict = {}
        mint_metadata = {}
        native_scripts = []
        for token in mints:
            if isinstance(token.policy, NativeScript):
                policy_hash = token.policy.hash()
            elif isinstance(token.policy, TokenPolicy):
                policy_hash = ScriptHash.from_primitive(token.policy_id)
            else:
                policy_hash = None

            policy_id = str(policy_hash)

            if not mints_dict.get(policy_hash):
                mints_dict[policy_hash] = {}

                if isinstance(token.policy, NativeScript):
                    native_scripts.append(token.policy)
                else:
                    native_scripts.append(token.policy.policy)

            mints_dict[policy_hash][token.name] = token
            if token.metadata and token.amount > 0:
                if not mint_metadata.get(policy_id):
                    mint_metadata[policy_id] = {}
                mint_metadata[policy_id][token.name] = token.metadata

        mint_multiasset = MultiAsset()
        all_assets = MultiAsset()

        for policy_hash, tokens in mints_dict.items():

            mint_assets = Asset()
            assets = Asset()
            for token in tokens.values():
                assets[AssetName(token.bytes_name)] = int(token.amount)

                if token.amount > 0:
                    mint_assets[AssetName(token.bytes_name)] = int(token.amount)

            if mint_assets:
                mint_multiasset[policy_hash] = mint_assets
            all_assets[policy_hash] = assets

        # create mint metadata
        if mint_metadata:
            all_metadata[721] = mint_metadata

        # add message
        if message:
            all_metadata[674] = format_message(message)

        # add custom metadata
        if other_metadata:
            for k, v in other_metadata.items():
                check_metadata(v)
                all_metadata[k] = v

        # Place metadata in AuxiliaryData, the format acceptable by a transaction.
        if all_metadata:
            auxiliary_data = AuxiliaryData(
                AlonzoMetadata(metadata=Metadata(all_metadata))
            )
        else:
            auxiliary_data = AuxiliaryData(Metadata())

        # create stake registrations, delegations
        certificates = []
        if stake_registration:  # add registrations
            if isinstance(stake_registration, bool):
                # register current wallet
                stake_credential = StakeCredential(self.stake_verification_key.hash())
                certificates.append(StakeRegistration(stake_credential))
                if self.stake_signing_key not in signers:
                    signers.append(self.stake_signing_key)
            else:
                for stake in stake_registration:
                    if isinstance(stake, str):
                        stake_hash = Address.from_primitive(stake).staking_part
                    elif isinstance(stake, self.__class__):
                        stake_hash = self.stake_verification_key.hash()
                    else:
                        stake_hash = stake.staking_part
                    stake_credential = StakeCredential(stake_hash)
                    certificates.append(StakeRegistration(stake_credential))
        if delegations:  # add delegations
            if isinstance(delegations, str):  # register current wallet
                pool_hash = PoolKeyHash(bytes.fromhex(delegations))
                stake_credential = StakeCredential(self.stake_verification_key.hash())
                certificates.append(
                    StakeDelegation(stake_credential, pool_keyhash=pool_hash)
                )
                if self.stake_signing_key not in signers:
                    signers.append(self.stake_signing_key)
            elif isinstance(delegations, PoolKeyHash):  # register current wallet
                stake_credential = StakeCredential(self.stake_verification_key.hash())
                certificates.append(
                    StakeDelegation(stake_credential, pool_keyhash=delegations)
                )
            else:
                for key, value in delegations:
                    # get stake hash from key
                    if isinstance(key, str):
                        stake_hash = Address.from_primitive(key).staking_part
                    elif isinstance(key, self.__class__):
                        stake_hash = self.stake_verification_key.hash()
                    else:
                        stake_hash = key.staking_part

                    # get pool hash from value:
                    if isinstance(value, str):
                        pool_hash = PoolKeyHash(bytes.fromhex(value))
                    else:
                        pool_hash = value

                    stake_credential = StakeCredential(stake_hash)
                    certificates.append(
                        StakeDelegation(stake_credential, pool_keyhash=pool_hash)
                    )

        # withdrawals
        withdraw = {}
        if withdrawals and isinstance(withdrawals, bool):  # withdraw current wallet
            withdraw[
                self.stake_address.to_primitive()
            ] = self.withdrawable_amount.lovelace
            if self.stake_signing_key not in signers:
                signers.append(self.stake_signing_key)
        elif isinstance(withdrawals, dict):
            for key, value in withdrawals.items():
                if isinstance(key, Address):
                    stake_address = key
                elif isinstance(key, self.__class__):
                    stake_address = key.stake_address
                else:
                    stake_address = Address.from_primitive(key)

                if isinstance(value, Amount):
                    withdrawal_amount = value
                elif isinstance(value, bool) or value == "all":  # withdraw all
                    account_info = get_stake_info(stake_address, self.context)
                    if account_info.get("withdrawable_amount"):
                        withdrawal_amount = Lovelace(
                            int(account_info.get("withdrawable_amount"))
                        )
                    else:
                        logger.warn(
                            f"Stake address {stake_address} is not registered yet."
                        )
                        withdrawal_amount = Lovelace(0)
                else:
                    withdrawal_amount = Lovelace(0)

                withdraw[
                    stake_address.staking_part.to_primitive()
                ] = withdrawal_amount.as_lovelace().amount

        # build the transaction
        builder = TransactionBuilder(context)

        # add transaction inputs
        for input_thing in inputs:
            if isinstance(input_thing, Address) or isinstance(input_thing, str):
                builder.add_input_address(input_thing)
            elif isinstance(input_thing, Wallet):
                builder.add_input_address(input_thing.address)
            elif isinstance(input_thing, UTxO):
                builder.add_input(input_thing)

        # set builder ttl to the min of the included policies
        if mints:
            builder.ttl = min(
                [TokenPolicy("", policy).expiration_slot for policy in native_scripts]
            )

            builder.mint = all_assets
            builder.native_scripts = native_scripts

        if all_metadata:
            builder.auxiliary_data = auxiliary_data

        # format tokens and lovelace of outputs
        if outputs:
            for output in outputs:
                multi_asset = {}
                if output.tokens:
                    multi_asset = MultiAsset()
                    output_policies = {}
                    for token in output.tokens:
                        if not output_policies.get(token.policy_id):
                            output_policies[token.policy_id] = {}

                        if output_policies[token.policy_id].get(token.name):
                            output_policies[token.policy_id][token.name] += token.amount
                        else:
                            output_policies[token.policy_id][token.name] = token.amount

                    for policy, token_info in output_policies.items():

                        asset = Asset()

                        for token_name, token_amount in token_info.items():
                            asset[AssetName(str.encode(token_name))] = token_amount

                        multi_asset[ScriptHash.from_primitive(policy)] = asset

                if not output.amount.lovelace:  # Calculate min lovelace if necessary
                    output.amount = Lovelace(
                        min_lovelace(
                            context=context,
                            output=TransactionOutput(
                                output.address, Value(1000000, mint_multiasset)
                            ),
                        )
                    )

                builder.add_output(
                    TransactionOutput(
                        output.address, Value(output.amount.lovelace, multi_asset)
                    )
                )

        # add registration + delegation certificates
        if certificates:
            builder.certificates = certificates

        # add withdrawals
        if withdraw:
            builder.withdrawals = Withdrawals(withdraw)

        if signers:
            signing_keys = []
            for signer in signers:
                if isinstance(signer, self.__class__):
                    signing_keys.append(signer.signing_key)
                else:
                    signing_keys.append(signer)

            if self.signing_key not in signing_keys:
                signing_keys.insert(0, self.signing_key)

        else:
            signing_keys = [self.signing_key]

        signed_tx = builder.build_and_sign(
            signing_keys, change_address=change_address, merge_change=merge_change
        )

        if not submit:
            return signed_tx.to_cbor()

        context.submit_tx(signed_tx.to_cbor())

        if await_confirmation:
            _ = wait_for_confirmation(str(signed_tx.id), self.context)
            self.sync()

        return str(signed_tx.id)


# Utility and Helper functions
@blockfrost_only
def get_utxo_creator(utxo: UTxO, context: ChainContext) -> Address:
    """Fetch the creator of a UTxO.
    If there are multiple input UTxOs, the creator is the first one.

    Args:
        utxo (UTxO): The UTxO to get the creator of.
        context (ChainContext): The context to use for the query. For now must be BlockFrost.

    Returns:
        Address: The creator of the UTxO.
    """
    utxo_creator = (
        context.api.transaction_utxos(str(utxo.input.transaction_id)).inputs[0].address
    )

    return utxo_creator


@blockfrost_only
def get_utxo_block_time(utxo: UTxO, context: ChainContext) -> int:
    """Get the block time at which a UTxO was created.

    Args:
        utxo (UTxO): The UTxO to get the block time of.
        context (ChainContext): The context to use for the query. For now must be BlockFrost.

    Returns:
        int: The block time at which the UTxO was created.

    """
    block_time = context.api.transaction(str(utxo.input.transaction_id)).block_time

    return block_time


@blockfrost_only
def get_stake_info(stake_address: Union[str, Address], context: ChainContext) -> dict:
    """Get the stake info of a stake address from Blockfrost.
    For more info see: https://docs.blockfrost.io/#tag/Cardano-Accounts/paths/~1accounts~1{stake_address}/get

    Args:
        stake_address (Union[str, Address]): The stake address to get the stake info of.
        context (ChainContext): The context to use for the query. For now must be BlockFrost.

    Returns:
        dict: Info regarding the given stake address.
    """

    if isinstance(stake_address, str):
        stake_address = Address.from_primitive(stake_address)

    if not stake_address.staking_part:
        raise TypeError(f"Address {stake_address} has no staking part.")

    try:
        return context.api.accounts(str(stake_address)).to_dict()
    except ApiError:
        return {}


def get_stake_address(address: Union[str, Address]) -> Address:
    """Get the stake address of any given address.

    Args:
        address (Union[str, Address]): The address to get the stake address of.

    Returns:
        Address: The stake address of the given address.
    """
    if isinstance(address, str):
        address = Address.from_primitive(address)

    return Address.from_primitive(
        bytes.fromhex(f"e{address.network.value}" + str(address.staking_part))
    )


def format_message(message: Union[str, List[str]]) -> dict:
    """Format a metadata message according to CIP-20

    Args:
        message (Union[str, List[str]]): The message to format.

    Returns:
        dict: The message formatted properly to attach to a transaction.
    """

    if isinstance(message, str):
        message = [message[i : i + 64] for i in range(0, len(message), 64)]

    for line in message:
        if len(line) > 64:
            raise MetadataFormattingException(
                f"Message field is too long (> 64 characters): {line}\nConsider splitting into an array of shorter "
                f"strings. "
            )
        if not isinstance(line, str):
            raise MetadataFormattingException(
                f"Message Field must be of type `str`: {line}"
            )

    return {"msg": message}


def check_metadata(to_check: Union[dict, list, str], top_level: bool = False):
    """Screen any given input metadata for potential issues.


    Used recursively to check inside all dicts and lists of the metadata.

    Args:
        to_check (Union[dict, list, str]): The metadata to check.
        top_level (bool): Whether this is the top level of the metadata.
            Set to True only for the full metadata dictionary in order to check that it is JSON serializable.
    """

    if isinstance(to_check, dict):
        for key, value in to_check.items():

            if len(str(key)) > 64:
                raise MetadataFormattingException(
                    f"Metadata key is too long (> 64 characters): {key}\nConsider splitting into an array of shorter "
                    f"strings. "
                )

            if isinstance(value, dict) or isinstance(value, list):
                check_metadata(to_check=value)

            elif len(str(value)) > 64:
                raise MetadataFormattingException(
                    f"Metadata field is too long (> 64 characters): {key}: {value}\nConsider splitting into an array "
                    f"of shorter strings. "
                )

    elif isinstance(to_check, list):

        for item in to_check:
            if len(str(item)) > 64:
                raise MetadataFormattingException(
                    f"Metadata field is too long (> 64 characters): {item}\nConsider splitting into an array of "
                    f"shorter strings. "
                )

    elif isinstance(to_check, str):
        if len(to_check) > 64:
            raise MetadataFormattingException(
                f"Metadata field is too long (> 64 characters): {to_check}\nConsider splitting into an array of "
                f"shorter strings. "
            )

    if top_level:
        try:
            json.dumps(to_check)
        except TypeError as e:
            raise MetadataFormattingException(f"Cannot format metadata: {e}")


def list_all_wallets(wallet_path: Union[str, Path] = Path("./priv")) -> List[str]:
    """List all PyCardano wallets in the directory specified by wallet_path.

    Args:
        wallet_path (Union[str, Path]): The path to the directory to list the wallets in.

    Returns:
        List[str]: A list of all names of wallets in the directory.
    """
    if isinstance(wallet_path, str):
        wallet_path = Path(wallet_path)

    wallets = [skey.stem for skey in list(wallet_path.glob("*.skey"))]

    return wallets


def get_all_policies(
    policy_path: Union[str, Path] = Path("./priv/policies")
) -> List[TokenPolicy]:
    """List all policies in the directory specified by policy_path.

    Args:
        policy_path (Union[str, Path]): The path to the directory to list the policies in.

    Returns:
        List[TokenPolicy]: A list of all policies in the directory.
    """
    if isinstance(policy_path, str):
        policy_path = Path(policy_path)

    policies = [TokenPolicy(skey.stem) for skey in list(policy_path.glob("*.script"))]

    return policies


@blockfrost_only
def confirm_tx(tx_id: Union[str, TransactionId], context: ChainContext) -> bool:
    """Confirm that a transaction has been included in a block.

    Args:
        tx_id (Union[str, TransactionId]): The transaction id to check.
        context (ChainContext): The context to use for the query. For now must be BlockFrost.

    Returns:
        bool: Whether the transaction has been included in a block.
    """

    try:
        _ = context.api.transaction(str(tx_id))
        confirmed = True
    except ApiError:
        confirmed = False

    return confirmed


@blockfrost_only
def wait_for_confirmation(
    tx_id: Union[str, TransactionId], context: ChainContext, delay: Optional[int] = 10
) -> bool:
    """Wait for a transaction to be confirmed, checking every `delay` seconds.

    Args:
        tx_id (Union[str, TransactionId]): The transaction id to check.
        context (ChainContext): The context to use for the query. For now must be BlockFrost.
        delay (Optional[int]): The number of seconds to wait between checking the context. Defaults to 10.

    Returns:
        bool: Whether the transaction has been confirmed.
    """

    confirmed = False
    while not confirmed:
        confirmed = confirm_tx(tx_id, context)
        if not confirmed:
            sleep(delay)

    return confirmed


# Exceptions
class MetadataFormattingException(PyCardanoException):
    pass
