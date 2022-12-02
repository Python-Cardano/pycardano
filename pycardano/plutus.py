"""Plutus related classes and functions."""

from __future__ import annotations

import inspect
import json
from dataclasses import dataclass, field, fields
from enum import Enum
from typing import Any, ClassVar, Optional, Type, Union

import cbor2
from cbor2 import CBORTag
from nacl.encoding import RawEncoder
from nacl.hash import blake2b

from pycardano.exception import DeserializeException
from pycardano.hash import DATUM_HASH_SIZE, SCRIPT_HASH_SIZE, DatumHash, ScriptHash
from pycardano.nativescript import NativeScript
from pycardano.serialization import (
    ArrayCBORSerializable,
    CBORSerializable,
    DictCBORSerializable,
    IndefiniteList,
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
    "PlutusV1Script",
    "PlutusV2Script",
    "RawPlutusData",
    "Redeemer",
    "datum_hash",
    "plutus_script_hash",
    "script_hash",
]


class CostModels(DictCBORSerializable):
    KEY_TYPE = int
    VALUE_TYPE = dict

    def to_shallow_primitive(self) -> dict:
        result = {}
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
                result[language] = [cost_model[k] for k in sorted(cost_model.keys())]
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
        >>> test.to_cbor()
        'd87a9f187b43333231ff'
        >>> assert test == Test.from_cbor("d87a9f187b43333231ff")
    """

    CONSTR_ID: ClassVar[int] = 0
    """Constructor ID of this plutus data.
       It is primarily used by Plutus core to reconstruct a data structure from serialized CBOR bytes."""

    def __post_init__(self):
        valid_types = (PlutusData, dict, IndefiniteList, int, bytes)
        for f in fields(self):
            if inspect.isclass(f.type) and not issubclass(f.type, valid_types):
                raise TypeError(
                    f"Invalid field type: {f.type}. A field in PlutusData should be one of {valid_types}"
                )

    def to_shallow_primitive(self) -> CBORTag:
        primitives = super().to_shallow_primitive()
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

    def to_json(self, **kwargs) -> str:
        """Convert to a json string

        Args:
            **kwargs: Extra key word arguments to be passed to `json.dumps()`

        Returns:
            str: a JSON encoded PlutusData.
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
            elif isinstance(obj, list):
                return [_dfs(item) for item in obj]
            elif isinstance(obj, IndefiniteList):
                return {"list": [_dfs(item) for item in obj]}
            elif isinstance(obj, dict):
                return {"map": [{"v": _dfs(v), "k": _dfs(k)} for k, v in obj.items()]}
            elif isinstance(obj, PlutusData):
                return {
                    "constructor": obj.CONSTR_ID,
                    "fields": _dfs([getattr(obj, f.name) for f in fields(obj)]),
                }
            else:
                raise TypeError(f"Unexpected type {type(obj)}")

        return json.dumps(_dfs(self), **kwargs)

    @classmethod
    def from_dict(cls: PlutusData, data: dict) -> PlutusData:
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
                            f"Mismatch between constructors, expect: {cls.CONSTR_ID}, "
                            f"got: {obj['constructor']} instead."
                        )
                    converted_fields = []
                    for f, f_info in zip(obj["fields"], fields(cls)):
                        if inspect.isclass(f_info.type) and issubclass(
                            f_info.type, PlutusData
                        ):
                            converted_fields.append(f_info.type.from_dict(f))
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
                        else:
                            converted_fields.append(_dfs(f))
                    return cls(*converted_fields)
                elif "map" in obj:
                    return {_dfs(pair["k"]): _dfs(pair["v"]) for pair in obj["map"]}
                elif "int" in obj:
                    return obj["int"]
                elif "bytes" in obj:
                    return bytes.fromhex(obj["bytes"])
                elif "list" in obj:
                    return IndefiniteList([_dfs(item) for item in obj["list"]])
                else:
                    raise DeserializeException(f"Unexpected data structure: {obj}")
            else:
                raise TypeError(f"Unexpected data type: {type(obj)}")

        return _dfs(data)

    @classmethod
    def from_json(cls: PlutusData, data: str) -> PlutusData:
        """Restore a json encoded string to a PlutusData.

        Args:
            data (str): An encoded json string.

        Returns:
            PlutusData: The restored PlutusData.
        """
        obj = json.loads(data)
        return cls.from_dict(obj)


@dataclass
class RawPlutusData(CBORSerializable):

    data: CBORTag

    def to_primitive(self) -> CBORTag:
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

    @classmethod
    @limit_primitive_type(CBORTag)
    def from_primitive(cls: Type[RawPlutusData], value: CBORTag) -> RawPlutusData:
        return cls(value)


Datum = Union[PlutusData, dict, IndefiniteList, int, bytes, RawCBOR, RawPlutusData]
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
    CERT = 2
    REWARD = 3

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


@dataclass(repr=False)
class Redeemer(ArrayCBORSerializable):
    tag: RedeemerTag

    index: int = field(default=0, init=False)

    data: Any

    ex_units: ExecutionUnits = None

    @classmethod
    @limit_primitive_type(list)
    def from_primitive(cls: Type[Redeemer], values: list) -> Redeemer:
        if isinstance(values[2], CBORTag) and cls is Redeemer:
            values[2] = RawPlutusData.from_primitive(values[2])
        redeemer = super(Redeemer, cls).from_primitive(
            [values[0], values[2], values[3]]
        )
        redeemer.index = values[1]
        return redeemer


def plutus_script_hash(
    script: Union[bytes, PlutusV1Script, PlutusV2Script]
) -> ScriptHash:
    """Calculates the hash of a Plutus script.

    Args:
        script (Union[bytes, PlutusV1Script, PlutusV2Script]): A plutus script.

    Returns:
        ScriptHash: blake2b hash of the script.
    """
    return script_hash(script)


def script_hash(
    script: Union[bytes, NativeScript, PlutusV1Script, PlutusV2Script]
) -> ScriptHash:
    """Calculates the hash of a script, which could be either native script or plutus script.

    Args:
        script (Union[bytes, NativeScript, PlutusV1Script, PlutusV2Script]): A script.

    Returns:
        ScriptHash: blake2b hash of the script.
    """
    if isinstance(script, NativeScript):
        return script.hash()
    elif isinstance(script, PlutusV1Script) or type(script) is bytes:
        return ScriptHash(
            blake2b(bytes.fromhex("01") + script, SCRIPT_HASH_SIZE, encoder=RawEncoder)
        )
    elif isinstance(script, PlutusV2Script):
        return ScriptHash(
            blake2b(bytes.fromhex("02") + script, SCRIPT_HASH_SIZE, encoder=RawEncoder)
        )
    else:
        raise TypeError(f"Unexpected script type: {type(script)}")


class PlutusV1Script(bytes):
    pass


class PlutusV2Script(bytes):
    pass
