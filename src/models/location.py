from __future__ import annotations
from typing import Any
from .base_entity import BaseEntity


class Location(BaseEntity):
    def __init__(self, id: str, name: str = "") -> None:
        super().__init__(id)
        self.name = name

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "name": self.name}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Location":
        return cls(data["id"], data.get("name", ""))
