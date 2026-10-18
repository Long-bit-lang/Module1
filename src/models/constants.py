"""Hằng số trạng thái cho các thực thể dữ liệu trong hệ thống."""
from __future__ import annotations

# Trạng thái tài xế (Driver)
FREE = "free"
BUSY = "busy"

# Trạng thái yêu cầu đặt xe (RideRequest)
QUEUED = "queued"

# Trạng thái dùng chung giữa yêu cầu và chuyến xe
ASSIGNED = "assigned"

# Trạng thái chuyến xe (Trip)
COMPLETED = "completed"

__all__ = [
    "FREE",
    "BUSY",
    "QUEUED",
    "ASSIGNED",
    "COMPLETED",
]
