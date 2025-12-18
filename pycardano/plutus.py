"""Plutus related classes and functions."""

from __future__ import annotations

import inspect
import json
import typing
from dataclasses import dataclass, field, fields
from enum import Enum
from hashlib import sha256
from typing import Any, List, Optional, Type, Union

from cbor2 import CBORTag
from nacl.encoding import RawEncoder
from nacl.hash import blake2b
from typeguard import typechecked

from pycardano.cbor import cbor2
from pycardano.exception import DeserializeException, InvalidArgumentException
from pycardano.hash import DATUM_HASH_SIZE, SCRIPT_HASH_SIZE, DatumHash, ScriptHash
from pycardano.nativescript import NativeScript
from pycardano.serialization import (
    ArrayCBORSerializable,
    ByteString,
    CBORSerializable,
    DictCBORSerializable,
    IndefiniteList,
    Primitive,
    RawCBOR,
    default_encoder,
    limit_primitive_type,
)

__all__ = [
    "CostModels",
    "PLUTUS_V1_COST_MODEL",
    "PLUTUS_V2_COST_MODEL",
    "COST_MODELS",
    "PlutusData",
    "Datum",
    "RedeemerTag",
    "ExecutionUnits",
    "PlutusScript",
    "PlutusV1Script",
    "PlutusV2Script",
    "PlutusV3Script",
    "RawPlutusData",
    "Redeemer",
    "RedeemerKey",
    "RedeemerValue",
    "RedeemerMap",
    "Redeemers",
    "ScriptType",
    "datum_hash",
    "plutus_script_hash",
    "script_hash",
    "Unit",
]


# taken from https://stackoverflow.com/a/13624858
class classproperty(property):
    def __get__(self, owner_self, owner_cls):
        return self.fget(owner_cls)


class CostModels(DictCBORSerializable):
    KEY_TYPE = int
    VALUE_TYPE = dict

    def to_shallow_primitive(self) -> dict:
        result: dict[bytes, Union[typing.List[Any], bytes]] = {}
        for language in sorted(self.keys()):
            cost_model = self[language]
            if language == 0:
                # Due to a bug in the Haskell implementation of ledger, we need to serialize the cost models twice.
                # See:
                # https://github.com/input-output-hk/cardano-ledger/blob/c9512ec56cd9b9ea20adea567649410289da0acc/eras/alonzo/test-suite/cddl-files/alonzo.cddl#L111-L115
                # https://github.com/input-output-hk/cardano-ledger/issues/2512
                l_cbor = cbor2.dumps(language, default=default_encoder)
                cm = IndefiniteList([cost_model[k] for k in sorted(cost_model.keys())])
                result[l_cbor] = cbor2.dumps(cm, default=default_encoder)
            else:
                result[language] = [cost_model[k] for k in cost_model.keys()]
        return result

    @classmethod
    @limit_primitive_type(dict)
    def from_primitive(cls: Type[CostModels], value: dict) -> CostModels:
        raise DeserializeException(
            "Deserialization of cost model is impossible, because some information is lost "
            "during serialization."
        )


