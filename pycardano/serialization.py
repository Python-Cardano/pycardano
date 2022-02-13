"""Defines CBOR serialization interfaces and provides useful serialization classes."""

from __future__ import annotations

import re
from collections import OrderedDict, defaultdict
from dataclasses import Field, dataclass, fields
from datetime import datetime
from decimal import Decimal
from inspect import isclass
from pprint import pformat
from typing import Any, Callable, ClassVar, List, Type, TypeVar, Union, get_type_hints

from cbor2 import dumps, loads
from cbor2.types import CBORSimpleValue, CBORTag, undefined
from typeguard import check_type, typechecked

from pycardano.exception import (
    DeserializeException,
    InvalidArgumentException,
    SerializeException,
)

__all__ = [
    "Primitive",
    "CBORBase",
    "CBORSerializable",
    "ArrayCBORSerializable",
    "MapCBORSerializable",
    "DictCBORSerializable",
    "list_hook",
]


Primitive = TypeVar(
    "Primitive",
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
)
"""
A list of types that could be encoded by
`Cbor2 encoder <https://cbor2.readthedocs.io/en/latest/modules/encoder.html>`_ directly.
"""

CBORBase = TypeVar("CBORBase", bound="CBORSerializable")


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
            :class:`pycardano.exception.SerializeException`: When the object could not be converted to CBOR primitive
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
            :class:`pycardano.exception.SerializeException`: When the object or its elements could not be converted to
                CBOR primitive types.
        """
        result = self.to_shallow_primitive()
        container_types = (dict, OrderedDict, defaultdict, set, frozenset, tuple, list)

        def _helper(value):
            if isinstance(value, CBORSerializable):
                return value.to_primitive()
            elif isinstance(value, container_types):
                return _dfs(value)
            else:
                return value

        def _dfs(value):
            if isinstance(value, (dict, OrderedDict, defaultdict)):
                new_result = type(value)()
                if hasattr(value, "default_factory"):
                    new_result.setdefault(value.default_factory)
                for k, v in value.items():
                    new_result[_helper(k)] = _helper(v)
                return new_result
            elif isinstance(value, set):
                return {_helper(v) for v in value}
            elif isinstance(value, frozenset):
                return frozenset({_helper(v) for v in value})
            elif isinstance(value, tuple):
                return tuple([_helper(k) for k in value])
            elif isinstance(value, list):
                return [_helper(k) for k in value]
            else:
                return value

        return _dfs(result)

    @classmethod
    def from_primitive(cls: Type[CBORBase], value: Primitive) -> CBORBase:
        """Turn a CBOR primitive to its original class type.

        Args:
            cls (Type[CBORBase]): The original class type.
            value (:const:`Primitive`): A CBOR primitive.

        Returns:
            CBORBase: A CBOR serializable object.

        Raises:
            :class:`pycardano.exception.DeserializeException`: When the object could not be restored from primitives.
        """
        raise NotImplementedError(
            f"'from_primitive()' is not implemented by {cls.__name__}."
        )

    def to_cbor(self, encoding: str = "hex") -> Union[str, bytes]:
        """Encode a Python object into CBOR format.

        Args:
            encoding (str): Encoding to use. Choose from "hex" or "bytes".

        Returns:
            Union[str, bytes]: CBOR encoded in a hex string if encoding is hex (default) or bytes if encoding is bytes.

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
            >>> a.to_cbor()
            '820102'
        """
        valid_encodings = ("hex", "bytes")

        # Make sure encoding is selected correctly before proceeding further.
        if encoding not in ("hex", "bytes"):
            raise InvalidArgumentException(
                f"Invalid encoding: {encoding}. Please choose from {valid_encodings}"
            )

        def _default_encoder(encoder, value):
            assert isinstance(value, CBORSerializable), (
                f"Type of input value is not CBORSerializable, "
                f"got {type(value)} instead."
            )
            encoder.encode(value.to_primitive())

        cbor = dumps(self, default=_default_encoder)
        if encoding == "hex":
            return cbor.hex()
        else:
            return cbor

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
            >>> cbor_hex = a.to_cbor()
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
            >>> cbor_hex = b.to_cbor()
            >>> cbor_hex
            '8203820102'
            >>> print(TestParent.from_cbor(cbor_hex))
            TestParent(3, Test(1, 2))

        """
        if type(payload) == str:
            payload = bytes.fromhex(payload)
        value = loads(payload)
        return cls.from_primitive(value)

    def __repr__(self):
        return pformat(vars(self))


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
    elif isclass(f.type) and issubclass(f.type, CBORSerializable):
        return f.type.from_primitive(v)
    elif hasattr(f.type, "__origin__") and f.type.__origin__ is Union:
        t_args = f.type.__args__
        for t in t_args:
            if isclass(t) and issubclass(t, CBORSerializable):
                try:
                    return t.from_primitive(v)
                except DeserializeException:
                    pass
            elif t in Primitive.__constraints__ and isinstance(v, t):
                return v
        raise DeserializeException(
            f"Cannot deserialize object: \n{v}\n in any valid type from {t_args}."
        )
    return v


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
        >>> cbor_hex = t.to_cbor()
        >>> cbor_hex
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
        >>> cbor_hex = t.to_cbor()
        >>> cbor_hex
        '826163816161'
        >>> Test2.from_cbor(cbor_hex) # doctest: +SKIP
        Test2(c='c', test1=Test1(a='a', b=None))
    """

    field_sorter: ClassVar[Callable[[List], List]] = lambda x: x

    def to_shallow_primitive(self) -> List[Primitive]:
        """
        Returns:
            :const:`Primitive`: A CBOR primitive.

        Raises:
            :class:`pycardano.exception.SerializeException`: When the object could not be converted to CBOR primitive
                types.
        """
        primitives = []
        for f in self.__class__.field_sorter(fields(self)):
            val = getattr(self, f.name)
            if val is None and f.metadata.get("optional"):
                continue
            primitives.append(val)
        return primitives

    @classmethod
    def from_primitive(cls: Type[ArrayBase], values: List[Primitive]) -> ArrayBase:
        """Restore a primitive value to its original class type.

        Args:
            cls (Type[ArrayBase]): The original class type.
            values (List[Primitive]): A list whose elements are CBOR primitives.

        Returns:
            :const:`ArrayBase`: Restored object.

        Raises:
            :class:`pycardano.exception.DeserializeException`: When the object could not be restored from primitives.
        """
        all_fields = fields(cls)
        if type(values) != list:
            raise DeserializeException(
                f"Expect input value to be a list, got a {type(values)} instead."
            )

        restored_vals = []
        type_hints = get_type_hints(cls)
        for f, v in zip(all_fields, values):
            if not isclass(f.type):
                f.type = type_hints[f.name]
            v = _restore_dataclass_field(f, v)
            restored_vals.append(v)
        return cls(*restored_vals)

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

        >>> from dataclasses import dataclass
        >>> @dataclass
        ... class Test1(MapCBORSerializable):
        ...     a: str=""
        ...     b: str=""
        >>> @dataclass
        ... class Test2(MapCBORSerializable):
        ...     c: str=None
        ...     test1: Test1=Test1()
        >>> t = Test2(test1=Test1(a="a"))
        >>> t
        Test2(c=None, test1=Test1(a='a', b=''))
        >>> t.to_primitive()
        {'c': None, 'test1': {'a': 'a', 'b': ''}}
        >>> cbor_hex = t.to_cbor()
        >>> cbor_hex
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
        ...     test1: Test1=field(default=Test1(), metadata={"key": "1"})
        >>> t = Test2(test1=Test1(a="a"))
        >>> t
        Test2(c=None, test1=Test1(a='a', b=''))
        >>> t.to_primitive()
        {'1': {'0': 'a', '1': ''}}
        >>> cbor_hex = t.to_cbor()
        >>> cbor_hex
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
    def from_primitive(cls: Type[MapBase], values: Primitive) -> MapBase:
        """Restore a primitive value to its original class type.

        Args:
            cls (Type[MapBase]): The original class type.
            values (:const:`Primitive`): A CBOR primitive.

        Returns:
            :const:`MapBase`: Restored object.

        Raises:
            :class:`pycardano.exception.DeserializeException`: When the object could not be restored from primitives.
        """
        all_fields = {f.metadata.get("key", f.name): f for f in fields(cls)}
        if type(values) != dict:
            raise DeserializeException(
                f"Expect input value to be a dict, got a {type(values)} instead."
            )

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


class DictCBORSerializable(dict, CBORSerializable):
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
        TypeError: type of key must be str; got int instead
    """

    KEY_TYPE = Any
    VALUE_TYPE = Any

    def __setitem__(self, key: KEY_TYPE, value: VALUE_TYPE):
        check_type("key", key, self.KEY_TYPE)
        check_type("value", value, self.VALUE_TYPE)
        super().__setitem__(key, value)

    def to_shallow_primitive(self) -> dict:
        return dict(self)

    @classmethod
    def from_primitive(cls: Type[DictBase], value: dict) -> DictBase:
        """Restore a primitive value to its original class type.

        Args:
            cls (Type[DictBase]): The original class type.
            value (:const:`Primitive`): A CBOR primitive.

        Returns:
            :const:`DictBase`: Restored object.

        Raises:
            :class:`pycardano.exception.DeserializeException`: When the object could not be restored from primitives.
        """
        if not value:
            raise DeserializeException(f"Cannot accept empty value {value}.")
        restored = cls()
        for k, v in value.items():
            k = (
                cls.KEY_TYPE.from_primitive(k)
                if isclass(cls.VALUE_TYPE)
                and issubclass(cls.KEY_TYPE, CBORSerializable)
                else k
            )
            v = (
                cls.VALUE_TYPE.from_primitive(v)
                if isclass(cls.VALUE_TYPE)
                and issubclass(cls.VALUE_TYPE, CBORSerializable)
                else v
            )
            restored[k] = v
        return restored

    def copy(self) -> DictBase:
        return self.__class__(self)


@typechecked
def list_hook(cls: Type[CBORBase]) -> Callable[[List[Primitive]], List[CBORBase]]:
    """A factory that generates a Callable which turns a list of Primitive to a list of CBORSerializables.

    Args:
        cls (CBORBase): The type of CBORSerializable the list will be converted to.

    Returns:
        Callable[[List[Primitive]], List[CBORBase]]: An Callable that restores a list of Primitive to a list of
            CBORSerializables.
    """
    return lambda vals: [cls.from_primitive(v) for v in vals]
