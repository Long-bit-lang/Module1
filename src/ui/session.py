"""TV5 - Quản lý Dispatcher / JsonStorage trong st.session_state.

Nguyên tắc (CONTRACT mục 7):
- Dispatcher chỉ khởi tạo MỘT LẦN cho mỗi phiên và giữ trong session_state, không nạp lại
  từ đĩa ở mỗi lần rerun, để hai ngăn xếp Undo/Redo không bị mất.
- Sau mỗi thao tác thành công gọi save_all(export_state()).
- Backend thật chưa đủ API thì tự rơi về mock (xem mock.py). Ép bằng biến môi trường
  RIDE_DISPATCH_BACKEND = "mock" | "real".
"""
from __future__ import annotations

import inspect
import os
from typing import Any, Callable

import streamlit as st

from core.strategies import MatchStrategy
from .ports import DISPATCHER_REQUIRED

K_DISPATCHER, K_STORAGE, K_STRATEGIES = "dispatcher", "storage", "strategies"
K_LOCATIONS, K_MODE, K_NOTE = "locations", "backend_mode", "backend_note"
K_FLASH, K_LAST = "flash", "last_dispatch"


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
    })


def reload_from_disk() -> None:
    """Bỏ phiên hiện tại và nạp lại từ đĩa (mất lịch sử Undo/Redo)."""
    for k in (K_DISPATCHER, K_STORAGE, K_STRATEGIES, K_LOCATIONS, K_LAST):
        st.session_state.pop(k, None)
    init_session()


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
    """Tách ID từ nhãn hiển thị dạng "N3 – Cầu Rồng" / "D1 – An"."""
    return label.split(" – ")[0]


# ------------------------------------------------------------ thông báo & lưu trữ
def flash(kind: str, message: str) -> None:
    st.session_state[K_FLASH].append((kind, message))


def render_flash() -> None:
    show = {"success": st.success, "error": st.error, "warning": st.warning, "info": st.info}
    for kind, message in st.session_state[K_FLASH]:
        show.get(kind, st.info)(message)
    st.session_state[K_FLASH] = []


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
