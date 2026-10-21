"""TV5 - Hằng số trạng thái dùng cho UI.

Nguồn chân lý là `models` (CONTRACT mục 1). Module này import và tái xuất các hằng số
trạng thái từ `models` kèm nhãn hiển thị trực quan cho giao diện người dùng.
"""
from models import ASSIGNED, BUSY, CANCELLED, COMPLETED, FREE, QUEUED


STATUS_LABEL = {
    FREE: "🟢 Rảnh",
    BUSY: "🔴 Bận",
    QUEUED: "⏳ Đang chờ",
    ASSIGNED: "🚗 Đang chạy",
    COMPLETED: "✅ Hoàn thành",
    CANCELLED: "⛔ Đã hủy",
}


def status_label(status: str) -> str:
    return STATUS_LABEL.get(status, status)


# ── Hằng số trạng thái & cấu hình Animation Timelapse ───────────────────────
ANIM_STATUS_PLAYING = "playing"
ANIM_STATUS_PAUSED = "paused"
ANIM_STATUS_COMPLETED = "completed"

# Ngân sách thời gian & tần suất khung hình (giây)
ANIM_TARGET_SECONDS = 4.0        # Tổng thời gian phát mục tiêu ở tốc độ 1x (3-5 giây cho lộ trình bình thường)
ANIM_MAX_SECONDS = 8.0           # Trần tuyệt đối thời gian phát ở tốc độ 1x (không quá 8 giây cho lộ trình dài)
ANIM_MIN_INTERVAL = 0.08         # Khoảng thời gian tối thiểu giữa 2 khung hình (giây)
ANIM_MAX_INTERVAL = 0.25         # Khoảng thời gian tối đa giữa 2 khung hình (giây)

# Giới hạn số tick cho mỗi cạnh đường
ANIM_TICKS_PER_EDGE_MIN = 2      # Số tick tối thiểu cho một cạnh đường
ANIM_TICKS_PER_EDGE_MAX = 6      # Số tick tối đa cho một cạnh đường
ANIM_MINUTES_PER_TICK = 1.0      # Số phút mô phỏng tương ứng mỗi tick (1.0 phút/tick)

# Tương thích ngược với các module/test cũ
MINUTES_PER_TICK = ANIM_MINUTES_PER_TICK
MIN_TICKS_PER_EDGE = ANIM_TICKS_PER_EDGE_MIN
MAX_TICKS_PER_EDGE = ANIM_TICKS_PER_EDGE_MAX
BASE_TICK_DELAY_SEC = 0.16


