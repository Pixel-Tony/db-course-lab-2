from abc import ABCMeta as __ABCMeta, abstractmethod as _abstract
from typing import Iterable, Generic, Iterator, TypeVar
from ._bases import (ComparableKeyT, IMultiKeyBpT, FormatterT as _FormatterT,
                     HasherT as _HasherT)
from dataclasses import dataclass


__all__ = ['MultiKeyBplusTree']


_KT = TypeVar('_KT', bound='ComparableKeyT')
_VT = TypeVar('_VT')
_NodeT = TypeVar('_NodeT', covariant=True)


@dataclass(eq=False, slots=True)
class _RemovalResult(Generic[_KT, _VT]):
    """The class representing result of a removal operation on the node."""
    removed: bool
    """Whether the key was removed."""
    join_result: '_AnyNodeT[_KT, _VT] | None' = None
    """Result of the join if siblings were joined in the process."""
    smallest_key: _KT | None = None
    """New smallest key of the node if it changed."""
    right_smallest_key: _KT | None = None
    """New smallest key of the right neighbor if it changed."""


@dataclass(eq=False, slots=True)
class _AnyNode(Generic[_KT, _VT, _NodeT], metaclass=__ABCMeta):
    _left: _NodeT | None
    _right: _NodeT | None

    @_abstract
    def __len__(self) -> int: ...

    @_abstract
    def trim(self) -> '_AnyNodeT[_KT, _VT]': ...

    @property
    @_abstract
    def smallest_key(self) -> _KT: ...

    @_abstract
    def to_str(self, k_format: _FormatterT[_KT],
               v_format: _FormatterT[_VT], indent: int, /) -> str: ...

    @_abstract
    def has(self, key: _KT, value: _VT, /) -> bool: ...

    @_abstract
    def insert(self, key: _KT, value: _VT, order: int,
               /) -> tuple[_NodeT, _KT] | None: ...

    @_abstract
    def all_less_than(self, key: _KT, value: _VT, /) -> Iterator[_VT]: ...

    @_abstract
    def all_bigger_than(self, key: _KT, value: _VT, /) -> Iterator[_VT]: ...

    # TODO FUTURE: support for multiple keys removal in-place
    @_abstract
    def remove(self, key: _KT, value: _VT, root: bool, halforder: int,
               can_join: tuple[bool, bool], /) -> _RemovalResult[_KT, _VT]: ...


_AnyNodeT = _AnyNode[_KT, _VT, '_AnyNodeT[_KT, _VT]']


# TODO comment asserts; use binary search for child
@dataclass(eq=False, slots=True)
class _Leaf(_AnyNode[_KT, _VT, '_Leaf[_KT, _VT]']):
    _keys: list[_KT]
    _values: list[_VT]

    def __len__(self):
        return len(self._keys)

    def trim(self):
        return self

    @property
    def smallest_key(self):
        return self._keys[0]

    @property
    def __pairs(self):
        return zip(self._keys, self._values)

    def has(self, key: _KT, value: _VT, /):
        return (key, value) in self.__pairs

    def insert(self, key: _KT, value: _VT, order: int, /):
        new_count = self._add(key, value)

        if new_count <= order:
            return None

        half = new_count // 2

        self._keys, k_right = self._keys[:half], self._keys[half:]
        self._values, v_right = self._values[:half], self._values[half:]

        old_right = self._right
        self._right = _Leaf(self, self._right, k_right, v_right)
        if old_right:
            old_right._left = self._right
        return self._right, k_right[0]

    def _add(self, key: _KT, value: _VT, /) -> int:
        if not self._keys or key > self._keys[-1]:
            self._keys.append(key)
            self._values.append(value)
            return 1

        count = len(self)

        i = 0 if key <= self._keys[0] else next(
            i
            for i in range(1, count)
            if self._keys[i - 1] < key <= self._keys[i]
        )
        self._keys.insert(i, key)
        self._values.insert(i, value)

        return count + 1

    def to_str(self, key_format: _FormatterT[_KT],
               value_format: _FormatterT[_VT], indent: int, /):
        return ' '*indent + f"\n{' '*indent}".join(
            f"{key_format(k)}: {value_format(v)}"
            for k, v in self.__pairs
        )

    def all_bigger_than(self, key: _KT, value: _VT, /) -> Iterator[_VT]:
        if self._keys and key <= self._keys[-1]:
            yield from (v
                        for k, v in self.__pairs
                        if k > key or (k == key and v != value))

        if self._right:
            yield from self._right.all_bigger_than(key, value)

    def all_less_than(self, key: _KT, value: _VT, /) -> Iterator[_VT]:
        if self._left:
            yield from self._left.all_less_than(key, value)

        if self._keys and key > self._keys[0]:
            yield from (v
                        for k, v in self.__pairs
                        if k < key or (k == key and v != value))

    def remove(self, key: _KT, value: _VT, root: bool, halforder: int,
               can_join: tuple[bool, bool], /) -> _RemovalResult[_KT, _VT]:
        target = key, value
        inds = [i for i, p in enumerate(self.__pairs) if p == target]

        if not inds:
            return _RemovalResult(False)

        # TODO multiple keys deletion at once
        i = inds[0]
        self._keys.pop(i)
        self._values.pop(i)

        smallest_key = self._keys[0] if i == 0 and self._keys else None

        if root:
            return _RemovalResult(True, None, smallest_key)

        count = len(self)
        if count >= halforder:
            return _RemovalResult(True, None, smallest_key)

        left, right = self._left, self._right

        if can_join[1] and right:
            if len(right) > halforder:
                self._keys.append(right._keys.pop(0))
                self._values.append(right._values.pop(0))
                return _RemovalResult(True, None, smallest_key, right._keys[0])

            if left is None or not can_join[0] or len(left) == halforder:
                self._join_from(right)
                return _RemovalResult(True, self, smallest_key)

        assert left

        if len(left) > halforder:
            smallest_key = left._keys.pop()
            self._keys.insert(0, smallest_key)
            self._values.insert(0, left._values.pop())
            return _RemovalResult(True, None, smallest_key)

        left._join_from(self)
        return _RemovalResult(True, left)

    def _join_from(self, other: '_Leaf[_KT, _VT]', /):
        self._keys.extend(other._keys)
        self._values.extend(other._values)
        self._right = other._right
        if self._right:
            self._right._left = self


