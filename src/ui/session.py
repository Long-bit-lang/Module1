"""TV5 - Quản lý Dispatcher / JsonStorage trong st.session_state.

Nguyên tắc (CONTRACT mục 7):
- Dispatcher chỉ khởi tạo MỘT LẦN cho mỗi phiên và giữ trong session_state, không nạp lại
  từ đĩa ở mỗi lần rerun.
- Sau mỗi thao tác thành công gọi save_all(export_state()).
- Mặc định chạy Backend thật (RIDE_DISPATCH_BACKEND="real"), ném lỗi rõ ràng nếu dữ liệu hỏng.
  Hỗ trợ chạy backend giả lập bằng RIDE_DISPATCH_BACKEND="mock" hoặc tự động rơi về mock khi đặt RIDE_DISPATCH_BACKEND="auto".
"""
import html
import inspect
import os
import time
import uuid
from datetime import datetime
from typing import Any, Callable

import streamlit as st

from core.strategies import MatchStrategy
from .ports import DISPATCHER_REQUIRED

K_DISPATCHER, K_STORAGE, K_STRATEGIES = "dispatcher", "storage", "strategies"
K_LOCATIONS, K_MODE, K_NOTE = "locations", "backend_mode", "backend_note"
K_FLASH, K_LAST = "flash", "last_dispatch"
K_NOTIFICATIONS = "notifications"


# ------------------------------------------------------------------ chọn backend
def _load_real():
    """Trả về (storage, dispatcher, strategies, locations) thật, hoặc ném lỗi mô tả lý do."""
    from core.dispatcher import Dispatcher
    from core.json_storage import JsonStorage
    from core.strategies import STRATEGIES  # noqa: F401 - TV2 chưa có thì ImportError

    missing = [n for n in DISPATCHER_REQUIRED if not hasattr(Dispatcher, n)]
    if missing:
        raise RuntimeError("Dispatcher chưa có: " + ", ".join(missing))
    params = list(inspect.signature(Dispatcher.submit_request).parameters)
    if params[1:] != ["pickup_node", "dropoff_node"]:
        raise RuntimeError("Dispatcher.submit_request chưa đúng chữ ký CONTRACT")

    runtime = os.environ.get("RIDE_DISPATCH_RUNTIME_DIR")
    storage = JsonStorage(runtime_dir=runtime) if runtime else JsonStorage()
    state = storage.load_all()
    dispatcher = Dispatcher.from_state(state)
    strategies = {name: cls() for name, cls in STRATEGIES.items()}
    return storage, dispatcher, strategies, state.get("locations", {})


def init_session() -> None:
    if K_DISPATCHER in st.session_state:
        return
    forced = os.environ.get("RIDE_DISPATCH_BACKEND", "real").lower()  # mặc định "real"; "auto" vẫn dùng được
    note, backend = "", None
    if forced != "mock":
        try:
            backend, mode = _load_real(), "real"
        except Exception as exc:  # backend chưa hoàn thiện -> dùng mock
            if forced == "real":
                raise
            note = f"{type(exc).__name__}: {exc}"
    if backend is None:
        from .mock import build_mock
        backend, mode = build_mock(), "mock"
        note = note or "Ép dùng mock bằng RIDE_DISPATCH_BACKEND=mock"
    storage, dispatcher, strategies, locations = backend
    st.session_state.update({
        K_STORAGE: storage, K_DISPATCHER: dispatcher, K_STRATEGIES: strategies,
        K_LOCATIONS: locations, K_MODE: mode, K_NOTE: note, K_FLASH: [], K_LAST: None,
        K_NOTIFICATIONS: [],
    })


def reload_from_disk() -> None:
    """Bỏ phiên hiện tại và nạp lại từ đĩa."""
    for k in (K_DISPATCHER, K_STORAGE, K_STRATEGIES, K_LOCATIONS, K_LAST, K_NOTIFICATIONS):
        st.session_state.pop(k, None)
    init_session()


def reset_to_seed() -> None:
    """Khôi phục hoàn toàn dữ liệu runtime từ thư mục seed ban đầu."""
    import shutil
    s = storage()
    if hasattr(s, "seed_dir") and hasattr(s, "runtime_dir"):
        req_files = getattr(s, "REQUIRED_FILES", ("graph.json", "drivers.json", "requests.json", "trips.json"))
        for filename in req_files:
            seed_file = s.seed_dir / filename
            runtime_file = s.runtime_dir / filename
            if seed_file.exists():
                shutil.copy2(seed_file, runtime_file)
    reload_from_disk()


# --------------------------------------------------------------------- truy cập
def dispatcher() -> Any:
    return st.session_state[K_DISPATCHER]


def storage() -> Any:
    return st.session_state[K_STORAGE]


def strategies() -> dict[str, Any]:
    return st.session_state[K_STRATEGIES]


def node_label(node_id: str) -> str:
    name = st.session_state[K_LOCATIONS].get(node_id)
    name = getattr(name, "name", name)  # Location thật hoặc chuỗi tên
    return f"{node_id} – {name}" if name else node_id


def node_labels() -> list[str]:
    return [node_label(n) for n in dispatcher().graph.nodes()]


def item_id(label: str) -> str:
    """Tách ID từ nhãn hiển thị dạng "N3 – Cầu Rồng" / "D1 – An" / "R16 (N3 → N7)"."""
    clean = label.split("(")[0].strip()
    return clean.split(" – ")[0].strip()


