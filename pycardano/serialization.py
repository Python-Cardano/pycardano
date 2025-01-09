"""Defines CBOR serialization interfaces and provides useful serialization classes."""

from __future__ import annotations

import re
import typing
from collections import OrderedDict, UserList, defaultdict
from copy import deepcopy
from dataclasses import Field, dataclass, fields
from datetime import datetime
from decimal import Decimal
from functools import wraps
from inspect import isclass
from typing import (
    Any,
    Callable,
    ClassVar,
    Dict,
    Generic,
    List,
    Optional,
    Type,
    TypeVar,
    Union,
    get_type_hints,
)

from cbor2 import CBOREncoder, CBORSimpleValue, CBORTag, dumps, loads, undefined
from frozendict import frozendict
from frozenlist import FrozenList
from pprintpp import pformat

from pycardano.exception import DeserializeException, SerializeException
from pycardano.types import check_type, typechecked

__all__ = [
    "default_encoder",
    "IndefiniteList",
    "Primitive",
    "CBORBase",
    "CBORSerializable",
    "ArrayCBORSerializable",
    "MapCBORSerializable",
    "DictCBORSerializable",
    "RawCBOR",
    "list_hook",
    "limit_primitive_type",
    "OrderedSet",
    "NonEmptyOrderedSet",
]

T = TypeVar("T")


def _identity(x):
    return x


class IndefiniteList(UserList):
    def __init__(self, li: Primitive):  # type: ignore
        super().__init__(li)  # type: ignore


class IndefiniteFrozenList(FrozenList, IndefiniteList):  # type: ignore
    pass


@dataclass
class ByteString:
    value: bytes

    def __hash__(self):
        return hash(self.value)

    def __eq__(self, other: object):
        if isinstance(other, ByteString):
            return self.value == other.value
        elif isinstance(other, bytes):
            return self.value == other
        else:
            return False


@dataclass
class RawCBOR:
    """A wrapper class for bytes that represents a CBOR value."""

    cbor: bytes


Primitive = Union[
    bytes,
    bytearray,
    str,
    int,
    float,
    Decimal,
    bool,
    None,
    tuple,
    list,
    IndefiniteList,
    dict,
    defaultdict,
    OrderedDict,
    datetime,
    re.Pattern,
    CBORSimpleValue,
    CBORTag,
    set,
    frozenset,
    frozendict,
    FrozenList,
    IndefiniteFrozenList,
    ByteString,
]

PRIMITIVE_TYPES = (
    bytes,
    bytearray,
    str,
    int,
    float,
    Decimal,
    bool,
    type(None),
    tuple,
    list,
    IndefiniteList,
    dict,
    defaultdict,
    OrderedDict,
    type(undefined),
    datetime,
    re.Pattern,
    CBORSimpleValue,
    CBORTag,
    set,
    frozenset,
    frozendict,
    FrozenList,
    IndefiniteFrozenList,
)
"""
A list of types that could be encoded by
`Cbor2 encoder <https://cbor2.readthedocs.io/en/latest/modules/encoder.html>`_ directly.
"""


def limit_primitive_type(*allowed_types):
    """
    A helper function to validate primitive type given to from_primitive class methods

    Not exposed to public by intention.
    """

    def decorator(func):
        @wraps(func)
        def wrapper(cls, value: Primitive):
            if not isinstance(value, allowed_types):
                allowed_types_str = [
                    allowed_type.__name__ for allowed_type in allowed_types
                ]
                raise DeserializeException(
                    f"{allowed_types_str} typed value is required for deserialization. Got {type(value)}: {value}"
                )
            return func(cls, value)

        return wrapper

    return decorator


CBORBase = TypeVar("CBORBase", bound="CBORSerializable")


