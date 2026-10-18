from typing import Any
from .base_entity import BaseEntity
from .trip import ASSIGNED

QUEUED = "queued"

_VALID_STATUSES = {QUEUED, ASSIGNED}


class RideRequest(BaseEntity):
    def __init__(
        self,
        id: str,
        pickup_node: str,
        dropoff_node: str,
        status: str = QUEUED,
    ) -> None:
        super().__init__(id)
        if not pickup_node or not pickup_node.strip():
            raise ValueError("pickup_node không được rỗng")
        if not dropoff_node or not dropoff_node.strip():
            raise ValueError("dropoff_node không được rỗng")
        if pickup_node == dropoff_node:
            raise ValueError("pickup_node và dropoff_node không được trùng nhau")
        if status not in _VALID_STATUSES:
            raise ValueError(f"status phải là {QUEUED!r} hoặc {ASSIGNED!r}, nhận: {status!r}")
        self.pickup_node = pickup_node
        self.dropoff_node = dropoff_node
        self.status = status

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "pickup_node": self.pickup_node,
            "dropoff_node": self.dropoff_node,
            "status": self.status,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RideRequest":
        return cls(
            id=data["id"],
            pickup_node=data["pickup_node"],
            dropoff_node=data["dropoff_node"],
            status=data.get("status", QUEUED),
        )
