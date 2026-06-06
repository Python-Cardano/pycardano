"""
Conditional cbor2 import module.

This module provides a centralized location for importing cbor2,
with support for both the C extension (cbor2) and pure Python (cbor2pure) versions.
Set the environment variable CBOR_C_EXTENSION=1 to use the C extension.

PyCardano anchors transaction identity in CBOR bytes (``tx.id`` is the blake2b
hash of the transaction body's CBOR). The C ``cbor2`` extension does not
guarantee preservation of map/set element order on decode (cbor2 issue #311),
so a decode-then-reserialize flow can change a transaction's id. For that reason
the pure-Python ``cbor2pure`` backend is the default, and enabling the C
extension triggers a runtime warning plus a startup round-trip self-test.
"""

import logging
import os
import warnings

logger = logging.getLogger("PyCardano")

_C_EXTENSION_WARNING = (
    "CBOR_C_EXTENSION=1: using the C cbor2 extension. The C extension does not "
    "guarantee preservation of map/set element order on decode (cbor2 issue #311), "
    "which can change a re-serialized transaction's id (tx.id = blake2b of body CBOR) "
    "and cause the node to reject or misattribute the transaction. The pure-Python "
    "cbor2pure backend (the default) is recommended for any decode-then-reserialize or "
    "transaction-signing workflow. See README 'cbor2' section."
)

# A tiny golden CBOR vector that exercises the order-preservation behaviour that
# matters for transaction ids: a tag-258 (set) holding three integers in a
# non-sorted order. PyCardano removes the semantic decoder for tag 258 (see
# ``serialization.py``) precisely so the element order is preserved on decode.
# A correct backend therefore round-trips these bytes unchanged; the C extension
# collapses the tag into a Python ``set`` (losing order) and re-encodes to
# different bytes.
_SELFTEST_GOLDEN = bytes.fromhex("d9010283030102")  # tag(258), array [3, 1, 2]


def _run_cbor_selftest(backend) -> None:
    """Run a dependency-free decode→encode round-trip check on ``backend``.

    Mirrors PyCardano's runtime configuration by removing the tag-258 semantic
    decoder before the check (and restoring it afterwards so the rest of the
    package's setup is unaffected). Raises :class:`PyCardanoException` if the
    backend is not byte-stable, i.e. if decode→encode would change transaction
    ids.
    """
    from pycardano.exception import PyCardanoException

    semantic_decoders = backend._decoder.semantic_decoders
    had_258 = 258 in semantic_decoders
    original_258 = semantic_decoders.get(258)
    if had_258:
        del semantic_decoders[258]
    try:
        reencoded = backend.dumps(backend.loads(_SELFTEST_GOLDEN))
    finally:
        if had_258:
            semantic_decoders[258] = original_258

    if reencoded != _SELFTEST_GOLDEN:
        raise PyCardanoException(
            "CBOR_C_EXTENSION=1 failed the CBOR round-trip self-test: decode->encode "
            "is not byte-stable for this build of cbor2, so transaction ids would be "
            "wrong. Unset CBOR_C_EXTENSION (use cbor2pure) for transaction workflows."
        )


if os.getenv("CBOR_C_EXTENSION", "0") == "1":
    import cbor2  # noqa: F401

    warnings.warn(_C_EXTENSION_WARNING, RuntimeWarning, stacklevel=2)
    logger.warning(_C_EXTENSION_WARNING)

    # Default the self-test on when the C extension is requested; allow embedders
    # to opt out with an explicit falsy PYCARDANO_CBOR_SELFTEST value.
    if os.getenv("PYCARDANO_CBOR_SELFTEST", "1").lower() not in ("0", "false", "no"):
        _run_cbor_selftest(cbor2)
else:
    import cbor2pure as cbor2  # type: ignore  # noqa: F401
