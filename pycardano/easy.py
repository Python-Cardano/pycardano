from dataclasses import dataclass, field
import datetime
import json
import logging
from os import getenv
from pathlib import Path
from time import sleep
from typing import List, Literal, Optional, Union
from pycardano.address import Address

from pycardano.backend.base import ChainContext
from pycardano.backend.blockfrost import BlockFrostChainContext
from pycardano.exception import PyCardanoException
from pycardano.hash import TransactionId
from pycardano.key import (
    PaymentKeyPair,
    PaymentSigningKey,
    PaymentVerificationKey,
    SigningKey,
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
)
from pycardano.txbuilder import TransactionBuilder
from pycardano.utils import min_lovelace


# set logging level to info
logger.setLevel(logging.INFO)


class Amount:
    """Base class for Cardano currency amounts."""

    def __init__(self, amount=0, amount_type="lovelace"):

        self._amount = amount
        self._amount_type = amount_type

        if self._amount_type == "lovelace":
            self.lovelace = int(self._amount)
            self.ada = self._amount / 1000000
        else:
            self.lovelace = int(self._amount * 1000000)
            self.ada = self._amount

        self._amount_dict = {"lovelace": self.lovelace, "ada": self.ada}

    @property
    def amount(self):

        if self._amount_type == "lovelace":
            return self.lovelace
        else:
            return self.ada

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
        elif isinstance(other, Amount):
            return self.__class__(self.amount + other[self._amount_type])
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
            return self.__class__(self.amount - other)
        elif isinstance(other, Amount):
            return self.__class__(self.amount - other[self._amount_type])
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
        elif isinstance(other, Amount):
            return self.__class__(self.amount * other[self._amount_type])
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
            return self.__class__(self.amount / other)
        elif isinstance(other, Amount):
            return self.__class__(self.amount / other[self._amount_type])
        else:
            raise TypeError("Must compute with a number or another Cardano amount")

    def __rfloordiv__(self, other):
        if isinstance(other, (int, float)):
            return self.__class__(self.amount // other)
        elif isinstance(other, Amount):
            return self.__class__(self.amount // other[self._amount_type])
        else:
            raise TypeError("Must compute with a number or another Cardano amount")

    def __neg__(self):
        return self.__class__(-self.amount)

    def __pos__(self):
        return self.__class__(+self.amount)

    def __abs__(self):
        return self.__class__(abs(self.amount))

    def __round__(self):
        return self.__class__(round(self.amount))


class Lovelace(Amount):
    def __init__(self, amount=0):
        super().__init__(amount, "lovelace")

    def __repr__(self):
        return f"Lovelace({self.lovelace})"

    def as_lovelace(self):
        return Lovelace(self.lovelace)

    def as_ada(self):
        return Ada(self.ada)


class Ada(Amount):
    def __init__(self, amount=0):
        super().__init__(amount, "ada")

    def __repr__(self):
        return f"Ada({self.ada})"

    def as_lovelace(self):
        return Lovelace(self.lovelace)

    def ad_ada(self):
        return Ada(self.ada)


@dataclass(unsafe_hash=True)
class TokenPolicy:
    name: str
    policy: Optional[Union[NativeScript, dict]] = field(repr=False, default=None)
    policy_dir: Optional[Union[str, Path]] = field(
        repr=False, default=Path("./priv/policies")
    )

    def __post_init__(self):

        # streamline inputs
        if isinstance(self.policy_dir, str):
            self.policy_dir = Path(self.policy_dir)

        if not self.policy_dir.exists():
            self.policy_dir.mkdir(parents=True, exist_ok=True)

        # look for the policy
        if Path(self.policy_dir / f"{self.name}.script").exists():
            with open(
                Path(self.policy_dir / f"{self.name}.script"), "r"
            ) as policy_file:
                self.policy = NativeScript.from_dict(json.load(policy_file))

        elif isinstance(self.policy, dict):
            self.policy = NativeScript.from_dict(self.policy)

    @property
    def policy_id(self):

        if self.policy:
            return str(self.policy.hash())

    @property
    def expiration_slot(self):
        """Get the expiration slot for a simple minting policy,
        like one generated by generate_minting_policy
        """

        if self.policy:
            scripts = getattr(self.policy, "native_scripts", None)

            if scripts:
                for script in scripts:
                    if script._TYPE == 5:
                        return script.after

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
                        datetime.datetime.utc
                    )
                else:
                    time_until_expiration = expiration - datetime.datetime.now()

                last_block_slot = context.last_block_slot

                must_before_slot = InvalidHereAfter(
                    last_block_slot + int(time_until_expiration.total_seconds())
                )

            policy = ScriptAll(pub_keys + [must_before_slot])

        else:
            policy = ScriptAll(pub_keys)

        # save policy to file
        with open(script_filepath, "w") as script_file:
            json.dump(policy.to_dict(), script_file, indent=4)

        self.policy = policy

    @staticmethod
    def _get_pub_key_hash(signer=Union["Wallet", Address]):

        if hasattr(signer, "verification_key"):
            return signer.verification_key.hash()
        elif isinstance(signer, Address):
            return str(signer.payment_part)
        else:
            raise TypeError("Input signer must be of type Wallet or Address.")


@dataclass(unsafe_hash=True)
class Token:
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
                        f"Metadata key is too long (> 64 characters): {key}\nConsider splitting into an array of shorter strings."
                    )

                if isinstance(value, dict) or isinstance(value, list):
                    self._check_metadata(to_check=value)

                elif len(str(value)) > 64:
                    raise MetadataFormattingException(
                        f"Metadata field is too long (> 64 characters): {key}: {value}\nConsider splitting into an array of shorter strings."
                    )

        elif isinstance(to_check, list):

            for item in to_check:
                if len(str(item)) > 64:
                    raise MetadataFormattingException(
                        f"Metadata field is too long (> 64 characters): {item}\nConsider splitting into an array of shorter strings."
                    )

        elif isinstance(to_check, str):
            if len(to_check) > 64:
                raise MetadataFormattingException(
                    f"Metadata field is too long (> 64 characters): {item}\nConsider splitting into an array of shorter strings."
                )

        if top_level:
            try:
                json.dumps(to_check)
            except TypeError as e:
                raise MetadataFormattingException(f"Cannot format metadata: {e}")

    @property
    def bytes_name(self):
        return bytes(self.name.encode("utf-8"))


