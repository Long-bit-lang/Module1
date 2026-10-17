"""TV5 - Entrypoint Streamlit chính cho hệ thống điều phối đặt xe thông minh."""
from __future__ import annotations

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
session.init_session()

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
t_data, t_dispatch, t_bench = st.tabs(
    ["Quản lý dữ liệu", "Điều phối chuyến", "Đối chuẩn thuật toán"]
)
with t_data:
    tab_data.render()
with t_dispatch:
    tab_dispatch.render()
with t_bench:
    tab_benchmark.render()