# Copied from https://github.com/input-output-hk/cardano-configurations/blob/26b6b6de73f90e4777602b372798bf77addcc321/
# network/mainnet/genesis/alonzo.json#L27-L194
PLUTUS_V1_COST_MODEL = {
    "sha2_256-memory-arguments": 4,
    "equalsString-cpu-arguments-constant": 1000,
    "cekDelayCost-exBudgetMemory": 100,
    "lessThanEqualsByteString-cpu-arguments-intercept": 103599,
    "divideInteger-memory-arguments-minimum": 1,
    "appendByteString-cpu-arguments-slope": 621,
    "blake2b-cpu-arguments-slope": 29175,
    "iData-cpu-arguments": 150000,
    "encodeUtf8-cpu-arguments-slope": 1000,
    "unBData-cpu-arguments": 150000,
    "multiplyInteger-cpu-arguments-intercept": 61516,
    "cekConstCost-exBudgetMemory": 100,
    "nullList-cpu-arguments": 150000,
    "equalsString-cpu-arguments-intercept": 150000,
    "trace-cpu-arguments": 150000,
    "mkNilData-memory-arguments": 32,
    "lengthOfByteString-cpu-arguments": 150000,
    "cekBuiltinCost-exBudgetCPU": 29773,
    "bData-cpu-arguments": 150000,
    "subtractInteger-cpu-arguments-slope": 0,
    "unIData-cpu-arguments": 150000,
    "consByteString-memory-arguments-intercept": 0,
    "divideInteger-memory-arguments-slope": 1,
    "divideInteger-cpu-arguments-model-arguments-slope": 118,
    "listData-cpu-arguments": 150000,
    "headList-cpu-arguments": 150000,
    "chooseData-memory-arguments": 32,
    "equalsInteger-cpu-arguments-intercept": 136542,
    "sha3_256-cpu-arguments-slope": 82363,
    "sliceByteString-cpu-arguments-slope": 5000,
    "unMapData-cpu-arguments": 150000,
    "lessThanInteger-cpu-arguments-intercept": 179690,
    "mkCons-cpu-arguments": 150000,
    "appendString-memory-arguments-intercept": 0,
    "modInteger-cpu-arguments-model-arguments-slope": 118,
    "ifThenElse-cpu-arguments": 1,
    "mkNilPairData-cpu-arguments": 150000,
    "lessThanEqualsInteger-cpu-arguments-intercept": 145276,
    "addInteger-memory-arguments-slope": 1,
    "chooseList-memory-arguments": 32,
    "constrData-memory-arguments": 32,
    "decodeUtf8-cpu-arguments-intercept": 150000,
    "equalsData-memory-arguments": 1,
    "subtractInteger-memory-arguments-slope": 1,
    "appendByteString-memory-arguments-intercept": 0,
    "lengthOfByteString-memory-arguments": 4,
    "headList-memory-arguments": 32,
    "listData-memory-arguments": 32,
    "consByteString-cpu-arguments-intercept": 150000,
    "unIData-memory-arguments": 32,
    "remainderInteger-memory-arguments-minimum": 1,
    "bData-memory-arguments": 32,
    "lessThanByteString-cpu-arguments-slope": 248,
    "encodeUtf8-memory-arguments-intercept": 0,
    "cekStartupCost-exBudgetCPU": 100,
    "multiplyInteger-memory-arguments-intercept": 0,
    "unListData-memory-arguments": 32,
    "remainderInteger-cpu-arguments-model-arguments-slope": 118,
    "cekVarCost-exBudgetCPU": 29773,
    "remainderInteger-memory-arguments-slope": 1,
    "cekForceCost-exBudgetCPU": 29773,
    "sha2_256-cpu-arguments-slope": 29175,
    "equalsInteger-memory-arguments": 1,
    "indexByteString-memory-arguments": 1,
    "addInteger-memory-arguments-intercept": 1,
    "chooseUnit-cpu-arguments": 150000,
    "sndPair-cpu-arguments": 150000,
    "cekLamCost-exBudgetCPU": 29773,
    "fstPair-cpu-arguments": 150000,
    "quotientInteger-memory-arguments-minimum": 1,
    "decodeUtf8-cpu-arguments-slope": 1000,
    "lessThanInteger-memory-arguments": 1,
    "lessThanEqualsInteger-cpu-arguments-slope": 1366,
    "fstPair-memory-arguments": 32,
    "modInteger-memory-arguments-intercept": 0,
    "unConstrData-cpu-arguments": 150000,
    "lessThanEqualsInteger-memory-arguments": 1,
    "chooseUnit-memory-arguments": 32,
    "sndPair-memory-arguments": 32,
    "addInteger-cpu-arguments-intercept": 197209,
    "decodeUtf8-memory-arguments-slope": 8,
    "equalsData-cpu-arguments-intercept": 150000,
    "mapData-cpu-arguments": 150000,
    "mkPairData-cpu-arguments": 150000,
    "quotientInteger-cpu-arguments-constant": 148000,
    "consByteString-memory-arguments-slope": 1,
    "cekVarCost-exBudgetMemory": 100,
    "indexByteString-cpu-arguments": 150000,
    "unListData-cpu-arguments": 150000,
    "equalsInteger-cpu-arguments-slope": 1326,
    "cekStartupCost-exBudgetMemory": 100,
    "subtractInteger-cpu-arguments-intercept": 197209,
    "divideInteger-cpu-arguments-model-arguments-intercept": 425507,
    "divideInteger-memory-arguments-intercept": 0,
    "cekForceCost-exBudgetMemory": 100,
    "blake2b-cpu-arguments-intercept": 2477736,
    "remainderInteger-cpu-arguments-constant": 148000,
    "tailList-cpu-arguments": 150000,
    "encodeUtf8-cpu-arguments-intercept": 150000,
    "equalsString-cpu-arguments-slope": 1000,
    "lessThanByteString-memory-arguments": 1,
    "multiplyInteger-cpu-arguments-slope": 11218,
    "appendByteString-cpu-arguments-intercept": 396231,
    "lessThanEqualsByteString-cpu-arguments-slope": 248,
    "modInteger-memory-arguments-slope": 1,
    "addInteger-cpu-arguments-slope": 0,
    "equalsData-cpu-arguments-slope": 10000,
    "decodeUtf8-memory-arguments-intercept": 0,
    "chooseList-cpu-arguments": 150000,
    "constrData-cpu-arguments": 150000,
    "equalsByteString-memory-arguments": 1,
    "cekApplyCost-exBudgetCPU": 29773,
    "quotientInteger-memory-arguments-slope": 1,
    "verifySignature-cpu-arguments-intercept": 3345831,
    "unMapData-memory-arguments": 32,
    "mkCons-memory-arguments": 32,
    "sliceByteString-memory-arguments-slope": 1,
    "sha3_256-memory-arguments": 4,
    "ifThenElse-memory-arguments": 1,
    "mkNilPairData-memory-arguments": 32,
    "equalsByteString-cpu-arguments-slope": 247,
    "appendString-cpu-arguments-intercept": 150000,
    "quotientInteger-cpu-arguments-model-arguments-slope": 118,
    "cekApplyCost-exBudgetMemory": 100,
    "equalsString-memory-arguments": 1,
    "multiplyInteger-memory-arguments-slope": 1,
    "cekBuiltinCost-exBudgetMemory": 100,
    "remainderInteger-memory-arguments-intercept": 0,
    "sha2_256-cpu-arguments-intercept": 2477736,
    "remainderInteger-cpu-arguments-model-arguments-intercept": 425507,
    "lessThanEqualsByteString-memory-arguments": 1,
    "tailList-memory-arguments": 32,
    "mkNilData-cpu-arguments": 150000,
    "chooseData-cpu-arguments": 150000,
    "unBData-memory-arguments": 32,
    "blake2b-memory-arguments": 4,
    "iData-memory-arguments": 32,
    "nullList-memory-arguments": 32,
    "cekDelayCost-exBudgetCPU": 29773,
    "subtractInteger-memory-arguments-intercept": 1,
    "lessThanByteString-cpu-arguments-intercept": 103599,
    "consByteString-cpu-arguments-slope": 1000,
    "appendByteString-memory-arguments-slope": 1,
    "trace-memory-arguments": 32,
    "divideInteger-cpu-arguments-constant": 148000,
    "cekConstCost-exBudgetCPU": 29773,
    "encodeUtf8-memory-arguments-slope": 8,
    "quotientInteger-cpu-arguments-model-arguments-intercept": 425507,
    "mapData-memory-arguments": 32,
    "appendString-cpu-arguments-slope": 1000,
    "modInteger-cpu-arguments-constant": 148000,
    "verifySignature-cpu-arguments-slope": 1,
    "unConstrData-memory-arguments": 32,
    "quotientInteger-memory-arguments-intercept": 0,
    "equalsByteString-cpu-arguments-constant": 150000,
    "sliceByteString-memory-arguments-intercept": 0,
    "mkPairData-memory-arguments": 32,
    "equalsByteString-cpu-arguments-intercept": 112536,
    "appendString-memory-arguments-slope": 1,
    "lessThanInteger-cpu-arguments-slope": 497,
    "modInteger-cpu-arguments-model-arguments-intercept": 425507,
    "modInteger-memory-arguments-minimum": 1,
    "sha3_256-cpu-arguments-intercept": 0,
    "verifySignature-memory-arguments": 1,
    "cekLamCost-exBudgetMemory": 100,
    "sliceByteString-cpu-arguments-intercept": 150000,
}


