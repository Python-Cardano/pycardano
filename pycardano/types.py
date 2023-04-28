import os
from functools import partial
from typing import Any, Dict

import typeguard

# https://github.com/python/typing/issues/182#issuecomment-199532520
JsonDict = Dict[str, Any]


def typechecked(func=None, *args, **kwargs):
    if os.getenv("PYCARDANO_NO_TYPE_CHECK", "False").lower() in ("true", "1"):
        if func is None:
            return partial(typechecked, *args, **kwargs)
        return func
    return typeguard.typechecked(func, *args, **kwargs)


def check_type(*args, **kwargs):
    if os.getenv("PYCARDANO_NO_TYPE_CHECK", "False").lower() in ("true", "1"):
        return None
    return typeguard.check_type(*args, **kwargs)
