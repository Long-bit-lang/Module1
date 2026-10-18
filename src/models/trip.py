import math
from typing import Any
from .base_entity import BaseEntity
from .constants import ASSIGNED, COMPLETED

_VALID_STATUSES = {ASSIGNED, COMPLETED}


class Trip(BaseEntity):
    def __init__(
        self,
        id: str,
        request_id: str,
        driver_id: str,
        eta: float,
        status: str = ASSIGNED,
    ) -> None:
        super().__init__(id)
        if not request_id or not request_id.strip():
            raise ValueError("request_id không được rỗng")
        if not driver_id or not driver_id.strip():
            raise ValueError("driver_id không được rỗng")
        if isinstance(eta, bool) or not isinstance(eta, (int, float)) or not math.isfinite(eta) or eta < 0:
            raise ValueError(f"eta phải là số hữu hạn >= 0, nhận: {eta}")
        if status not in _VALID_STATUSES:
            raise ValueError(f"status phải là {ASSIGNED!r} hoặc {COMPLETED!r}, nhận: {status!r}")
        self.request_id = request_id
        self.driver_id = driver_id
        self.eta = float(eta)
        self.status = status

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "request_id": self.request_id,
            "driver_id": self.driver_id,
            "eta": self.eta,
            "status": self.status,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Trip":
        return cls(
            id=data["id"],
            request_id=data["request_id"],
            driver_id=data["driver_id"],
            eta=float(data["eta"]),
            status=data.get("status", ASSIGNED),
        )