def default_encoder(
    encoder: CBOREncoder, value: Union[CBORSerializable, IndefiniteList]
):
    """A fallback function that encodes CBORSerializable to CBOR"""
    assert isinstance(
        value,
        (
            ByteString,
            CBORSerializable,
            IndefiniteList,
            RawCBOR,
            FrozenList,
            IndefiniteFrozenList,
            frozendict,
        ),
    ), (
        f"Type of input value is not CBORSerializable, " f"got {type(value)} instead."
    )
    if isinstance(value, (IndefiniteList, IndefiniteFrozenList)):
        # Currently, cbor2 doesn't support indefinite list, therefore we need special
        # handling here to explicitly write header (b'\x9f'), each body item, and footer (b'\xff') to
        # the output bytestring.
        encoder.write(b"\x9f")
        for item in value:
            encoder.encode(item)
        encoder.write(b"\xff")
    elif isinstance(value, ByteString):
        if len(value.value) > 64:
            encoder.write(b"\x5f")
            for i in range(0, len(value.value), 64):
                imax = min(i + 64, len(value.value))
                encoder.encode(value.value[i:imax])
            encoder.write(b"\xff")
        else:
            encoder.encode(value.value)
    elif isinstance(value, RawCBOR):
        encoder.write(value.cbor)
    elif isinstance(value, FrozenList):
        encoder.encode(list(value))
    elif isinstance(value, frozendict):
        encoder.encode(dict(value))
    else:
        encoder.encode(value.to_validated_primitive())


