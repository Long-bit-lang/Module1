"""TV5 - Hằng số trạng thái dùng cho UI.

Nguồn chân lý là `models` (CONTRACT mục 1). Module này import và tái xuất các hằng số
trạng thái từ `models` kèm nhãn hiển thị trực quan cho giao diện người dùng.
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
