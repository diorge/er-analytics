import itertools
import typing


def incdec_alternator(start_value: int) -> typing.Iterator[int]:
    """
    Generator that alternates between incrementing and decrementing the original start_value

    >>> list(itertools.islice(incdec_alternator(10), 6))
    [10, 11, 9, 12, 8, 13]
    """
    increasing = itertools.count(start_value + 1)
    decreasing = itertools.count(start_value - 1, step=-1)

    yield start_value
    for next_inc, next_down in zip(increasing, decreasing):
        yield next_inc
        yield next_down
