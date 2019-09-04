"""
https://stackoverflow.com/questions/8991506/iterate-an-iterator-by-chunks-of-n-in-python
"""
import itertools


def grouper(iterable, n: int):
    """

    Args:
        iterable:
        n:

    Returns:

    """
    while True:
        yield itertools.chain((next(iterable),), itertools.islice(iterable, n - 1))


def grouper_it(iterable, n: int):
    """

    Args:
        iterable:
        n:

    Returns:

    """
    it = iter(iterable)
    while True:
        chunk_it = itertools.islice(it, n)
        try:
            first_el = next(chunk_it)
        except StopIteration:
            return
        yield itertools.chain((first_el,), chunk_it)