PLUTUS_V2_COST_MODEL = {
    "addInteger-cpu-arguments-intercept": 205665,
    "addInteger-cpu-arguments-slope": 812,
    "addInteger-memory-arguments-intercept": 1,
    "addInteger-memory-arguments-slope": 1,
    "appendByteString-cpu-arguments-intercept": 1000,
    "appendByteString-cpu-arguments-slope": 571,
    "appendByteString-memory-arguments-intercept": 0,
    "appendByteString-memory-arguments-slope": 1,
    "appendString-cpu-arguments-intercept": 1000,
    "appendString-cpu-arguments-slope": 24177,
    "appendString-memory-arguments-intercept": 4,
    "appendString-memory-arguments-slope": 1,
    "bData-cpu-arguments": 1000,
    "bData-memory-arguments": 32,
    "blake2b_256-cpu-arguments-intercept": 117366,
    "blake2b_256-cpu-arguments-slope": 10475,
    "blake2b_256-memory-arguments": 4,
    "cekApplyCost-exBudgetCPU": 23000,
    "cekApplyCost-exBudgetMemory": 100,
    "cekBuiltinCost-exBudgetCPU": 23000,
    "cekBuiltinCost-exBudgetMemory": 100,
    "cekConstCost-exBudgetCPU": 23000,
    "cekConstCost-exBudgetMemory": 100,
    "cekDelayCost-exBudgetCPU": 23000,
    "cekDelayCost-exBudgetMemory": 100,
    "cekForceCost-exBudgetCPU": 23000,
    "cekForceCost-exBudgetMemory": 100,
    "cekLamCost-exBudgetCPU": 23000,
    "cekLamCost-exBudgetMemory": 100,
    "cekStartupCost-exBudgetCPU": 100,
    "cekStartupCost-exBudgetMemory": 100,
    "cekVarCost-exBudgetCPU": 23000,
    "cekVarCost-exBudgetMemory": 100,
    "chooseData-cpu-arguments": 19537,
    "chooseData-memory-arguments": 32,
    "chooseList-cpu-arguments": 175354,
    "chooseList-memory-arguments": 32,
    "chooseUnit-cpu-arguments": 46417,
    "chooseUnit-memory-arguments": 4,
    "consByteString-cpu-arguments-intercept": 221973,
    "consByteString-cpu-arguments-slope": 511,
    "consByteString-memory-arguments-intercept": 0,
    "consByteString-memory-arguments-slope": 1,
    "constrData-cpu-arguments": 89141,
    "constrData-memory-arguments": 32,
    "decodeUtf8-cpu-arguments-intercept": 497525,
    "decodeUtf8-cpu-arguments-slope": 14068,
    "decodeUtf8-memory-arguments-intercept": 4,
    "decodeUtf8-memory-arguments-slope": 2,
    "divideInteger-cpu-arguments-constant": 196500,
    "divideInteger-cpu-arguments-model-arguments-intercept": 453240,
    "divideInteger-cpu-arguments-model-arguments-slope": 220,
    "divideInteger-memory-arguments-intercept": 0,
    "divideInteger-memory-arguments-minimum": 1,
    "divideInteger-memory-arguments-slope": 1,
    "encodeUtf8-cpu-arguments-intercept": 1000,
    "encodeUtf8-cpu-arguments-slope": 28662,
    "encodeUtf8-memory-arguments-intercept": 4,
    "encodeUtf8-memory-arguments-slope": 2,
    "equalsByteString-cpu-arguments-constant": 245000,
    "equalsByteString-cpu-arguments-intercept": 216773,
    "equalsByteString-cpu-arguments-slope": 62,
    "equalsByteString-memory-arguments": 1,
    "equalsData-cpu-arguments-intercept": 1060367,
    "equalsData-cpu-arguments-slope": 12586,
    "equalsData-memory-arguments": 1,
    "equalsInteger-cpu-arguments-intercept": 208512,
    "equalsInteger-cpu-arguments-slope": 421,
    "equalsInteger-memory-arguments": 1,
    "equalsString-cpu-arguments-constant": 187000,
    "equalsString-cpu-arguments-intercept": 1000,
    "equalsString-cpu-arguments-slope": 52998,
    "equalsString-memory-arguments": 1,
    "fstPair-cpu-arguments": 80436,
    "fstPair-memory-arguments": 32,
    "headList-cpu-arguments": 43249,
    "headList-memory-arguments": 32,
    "iData-cpu-arguments": 1000,
    "iData-memory-arguments": 32,
    "ifThenElse-cpu-arguments": 80556,
    "ifThenElse-memory-arguments": 1,
    "indexByteString-cpu-arguments": 57667,
    "indexByteString-memory-arguments": 4,
    "lengthOfByteString-cpu-arguments": 1000,
    "lengthOfByteString-memory-arguments": 10,
    "lessThanByteString-cpu-arguments-intercept": 197145,
    "lessThanByteString-cpu-arguments-slope": 156,
    "lessThanByteString-memory-arguments": 1,
    "lessThanEqualsByteString-cpu-arguments-intercept": 197145,
    "lessThanEqualsByteString-cpu-arguments-slope": 156,
    "lessThanEqualsByteString-memory-arguments": 1,
    "lessThanEqualsInteger-cpu-arguments-intercept": 204924,
    "lessThanEqualsInteger-cpu-arguments-slope": 473,
    "lessThanEqualsInteger-memory-arguments": 1,
    "lessThanInteger-cpu-arguments-intercept": 208896,
    "lessThanInteger-cpu-arguments-slope": 511,
    "lessThanInteger-memory-arguments": 1,
    "listData-cpu-arguments": 52467,
    "listData-memory-arguments": 32,
    "mapData-cpu-arguments": 64832,
    "mapData-memory-arguments": 32,
    "mkCons-cpu-arguments": 65493,
    "mkCons-memory-arguments": 32,
    "mkNilData-cpu-arguments": 22558,
    "mkNilData-memory-arguments": 32,
    "mkNilPairData-cpu-arguments": 16563,
    "mkNilPairData-memory-arguments": 32,
    "mkPairData-cpu-arguments": 76511,
    "mkPairData-memory-arguments": 32,
    "modInteger-cpu-arguments-constant": 196500,
    "modInteger-cpu-arguments-model-arguments-intercept": 453240,
    "modInteger-cpu-arguments-model-arguments-slope": 220,
    "modInteger-memory-arguments-intercept": 0,
    "modInteger-memory-arguments-minimum": 1,
    "modInteger-memory-arguments-slope": 1,
    "multiplyInteger-cpu-arguments-intercept": 69522,
    "multiplyInteger-cpu-arguments-slope": 11687,
    "multiplyInteger-memory-arguments-intercept": 0,
    "multiplyInteger-memory-arguments-slope": 1,
    "nullList-cpu-arguments": 60091,
    "nullList-memory-arguments": 32,
    "quotientInteger-cpu-arguments-constant": 196500,
    "quotientInteger-cpu-arguments-model-arguments-intercept": 453240,
    "quotientInteger-cpu-arguments-model-arguments-slope": 220,
    "quotientInteger-memory-arguments-intercept": 0,
    "quotientInteger-memory-arguments-minimum": 1,
    "quotientInteger-memory-arguments-slope": 1,
    "remainderInteger-cpu-arguments-constant": 196500,
    "remainderInteger-cpu-arguments-model-arguments-intercept": 453240,
    "remainderInteger-cpu-arguments-model-arguments-slope": 220,
    "remainderInteger-memory-arguments-intercept": 0,
    "remainderInteger-memory-arguments-minimum": 1,
    "remainderInteger-memory-arguments-slope": 1,
    "serialiseData-cpu-arguments-intercept": 1159724,
    "serialiseData-cpu-arguments-slope": 392670,
    "serialiseData-memory-arguments-intercept": 0,
    "serialiseData-memory-arguments-slope": 2,
    "sha2_256-cpu-arguments-intercept": 806990,
    "sha2_256-cpu-arguments-slope": 30482,
    "sha2_256-memory-arguments": 4,
    "sha3_256-cpu-arguments-intercept": 1927926,
    "sha3_256-cpu-arguments-slope": 82523,
    "sha3_256-memory-arguments": 4,
    "sliceByteString-cpu-arguments-intercept": 265318,
    "sliceByteString-cpu-arguments-slope": 0,
    "sliceByteString-memory-arguments-intercept": 4,
    "sliceByteString-memory-arguments-slope": 0,
    "sndPair-cpu-arguments": 85931,
    "sndPair-memory-arguments": 32,
    "subtractInteger-cpu-arguments-intercept": 205665,
    "subtractInteger-cpu-arguments-slope": 812,
    "subtractInteger-memory-arguments-intercept": 1,
    "subtractInteger-memory-arguments-slope": 1,
    "tailList-cpu-arguments": 41182,
    "tailList-memory-arguments": 32,
    "trace-cpu-arguments": 212342,
    "trace-memory-arguments": 32,
    "unBData-cpu-arguments": 31220,
    "unBData-memory-arguments": 32,
    "unConstrData-cpu-arguments": 32696,
    "unConstrData-memory-arguments": 32,
    "unIData-cpu-arguments": 43357,
    "unIData-memory-arguments": 32,
    "unListData-cpu-arguments": 32247,
    "unListData-memory-arguments": 32,
    "unMapData-cpu-arguments": 38314,
    "unMapData-memory-arguments": 32,
    "verifyEcdsaSecp256k1Signature-cpu-arguments": 20000000000,
    "verifyEcdsaSecp256k1Signature-memory-arguments": 20000000000,
    "verifyEd25519Signature-cpu-arguments-intercept": 9462713,
    "verifyEd25519Signature-cpu-arguments-slope": 1021,
    "verifyEd25519Signature-memory-arguments": 10,
    "verifySchnorrSecp256k1Signature-cpu-arguments-intercept": 20000000000,
    "verifySchnorrSecp256k1Signature-cpu-arguments-slope": 0,
    "verifySchnorrSecp256k1Signature-memory-arguments": 20000000000,
}