@typechecked
class CBORSerializable:
    """
    CBORSerializable standardizes the interfaces a class should implement in order for it to be serialized to and
    deserialized from CBOR.

    Two required interfaces to implement are :meth:`to_primitive` and :meth:`from_primitive`.
    :meth:`to_primitive` converts an object to a CBOR primitive type (see :const:`Primitive`), which could be then
    encoded by CBOR library. :meth:`from_primitive` restores an object from a CBOR primitive type.

    To convert a CBORSerializable to CBOR, use :meth:`to_cbor`.
    To restore a CBORSerializable from CBOR, use :meth:`from_cbor`.

    .. note::
        :meth:`to_primitive` needs to return a pure CBOR primitive type, meaning that the returned value and all its
        child elements have to be CBOR primitives, which could mean a good amount of work. An alternative but simpler
        approach is to implement :meth:`to_shallow_primitive` instead. `to_shallow_primitive` allows the returned object
        to be either CBOR :const:`Primitive` or a :class:`CBORSerializable`, as long as the :class:`CBORSerializable`
        does not refer to itself, which could cause infinite loops.
    """

    def to_shallow_primitive(self) -> Primitive:
        """
        Convert the instance to a CBOR primitive. If the primitive is a container, e.g. list, dict, the type of
        its elements could be either a Primitive or a CBORSerializable.

        Returns:
            :const:`Primitive`: A CBOR primitive.

        Raises:
            SerializeException: When the object could not be converted to CBOR primitive
                types.
        """
        raise NotImplementedError(
            f"'to_shallow_primitive()' is not implemented by {self.__class__}."
        )

    def to_primitive(self) -> Primitive:
        """Convert the instance and its elements to CBOR primitives recursively.

        Returns:
            :const:`Primitive`: A CBOR primitive.

        Raises:
            SerializeException: When the object or its elements could not be converted to
                CBOR primitive types.
        """
        result = self.to_shallow_primitive()

        def _dfs(value, freeze=False):
            if isinstance(value, CBORSerializable):
                return _dfs(value.to_primitive(), freeze)
            elif isinstance(value, (dict, OrderedDict, defaultdict)):
                _dict = type(value)()
                if hasattr(value, "default_factory"):
                    _dict.setdefault(value.default_factory)
                for k, v in value.items():
                    _dict[_dfs(k, freeze=True)] = _dfs(v, freeze)
                if freeze:
                    return frozendict(_dict)
                return _dict
            elif isinstance(value, set):
                _set = set(_dfs(v, freeze=True) for v in value)
                if freeze:
                    return frozenset(_set)
                return _set
            elif isinstance(value, tuple):
                return tuple(_dfs(v, freeze) for v in value)
            elif isinstance(value, list):
                _list = [_dfs(v, freeze) for v in value]
                if freeze:
                    fl = FrozenList(_list)
                    fl.freeze()
                    return fl
                return _list
            elif isinstance(value, IndefiniteList):
                _list = [_dfs(v, freeze) for v in value]
                if freeze:
                    fl = IndefiniteFrozenList(_list)
                    fl.freeze()
                    return fl
                return IndefiniteList(_list)
            elif isinstance(value, CBORTag):
                return CBORTag(value.tag, _dfs(value.value, freeze))
            else:
                return value

        return _dfs(result)

    def validate(self):
        """Validate the data stored in the current instance. Defaults to always pass.

        Raises:
            InvalidDataException: When the data is invalid.
        """
        type_hints = get_type_hints(self.__class__)

        def _check_recursive(value, type_hint):
            if type_hint is Any:
                return True

            if isinstance(value, CBORSerializable):
                value.validate()

            origin = getattr(type_hint, "__origin__", None)
            if origin is None:
                return isinstance(value, type_hint)
            elif origin is ClassVar:
                return _check_recursive(value, type_hint.__args__[0])
            elif origin is Union:
                return any(_check_recursive(value, arg) for arg in type_hint.__args__)
            elif origin is Dict or isinstance(value, (dict, frozendict)):
                key_type, value_type = type_hint.__args__
                return all(
                    _check_recursive(k, key_type) and _check_recursive(v, value_type)
                    for k, v in value.items()
                )
            elif origin in (list, set, tuple, frozenset, OrderedSet):
                if value is None:
                    return True
                args = type_hint.__args__
                if len(args) == 1:
                    return all(_check_recursive(item, args[0]) for item in value)
                elif len(args) > 1:
                    return all(
                        _check_recursive(item, arg) for item, arg in zip(value, args)
                    )
            return True  # We don't know how to check this type

        for field_name, field_type in type_hints.items():
            field_value = getattr(self, field_name)
            if not _check_recursive(field_value, field_type):
                raise TypeError(
                    f"Field '{field_name}' should be of type {field_type}, "
                    f"got {repr(field_value)} instead."
                )

    def to_validated_primitive(self) -> Primitive:
        """Convert the instance and its elements to CBOR primitives recursively with data validated by :meth:`validate`
        method.

        Returns:
            :const:`Primitive`: A CBOR primitive.

        Raises:
            SerializeException: When the object or its elements could not be converted to
                CBOR primitive types.
        """
        self.validate()
        return self.to_primitive()

    @classmethod
    def from_primitive(cls: Type[CBORBase], value: Any) -> CBORBase:
        """Turn a CBOR primitive to its original class type.

        Args:
            cls (CBORBase): The original class type.
            value (:const:`Primitive`): A CBOR primitive.

        Returns:
            CBORBase: A CBOR serializable object.

        Raises:
            DeserializeException: When the object could not be restored from primitives.
        """
        raise NotImplementedError(
            f"'from_primitive()' is not implemented by {cls.__name__}."
        )

    def to_cbor(self) -> bytes:
        """Encode a Python object into CBOR bytes.

        Returns:
            bytes: Python object encoded in cbor bytes.

        Examples:
            >>> class Test(CBORSerializable):
            ...     def __init__(self, number1, number2):
            ...         self.number1 = number1
            ...         self.number2 = number2
            ...
            ...     def to_primitive(value):
            ...         return [value.number1, value.number2]
            ...
            ...     @classmethod
            ...     def from_primitive(cls, value):
            ...         return cls(value[0], value[1])
            ...
            ...     def __repr__(self):
            ...         return f"Test({self.number1}, {self.number2})"
            >>> a = Test(1, 2)
            >>> a.to_cbor().hex()
            '820102'
        """
        return dumps(self, default=default_encoder)

    def to_cbor_hex(self) -> str:
        """Encode a Python object into CBOR hex.

        Returns:
            str: Python object encoded in cbor hex string.
        """
        return self.to_cbor().hex()

    @classmethod
    def from_cbor(cls, payload: Union[str, bytes]) -> CBORSerializable:
        """Restore a CBORSerializable object from a CBOR.

        Args:
            payload (Union[str, bytes]): CBOR bytes or hex string to restore from.

        Returns:
            CBORSerializable: Restored CBORSerializable object.

        Examples:

            Basic use case:

            >>> class Test(CBORSerializable):
            ...     def __init__(self, number1, number2):
            ...         self.number1 = number1
            ...         self.number2 = number2
            ...
            ...     def to_primitive(value):
            ...         return [value.number1, value.number2]
            ...
            ...     @classmethod
            ...     def from_primitive(cls, value):
            ...         return cls(value[0], value[1])
            ...
            ...     def __repr__(self):
            ...         return f"Test({self.number1}, {self.number2})"
            >>> a = Test(1, 2)
            >>> cbor_hex = a.to_cbor_hex()
            >>> print(Test.from_cbor(cbor_hex))
            Test(1, 2)

            For a CBORSerializable that has CBORSerializables as attributes, we will need to pass
            each child value to the :meth:`from_primitive` method of its corresponding CBORSerializable. Example:

            >>> class TestParent(CBORSerializable):
            ...     def __init__(self, number1, test):
            ...         self.number1 = number1
            ...         self.test = test
            ...
            ...     def to_shallow_primitive(value): # Implementing `to_shallow_primitive` simplifies the work.
            ...         return [value.number1, value.test]
            ...
            ...     @classmethod
            ...     def from_primitive(cls, value):
            ...         test = Test.from_primitive(value[1]) # Restore test by passing `value[1]` to
            ...                                              # `Test.from_primitive`
            ...         return cls(value[0], test)
            ...
            ...     def __repr__(self):
            ...         return f"TestParent({self.number1}, {self.test})"
            >>> a = Test(1, 2)
            >>> b = TestParent(3, a)
            >>> b
            TestParent(3, Test(1, 2))
            >>> cbor_hex = b.to_cbor_hex()
            >>> cbor_hex
            '8203820102'
            >>> print(TestParent.from_cbor(cbor_hex))
            TestParent(3, Test(1, 2))

        """
        if type(payload) is str:
            payload = bytes.fromhex(payload)
        value = loads(payload)  # type: ignore
        return cls.from_primitive(value)

    def __repr__(self):
        return pformat(vars(self), indent=2)


