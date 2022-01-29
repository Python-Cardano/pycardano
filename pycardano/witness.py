"""Transaction witness."""

from dataclasses import dataclass, field
from typing import Any, List

from pycardano.key import AddressKey
from pycardano.serialization import ArrayCBORSerializable, MapCBORSerializable, list_hook


@dataclass(repr=False)
class VerificationKeyWitness(ArrayCBORSerializable):
    vkey: AddressKey
    signature: bytes


@dataclass(repr=False)
class TransactionWitnessSet(MapCBORSerializable):
    vkey_witnesses: List[VerificationKeyWitness] = \
        field(default=None,
              metadata={"optional": True,
                        "key": 0,
                        "object_hook": list_hook(VerificationKeyWitness)})

    # TODO: Add native script support
    native_scripts: List[Any] = field(default=None,
                                      metadata={"optional": True,
                                                "key": 1})

    # TODO: Add bootstrap witness (byron) support
    bootstrap_witness: List[Any] = field(default=None,
                                         metadata={"optional": True,
                                                   "key": 2})

    # TODO: Add plutus script support
    plutus_script: List[Any] = field(default=None,
                                     metadata={"optional": True,
                                               "key": 3})

    plutus_data: List[Any] = field(default=None,
                                   metadata={"optional": True,
                                             "key": 4})

    redeemer: List[Any] = field(default=None,
                                metadata={"optional": True,
                                          "key": 5})
