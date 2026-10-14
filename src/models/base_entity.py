"""TV1 - Lớp cơ sở cho mọi entity (có id và chuyển đổi dict)."""
from __future__ import annotations
from typing import Any


class BaseEntity:
    def __init__(self, id: str):
        if not id:
            raise ValueError("id không được rỗng")
        self.id = id

    def to_dict(self) -> dict[str, Any]:
        raise NotImplementedError  # TODO(TV1)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BaseEntity":
        raise NotImplementedError  # TODO(TV1)