def _restore_dataclass_field(
    f: Field, v: Primitive
) -> Union[Primitive, CBORSerializable]:
    """Try to restore a value back to its original type based on information given in field.

    Args:
        f (dataclass_field): A data class field.
        v (:const:`Primitive`): A CBOR primitive.

    Returns:
        Union[:const:`Primitive`, CBORSerializable]: A CBOR primitive or a CBORSerializable.
    """

    if "object_hook" in f.metadata:
        return f.metadata["object_hook"](v)
    return _restore_typed_primitive(f.type, v)


def _restore_typed_primitive(
    t: typing.Type, v: Primitive
) -> Union[Primitive, CBORSerializable]:
    """Try to restore a value back to its original type based on information given in field.

    Args:
        f (type): A type
        v (:const:`Primitive`): A CBOR primitive.

    Returns:
        Union[:const:`Primitive`, CBORSerializable]: A CBOR primitive or a CBORSerializable.
    """

    if t is Any or (t in PRIMITIVE_TYPES and isinstance(v, t)):
        return v
    elif isclass(t) and issubclass(t, CBORSerializable):
        return t.from_primitive(v)
    elif hasattr(t, "__origin__") and (t.__origin__ is list):
        t_args = t.__args__
        if len(t_args) != 1:
            raise DeserializeException(
                f"List types need exactly one type argument, but got {t_args}"
            )
        t = t_args[0]
        if not isinstance(v, list):
            raise DeserializeException(f"Expected type list but got {type(v)}")
        return IndefiniteList([_restore_typed_primitive(t, w) for w in v])
    elif isclass(t) and t == ByteString:
        if not isinstance(v, bytes):
            raise DeserializeException(f"Expected type bytes but got {type(v)}")
        return ByteString(v)
    elif isclass(t) and t.__name__ in [
        "PlutusV1Script",
        "PlutusV2Script",
        "PlutusV3Script",
    ]:
        if not isinstance(v, bytes):
            raise DeserializeException(f"Expected type bytes but got {type(v)}")
        return t(v)
    elif hasattr(t, "__origin__") and (t.__origin__ is dict):
        t_args = t.__args__
        if len(t_args) != 2:
            raise DeserializeException(
                f"Dict types need exactly two type arguments, but got {t_args}"
            )
        key_t = t_args[0]
        val_t = t_args[1]
        if not isinstance(v, dict):
            raise DeserializeException(f"Expected dict type but got {type(v)}")
        return {
            _restore_typed_primitive(key_t, key): _restore_typed_primitive(val_t, val)
            for key, val in v.items()
        }
    elif hasattr(t, "__origin__") and (
        t.__origin__ is Union or t.__origin__ is Optional
    ):
        t_args = t.__args__
        for t in t_args:
            try:
                return _restore_typed_primitive(t, v)
            except DeserializeException:
                pass
        raise DeserializeException(
            f"Cannot deserialize object: \n{v}\n in any valid type from {t_args}."
        )
    elif isclass(t) and issubclass(t, IndefiniteList):
        try:
            return t(v)
        except TypeError:
            raise DeserializeException(f"Can not initialize IndefiniteList from {v}")
    raise DeserializeException(f"Cannot deserialize object: \n{v}\n to type {t}.")