COST_MODELS = CostModels({0: PLUTUS_V1_COST_MODEL})
"""A dictionary of current cost models, which could be used to calculate script data hash."""


def get_tag(constr_id: int) -> Optional[int]:
    if 0 <= constr_id < 7:
        return 121 + constr_id
    elif 7 <= constr_id < 128:
        return 1280 + (constr_id - 7)
    else:
        return None


def get_constructor_id_and_fields(
    raw_tag: CBORTag,
) -> typing.Tuple[int, typing.List[Any]]:
    tag = raw_tag.tag
    if tag == 102:
        if len(raw_tag.value) != 2:
            raise DeserializeException(
                f"Expect the length of value to be exactly 2, got {len(raw_tag.value)} instead."
            )
        return raw_tag.value[0], raw_tag.value[1]
    else:
        if 121 <= tag < 128:
            constr = tag - 121
        elif 1280 <= tag < 1536:
            constr = tag - 1280 + 7
        else:
            raise DeserializeException(f"Unexpected tag for RawPlutusData: {tag}")
        return constr, raw_tag.value


def id_map(cls, skip_constructor=False):
    """
    Constructs a unique representation of a PlutusData type definition.
    Intended for automatic constructor generation.
    """
    if cls == bytes or cls == ByteString:
        return "bytes"
    if cls == int:
        return "int"
    if cls == RawCBOR or cls == RawPlutusData or cls == Datum:
        return "any"
    if cls == IndefiniteList:
        return "list"
    if hasattr(cls, "__origin__"):
        origin = getattr(cls, "__origin__")
        if origin == list:
            prefix = "list"
        elif origin == dict:
            prefix = "map"
        elif origin == typing.Union:
            prefix = "union"
        else:
            raise TypeError(
                f"Unexpected parameterized type for automatic constructor generation: {cls}"
            )
        return prefix + "<" + ",".join(id_map(a) for a in cls.__args__) + ">"
    if issubclass(cls, PlutusData):
        return (
            "cons["
            + cls.__name__
            + "]("
            + (str(cls.CONSTR_ID) if not skip_constructor else "_")
            + ";"
            + ",".join(f.name + ":" + id_map(f.type) for f in fields(cls))
            + ")"
        )
    raise TypeError(f"Unexpected type for automatic constructor generation: {cls}")


