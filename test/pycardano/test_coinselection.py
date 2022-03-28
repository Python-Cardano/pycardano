from functools import reduce
from test.pycardano.util import chain_context
from typing import List

import pytest

from pycardano.coinselection import LargestFirstSelector, RandomImproveMultiAsset
from pycardano.exception import (
    InputUTxODepletedException,
    InsufficientUTxOBalanceException,
    MaxInputCountExceededException,
)
from pycardano.transaction import TransactionInput, TransactionOutput, UTxO, Value

address = "addr_test1vrm9x2zsux7va6w892g38tvchnzahvcd9tykqf3ygnmwtaqyfg52x"

# 10 UTxOs with different ADA amount and assets
TOTAL_UTXOS = 10
UTXOS = [
    UTxO(
        TransactionInput.from_primitive([b"1" * 32, i]),
        TransactionOutput.from_primitive(
            [
                address,
                [
                    (i + 1) * 1000000,
                    {
                        b"1"
                        * 28: {
                            bytes(f"token{i}", encoding="utf-8"): (i + 1) * 100,
                        }
                    },
                ],
            ]
        ),
    )
    for i in range(TOTAL_UTXOS)
]


def assert_request_fulfilled(request: List[TransactionOutput], selected: List[UTxO]):
    assert reduce(lambda x, y: x + y, [r.amount for r in request], Value()) <= reduce(
        lambda x, y: x + y, [s.output.amount for s in selected], Value()
    )


class TestLargestFirst:

    selector = LargestFirstSelector()

    def test_ada_only(self, chain_context):
        request = [TransactionOutput.from_primitive([address, [15000000]])]

        selected, change = self.selector.select(UTXOS, request, chain_context)

        assert selected == [UTXOS[-1], UTXOS[-2]]
        assert_request_fulfilled(request, selected)

    def test_multiple_request_outputs(self, chain_context):
        request = [
            TransactionOutput.from_primitive([address, [9000000]]),
            TransactionOutput.from_primitive([address, [6000000]]),
        ]

        selected, change = self.selector.select(UTXOS, request, chain_context)

        assert selected == [UTXOS[-1], UTXOS[-2]]
        assert_request_fulfilled(request, selected)

    def test_fee_effect(self, chain_context):
        request = [TransactionOutput.from_primitive([address, [10000000]])]
        selected, change = self.selector.select(
            UTXOS, request, chain_context, respect_min_utxo=False
        )
        assert selected == [UTXOS[-1], UTXOS[-2]]
        assert_request_fulfilled(request, selected)

    def test_no_fee_effect(self, chain_context):
        request = [TransactionOutput.from_primitive([address, [10000000]])]
        selected, change = self.selector.select(
            UTXOS, request, chain_context, include_max_fee=False, respect_min_utxo=False
        )
        assert selected == [UTXOS[-1]]

    def test_no_fee_but_respect_min_utxo(self, chain_context):
        request = [TransactionOutput.from_primitive([address, [10000000]])]
        selected, change = self.selector.select(
            UTXOS, request, chain_context, include_max_fee=False, respect_min_utxo=True
        )
        assert selected == [UTXOS[-1], UTXOS[-2]]

    def test_insufficient_balance(self, chain_context):
        request = [TransactionOutput.from_primitive([address, [1000000000]])]

        with pytest.raises(InsufficientUTxOBalanceException):
            self.selector.select(UTXOS, request, chain_context)

    def test_max_input_count(self, chain_context):
        request = [TransactionOutput.from_primitive([address, [15000000]])]

        with pytest.raises(MaxInputCountExceededException):
            self.selector.select(UTXOS, request, chain_context, max_input_count=1)

    def test_multi_asset(self, chain_context):
        request = [
            TransactionOutput.from_primitive(
                [
                    address,
                    [
                        1500000,
                        {
                            b"1"
                            * 28: {
                                bytes(f"token0", encoding="utf-8"): 50,
                            }
                        },
                    ],
                ]
            )
        ]

        selected, change = self.selector.select(UTXOS, request, chain_context)

        # token0 is attached to the smallest utxo, which will be the last utxo during selection,
        # so we expect all utxos to be selected.
        assert selected == list(reversed(UTXOS))
        assert_request_fulfilled(request, selected)


class TestRandomImproveMultiAsset:
    @property
    def selector(self):
        return RandomImproveMultiAsset(random_generator=reversed(range(TOTAL_UTXOS)))

    def test_ada_only(self, chain_context):
        request = [TransactionOutput.from_primitive([address, [15000000]])]

        selected, change = self.selector.select(UTXOS, request, chain_context)

        assert selected == list(reversed(UTXOS[-4:]))
        assert_request_fulfilled(request, selected)

        request = [
            TransactionOutput.from_primitive([address, [9000000]]),
            TransactionOutput.from_primitive([address, [6000000]]),
        ]

        selected, change = self.selector.select(UTXOS, request, chain_context)

        assert selected == list(reversed(UTXOS[-4:]))
        assert_request_fulfilled(request, selected)

    def test_fee_effect(self, chain_context):
        request = [TransactionOutput.from_primitive([address, [9000000]])]
        selected, change = self.selector.select(UTXOS, request, chain_context)
        assert selected == [UTXOS[9], UTXOS[8], UTXOS[5]]
        assert_request_fulfilled(request, selected)

    def test_no_fee_effect(self, chain_context):
        request = [TransactionOutput.from_primitive([address, [9000000]])]
        selected, change = self.selector.select(
            UTXOS, request, chain_context, include_max_fee=False
        )
        assert selected == list(reversed(UTXOS[-2:]))
        assert_request_fulfilled(request, selected)

    def test_no_fee_but_respect_min_utxo(self, chain_context):
        request = [TransactionOutput.from_primitive([address, [500000]])]
        # Only the first two UTxOs should be selected in this test case.
        # The first one is for the request amount, the second one is to respect min UTxO size.
        selected, change = RandomImproveMultiAsset(random_generator=[0, 0]).select(
            UTXOS, request, chain_context, include_max_fee=False, respect_min_utxo=True
        )
        assert selected == [
            UTXOS[0],
            UTXOS[1],
        ]  # UTXOS[1] is selected to respect min utxo amount
        assert_request_fulfilled(request, selected)

    def test_utxo_depleted(self, chain_context):
        request = [TransactionOutput.from_primitive([address, [1000000000]])]

        with pytest.raises(InputUTxODepletedException):
            self.selector.select(UTXOS, request, chain_context)

    def test_max_input_count(self, chain_context):
        request = [TransactionOutput.from_primitive([address, [15000000]])]

        with pytest.raises(MaxInputCountExceededException):
            self.selector.select(UTXOS, request, chain_context, max_input_count=1)

    def test_multi_asset(self, chain_context):
        request = [
            TransactionOutput.from_primitive(
                [
                    address,
                    [
                        1500000,
                        {
                            b"1"
                            * 28: {
                                bytes(f"token0", encoding="utf-8"): 50,
                                bytes(f"token3", encoding="utf-8"): 50,
                            }
                        },
                    ],
                ]
            )
        ]

        sequence = [9, 8, 3, 6, 0]
        selector = RandomImproveMultiAsset(random_generator=sequence)

        selected, change = selector.select(UTXOS, request, chain_context)

        assert selected == [
            UTXOS[9],
            UTXOS[8],
            UTXOS[3],
            UTXOS[
                7
            ],  # Because utxo3 is selected, the random index of 6 will result in selecting utxo7
            UTXOS[0],
        ]
        assert_request_fulfilled(request, selected)
