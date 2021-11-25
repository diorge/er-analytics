import itertools

from requester.alternator import incdec_alternator


def test_basic_alternator() -> None:
    """Inc/Dec alternator generates alternating elements."""
    gen = incdec_alternator(10)
    first_six = tuple(itertools.islice(gen, 6))

    assert (10, 11, 9, 12, 8, 13) == first_six


def test_negative_alternator() -> None:
    """Alternator can reach negative elements."""
    gen = incdec_alternator(1)
    first_seven = tuple(itertools.islice(gen, 7))

    assert (1, 2, 0, 3, -1, 4, -2) == first_seven
