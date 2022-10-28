from pprint import pprint
from unittest import TestCase

import pytest
from blockfrost import ApiUrls, BlockFrostApi

from pycardano.backend.ogmios import OgmiosQueryType


@pytest.mark.single
class MyTest(TestCase):
    def test_blockfrost(self):
        # token = "mainnetYQugwY4ksxT3LSyHBb87HemGEho728Nr"
        # api = BlockFrostApi(token)
        # pprint(api.genesis())
        # pprint(vars(api.genesis()))

        print(type(OgmiosQueryType.Query))
        print(type(OgmiosQueryType.SubmitTx))
