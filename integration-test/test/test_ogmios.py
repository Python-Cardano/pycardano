from retry import retry

from .base import TEST_RETRIES, TestBase


class TestProtocolParam(TestBase):
    @retry(tries=TEST_RETRIES, backoff=1.3, delay=2, jitter=(0, 10))
    def test_protocol_param_cost_models(self):
        protocol_param = self.chain_context.protocol_param

        cost_models = protocol_param.cost_models
        for _, cost_model in cost_models.items():
            assert len(cost_model) > 0
