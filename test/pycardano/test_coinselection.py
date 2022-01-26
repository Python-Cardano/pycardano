import pytest

from functools import reduce
from typing import List

from pycardano.coinselection import LargestFirstSelector
from pycardano.exception import UTxOSelectionException
from pycardano.transaction import FullMultiAsset, TransactionInput, TransactionOutput, UTxO
from test.pycardano.util import chain_context

address = "addr_test1vrm9x2zsux7va6w892g38tvchnzahvcd9tykqf3ygnmwtaqyfg52x"

# 10 UTxOs with different ADA amount and assets
utxos = [UTxO(TransactionInput.from_primitive([b"1" * 32, i]),
              TransactionOutput.from_primitive(
                  [address,
                   [(i + 1) * 1000000,
                    {
                        b"1" * 28: {
                            bytes(f"token{i}",
                                  encoding="utf-8"): (i + 1) * 100,
                        }
                    }]
                   ]))
         for i in range(10)]


def assert_request_fulfilled(request: List[TransactionOutput], selected: List[UTxO]):
    assert reduce(lambda x, y: x + y, [r.amount for r in request], FullMultiAsset()) <= \
           reduce(lambda x, y: x + y, [s.output.amount for s in selected], FullMultiAsset())


class TestLargestFirst:

    selector = LargestFirstSelector()

    def test_ada_only(self, chain_context):
        request = [
            TransactionOutput.from_primitive([address, [15000000]])
        ]

        selected, change = self.selector.select(utxos, request, chain_context)

        assert selected == [utxos[-1], utxos[-2]]
        assert_request_fulfilled(request, selected)

    def test_multiple_request_outputs(self, chain_context):
        request = [
            TransactionOutput.from_primitive([address, [9000000]]),
            TransactionOutput.from_primitive([address, [6000000]])
        ]

        selected, change = self.selector.select(utxos, request, chain_context)

        assert selected == [utxos[-1], utxos[-2]]
        assert_request_fulfilled(request, selected)

    def test_fee_effect(self, chain_context):
        request = [
            TransactionOutput.from_primitive([address, [10000000]])
        ]
        selected, change = self.selector.select(utxos, request, chain_context)
        assert selected == [utxos[-1], utxos[-2]]
        assert_request_fulfilled(request, selected)

    def test_no_fee_effect(self, chain_context):
        request = [
            TransactionOutput.from_primitive([address, [10000000]])
        ]
        selected, change = self.selector.select(utxos, request, chain_context, include_max_fee=False)
        assert selected == [utxos[-1]]

    def test_insufficient_balance(self, chain_context):
        request = [
            TransactionOutput.from_primitive([address, [1000000000]])
        ]

        with pytest.raises(UTxOSelectionException) as e_info:
            self.selector.select(utxos, request, chain_context)
            assert "insufficient" in e_info.value

    def test_max_input_count(self, chain_context):
        request = [
            TransactionOutput.from_primitive([address, [15000000]])
        ]

        with pytest.raises(UTxOSelectionException) as e_info:
            self.selector.select(utxos, request, chain_context, max_input_count=1)
            assert "Max input count: 1 exceeded!" in e_info.value

    def test_multi_asset(self, chain_context):
        request = [
            TransactionOutput.from_primitive(
                [address,
                 [1500000,
                  {
                      b"1" * 28: {
                          bytes(f"token0",
                                encoding="utf-8"): 50,
                      }
                  }]
                 ])
        ]

        selected, change = self.selector.select(utxos, request, chain_context)

        # token0 is attached to the smallest utxo, which will be the last utxo during selection,
        # so we expect all utxos to be selected.
        assert selected == list(reversed(utxos))
        assert_request_fulfilled(request, selected)