@dataclass
class Wallet:
    """An address for which you own the keys or will later create them."""

    name: str
    address: Optional[Union[Address, str]] = None
    keys_dir: Optional[Union[str, Path]] = field(repr=False, default=Path("./priv"))
    network: Optional[Literal["mainnet", "testnet"]] = "mainnet"

    # generally added later
    lovelace: Optional[Lovelace] = field(repr=False, default=Lovelace(0))
    ada: Optional[Ada] = field(repr=True, default=Ada(0))
    signing_key: Optional[SigningKey] = field(repr=False, default=None)
    verification_key: Optional[VerificationKey] = field(repr=False, default=None)
    uxtos: Optional[list] = field(repr=False, default_factory=list)
    policy: Optional[NativeScript] = field(repr=False, default=None)
    context: Optional[BlockFrostChainContext] = field(repr=False, default=None)

    def __post_init__(self):

        # convert address into pycardano format
        if isinstance(self.address, str):
            self.address = Address.from_primitive(self.address)

        if isinstance(self.keys_dir, str):
            self.keys_dir = Path(self.keys_dir)

        # if not address was provided, get keys
        if not self.address:
            self._load_or_create_key_pair()
        # otherwise derive the network from the address provided
        else:
            self.network = self.address.network.name.lower()

        # try to automatically create blockfrost context
        if not self.context:
            if self.network.lower() == "mainnet":
                if getenv("BLOCKFROST_ID"):
                    self.context = BlockFrostChainContext(getenv("BLOCKFROST_ID"))
            elif getenv("BLOCKFROST_ID_TESTNET"):
                self.context = BlockFrostChainContext(getenv("BLOCKFROST_ID_TESTNET"))

        if self.context:
            self.query_utxos()

        logger.info(self.__repr__())

    def query_utxos(self, context: Optional[ChainContext] = None):

        context = self._find_context(context)

        try:
            self.utxos = context.utxos(str(self.address))
        except Exception as e:
            logger.debug(
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

            logger.debug(
                f"Wallet {self.name} has {len(self.utxos)} UTxOs containing a total of {self.ada} ₳."
            )

        else:
            logger.debug(f"Wallet {self.name} has no UTxOs.")

            self.lovelace = Lovelace(0)
            self.ada = Ada(0)

    @property
    def stake_address(self):

        if isinstance(self.address, str):
            address = Address.from_primitive(self.address)
        else:
            address = self.address

        return Address.from_primitive(
            bytes.fromhex(f"e{address.network.value}" + str(address.staking_part))
        )

    @property
    def verification_key_hash(self):
        return str(self.address.payment_part)

    @property
    def tokens(self):
        return self._token_list

    @property
    def tokens_dict(self):
        return self._token_dict

    def _load_or_create_key_pair(self):

        if not self.keys_dir.exists():
            self.keys_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Creating directory {self.keys_dir}.")

        skey_path = self.keys_dir / f"{self.name}.skey"
        vkey_path = self.keys_dir / f"{self.name}.vkey"

        if skey_path.exists():
            skey = PaymentSigningKey.load(str(skey_path))
            vkey = PaymentVerificationKey.from_signing_key(skey)
            logger.info(f"Wallet {self.name} found.")
        else:
            key_pair = PaymentKeyPair.generate()
            key_pair.signing_key.save(str(skey_path))
            key_pair.verification_key.save(str(vkey_path))
            skey = key_pair.signing_key
            vkey = key_pair.verification_key
            logger.info(f"New wallet {self.name} created in {self.keys_dir}.")

        self.signing_key = skey
        self.verification_key = vkey

        self.address = Address(vkey.hash(), network=Network[self.network.upper()])

    def _find_context(self, context: Optional[ChainContext] = None):
        """Helper function to ensure that a context is always provided when needed.
        By default will return self.context unless a context variable has been specifically specified.
        """

        if not context and not self.context:
            raise TypeError("Please pass `context` or set Wallet.context.")
        elif not self.context:
            return context
        else:
            return self.context

    def _get_tokens(self):

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
        token_list = []
        for policy_id, assets in tokens.items():
            for asset, amount in assets.items():
                token_list.append(Token(policy_id, amount=amount, name=asset))

        self._token_dict = tokens
        self._token_list = token_list

    def get_utxo_creators(self, context: Optional[ChainContext] = None):

        context = self._find_context(context)

        for utxo in self.utxos:
            utxo.creator = get_utxo_creator(utxo, context)

    def send_ada(
        self,
        to: Union[str, Address],
        amount: Union[Ada, Lovelace],
        utxos: Optional[Union[UTxO, List[UTxO]]] = [],
        message: Optional[Union[str, List[str]]] = None,
        await_confirmation: Optional[bool] = False,
        context: Optional[ChainContext] = None,
    ):

        context = self._find_context(context)

        # streamline inputs
        if isinstance(to, str):
            to = Address.from_primitive(to)

        if not isinstance(amount, Ada) and not isinstance(amount, Lovelace):
            raise TypeError(
                "Please provide amount as either `Ada(amount)` or `Lovelace(amount)`."
            )

        if utxos:
            if isinstance(utxos, UTxO):
                utxos = [utxos]

        builder = TransactionBuilder(context)

        builder.add_input_address(self.address)

        if utxos:
            for utxo in utxos:
                builder.add_input(utxo)

        builder.add_output(
            TransactionOutput(to, Value.from_primitive([amount.as_lovelace().amount]))
        )

        if message:
            metadata = {674: format_message(message)}
            builder.auxiliary_data = AuxiliaryData(
                AlonzoMetadata(metadata=Metadata(metadata))
            )

        signed_tx = builder.build_and_sign(
            [self.signing_key], change_address=self.address
        )

        context.submit_tx(signed_tx.to_cbor())

        if await_confirmation:
            confirmed = wait_for_confirmation(str(signed_tx.id), self.context)
            self.query_utxos()

        return str(signed_tx.id)

    def send_utxo(
        self,
        to: Union[str, Address],
        utxos: Union[UTxO, List[UTxO]],
        message: Optional[Union[str, List[str]]] = None,
        await_confirmation: Optional[bool] = False,
        context: Optional[ChainContext] = None,
    ):

        # streamline inputs
        context = self._find_context(context)

        if isinstance(to, str):
            to = Address.from_primitive(to)

        if isinstance(utxos, UTxO):
            utxos = [utxos]

        builder = TransactionBuilder(context)

        builder.add_input_address(self.address)

        for utxo in utxos:
            builder.add_input(utxo)

        if message:
            metadata = {674: format_message(message)}
            builder.auxiliary_data = AuxiliaryData(
                AlonzoMetadata(metadata=Metadata(metadata))
            )

        signed_tx = builder.build_and_sign(
            [self.signing_key],
            change_address=to,
            merge_change=True,
        )

        context.submit_tx(signed_tx.to_cbor())

        if await_confirmation:
            confirmed = wait_for_confirmation(str(signed_tx.id), self.context)
            self.query_utxos()

        return str(signed_tx.id)

    def empty_wallet(
        self,
        to: Union[str, Address],
        message: Optional[Union[str, List[str]]] = None,
        await_confirmation: Optional[bool] = False,
        context: Optional[ChainContext] = None,
    ):

        return self.send_utxo(
            to=to,
            utxos=self.utxos,
            message=message,
            await_confirmation=await_confirmation,
            context=context,
        )

    def mint_tokens(
        self,
        to: Union[str, Address],
        mints: Union[Token, List[Token]],
        amount: Optional[Union[Ada, Lovelace]] = None,
        utxos: Optional[Union[UTxO, List[UTxO]]] = [],
        other_signers: Optional[Union["Wallet", List["Wallet"]]] = [],
        message: Optional[Union[str, List[str]]] = None,
        await_confirmation: Optional[bool] = False,
        context: Optional[ChainContext] = None,
    ):
        """Under construction."""

        # streamline inputs
        context = self._find_context(context)

        if isinstance(to, str):
            to = Address.from_primitive(to)

        if amount and not isinstance(amount, Ada) and not isinstance(amount, Lovelace):
            raise TypeError(
                "Please provide amount as either `Ada(amount)` or `Lovelace(amount)`."
            )

        if not isinstance(mints, list):
            mints = [mints]

        if isinstance(utxos, UTxO):
            utxos = [utxos]

        if not isinstance(other_signers, list):
            other_signers = [other_signers]

        # sort assets by policy_id
        mints_dict = {}
        mint_metadata = {}
        native_scripts = []
        for token in mints:
            if isinstance(token.policy, NativeScript):
                policy_hash = token.policy.hash()
            elif isinstance(token.policy, TokenPolicy):
                policy_hash = token.policy.policy.hash()

            policy_id = str(policy_hash)

            if not mints_dict.get(policy_hash):
                mints_dict[policy_hash] = {}
                mint_metadata[policy_id] = {}

                if isinstance(token.policy, NativeScript):
                    native_scripts.append(token.policy)
                else:
                    native_scripts.append(token.policy.policy)

            mints_dict[policy_hash][token.name] = token
            if token.metadata:
                mint_metadata[policy_id][token.name] = token.metadata

        asset_mints = MultiAsset()

        for policy_hash, tokens in mints_dict.items():

            assets = Asset()
            for token in tokens.values():
                assets[AssetName(token.bytes_name)] = int(token.amount)

            asset_mints[policy_hash] = assets

        # create mint metadata
        mint_metadata = {721: mint_metadata}

        # add message
        if message:
            mint_metadata[674] = format_message(message)

        # Place metadata in AuxiliaryData, the format acceptable by a transaction.
        auxiliary_data = AuxiliaryData(AlonzoMetadata(metadata=Metadata(mint_metadata)))

        # build the transaction
        builder = TransactionBuilder(context)

        # add transaction inputs
        if utxos:
            for utxo in utxos:
                builder.add_input(utxo)

        builder.add_input_address(self.address)

        # set builder ttl to the min of the included policies
        builder.ttl = min(
            [TokenPolicy("", policy).expiration_slot for policy in native_scripts]
        )

        builder.mint = asset_mints
        builder.native_scripts = native_scripts
        builder.auxiliary_data = auxiliary_data

        if not amount:  # sent min amount if none specified
            amount = Lovelace(min_lovelace(Value(0, asset_mints), context))
            print("Min value =", amount)

        builder.add_output(TransactionOutput(to, Value(amount.lovelace, asset_mints)))

        if other_signers:
            signing_keys = [wallet.signing_key for wallet in other_signers] + [
                self.signing_key
            ]
        else:
            signing_keys = [self.signing_key]

        signed_tx = builder.build_and_sign(signing_keys, change_address=self.address)

        print(signed_tx.to_cbor())

        context.submit_tx(signed_tx.to_cbor())

        if await_confirmation:
            confirmed = wait_for_confirmation(str(signed_tx.id), self.context)
            self.query_utxos()

        return str(signed_tx.id)


# helpers
def get_utxo_creator(utxo: UTxO, context: ChainContext):

    if isinstance(context, BlockFrostChainContext):
        utxo_creator = (
            context.api.transaction_utxos(str(utxo.input.transaction_id))
            .inputs[0]
            .address
        )

        return utxo_creator

    else:
        logger.warn(
            "Fetching UTxO creators (sender) is only possible with Blockfrost Chain Context."
        )


def get_stake_address(address: Union[str, Address]):

    if isinstance(address, str):
        address = Address.from_primitive(address)

    return Address.from_primitive(
        bytes.fromhex(f"e{address.network.value}" + str(address.staking_part))
    )


def format_message(message: Union[str, List[str]]):

    if isinstance(message, str):
        message = [message]

    for line in message:
        if len(line) > 64:
            raise MetadataFormattingException(
                f"Message field is too long (> 64 characters): {line}\nConsider splitting into an array of shorter strings."
            )
        if not isinstance(line, str):
            raise MetadataFormattingException(
                f"Message Field must be of type `str`: {line}"
            )

    return {"msg": message}


def list_all_wallets(wallet_path: Union[str, Path] = Path("./priv")):

    if isinstance(wallet_path, str):
        wallet_path = Path(wallet_path)

    wallets = [skey.stem for skey in list(wallet_path.glob("*.skey"))]

    return wallets


def confirm_tx(tx_id: Union[str, TransactionId], context: ChainContext):

    if isinstance(context, BlockFrostChainContext):

        from blockfrost import ApiError

        try:
            transaction_info = context.api.transaction(str(tx_id))
            confirmed = True
        except ApiError:
            confirmed = False
            transaction_info = {}

        return confirmed

    else:
        logger.warn(
            "Confirming transactions is is only possible with Blockfrost Chain Context."
        )


def wait_for_confirmation(
    tx_id: Union[str, TransactionId], context: ChainContext, delay: Optional[int] = 10
):

    if not isinstance(context, BlockFrostChainContext):
        logger.warn(
            "Confirming transactions is is only possible with Blockfrost Chain Context."
        )
        return

    confirmed = False
    while not confirmed:
        confirmed = confirm_tx(tx_id, context)
        if not confirmed:
            sleep(delay)

    return confirmed


# Exceptions
class MetadataFormattingException(PyCardanoException):
    pass