@dataclass(repr=False)
class PlutusData(ArrayCBORSerializable):
    """
    PlutusData is a helper class that can serialize itself into a CBOR format, which could be intepreted as
    a data structure in Plutus scripts.
    It is not required to use this class to interact with Plutus scripts. However, wrapping datum in PlutusData
    class will reduce the complexity of serialization and deserialization tremendously.

    Examples:

        >>> @dataclass
        ... class Test(PlutusData):
        ...     CONSTR_ID = 1
        ...     a: int
        ...     b: bytes
        >>> test = Test(123, b"321")
        >>> test.to_cbor_hex()
        'd87a9f187b43333231ff'
        >>> assert test == Test.from_cbor("d87a9f187b43333231ff")
    """

    MAX_BYTES_SIZE = 64

    @classproperty
    def CONSTR_ID(cls):
        """
        Constructor ID of this plutus data.
        It is primarily used by Plutus core to reconstruct a data structure from serialized CBOR bytes.
        The default implementation is an almost unique, deterministic constructor ID in the range 1 - 2^32 based
        on class attributes, types and class name.
        """
        k = f"_CONSTR_ID_{cls.__name__}"
        if not hasattr(cls, k):
            det_string = id_map(cls, skip_constructor=True)
            det_hash = sha256(det_string.encode("utf8")).hexdigest()
            setattr(cls, k, int(det_hash, 16) % 2**32)

        return getattr(cls, k)

    def __post_init__(self):
        valid_types = (
            RawPlutusData,
            PlutusData,
            dict,
            IndefiniteList,
            int,
            ByteString,
            bytes,
        )
        for f in fields(self):
            if inspect.isclass(f.type) and not issubclass(f.type, valid_types):
                raise TypeError(
                    f"Invalid field type: {f.type}. A field in PlutusData should be one of {valid_types}"
                )

            data = getattr(self, f.name)
            if isinstance(data, bytes) and len(data) > 64:
                raise InvalidArgumentException(
                    f"The size of {data} exceeds {self.MAX_BYTES_SIZE} bytes. "
                    "Use pycardano.serialization.ByteString for long bytes."
                )

    def to_shallow_primitive(self) -> CBORTag:
        primitives: Primitive = super().to_shallow_primitive()
        if primitives:
            primitives = IndefiniteList(primitives)
        tag = get_tag(self.CONSTR_ID)
        if tag:
            return CBORTag(tag, primitives)
        else:
            return CBORTag(102, [self.CONSTR_ID, primitives])

    @classmethod
    @limit_primitive_type(CBORTag)
    def from_primitive(cls: Type[PlutusData], value: CBORTag) -> PlutusData:
        if value.tag == 102:
            tag = value.value[0]
            if tag != cls.CONSTR_ID:
                raise DeserializeException(
                    f"Unexpected constructor ID for {cls}. Expect {cls.CONSTR_ID}, got "
                    f"{tag} instead."
                )
            if len(value.value) != 2:
                raise DeserializeException(
                    f"Expect the length of value to be exactly 2, got {len(value.value)} instead."
                )
            return super(PlutusData, cls).from_primitive(value.value[1])
        else:
            expected_tag = get_tag(cls.CONSTR_ID)
            if expected_tag != value.tag:
                raise DeserializeException(
                    f"Unexpected constructor ID for {cls}. Expect {expected_tag}, got "
                    f"{value.tag} instead."
                )
            return super(PlutusData, cls).from_primitive(value.value)

    def hash(self) -> DatumHash:
        return datum_hash(self)

    def to_dict(self) -> dict:
        """
        Convert to a dictionary.

        Returns:
            str: a dict PlutusData that can be JSON encoded.
        """

        def _dfs(obj):
            """
            Reference of Haskell's implementation:
            https://github.com/input-output-hk/cardano-node/blob/baa9b5e59c5d448d475f94cc88a31a5857c2bda5/cardano-api/
            src/Cardano/Api/ScriptData.hs#L449-L474
            """
            if isinstance(obj, int):
                return {"int": obj}
            elif isinstance(obj, bytes):
                return {"bytes": obj.hex()}
            elif isinstance(obj, ByteString):
                return {"bytes": obj.value.hex()}
            elif isinstance(obj, IndefiniteList) or isinstance(obj, list):
                return {"list": [_dfs(item) for item in obj]}
            elif isinstance(obj, dict):
                return {"map": [{"v": _dfs(v), "k": _dfs(k)} for k, v in obj.items()]}
            elif isinstance(obj, PlutusData):
                return {
                    "constructor": obj.CONSTR_ID,
                    "fields": [_dfs(getattr(obj, f.name)) for f in fields(obj)],
                }
            elif isinstance(obj, RawPlutusData):
                return obj.to_dict()
            elif isinstance(obj, RawCBOR):
                return RawPlutusData.from_cbor(obj.cbor).to_dict()
            else:
                raise TypeError(f"Unexpected type {type(obj)}")

        return _dfs(self)

    def to_json(self, **kwargs) -> str:  # type: ignore
        """Convert to a json string

        Args:
            **kwargs: Extra key word arguments to be passed to `json.dumps()`

        Returns:
            str: a JSON encoded PlutusData.
        """

        return json.dumps(self.to_dict(), **kwargs)

    @classmethod
    def from_dict(cls: Type[PlutusData], data: dict) -> PlutusData:
        """Convert a dictionary to PlutusData

        Args:
            data (dict): A dictionary.

        Returns:
            PlutusData: Restored PlutusData.
        """

        def _dfs(obj):
            if isinstance(obj, dict):
                if "constructor" in obj:
                    if obj["constructor"] != cls.CONSTR_ID:
                        raise DeserializeException(
                            f"Mismatch between constructors in class {cls.__name__}, expect: {cls.CONSTR_ID}, "
                            f"got: {obj['constructor']} instead."
                        )
                    converted_fields = []
                    for f, f_info in zip(obj["fields"], fields(cls)):
                        if inspect.isclass(f_info.type) and issubclass(
                            f_info.type, PlutusData
                        ):
                            converted_fields.append(f_info.type.from_dict(f))
                        elif f_info.type == Datum:
                            converted_fields.append(RawPlutusData.from_dict(f))
                        elif (
                            hasattr(f_info.type, "__origin__")
                            and f_info.type.__origin__ is Union
                        ):
                            t_args = f_info.type.__args__
                            found_match = False
                            for t in t_args:
                                if (
                                    inspect.isclass(t)
                                    and issubclass(t, PlutusData)
                                    and t.CONSTR_ID == f["constructor"]
                                ):
                                    converted_fields.append(t.from_dict(f))
                                    found_match = True
                                    break
                            if not found_match:
                                raise DeserializeException(
                                    f"Unexpected data structure: {f}."
                                )
                        elif (
                            hasattr(f_info.type, "__origin__")
                            and f_info.type.__origin__ is list
                        ):
                            t_args = f_info.type.__args__
                            if len(t_args) != 1:
                                raise DeserializeException(
                                    f"List types need exactly one type argument, but got {t_args}"
                                )
                            if "list" not in f:
                                raise DeserializeException(
                                    f'Expected type "list" for constructor List but got {f}'
                                )
                            t = t_args[0]
                            if inspect.isclass(t) and issubclass(t, PlutusData):
                                converted_fields.append(t.from_dict(f))
                            else:
                                converted_fields.append(_dfs(f))

                        elif (
                            hasattr(f_info.type, "__origin__")
                            and f_info.type.__origin__ is dict
                        ):
                            t_args = f_info.type.__args__
                            if len(t_args) != 2:
                                raise DeserializeException(
                                    "Dict type with wrong number of arguments"
                                )
                            if "map" not in f:
                                raise DeserializeException(
                                    f'Expected type "map" in object but got "{f}"'
                                )
                            key_t = t_args[0]
                            val_t = t_args[1]
                            if inspect.isclass(key_t) and issubclass(key_t, PlutusData):
                                key_convert = key_t.from_dict
                            else:
                                key_convert = _dfs
                            if inspect.isclass(val_t) and issubclass(val_t, PlutusData):
                                val_convert = val_t.from_dict
                            else:
                                val_convert = _dfs
                            converted_fields.append(
                                {
                                    key_convert(pair["k"]): val_convert(pair["v"])
                                    for pair in f["map"]
                                }
                            )
                        else:
                            converted_fields.append(_dfs(f))
                    return cls(*converted_fields)
                elif "map" in obj:
                    return {_dfs(pair["k"]): _dfs(pair["v"]) for pair in obj["map"]}
                elif "int" in obj:
                    return obj["int"]
                elif "bytes" in obj:
                    if len(obj["bytes"]) > 64:
                        return ByteString(bytes.fromhex(obj["bytes"]))
                    else:
                        return bytes.fromhex(obj["bytes"])
                elif "list" in obj:
                    return IndefiniteList([_dfs(item) for item in obj["list"]])
                else:
                    raise DeserializeException(f"Unexpected data structure: {obj}")
            else:
                raise TypeError(f"Unexpected data type: {type(obj)}")

        return _dfs(data)

    @classmethod
    def from_json(cls: Type[PlutusData], data: str) -> PlutusData:
        """Restore a json encoded string to a PlutusData.

        Args:
            data (str): An encoded json string.

        Returns:
            PlutusData: The restored PlutusData.
        """
        obj = json.loads(data)
        return cls.from_dict(obj)

    def __deepcopy__(self, memo):
        return self.__class__.from_cbor(self.to_cbor_hex())


