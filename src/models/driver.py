from __future__ import annotations
from typing import Any
from .base_entity import BaseEntity

FREE = "free"
BUSY = "busy"

_VALID_STATUSES = {FREE, BUSY}


class Driver(BaseEntity):
    def __init__(self, id: str, name: str, node: str, status: str = FREE) -> None:
        super().__init__(id)
        if not name or not name.strip():
            raise ValueError("name không được rỗng")
        if not node or not node.strip():
            raise ValueError("node không được rỗng")
        if status not in _VALID_STATUSES:
            raise ValueError(f"status phải là {FREE!r} hoặc {BUSY!r}, nhận: {status!r}")
        self.name = name
        self.node = node
        self.status = status

    def assign(self) -> None:
        if self.status == BUSY:
            raise RuntimeError(f"Tài xế {self.id!r} đang bận, không thể nhận chuyến mới")
        self.status = BUSY

    def release(self) -> None:
        self.status = FREE

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "name": self.name, "node": self.node, "status": self.status}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Driver":
        return cls(
            id=data["id"],
            name=data["name"],
            node=data["node"],
            status=data.get("status", FREE),
        )