# ------------------------------------------------------------ thông báo & lưu trữ
def flash(kind: str, message: str) -> None:
    """B1 & B4: Thêm thông báo vào trung tâm thông báo (tối đa 20 bản ghi)."""
    if K_NOTIFICATIONS not in st.session_state:
        st.session_state[K_NOTIFICATIONS] = []
    if K_FLASH not in st.session_state:
        st.session_state[K_FLASH] = []

    notif_id = str(uuid.uuid4())[:8]
    now_str = datetime.now().strftime("%H:%M:%S")

    # B2: Khi có thao tác thành công mới -> giải phóng/ẩn error/warning trước đó
    if kind == "success":
        for old_n in st.session_state[K_NOTIFICATIONS]:
            if old_n["kind"] in ("error", "warning"):
                old_n["active"] = False

    new_notif = {
        "id": notif_id,
        "kind": kind,
        "message": str(message),
        "timestamp": now_str,
        "created_at": time.time(),
        "active": True,
    }

    st.session_state[K_NOTIFICATIONS].append(new_notif)
    if len(st.session_state[K_NOTIFICATIONS]) > 20:
        st.session_state[K_NOTIFICATIONS] = st.session_state[K_NOTIFICATIONS][-20:]

    st.session_state[K_FLASH].append((kind, str(message)))

    # B2: st.toast(duration=...) cho phản hồi nhanh (Streamlit 1.66)
    icon_map = {"success": "✅", "error": "🚨", "warning": "⚠️", "info": "ℹ️"}
    try:
        st.toast(str(message), icon=icon_map.get(kind, "ℹ️"), duration="short")
    except Exception:
        pass


def render_flash() -> None:
    """B1-B4: Hiển thị banner thông báo nổi bật và nhật ký thao tác."""
    if K_NOTIFICATIONS not in st.session_state:
        st.session_state[K_NOTIFICATIONS] = []

    now = time.time()
    # B2: success/info tự ẩn sau ~8s
    for n in st.session_state[K_NOTIFICATIONS]:
        if n.get("active", True) and n["kind"] in ("success", "info"):
            if now - n.get("created_at", now) >= 8.0:
                n["active"] = False

    active_notifs = [n for n in st.session_state[K_NOTIFICATIONS] if n.get("active", True)]

    if active_notifs:
        with st.container(key="notification_center"):
            for n in active_notifs:
                icon_map = {"success": "✅", "error": "🚨", "warning": "⚠️", "info": "ℹ️"}
                icon = icon_map.get(n["kind"], "ℹ️")
                kind_cls = f"notif-banner-{n['kind']}"

                safe_msg = html.escape(n["message"])
                safe_time = html.escape(n["timestamp"])

                banner_html = f"""
                <div class="notif-banner {kind_cls}">
                    <div class="notif-banner-body">
                        <span class="notif-banner-icon">{icon}</span>
                        <div class="notif-banner-content">
                            <span class="notif-banner-text">{safe_msg}</span>
                            <span class="notif-banner-time">[{safe_time}]</span>
                        </div>
                    </div>
                </div>
                """
                col_banner, col_close = st.columns([11, 1], vertical_alignment="center")
                with col_banner:
                    st.markdown(banner_html, unsafe_allow_html=True)
                    if n["kind"] == "error":
                        st.markdown('<div class="sr-only-notif">', unsafe_allow_html=True)
                        st.error(n["message"])
                        st.markdown('</div>', unsafe_allow_html=True)
                with col_close:
                    if st.button("✕", key=f"btn_close_notif_{n['id']}", help="Đóng thông báo"):
                        n["active"] = False
                        st.rerun()

    # B3: Popover/Expander "Nhật ký thao tác" liệt kê 20 thông báo gần nhất
    all_notifs = st.session_state[K_NOTIFICATIONS]
    if all_notifs:
        with st.expander(f"📋 Nhật ký thao tác ({len(all_notifs)}/20 gần nhất)", expanded=False):
            for item in reversed(all_notifs):
                icon_map = {"success": "✅", "error": "🚨", "warning": "⚠️", "info": "ℹ️"}
                icon = icon_map.get(item["kind"], "ℹ️")
                badge_color = {
                    "success": "#047857",
                    "error": "#B91C1C",
                    "warning": "#B45309",
                    "info": "#1D4ED8",
                }.get(item["kind"], "#475569")
                st.markdown(
                    f"""
                    <div class="notif-log-item">
                        <span class="notif-log-time">[{html.escape(item['timestamp'])}]</span>
                        <span style="color: {badge_color}; font-weight: 600;">{icon} {html.escape(item['kind'].upper())}:</span>
                        <span>{html.escape(item['message'])}</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )


def commit() -> bool:
    """Tự động lưu trạng thái hiện tại xuống đĩa."""
    try:
        storage().save_all(dispatcher().export_state())
        return True
    except Exception as exc:
        flash("error", f"Không lưu được dữ liệu: {exc}")
        return False


def perform(action: Callable[[], Any], success: str | None = None) -> tuple[bool, Any]:
    """Chạy một thao tác nghiệp vụ; lỗi -> thông báo trực quan, thành công -> lưu.

    Trả về (ok, kết quả). ok=False khi có ngoại lệ (kết quả None).
    """
    try:
        result = action()
    except Exception as exc:
        flash("error", str(exc) or type(exc).__name__)
        return False, None
    if success:
        flash("success", success)
    commit()
    return True, result


class RecordingStrategy(MatchStrategy):
    """Bọc một chiến lược để UI đọc được MatchResult.

    dispatch_next() chỉ trả về Trip nên UI không thấy visited_count / runtime_ms / path;
    wrapper này ghi lại kết quả gần nhất mà không cần sửa Dispatcher.
    """

    def __init__(self, inner: Any):
        self.inner = inner
        self.name = getattr(inner, "name", type(inner).__name__)
        self.last_result = None

    def find_driver(self, graph, pickup_node, free_drivers):
        self.last_result = self.inner.find_driver(graph, pickup_node, free_drivers)
        return self.last_result
