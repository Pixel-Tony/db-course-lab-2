from math import log2, ceil
__all__ = ['name_hash']


HASH_BITLEN = 64


__alphabet = {a: i for i, a in enumerate('абвгґдеєжзиіїйклмнопрстуфчцчшщьюя'
                                         'abcdefghijklmnopqrstuvwxyz')}

__LEN = len(__alphabet)
__D = ceil(log2(__LEN))
SYM_COUNT = HASH_BITLEN // __D
__M = 2 << (__D - 1)


def name_hash(s: str) -> int:
    res = 0

    for char in s[:SYM_COUNT].lower():
        w = __alphabet.get(char, __LEN)
        res = res * __M + w

    if (i := len(s)) < SYM_COUNT:
        res *= (__M ** (SYM_COUNT - i))

    return res
