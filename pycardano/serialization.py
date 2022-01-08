from __future__ import annotations

import re
from collections import defaultdict, OrderedDict
from dataclasses import fields
from datetime import datetime
from decimal import Decimal
from inspect import isclass
from typing import Any, Callable, List, Union, get_type_hints

from cbor2 import dumps, loads
from cbor2.types import undefined, CBORSimpleValue, CBORTag

from pycardano.exception import DeserializeException, SerializeException

CBOR_PRIMITIVE = (bytes, bytearray, str, int, float, Decimal,
                  bool, type(None), tuple, list, dict, defaultdict,
                  OrderedDict, type(undefined), datetime,
                  type(re.compile("")), CBORSimpleValue, CBORTag,
                  set, frozenset)
"""
A list of types that could be encoded by
`Cbor2 encoder <https://cbor2.readthedocs.io/en/latest/modules/encoder.html>`_ directly.
"""


class CBORSerializable:
    """
    CBORSerializable standardizes the interfaces a class should implement in order for it to be serialized to and
    deserialized from CBOR hex.

    Two required interfaces to implement are :meth:`serialize` and :meth:`deserialize`.
    :meth:`serialize` converts an object to a CBOR primitive type, which could be encoded by
    CBOR library. :meth:`deserialize` restores an object from a CBOR primitive type.

    To convert a CBORSerializable to CBOR hex, use :meth:`to_cborhex`.
    To restore a CBORSerializable from CBOR hex, use :meth:`from_cborhex`.
    """

    def serialize(self) -> Union[CBOR_PRIMITIVE]:
        """Serialize the instance to a CBOR primitive type.

        Returns:
            Union[CBOR_PRIMITIVE]: A CBOR primitive type.

        Raises:
            :class:`pycardano.exception.SerializeException`: When the object could not be serialized.
        """
        raise NotImplementedError(f"'serialize()' is not implemented by {self.__class__}.")

    @classmethod
    def deserialize(cls, value: Union[CBOR_PRIMITIVE]) -> CBORSerializable:
        """Turn a CBOR primitive type to its original class type.

        Args:
            value (Union[CBOR_PRIMITIVE]): A CBOR primitive type.

        Returns:
            CBORSerializable: A CBOR serializable object.

        Raises:
            :class:`pycardano.exception.DeserializeException`: When the object could not be deserialized.
        """
        raise NotImplementedError(f"'deserialize()' is not implemented by {cls.__name__}.")

    def to_cborhex(self) -> str:
        """Encode an object into a CBOR hex string.

        Returns:
            str: CBOR hex encoded from the object

        Examples:
            >>> class Test(CBORSerializable):
            ...     def __init__(self, number1, number2):
            ...         self.number1 = number1
            ...         self.number2 = number2
            ...
            ...     def serialize(value):
            ...         return [value.number1, value.number2]
            ...
            ...     @classmethod
            ...     def deserialize(cls, value):
            ...         return cls(value[0], value[1])
            ...
            ...     def __repr__(self):
            ...         return f"Test({self.number1}, {self.number2})"
            >>> a = Test(1, 2)
            >>> a.to_cborhex()
            '820102'
        """
        return self.to_cbor().hex()

    @classmethod
    def from_cborhex(cls, payload: str) -> CBORSerializable:
        """Restore a CBORSerializable object from a CBOR hex.

        Args:
            payload (str): CBOR hex to restore.

        Returns:
            CBORSerializable: Restored CBORSerializable object.

        Examples:

            Basic use case:

            >>> class Test(CBORSerializable):
            ...     def __init__(self, number1, number2):
            ...         self.number1 = number1
            ...         self.number2 = number2
            ...
            ...     def serialize(value):
            ...         return [value.number1, value.number2]
            ...
            ...     @classmethod
            ...     def deserialize(cls, value):
            ...         return cls(value[0], value[1])
            ...
            ...     def __repr__(self):
            ...         return f"Test({self.number1}, {self.number2})"
            >>> a = Test(1, 2)
            >>> cbor_hex = a.to_cborhex()
            >>> print(Test.from_cborhex(cbor_hex))
            Test(1, 2)

            For a CBORSerializable that has CBORSerializables as attributes, we will need to pass
            each child value to the :meth:`deserialized` method of its corresponding CBORSerializable. Example:

            >>> class TestParent(CBORSerializable):
            ...     def __init__(self, number1, test):
            ...         self.number1 = number1
            ...         self.test = test
            ...
            ...     def serialize(value):
            ...         return [value.number1, value.test]
            ...
            ...     @classmethod
            ...     def deserialize(cls, value):
            ...         test = Test.deserialize(value[1]) # Restore test by passing `value[1]` to `Test.deserialize`
            ...         return cls(value[0], test)
            ...
            ...     def __repr__(self):
            ...         return f"TestParent({self.number1}, {self.test})"
            >>> a = Test(1, 2)
            >>> b = TestParent(3, a)
            >>> b
            TestParent(3, Test(1, 2))
            >>> cbor_hex = b.to_cborhex()
            >>> cbor_hex
            '8203820102'
            >>> print(TestParent.from_cborhex(cbor_hex))
            TestParent(3, Test(1, 2))

        """
        value = loads(bytes.fromhex(payload))
        return cls.deserialize(value)

    def to_cbor(self) -> bytes:
        """Same as :meth:`to_cborhex`, except the output type is bytes."""
        def _default_encoder(encoder, value):
            assert isinstance(value, CBORSerializable), f"Type of input value is not CBORSerializable, " \
                                                        f"got {type(value)} instead."
            encoder.encode(value.serialize())

        return dumps(self, default=_default_encoder)

    @classmethod
    def from_cbor(cls, payload: bytes) -> CBORSerializable:
        """Same as :meth:`from_cborhex`, except the input type is bytes."""
        value = loads(payload)
        return cls.deserialize(value)