RawDatum = Union[PlutusData, dict, int, bytes, IndefiniteList, RawCBOR, CBORTag]


@dataclass(repr=True)
class RawPlutusData(CBORSerializable):
    data: RawDatum

    def to_primitive(self) -> Primitive:
        def _dfs(obj):
            if isinstance(obj, list) and obj:
                return IndefiniteList([_dfs(item) for item in obj])
            elif isinstance(obj, dict):
                return {_dfs(k): _dfs(v) for k, v in obj.items()}
            elif isinstance(obj, CBORTag) and isinstance(obj.value, list) and obj.value:
                if obj.tag != 102:
                    value = IndefiniteList([_dfs(item) for item in obj.value])
                else:
                    value = [_dfs(item) for item in obj.value]
                return CBORTag(tag=obj.tag, value=value)
            return obj

        return _dfs(self.data)

    def to_dict(self) -> dict:
        """
        Convert to a dictionary.

        Returns:
            str: a dict RawPlutusData that can be JSON encoded.
        """

        def _dfs(obj):
            if isinstance(obj, int):
                return {"int": obj}
            elif isinstance(obj, bytes):
                return {"bytes": obj.hex()}
            elif isinstance(obj, ByteString):
                return {"bytes": obj.value.hex()}
            elif isinstance(obj, IndefiniteList) or isinstance(obj, list):
                return {"list": [_dfs(item) for item in obj]}
            elif isinstance(obj, dict):
                return {"map": [{"v": _dfs(v), "k": _dfs(k)} for k, v in obj.items()]}
            elif isinstance(obj, CBORTag):
                constructor, fields = get_constructor_id_and_fields(obj)
                return {"constructor": constructor, "fields": [_dfs(f) for f in fields]}
            elif isinstance(obj, RawCBOR):
                return RawPlutusData.from_cbor(obj.cbor).to_dict()
            raise TypeError(f"Unexpected type {type(obj)}")

        return _dfs(RawPlutusData.to_primitive(self))

    def to_json(self, **kwargs) -> str:  # type: ignore
        """Convert to a json string

        Args:
            **kwargs: Extra key word arguments to be passed to `json.dumps()`

        Returns:
            str: a JSON encoded RawPlutusData.
        """

        return json.dumps(RawPlutusData.to_dict(self), **kwargs)

    @classmethod
    @limit_primitive_type(
        PlutusData, dict, int, bytes, IndefiniteList, RawCBOR, CBORTag
    )  # equal to RawDatum parameter list
    def from_primitive(cls: Type[RawPlutusData], value: RawDatum) -> RawPlutusData:
        return cls(value)

    @classmethod
    def from_dict(cls: Type[RawPlutusData], data: dict) -> RawPlutusData:
        """Convert a dictionary to RawPlutusData

        Args:
            data (dict): A dictionary.

        Returns:
            RawPlutusData: Restored RawPlutusData.
        """

        def _dfs(obj):
            if isinstance(obj, dict):
                if "constructor" in obj:
                    converted_fields = []
                    for f in obj["fields"]:
                        converted_fields.append(_dfs(f))
                    tag = get_tag(obj["constructor"])
                    if tag is None:
                        return CBORTag(
                            102, [obj["constructor"], IndefiniteList(converted_fields)]
                        )
                    else:
                        return CBORTag(tag, converted_fields)
                elif "map" in obj:
                    return {_dfs(pair["k"]): _dfs(pair["v"]) for pair in obj["map"]}
                elif "int" in obj:
                    return obj["int"]
                elif "bytes" in obj:
                    if len(obj["bytes"]) > 64:
                        return ByteString(bytes.fromhex(obj["bytes"]))
                    else:
                        return bytes.fromhex(obj["bytes"])
                elif "list" in obj:
                    return IndefiniteList([_dfs(item) for item in obj["list"]])
                else:
                    raise DeserializeException(f"Unexpected data structure: {obj}")
            else:
                raise TypeError(f"Unexpected data type: {type(obj)}")

        return cls(_dfs(data))

    @classmethod
    def from_json(cls: Type[RawPlutusData], data: str) -> RawPlutusData:
        """Restore a json encoded string to a RawPlutusData.

        Args:
            data (str): An encoded json string.

        Returns:
            RawPlutusData: The restored RawPlutusData.
        """
        obj = json.loads(data)
        return cls.from_dict(obj)

    def __deepcopy__(self, memo):
        return self.__class__.from_cbor(self.to_cbor_hex())


