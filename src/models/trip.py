import math
from typing import Any
from .base_entity import BaseEntity
from .constants import ASSIGNED, COMPLETED, CANCELLED

_VALID_STATUSES = {ASSIGNED, COMPLETED, CANCELLED}


class Trip(BaseEntity):
    def __init__(
        self,
        id: str,
        request_id: str,
        driver_id: str,
        eta: float,
        status: str = ASSIGNED,
        pickup_path: list[str] | None = None,
    ) -> None:
        super().__init__(id)
        if not request_id or not request_id.strip():
            raise ValueError("request_id không được rỗng")
        if not driver_id or not driver_id.strip():
            raise ValueError("driver_id không được rỗng")
        if isinstance(eta, bool) or not isinstance(eta, (int, float)) or not math.isfinite(eta) or eta < 0:
            raise ValueError(f"eta phải là số hữu hạn >= 0, nhận: {eta}")
        if status not in _VALID_STATUSES:
            raise ValueError(f"status phải là {ASSIGNED!r}, {COMPLETED!r} hoặc {CANCELLED!r}, nhận: {status!r}")

        if pickup_path is None:
            self.pickup_path: list[str] = []
        elif isinstance(pickup_path, list):
            for node in pickup_path:
                if not isinstance(node, str) or not node.strip():
                    raise ValueError(f"pickup_path phải là danh sách các chuỗi không rỗng, nhận phần tử: {node!r}")
            self.pickup_path = list(pickup_path)
        else:
            raise ValueError(f"pickup_path phải là list các chuỗi hoặc None, nhận: {type(pickup_path).__name__}")

        self.request_id = request_id
        self.driver_id = driver_id
        self.eta = float(eta)
        self.status = status

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "id": self.id,
            "request_id": self.request_id,
            "driver_id": self.driver_id,
            "eta": self.eta,
            "status": self.status,
        }
        if self.pickup_path:
            data["pickup_path"] = list(self.pickup_path)
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Trip":
        return cls(
            id=data["id"],
            request_id=data["request_id"],
            driver_id=data["driver_id"],
            eta=float(data["eta"]),
            status=data.get("status", ASSIGNED),
            pickup_path=data.get("pickup_path"),
        )

