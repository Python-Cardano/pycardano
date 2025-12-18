"""
Conditional cbor2 import module.

This module provides a centralized location for importing cbor2,
with support for both the C extension (cbor2) and pure Python (cbor2pure) versions.
Set the environment variable CBOR_C_EXTENSION=1 to use the C extension.
"""

import os

if os.getenv("CBOR_C_EXTENSION", "0") == "1":
    import cbor2  # noqa: F401
else:
    import cbor2pure as cbor2  # type: ignore  # noqa: F401
