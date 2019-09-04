from typing import Callable


def binary_search_find_last_true(
        r: range,
        func_call: Callable[[int], bool]
) -> int:
    """
    TODO: rewrite with `bisect`

    Args:
        r:
        func_call:

    Returns:

    >>> bools = [True, True, True, True]
    >>> r = range(len(bools) + 1)
    >>> binary_search_find_last_true(r, lambda i: bools[i])
    3
    >>> bools[-1] = False; binary_search_find_last_true(r, lambda i: bools[i])
    2
    >>> bools[-2] = False; binary_search_find_last_true(r, lambda i: bools[i])
    1
    >>> bools[-3] = False; binary_search_find_last_true(r, lambda i: bools[i])
    0
    >>> bools[-4] = False; binary_search_find_last_true(r, lambda i: bools[i])
    0
    """
    if len(r) == 0:
        raise ValueError(f"range must not be empty!")

    min_ind = min(r)
    max_ind = max(r)
    cur_ind = (min_ind + max_ind) // 2
    while (max_ind - cur_ind) > 1:
        b_cur_ind = func_call(cur_ind)
        if b_cur_ind:
            min_ind = cur_ind
        else:
            max_ind = cur_ind
        cur_ind = (min_ind + max_ind) // 2
    if not func_call(cur_ind):
        cur_ind -= 1
    return min(max(cur_ind, 0), max(r))
