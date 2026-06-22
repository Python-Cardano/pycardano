from pycardano.backend.ogmios_v6 import OgmiosV6ChainContext


def _parse(plutus_cost_models):
    # _parse_cost_models needs no connection state; build a bare instance.
    ctx = OgmiosV6ChainContext.__new__(OgmiosV6ChainContext)
    return ctx._parse_cost_models(plutus_cost_models)


class TestParseCostModels:
    """The Plutus cost models returned by Ogmios are arrays of operation costs
    already in the ledger's canonical parameter order. The script integrity hash
    is computed over that order, so ``_parse_cost_models`` must preserve it and
    never drop entries — otherwise a transaction's script integrity hash is wrong
    and is rejected on submit (while ``evaluateTransaction`` still passes)."""

    def test_preserves_order_for_every_language(self):
        v1 = list(range(100, 100 + 166))
        v2 = list(range(1000, 1000 + 332))
        v3 = list(range(5, 5 + 251))
        parsed = _parse({"plutus:v1": v1, "plutus:v2": v2, "plutus:v3": v3})
        assert list(parsed["PlutusV1"].values()) == v1
        assert list(parsed["PlutusV2"].values()) == v2
        assert list(parsed["PlutusV3"].values()) == v3

    def test_does_not_truncate_when_model_grows(self):
        # The ledger's cost models grow over time (e.g. PlutusV2 grew past 300
        # parameters at Conway). Every operation cost must be kept, regardless of
        # how long the array is.
        v2 = list(range(332))
        parsed = _parse({"plutus:v2": v2})
        assert len(parsed["PlutusV2"]) == len(v2)
        assert list(parsed["PlutusV2"].values()) == v2

    def test_keys_are_zero_padded_indices_that_sort_canonically(self):
        # Keys are positional and zero-padded so a lexicographic ``sorted(keys)``
        # (used when serializing the V1 language view) stays in canonical order.
        parsed = _parse({"plutus:v2": list(range(15))})
        keys = list(parsed["PlutusV2"].keys())
        assert keys == sorted(keys)
        assert keys[:3] == ["00", "01", "02"]

    def test_absent_language_is_omitted(self):
        parsed = _parse({"plutus:v2": [1, 2, 3]})
        assert set(parsed) == {"PlutusV2"}

    def test_empty_input(self):
        assert _parse(None) == {}
        assert _parse({}) == {}