ArrayBase = TypeVar("ArrayBase", bound="ArrayCBORSerializable")
"""A generic type that is bounded by ArrayCBORSerializable."""


@dataclass(repr=False)
class ArrayCBORSerializable(CBORSerializable):
    """
    A base class that can serialize its child `dataclass <https://docs.python.org/3/library/dataclasses.html>`_
    into a `CBOR array <https://datatracker.ietf.org/doc/html/rfc8610#section-3.4>`_.

    The class is useful when the position of each item in a list have its own semantic meaning.

    Examples:

        Basic usages:

        >>> from dataclasses import dataclass
        >>> @dataclass
        ... class Test1(ArrayCBORSerializable):
        ...     a: str
        ...     b: str=None
        >>> @dataclass
        ... class Test2(ArrayCBORSerializable):
        ...     c: str
        ...     test1: Test1
        >>> t = Test2(c="c", test1=Test1(a="a"))
        >>> t
        Test2(c='c', test1=Test1(a='a', b=None))
        >>> cbor_hex = t.to_cbor_hex() # doctest: +SKIP
        >>> cbor_hex # doctest: +SKIP
        '826163826161f6'
        >>> Test2.from_cbor(cbor_hex) # doctest: +SKIP
        Test2(c='c', test1=Test1(a='a', b=None))

        A value of `None` will be encoded as nil (#7.22) in cbor. This will become a problem if the field is meant to be
        optional. To exclude an optional attribute from cbor, we can use `field` constructor with a metadata field
        "optional" set to True and default value set to `None`.

        .. Note::
            In ArrayCBORSerializable, all non-optional fields have to be declared before any optional field.

        Example:

        >>> from dataclasses import dataclass, field
        >>> @dataclass
        ... class Test1(ArrayCBORSerializable):
        ...     a: str
        ...     b: str=field(default=None, metadata={"optional": True})
        >>> @dataclass
        ... class Test2(ArrayCBORSerializable):
        ...     c: str
        ...     test1: Test1
        >>> t = Test2(c="c", test1=Test1(a="a"))
        >>> t
        Test2(c='c', test1=Test1(a='a', b=None))
        >>> t.to_primitive() # Notice below that attribute "b" is not included in converted primitive.
        ['c', ['a']]
        >>> cbor_hex = t.to_cbor_hex() # doctest: +SKIP
        >>> cbor_hex # doctest: +SKIP
        '826163816161'
        >>> Test2.from_cbor(cbor_hex) # doctest: +SKIP
        Test2(c='c', test1=Test1(a='a', b=None))
    """

    def to_shallow_primitive(self) -> Primitive:
        """
        Returns:
            :const:`Primitive`: A CBOR primitive.

        Raises:
            SerializeException: When the object could not be converted to CBOR primitive
                types.
        """
        primitives = []
        for f in fields(self):
            val = getattr(self, f.name)
            if val is None and f.metadata.get("optional"):
                continue
            primitives.append(val)
        return primitives

    @classmethod
    @limit_primitive_type(list, tuple)
    def from_primitive(cls: Type[ArrayBase], values: Union[list, tuple]) -> ArrayBase:
        """Restore a primitive value to its original class type.

        Args:
            cls (ArrayBase): The original class type.
            values (List[Primitive]): A list whose elements are CBOR primitives.

        Returns:
            :const:`ArrayBase`: Restored object.

        Raises:
            DeserializeException: When the object could not be restored from primitives.
        """
        all_fields = [f for f in fields(cls) if f.init]

        restored_vals = []
        type_hints = get_type_hints(cls)
        for f, v in zip(all_fields, values):
            if not isclass(f.type):
                f.type = type_hints[f.name]
            v = _restore_dataclass_field(f, v)
            restored_vals.append(v)
        obj = cls(*restored_vals)
        for i in range(len(all_fields), len(values)):
            setattr(obj, f"unknown_field{i - len(all_fields)}", values[i])
        return obj

    def __repr__(self):
        return super().__repr__()


