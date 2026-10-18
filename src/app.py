"""TV5 - Entrypoint Streamlit chính cho hệ thống điều phối đặt xe thông minh."""
from __future__ import annotations

import os
from pathlib import Path

import streamlit as st

from ui import session, tab_benchmark, tab_data, tab_dispatch
from ui.constants import ASSIGNED, COMPLETED, FREE
from ui.styles import CUSTOM_CSS

st.set_page_config(
    page_title="Điều phối đặt xe",
    page_icon="🚕",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

try:
    session.init_session()
except Exception as exc:
    st.error(f"Lỗi khởi tạo dữ liệu: {exc}")
    runtime_env = os.environ.get("RIDE_DISPATCH_RUNTIME_DIR")
    runtime_dir = Path(runtime_env) if runtime_env else Path(__file__).resolve().parent.parent / "data" / "runtime"
    if st.button("Xóa file runtime và nạp lại từ seed"):
        for filename in ("graph.json", "drivers.json", "requests.json", "trips.json"):
            target = runtime_dir / filename
            if target.is_file():
                try:
                    target.unlink()
                except OSError:
                    pass
        st.rerun()
    st.stop()

# ── Tiêu đề ──────────────────────────────────────────────────────────────────
st.title("🚕 Hệ thống Điều phối Đặt xe Thông minh")
st.caption("Tối ưu hóa hành trình trên đồ thị giao thông · Dijkstra A1/A2 · Hàng đợi FIFO · Undo/Redo")

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    if st.session_state[session.K_MODE] == "mock":
        st.warning("Đang chạy backend **giả lập** (mock)")
        st.caption(st.session_state[session.K_NOTE])
    else:
        st.success("Backend **thật** (JsonStorage + Dispatcher)")

    d = session.dispatcher()
    drivers = d.drivers_snapshot()
    queue = d.queue_snapshot()
    trips = d.trips_snapshot()
    free = sum(1 for x in drivers.values() if x.status == FREE)

    st.divider()
    c1, c2 = st.columns(2)
    c1.metric("Tài xế rảnh", f"{free}/{len(drivers)}")
    c2.metric("Hàng đợi", len(queue))

    c3, c4 = st.columns(2)
    c3.metric("Chuyến đang chạy", sum(1 for t in trips if t.status == ASSIGNED))
    c4.metric("Đã hoàn thành", sum(1 for t in trips if t.status == COMPLETED))

    st.divider()
    st.markdown(
        "**Lưu ý:** Undo/Redo giữ qua các lần rerun nhưng "
        "mất khi tải lại trang (F5). Hoàn thành chuyến sẽ xóa "
        "lịch sử Undo/Redo."
    )

# ── Flash messages (ngay trước tabs, gần khu vực thao tác) ────────────────────
session.render_flash()

# ── Tabs ──────────────────────────────────────────────────────────────────────
TAB_NAMES = ["Quản lý dữ liệu", "Điều phối chuyến", "Đối chuẩn thuật toán"]


def _on_tab_change() -> None:
    st.session_state["active_tab"] = st.session_state["main_tabs"]


if "active_tab" not in st.session_state:
    st.session_state["active_tab"] = TAB_NAMES[0]
elif "main_tabs" in st.session_state and st.session_state["main_tabs"] in TAB_NAMES:
    st.session_state["active_tab"] = st.session_state["main_tabs"]

t_data, t_dispatch, t_bench = st.tabs(
    TAB_NAMES,
    default=st.session_state["active_tab"],
    key="main_tabs",
    on_change=_on_tab_change,
)
with t_data:
    tab_data.render()
with t_dispatch:
    tab_dispatch.render()
with t_bench:
    tab_benchmark.render()

