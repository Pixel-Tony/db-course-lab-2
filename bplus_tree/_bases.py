from abc import ABCMeta, abstractmethod as _abstract
from typing import Generic, Iterator, Literal, Protocol, TypeVar, Callable


_KT = TypeVar('_KT', bound='ComparableKeyT')
_VT = TypeVar('_VT')
_T = TypeVar('_T')
FormatterT = Callable[[_T], str]
HasherT = Callable[[_VT], _KT]


class ComparableKeyT(Protocol):
    @_abstract
    def __le__(self: _KT, obj: _KT, /) -> bool: ...
    @_abstract
    def __gt__(self: _KT, obj: _KT, /) -> bool: ...
    @_abstract
    def __eq__(self, obj: object, /) -> bool: ...
    @_abstract
    def __ne__(self, obj: object, /) -> bool: ...
    @_abstract
    def __lt__(self: _KT, obj: _KT, /) -> bool: ...
    @_abstract
    def __ge__(self: _KT, obj: _KT, /) -> bool: ...


class IBplusTree(Generic[_KT, _VT], metaclass=ABCMeta):
    '''B+ Tree, a data structure for storing block data as key-value pairs.'''

    @_abstract
    def insert(self, value: _VT, /) -> bool: ...
    @_abstract
    def remove(self, value: _VT, /) -> bool: ...
    @_abstract
    def has(self, value: _VT, /) -> bool: ...
    @_abstract
    def all_less_than(self, value: _VT, /) -> Iterator[_VT]: ...
    @_abstract
    def all_bigger_than(self, value: _VT, /) -> Iterator[_VT]: ...

    @_abstract
    def to_str(self, key_format: FormatterT[_KT] = ...,
               value_format: FormatterT[_VT] = ...) -> str: ...


class IUniqueKeyBpT(IBplusTree[_KT, _VT]):
    '''B+ tree with unique keys.'''

    @_abstract
    def __getitem__(self, key: _KT) -> _VT: ...
    @_abstract
    def get(self, key: _KT, default: _VT | None = None) -> _VT | None: ...


class IMultiKeyBpT(IBplusTree[_KT, _VT]):
    '''B+ tree with support of non-unique keys.'''

    # TODO FUTURE
    # @__abstract
    # def get(self, key: _KT, default: _VT) -> Iterable[_VT]: ...
    @_abstract
    def insert(self, value: _VT, /) -> Literal[True]: ...
    @_abstract
    def remove(self, value: _VT, /) -> bool: ...
