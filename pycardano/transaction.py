from dataclasses import dataclass, field
from typing import List, Any, Union

from nacl.hash import blake2b
from nacl.encoding import RawEncoder

from pycardano.address import Address
from pycardano.hash import TransactionHash, DatumHash, AuxiliaryDataHash, ScriptHash, AddrKeyHash, TRANSACTION_HASH_SIZE
from pycardano.network import Network
from pycardano.serialization import ArrayCBORSerializable, MapCBORSerializable, homogenous_list_hook
from pycardano.witness import TransactionWitnessSet


@dataclass
class TransactionInput(ArrayCBORSerializable):

    transaction_id: TransactionHash

    index: int


@dataclass
class TransactionOutput(ArrayCBORSerializable):

    address: Address

    amount: int

    datum_hash: DatumHash = field(default=None, metadata={"optional": True})


@dataclass
class TransactionBody(MapCBORSerializable):

    inputs: List[TransactionInput] = field(
        default_factory=list,
        metadata={"key": 0,
                  "object_hook": homogenous_list_hook(TransactionInput)})

    outputs: List[TransactionOutput] = field(
        default_factory=list,
        metadata={"key": 1,
                  "object_hook": homogenous_list_hook(TransactionOutput)})

    fee: int = field(default=0, metadata={"key": 2})

    ttl: int = field(default=None, metadata={"key": 3, "optional": True})

    # TODO: Add certificate support
    certificates: Any = field(default=None, metadata={"key": 4, "optional": True})

    # TODO: Add reward withdraw support
    withdraws: Any = field(default=None, metadata={"key": 5, "optional": True})

    # TODO: Add proposal update support
    update: Any = field(default=None, metadata={"key": 6, "optional": True})

    auxiliary_data_hash: AuxiliaryDataHash = field(default=None, metadata={"key": 7, "optional": True})

    validity_start: int = field(default=None, metadata={"key": 8, "optional": True})

    # TODO: Add multi-asset minting support
    mint: Any = field(default=None, metadata={"key": 9, "optional": True})

    script_data_hash: ScriptHash = field(default=None, metadata={"key": 11, "optional": True})

    collateral: List[TransactionInput] = field(
        default=None,
        metadata={"key": 13,
                  "optional": True,
                  "object_hook": homogenous_list_hook(TransactionInput)})

    required_signers: List[AddrKeyHash] = field(
        default=None,
        metadata={"key": 14,
                  "optional": True,
                  "object_hook": homogenous_list_hook(AddrKeyHash)})

    network_id: Network = field(default=None, metadata={"key": 15, "optional": True})

    def hash(self) -> bytes:
        return blake2b(self.to_cbor(encoding="bytes"), TRANSACTION_HASH_SIZE, encoder=RawEncoder)


@dataclass
class Transaction(ArrayCBORSerializable):

    transaction_body: TransactionBody

    transaction_witness_set: TransactionWitnessSet

    valid: bool = True

    # TODO: Add axuiliary data support
    auxiliary_data: Union[Any, type(None)] = None