@dataclass(eq=False, slots=True)
class _Node(_AnyNode[_KT, _VT, '_Node[_KT, _VT]']):
    _bounds: list[_KT]
    _children: list[_AnyNodeT[_KT, _VT]]

    def __len__(self):
        return len(self._children)

    def trim(self):
        return self if len(self) > 1 else self._children[0]

    @property
    def smallest_key(self):
        return self._children[0].smallest_key

    def has(self, key: _KT, value: _VT, /) -> bool:
        if not self._children:
            return False
        return any(self._children[i].has(key, value)
                   for i in self._children_range_containing(key))

    def insert(self, key: _KT, value: _VT, order: int, /):
        if not self._bounds:
            i = 0
        if key >= self._bounds[-1]:
            i = len(self) - 1
        else:
            i = next(i for i, k in enumerate(self._bounds) if k > key)

        another = self._children[i].insert(key, value, order)
        if another is None:
            return None

        neighbor, smallest_key = another
        self._children.insert(i + 1, neighbor)
        self._bounds.insert(i, smallest_key)

        if len(self) <= order:
            return None

        half = len(self) // 2

        self._children, ch_right = self._children[:half], self._children[half:]
        mid, *b_right = self._bounds[half - 1:]
        self._bounds = self._bounds[:half - 1]

        old_right = self._right
        self._right = _Node(self, self._right, b_right, ch_right)
        if old_right:
            old_right._left = self._right
        return self._right, mid

    def to_str(self, key_format: _FormatterT[_KT],
               value_format: _FormatterT[_VT], indent: int):
        formats = key_format, value_format
        IND = ' ' * indent
        return (
            self._children[0].to_str(*formats, indent + 4)
            + IND.join(
                f'\n{IND}{key_format(bd)}'
                f'\n{ch.to_str(*formats, indent + 4)}'
                for bd, ch in zip(self._bounds, self._children[1:])
            )
        )

    def all_bigger_than(self, key: _KT, value: _VT) -> Iterator[_VT]:
        if not self._children:
            return
        bds = self._bounds
        if not bds or key <= bds[0]:
            i = 0
        elif key > bds[-1]:
            i = -1
        else:
            i = next(i + 1 for i in range(len(bds) - 1)
                     if bds[i] < key <= bds[i + 1])
        yield from self._children[i].all_bigger_than(key, value)

    def all_less_than(self, key: _KT, value: _VT) -> Iterator[_VT]:
        if not self._children:
            return
        bounds = self._bounds
        if not bounds or key < bounds[0]:
            i = 0
        elif key >= bounds[-1]:
            i = -1
        else:
            i = next(i + 1 for i in range(len(bounds) - 1)
                     if bounds[i] <= key < bounds[i + 1])
        yield from self._children[i].all_less_than(key, value)

    def _children_range_containing(self, key: _KT) -> Iterable[int]:
        bounds = self._bounds
        MAX = len(bounds)

        if key < bounds[0]:
            return [0]
        if key > bounds[-1]:
            return [MAX]

        if key == bounds[0]:
            i_mn = 0
        else:
            i_mn = next(i + 1 for i in range(MAX - 1)
                        if bounds[i] < key <= bounds[i + 1])

        if key == bounds[-1]:
            return range(i_mn, MAX + 1)

        i_mx = next(i + 1 for i in range(i_mn, MAX)
                    if bounds[i - 1] <= key < bounds[i])
        return range(i_mn, i_mx)

    def remove(self, key: _KT, value: _VT, root: bool, halforder: int,
               can_join: tuple[bool, bool], /) -> _RemovalResult[_KT, _VT]:
        if not self._children:
            return _RemovalResult(False)

        MAX = len(self) - 1
        for i in self._children_range_containing(key):
            child = self._children[i]
            cans_joins = i > 0, i < MAX
            result = child.remove(key, value, False, halforder, cans_joins)
            if not result.removed:
                continue
            return self._remove(root, child, i, result, can_join, halforder)

        return _RemovalResult(False)

    def _remove(self, root: bool, child: _AnyNodeT[_KT, _VT], i: int,
                result: _RemovalResult[_KT, _VT], can_join: tuple[bool, bool],
                halforder: int, /) -> _RemovalResult[_KT, _VT]:

        if result.right_smallest_key:
            self._bounds[i] = result.right_smallest_key

        smallest_key = result.smallest_key
        if smallest_key and i > 0:
            self._bounds[i - 1] = smallest_key
            smallest_key = None

        if result.join_result is None:
            return _RemovalResult(True)

        offset = i + (result.join_result is child)
        self._children.pop(offset)
        self._bounds.pop(offset - 1)

        if root or len(self) >= halforder:
            return _RemovalResult(True, None, smallest_key)

        left, right = self._left, self._right

        if can_join[1] and right:
            if len(right) > halforder:
                to_append = right._children.pop(0)
                right_smallest_key = right._bounds.pop(0)
                self._children.append(to_append)
                self._bounds.append(to_append.smallest_key)
                return _RemovalResult(True, None, smallest_key,
                                      right_smallest_key)

            if left is None or not can_join[0] or len(left) == halforder:
                self._join_from(right)
                return _RemovalResult(True, self, smallest_key)

        assert left and can_join[0]

        if len(left) > halforder:
            to_append = left._children.pop()
            left._bounds.pop()
            bound = self._children[0].smallest_key
            self._bounds.insert(0, bound)
            self._children.insert(0, to_append)
            return _RemovalResult(True, None, smallest_key)

        left._join_from(self)
        return _RemovalResult(True, left)

    def _join_from(self, right: '_Node[_KT, _VT]', /):
        right_children = right._children
        self._children.extend(right_children)
        self._bounds.append(right_children[0].smallest_key)
        self._bounds.extend(right._bounds)
        self._right = right._right
        if self._right:
            self._right._left = self