class ArrayCBORSerializable(CBORSerializable):
    """
    A base class that can serialize its child `dataclass <https://docs.python.org/3/library/dataclasses.html>`_
    into a `CBOR array <https://datatracker.ietf.org/doc/html/rfc8610#section-3.4>`_.

    Examples

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
        >>> cbor_hex = t.to_cborhex()
        >>> cbor_hex
        '826163826161f6'
        >>> Test2.from_cborhex(cbor_hex) # doctest: +SKIP
        Test2(c='c', test1=Test1(a='a', b=None))

        A value of `None` will be encoded as nil (#7.22) in cbor. This will become a problem if the field is meant to be
        optional. To exclude an optional attribute from cbor, we can use `field` constructor with a metadata field
        "optional" set to True and default value set to `None`.

        **Note:** In ArrayCBORSerializable, all non-optional fields have to be declared before any optional field.

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
        >>> t.serialize()
        ['c', Test1(a='a', b=None)]
        >>> t.test1.serialize() # Notice 'b' is not included in the serialized object.
        ['a']
        >>> cbor_hex = t.to_cborhex()
        >>> cbor_hex
        '826163816161'
        >>> Test2.from_cborhex(cbor_hex) # doctest: +SKIP
        Test2(c='c', test1=Test1(a='a', b=None))
    """

    def serialize(self) -> Union[CBOR_PRIMITIVE]:
        serialized = []
        for field in fields(self):
            val = getattr(self, field.name)
            if val is None and field.metadata.get("optional"):
                continue
            serialized.append(val)
        return serialized

    @classmethod
    def deserialize(cls, values: Union[CBOR_PRIMITIVE]) -> CBORSerializable:
        all_fields = fields(cls)
        if type(values) != list:
            raise DeserializeException(f"Expect input value to be a list, got a {type(values)} instead.")

        wrapped_vals = []
        type_hints = get_type_hints(cls)
        for field, v in zip(all_fields, values):
            if not isclass(field.type):
                field.type = type_hints[field.name]
            if "object_hook" in field.metadata:
                v = field.metadata["object_hook"](v)
            elif isclass(field.type) and issubclass(field.type, CBORSerializable):
                v = field.type.deserialize(v)
            wrapped_vals.append(v)
        return cls(*wrapped_vals)


class MapCBORSerializable(CBORSerializable):
    """
    A base class that can serialize its child `dataclass <https://docs.python.org/3/library/dataclasses.html>`_
    into a `CBOR Map <https://datatracker.ietf.org/doc/html/rfc8610#section-3.5.1>`_.

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
        >>> cbor_hex = t.to_cborhex()
        >>> cbor_hex
        'a26163f6657465737431a261616161616260'
        >>> Test2.from_cborhex(cbor_hex) # doctest: +SKIP
        Test2(c=None, test1=Test1(a='a', b=''))

        In the example above, all keys in the map share the same name as their corresponding attributes. However,
        sometimes we want to use different keys when serialize the attributes, this could be achieved by adding a
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
        >>> t.serialize() # Notice the key is '1' now. Also, '0' is missing because it is marked as optional.
        {'1': Test1(a='a', b='')}
        >>> t.test1.serialize() # Keys are now '0' and '1' instead of 'c' and 'test1'.
        {'0': 'a', '1': ''}
        >>> cbor_hex = t.to_cborhex()
        >>> cbor_hex
        'a16131a261306161613160'
        >>> Test2.from_cborhex(cbor_hex) # doctest: +SKIP
        Test2(c=None, test1=Test1(a='a', b=''))
    """

    def serialize(self) -> Union[CBOR_PRIMITIVE]:
        serialized = {}
        for field in fields(self):
            if "key" in field.metadata:
                key = field.metadata["key"]
            else:
                key = field.name
            if key in serialized:
                raise SerializeException(f"Key: '{key}' already exists in the map.")
            val = getattr(self, field.name)
            if val is None and field.metadata.get("optional"):
                continue
            serialized[key] = val
        return serialized

    @classmethod
    def deserialize(cls, values: Union[CBOR_PRIMITIVE]) -> CBORSerializable:
        all_fields = {f.metadata.get("key", f.name): f for f in fields(cls)}
        if type(values) != dict:
            raise DeserializeException(f"Expect input value to be a dict, got a {type(values)} instead.")

        kwargs = {}
        type_hints = get_type_hints(cls)
        for key in values:
            if key not in all_fields:
                raise DeserializeException(f"Unexpected map key {key} in CBOR.")
            field = all_fields[key]
            v = values[key]
            if not isclass(field.type):
                field.type = type_hints[field.name]
            if "object_hook" in field.metadata:
                v = field.metadata["object_hook"](v)
            elif isclass(field.type) and issubclass(field.type, CBORSerializable):
                v = field.type.deserialize(v)
            kwargs[field.name] = v
        return cls(**kwargs)


def homogenous_list_hook(cls: type(CBORSerializable)) -> Callable[[List[Any]], List[CBORSerializable]]:
    """A helper function that generates an object hook for a list of CBORSerializables who share the same type.

    Args:
        cls: Type of CBORSerializable

    Returns:
        Callable[[List[Any]], List[CBORSerializable]]: An object hook (Callable) that deserializes each item
        into a CBORSerializable.
    """
    return lambda vals: [cls.deserialize(v) for v in vals]
