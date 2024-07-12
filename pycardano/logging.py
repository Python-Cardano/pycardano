import logging

from pprintpp import pformat

__all__ = ["logger", "log_state"]

# create logger
logger = logging.getLogger("PyCardano")

# create console handler and set level to debug
ch = logging.StreamHandler()

# create formatter
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

# add formatter to ch
ch.setFormatter(formatter)

# add ch to logger
logger.addHandler(ch)


def log_state(func):
    """Decorator to log the state of an object after its function call."""

    def wrapper(obj, *args, **kwargs):
        try:
            output = func(obj, *args, **kwargs)
            logger.debug(
                f"Class: {obj.__class__}, method: {func}, state:\n {pformat(vars(obj), indent=2)}"
            )
            return output
        except Exception as e:
            logger.warning(
                f"Class: {obj.__class__}, method: {func}, state:\n {pformat(vars(obj), indent=2)}"
            )
            raise e

    return wrapper