class MultiKeyBplusTree(IMultiKeyBpT[_KT, _VT]):
    """B+ tree implementation with support for repeated values."""

    def __init__(self, order: int, keygen: _HasherT[_VT, _KT]):
        assert not (order % 2), 'Order of the B+ tree must be an even number'
        assert order > 2, 'Order of the B+ tree must be bigger than 2'

        self._order = order
        self._keygen = keygen
        self._root: _AnyNodeT[_KT, _VT] = _Leaf(None, None, [], [])

    def insert(self, value: _VT, /):
        another = self._root.insert(self._keygen(value), value, self._order)
        if another is None:
            return True
        neighbor, border = another

        self._root = _Node(None, None, [border], [self._root, neighbor])
        return True

    def to_str(self, key_format: _FormatterT[_KT] = str,
               value_format: _FormatterT[_VT] = str):
        return self._root.to_str(key_format, value_format, 0)

    def has(self, value: _VT) -> bool:
        return self._root.has(self._keygen(value), value)

    def remove(self, value: _VT) -> bool:
        key = self._keygen(value)
        halforder = self._order // 2
        result = self._root.remove(key, value, True, halforder, (False, False))
        self._root = self._root.trim()
        return result.removed

    def all_less_than(self, value: _VT) -> Iterator[_VT]:
        return self._root.all_less_than(self._keygen(value), value)

    def all_bigger_than(self, value: _VT) -> Iterator[_VT]:
        return self._root.all_bigger_than(self._keygen(value), value)
