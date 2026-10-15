from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any


class BaseEntity(ABC):
    def __init__(self, id: str) -> None:
        if not id or not id.strip():
            raise ValueError("id không được rỗng")
        self.id = id

    @abstractmethod
    def to_dict(self) -> dict[str, Any]: ...

    @classmethod
    @abstractmethod
    def from_dict(cls, data: dict[str, Any]) -> "BaseEntity": ...

    def __eq__(self, other: object) -> bool:
        return isinstance(other, self.__class__) and self.id == other.id

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(id={self.id!r})"