MapBase = TypeVar("MapBase", bound="MapCBORSerializable")
"""A generic type that is bounded by MapCBORSerializable."""


@dataclass(repr=False)
class MapCBORSerializable(CBORSerializable):
    """
    A base class that can serialize its child `dataclass <https://docs.python.org/3/library/dataclasses.html>`_
    into a `CBOR Map <https://datatracker.ietf.org/doc/html/rfc8610#section-3.5.1>`_.

    The class is useful when each key in a map have its own semantic meaning.

    Examples:

        Basic usage:

        >>> from dataclasses import dataclass, field
        >>> @dataclass
        ... class Test1(MapCBORSerializable):
        ...     a: str=""
        ...     b: str=""
        >>> @dataclass
        ... class Test2(MapCBORSerializable):
        ...     c: str=None
        ...     test1: Test1=field(default_factory=Test1)
        >>> t = Test2(test1=Test1(a="a"))
        >>> t
        Test2(c=None, test1=Test1(a='a', b=''))
        >>> t.to_primitive()
        {'c': None, 'test1': {'a': 'a', 'b': ''}}
        >>> cbor_hex = t.to_cbor_hex() # doctest: +SKIP
        >>> cbor_hex # doctest: +SKIP
        'a26163f6657465737431a261616161616260'
        >>> Test2.from_cbor(cbor_hex) # doctest: +SKIP
        Test2(c=None, test1=Test1(a='a', b=''))

        In the example above, all keys in the map share the same name as their corresponding attributes. However,
        sometimes we want to use different keys when serializing some attributes, this could be achieved by adding a
        "key" value to the metadata of a field. Example:

        >>> from dataclasses import dataclass, field
        >>> @dataclass
        ... class Test1(MapCBORSerializable):
        ...     a: str=field(default="", metadata={"key": "0"})
        ...     b: str=field(default="", metadata={"key": "1"})
        >>> @dataclass
        ... class Test2(MapCBORSerializable):
        ...     c: str=field(default=None, metadata={"key": "0", "optional": True})
        ...     test1: Test1=field(default_factory=Test1, metadata={"key": "1"})
        >>> t = Test2(test1=Test1(a="a"))
        >>> t
        Test2(c=None, test1=Test1(a='a', b=''))
        >>> t.to_primitive()
        {'1': {'0': 'a', '1': ''}}
        >>> cbor_hex = t.to_cbor_hex() # doctest: +SKIP
        >>> cbor_hex # doctest: +SKIP
        'a16131a261306161613160'
        >>> Test2.from_cbor(cbor_hex) # doctest: +SKIP
        Test2(c=None, test1=Test1(a='a', b=''))
    """

    def to_shallow_primitive(self) -> Primitive:
        primitives = {}
        for f in fields(self):
            if "key" in f.metadata:
                key = f.metadata["key"]
            else:
                key = f.name
            if key in primitives:
                raise SerializeException(f"Key: '{key}' already exists in the map.")
            val = getattr(self, f.name)
            if val is None and f.metadata.get("optional"):
                continue
            primitives[key] = val
        return primitives

    @classmethod
    @limit_primitive_type(dict)
    def from_primitive(cls: Type[MapBase], values: dict) -> MapBase:
        """Restore a primitive value to its original class type.

        Args:
            cls (MapBase): The original class type.
            values (:const:`Primitive`): A CBOR primitive.

        Returns:
            :const:`MapBase`: Restored object.

        Raises:
            :class:`pycardano.exception.DeserializeException`: When the object could not be restored from primitives.
        """
        all_fields = {f.metadata.get("key", f.name): f for f in fields(cls) if f.init}

        kwargs = {}
        type_hints = get_type_hints(cls)
        for key in values:
            if key not in all_fields:
                raise DeserializeException(f"Unexpected map key {key} in CBOR.")
            f = all_fields[key]
            v = values[key]
            if not isclass(f.type):
                f.type = type_hints[f.name]
            v = _restore_dataclass_field(f, v)
            kwargs[f.name] = v
        return cls(**kwargs)

    def __repr__(self):
        return super().__repr__()


