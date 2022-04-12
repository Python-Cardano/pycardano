class PyCardanoException(Exception):
    pass


class DecodingException(PyCardanoException):
    pass


class InvalidKeyTypeException(PyCardanoException):
    pass


class InvalidAddressInputException(PyCardanoException):
    pass


class InvalidDataException(PyCardanoException):
    pass


class InvalidArgumentException(PyCardanoException):
    pass


class InvalidOperationException(PyCardanoException):
    pass


class SerializeException(PyCardanoException):
    pass


class DeserializeException(PyCardanoException):
    pass


class InvalidTransactionException(PyCardanoException):
    pass


class TransactionBuilderException(PyCardanoException):
    pass


class TransactionFailedException(PyCardanoException):
    pass


class UTxOSelectionException(PyCardanoException):
    pass


class InsufficientUTxOBalanceException(UTxOSelectionException):
    pass


class MaxInputCountExceededException(UTxOSelectionException):
    pass


class InputUTxODepletedException(UTxOSelectionException):
    pass
