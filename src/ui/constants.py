"""TV5 - Hằng số trạng thái dùng cho UI.

Nguồn chân lý là `models` (CONTRACT mục 1). Khi TV1 chưa export xong thì dùng giá trị
dự phòng trùng đúng chuỗi trong CONTRACT, để UI không phải hardcode rải rác.
"""
from models import ASSIGNED, BUSY, COMPLETED, FREE, QUEUED


STATUS_LABEL = {
    FREE: "🟢 Rảnh",
    BUSY: "🔴 Bận",
    QUEUED: "⏳ Đang chờ",
    ASSIGNED: "🚗 Đang chạy",
    COMPLETED: "✅ Hoàn thành",
}


def status_label(status: str) -> str:
    return STATUS_LABEL.get(status, status)