DictBase = TypeVar("DictBase", bound="DictCBORSerializable")
"""A generic type that is bounded by DictCBORSerializable."""


class DictCBORSerializable(CBORSerializable):
    """A dictionary class where all keys share the same type and all values share the same type.

    Examples:

        >>> @dataclass
        ... class Test1(ArrayCBORSerializable):
        ...     a: int
        ...     b: str
        >>>
        >>> class Test2(DictCBORSerializable):
        ...     KEY_TYPE = str
        ...     VALUE_TYPE = Test1
        >>>
        >>> t = Test2()
        >>> t["x"] = Test1(a=1, b="x")
        >>> t["y"] = Test1(a=2, b="y")
        >>> primitives = t.to_primitive()
        >>> deserialized = Test2.from_primitive(primitives)
        >>> assert t == deserialized
        >>> t[1] = 2
        Traceback (most recent call last):
         ...
        typeguard.TypeCheckError: int is not an instance of str
    """

    KEY_TYPE = Type[Any]
    VALUE_TYPE = Type[Any]

    def __init__(self, *args, **kwargs):
        self.data = dict(*args, **kwargs)

    def __getattr__(self, item):
        return getattr(self.data, item)

    def __setitem__(self, key: Any, value: Any):
        check_type(key, self.KEY_TYPE)
        check_type(value, self.VALUE_TYPE)
        self.data[key] = value

    def __getitem__(self, key):
        return self.data[key]

    def __eq__(self, other):
        if isinstance(other, DictCBORSerializable):
            return self.data == other.data
        else:
            return False

    def __len__(self):
        return len(self.data)

    def __iter__(self):
        return iter(self.data)

    def __delitem__(self, key):
        del self.data[key]

    def __repr__(self):
        return self.data.__repr__()

    def __copy__(self):
        return self.__class__(self)

    def __deepcopy__(self, memodict={}):
        return self.__class__(deepcopy(self.data))

    def validate(self):
        for key, value in self.data.items():
            if isinstance(key, CBORSerializable):
                key.validate()
            if isinstance(value, CBORSerializable):
                value.validate()

    def to_shallow_primitive(self) -> dict:
        # Sort keys in a map according to https://datatracker.ietf.org/doc/html/rfc7049#section-3.9
        def _get_sortable_val(key):
            if isinstance(key, CBORSerializable):
                cbor_bytes = key.to_cbor()
            else:
                cbor_bytes = dumps(key)
            return len(cbor_bytes), cbor_bytes

        return dict(sorted(self.data.items(), key=lambda x: _get_sortable_val(x[0])))

    @classmethod
    @limit_primitive_type(dict)
    def from_primitive(cls: Type[DictBase], value: dict) -> DictBase:
        """Restore a primitive value to its original class type.

        Args:
            cls (DictBase): The original class type.
            value (:const:`Primitive`): A CBOR primitive.

        Returns:
            :const:`DictBase`: Restored object.

        Raises:
            DeserializeException: When the object could not be restored from primitives.
        """
        restored = cls()
        for k, v in value.items():
            k = (
                cls.KEY_TYPE.from_primitive(k)  # type: ignore
                if isclass(cls.KEY_TYPE) and issubclass(cls.KEY_TYPE, CBORSerializable)
                else k
            )
            v = (
                cls.VALUE_TYPE.from_primitive(v)  # type: ignore
                if isclass(cls.VALUE_TYPE)
                and issubclass(cls.VALUE_TYPE, CBORSerializable)
                else v
            )
            restored[k] = v
        return restored

    def copy(self) -> DictCBORSerializable:
        return self.__class__(self)


@typechecked
def list_hook(
    cls: Type[CBORBase],
) -> Callable[[List[Primitive]], List[CBORBase]]:
    """A factory that generates a Callable which turns a list of Primitive to a list of CBORSerializables.

    Args:
        cls (CBORBase): The type of CBORSerializable the list will be converted to.

    Returns:
        Callable[[List[Primitive]], List[CBORBase]]: An Callable that restores a list of Primitive to a list of
            CBORSerializables.
    """
    return lambda vals: [cls.from_primitive(v) for v in vals]