Datum = Union[PlutusData, dict, int, bytes, IndefiniteList, RawCBOR, RawPlutusData]
"""Plutus Datum type. A Union type that contains all valid datum types."""


def datum_hash(datum: Datum) -> DatumHash:
    return DatumHash(
        blake2b(
            cbor2.dumps(datum, default=default_encoder),
            DATUM_HASH_SIZE,
            encoder=RawEncoder,
        )
    )


class RedeemerTag(CBORSerializable, Enum):
    """
    Redeemer tag, which indicates the type of redeemer.
    """

    SPEND = 0
    MINT = 1
    CERTIFICATE = 2
    WITHDRAWAL = 3
    VOTING = 4
    PROPOSING = 5

    def to_primitive(self) -> int:
        return self.value

    @classmethod
    @limit_primitive_type(int)
    def from_primitive(cls: Type[RedeemerTag], value: int) -> RedeemerTag:
        return cls(value)


@dataclass(repr=False)
class ExecutionUnits(ArrayCBORSerializable):
    mem: int

    steps: int

    def __add__(self, other: ExecutionUnits) -> ExecutionUnits:
        if not isinstance(other, ExecutionUnits):
            raise TypeError(
                f"Expect type: {ExecutionUnits}, got {type(other)} instead."
            )
        return ExecutionUnits(self.mem + other.mem, self.steps + other.steps)

    def is_empty(self) -> bool:
        return self.mem == 0 and self.steps == 0

    def __bool__(self):
        return not self.is_empty()


