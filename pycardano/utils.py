from pycardano.backend.base import ChainContext


def max_tx_fee(context: ChainContext) -> int:
    return context.protocol_param.max_tx_size * context.protocol_param.min_fee_coefficient + \
           context.protocol_param.min_fee_constant