class OrderedSet(list, CBORSerializable):
    """An ordered set implementation that maintains insertion order and enforces uniqueness.
    Handles both pre-Conway (list) and Conway era (tagged set) serialization formats."""

    _inner_type: Optional[Type] = None

    def __init__(self, iterable=None, *, use_tag: bool = True):
        super().__init__()
        self._set = set()
        self._use_tag = use_tag
        if iterable:
            for item in iterable:
                self.append(item)

    def append(self, item):
        # Use string representation for unhashable items
        item_hash = str(item)
        if item_hash not in self._set:
            self._set.add(item_hash)
            super().append(item)

    def extend(self, items):
        for item in items:
            self.append(item)

    def __contains__(self, item):
        return str(item) in self._set

    def __eq__(self, other):
        if isinstance(other, list):
            # For regular lists, only compare values
            return list(self) == other
        if isinstance(other, OrderedSet):
            # For OrderedSets, compare both values and use_tag
            return list(self) == list(other) and self._use_tag == other._use_tag
        return NotImplemented

    def to_shallow_primitive(self) -> Primitive:
        """Convert to a primitive type. Uses tag 258 for Conway era if _use_tag is True."""
        items = list(self)
        return CBORTag(258, items) if self._use_tag else items

    @classmethod
    def __class_getitem__(cls, item):
        """Support for generic type parameters, e.g., OrderedSet[TransactionInput]."""
        if cls is OrderedSet:
            new_cls = type(f"OrderedSet[{item.__name__}]", (_GenericOrderedSet,), {})
            new_cls._inner_type = item
            return new_cls
        return cls

    @classmethod
    def from_primitive(cls, value: Any) -> "OrderedSet":
        """Create an OrderedSet from a value. Only accepts list/tuple values, optionally tagged with 258."""
        try:
            # Determine if we should use tag 258 when serializing this set
            use_tag = isinstance(value, CBORTag) and value.tag == 258
            items = value.value if use_tag else value

            # When decoding CBORTag.258, cbor2 automatically converts it into a tuple or a set
            # see https://github.com/agronholm/cbor2/blob/d9cee77308056776859d40c81a82fac5f414d4db/cbor2/_decoder.py#L779 # noqa
            if not isinstance(items, (list, tuple, set)):
                raise DeserializeException(
                    f"Expected list, tuple, or set, got {type(items)}"
                )

            # Use the inner type directly from the class
            if cls._inner_type and hasattr(cls._inner_type, "from_primitive"):
                items = [cls._inner_type.from_primitive(item) for item in items]

            return cls(items, use_tag=use_tag)
        except (AttributeError, TypeError) as e:
            raise DeserializeException(
                f"Cannot deserialize {value} to OrderedSet: {str(e)}"
            )


class _GenericOrderedSet(OrderedSet, Generic[T]):
    """Internal class for handling generic type parameters."""

    pass


class NonEmptyOrderedSet(OrderedSet):
    """An ordered set that must be non-empty when serialized.
    Used for CDDL nonempty_set definitions in the Conway era."""

    def validate(self):
        """Validate that the set is not empty before serialization."""
        if not self:
            raise SerializeException(
                "NonEmptyOrderedSet cannot be empty when serialized"
            )

    def to_validated_primitive(self) -> Primitive:
        """Convert to a primitive type with validation. Uses tag 258 for Conway era if _use_tag is True."""
        self.validate()
        return self.to_primitive()

    @classmethod
    def __class_getitem__(cls, item):
        """Support for generic type parameters, e.g., NonEmptyOrderedSet[TransactionInput]."""
        if cls is NonEmptyOrderedSet:
            new_cls = type(
                f"NonEmptyOrderedSet[{item.__name__}]",
                (_GenericNonEmptyOrderedSet,),
                {},
            )
            new_cls._inner_type = item
            return new_cls
        return cls


class _GenericNonEmptyOrderedSet(NonEmptyOrderedSet, Generic[T]):
    """Internal class for handling generic type parameters for NonEmptyOrderedSet."""

    pass