@dataclass(repr=False)
class Redeemer(ArrayCBORSerializable):
    tag: Optional[RedeemerTag] = field(default=None, init=False)

    index: int = field(default=0, init=False)

    data: Any

    ex_units: Optional[ExecutionUnits] = None

    @classmethod
    @limit_primitive_type(list, tuple)
    def from_primitive(cls: Type[Redeemer], values: list) -> Redeemer:
        if isinstance(values[2], CBORTag) and cls is Redeemer:
            values[2] = RawPlutusData.from_primitive(values[2])
        redeemer = super(Redeemer, cls).from_primitive([values[2], values[3]])
        redeemer.tag = RedeemerTag.from_primitive(values[0])
        redeemer.index = values[1]
        return redeemer


@dataclass(repr=False)
class RedeemerKey(ArrayCBORSerializable):
    tag: RedeemerTag

    index: int = field(default=0)

    @classmethod
    @limit_primitive_type(list, tuple)
    def from_primitive(cls: Type[RedeemerKey], values: list) -> RedeemerKey:
        tag = RedeemerTag.from_primitive(values[0])
        index = values[1]
        return cls(tag, index)

    def __eq__(self, other):
        if not isinstance(other, RedeemerKey):
            return False
        return self.tag == other.tag and self.index == other.index

    def __hash__(self):
        return hash(self.to_cbor())


@dataclass(repr=False)
class RedeemerValue(ArrayCBORSerializable):
    data: Any

    ex_units: ExecutionUnits

    @classmethod
    @limit_primitive_type(list, tuple)
    def from_primitive(cls: Type[RedeemerValue], values: list) -> RedeemerValue:
        if isinstance(values[0], CBORTag) and cls is RedeemerValue:
            values[0] = RawPlutusData.from_primitive(values[0])
        return super(RedeemerValue, cls).from_primitive([values[0], values[1]])

    def __eq__(self, other):
        if not isinstance(other, RedeemerValue):
            return False
        return self.data == other.data and self.ex_units == other.ex_units


@typechecked
class RedeemerMap(DictCBORSerializable):
    KEY_TYPE = RedeemerKey

    VALUE_TYPE = RedeemerValue


Redeemers = Union[List[Redeemer], RedeemerMap]


def plutus_script_hash(script: Union[NativeScript, PlutusScript]) -> ScriptHash:
    """Calculates the hash of a Plutus script.

    Args:
        script (Union[bytes, PlutusScript]): A plutus script.

    Returns:
        ScriptHash: blake2b hash of the script.
    """
    return script_hash(script)


class PlutusScript(CBORSerializable, bytes):
    """
    Plutus script class.

    This class is a base class for all Plutus script versions.

    Example - Load a Plutus script from `test/resources/scriptV2.plutus <https://github.com/Python-Cardano/pycardano/blob/main/test/resources/scriptV2.plutus>`_ and get its address: # noqa: E501


        >>> from pycardano import Address, Network
        >>> script = PlutusV2Script.load("test/resources/scriptV2.plutus")
        >>> Address(plutus_script_hash(script), network=Network.TESTNET).encode()
        'addr_test1wrmz3pjz4dmfxj0fc0a0eyw69tp6h7mpndzf9g3kttq9cqqqw47ym'
    """

    @property
    def version(self) -> int:
        raise NotImplementedError("")

    def to_shallow_primitive(self) -> bytes:
        return bytes(self)

    @classmethod
    def from_primitive(
        cls: Type[PlutusScript], value: Any, type_args: Optional[tuple] = None
    ) -> PlutusScript:
        if not isinstance(value, (bytes, bytearray)):
            raise DeserializeException(f"Expect bytes, got {type(value)} instead.")
        return cls(value)

    @classmethod
    def from_version(cls, version: int, script_data: bytes) -> "PlutusScript":
        class_name = f"PlutusV{version}Script"
        script_class = globals().get(class_name)

        if script_class is None:
            raise ValueError(f"No Plutus script class found for version {version}")

        return script_class(script_data)

    def get_script_hash_prefix(self) -> bytes:
        raise NotImplementedError("")

    def __repr__(self):
        return f"{self.__class__.__name__}({self.hex()})"


class PlutusV1Script(PlutusScript):
    def get_script_hash_prefix(self) -> bytes:
        return bytes.fromhex("01")

    @property
    def version(self) -> int:
        return 1


class PlutusV2Script(PlutusScript):
    def get_script_hash_prefix(self) -> bytes:
        return bytes.fromhex("02")

    @property
    def version(self) -> int:
        return 2


class PlutusV3Script(PlutusScript):
    def get_script_hash_prefix(self) -> bytes:
        return bytes.fromhex("03")

    @property
    def version(self) -> int:
        return 3


ScriptType = Union[NativeScript, PlutusScript]
"""Script type. A Union type that contains all valid script types."""


def script_hash(script: ScriptType) -> ScriptHash:
    """Calculates the hash of a script, which could be either native script or plutus script.

    Args:
        script (ScriptType): A script.

    Returns:
        ScriptHash: blake2b hash of the script.
    """
    if isinstance(script, NativeScript):
        return script.hash()
    elif isinstance(script, PlutusScript):
        return ScriptHash(
            blake2b(
                script.get_script_hash_prefix() + script,
                SCRIPT_HASH_SIZE,
                encoder=RawEncoder,
            )
        )
    elif type(script) is bytes:
        return ScriptHash(
            blake2b(bytes.fromhex("01") + script, SCRIPT_HASH_SIZE, encoder=RawEncoder)
        )
    else:
        raise TypeError(f"Unexpected script type: {type(script)}")


@dataclass
class Unit(PlutusData):
    """The default "Unit type" with a 0 constructor ID"""

    CONSTR_ID = 0
