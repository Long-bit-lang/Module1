"""TV5 - Entrypoint Streamlit chính cho hệ thống điều phối đặt xe thông minh."""
from __future__ import annotations

import os
from pathlib import Path

import streamlit as st

from ui import session, tab_benchmark, tab_data, tab_dispatch
from ui.components import render_kpi_card
from ui.constants import ASSIGNED, COMPLETED, FREE
from ui.styles import CUSTOM_CSS

st.set_page_config(
    page_title="Hệ thống Điều phối Đặt xe Thông minh",
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

d = session.dispatcher()
drivers = d.drivers_snapshot()
queue = d.queue_snapshot()
trips = d.trips_snapshot()
free = sum(1 for x in drivers.values() if x.status == FREE)
active_trips = sum(1 for t in trips if t.status == ASSIGNED)
completed_trips = sum(1 for t in trips if t.status == COMPLETED)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ Trạng thái Hệ thống")
    if st.session_state[session.K_MODE] == "mock":
        st.warning("Đang chạy backend **giả lập** (mock)")
        st.caption(st.session_state[session.K_NOTE])
    else:
        st.success("Backend **thật** (JsonStorage + Dispatcher)")

    st.divider()
    st.markdown("### 🎬 Trình diễn & Thuyết trình")
    st.toggle(
        "Bật chế độ trình diễn (Demo)",
        key="demo_mode",
        value=False,
        help="Hiển thị thanh kịch bản từng bước theo luồng thuyết trình 5-7 phút ở đầu trang chính.",
    )

    st.divider()
    st.markdown("### 📌 Ghi chú Vận hành")
    st.info(
        "• **Undo / Redo** được giữ an toàn qua các lần rerun tương tác, nhưng sẽ đặt lại khi F5 toàn trang.\n\n"
        "• Khi **Hoàn thành chuyến**, lịch sử Undo/Redo sẽ được làm mới vì vị trí tài xế đã thay đổi vĩnh viễn.",
        icon="ℹ️",
    )

# ── Header ──────────────────────────────────────────────────────────────────
st.title("🚕 Hệ thống Điều phối Đặt xe Thông minh")
st.caption(
    "Tối ưu hóa hành trình trên đồ thị giao thông · Thuật toán Dijkstra A1/A2 · "
    "Hàng đợi FIFO · Lịch sử Undo/Redo · Lưu trữ nguyên tử (Atomic)"
)

# ── Header KPI Cards (Đặt ở đầu trang chính) ─────────────────────────────────
kpi_c1, kpi_c2, kpi_c3, kpi_c4 = st.columns(4)
with kpi_c1:
    render_kpi_card(
        "Tài xế sẵn sàng",
        f"{free}/{len(drivers)} xe",
        "Đang rảnh đón khách",
        "🟢",
        "Số lượng tài xế rảnh sẵn sàng nhận cuốc trên tổng số tài xế",
    )
with kpi_c2:
    render_kpi_card(
        "Hàng đợi yêu cầu",
        f"{len(queue)} yêu cầu",
        "Chờ điều phối FIFO",
        "⏳",
        "Số lượng khách hàng đang chờ điều phối xe theo thứ tự đến trước xử lý trước",
    )
with kpi_c3:
    render_kpi_card(
        "Chuyến đang chạy",
        f"{active_trips} chuyến",
        "Đang đón / chở khách",
        "🚗",
        "Số lượng chuyến xe đang hoạt động",
    )
with kpi_c4:
    render_kpi_card(
        "Đã hoàn thành",
        f"{completed_trips} chuyến",
        "Kết thúc an toàn",
        "✅",
        "Tổng số chuyến xe đã kết thúc thành công",
    )

# ── Khối Bắt đầu nhanh ───────────────────────────────────────────────────────
with st.expander("🚀 Bắt đầu nhanh (3 bước trải nghiệm luồng nghiệp vụ)", expanded=True):
    st.markdown(
        """
        <div class="quick-start-box">
            <div style="margin-bottom: 0.6rem; line-height: 1.65;">
                <span class="qs-step">1</span><b>Đặt xe mới:</b> Chọn điểm đón & trả khách tại tab <i>"Điều phối chuyến"</i> → nhấn <b>"Gửi yêu cầu"</b> (xếp vào hàng đợi FIFO).<br>
                <span class="qs-step">2</span><b>Ghép chuyến tối ưu:</b> Chọn thuật toán <b>A1</b> (Dijkstra từng tài xế) hoặc <b>A2</b> (Dijkstra đảo chiều) → nhấn <b>"Ghép chuyến"</b> (hệ thống tự động chọn xe đón nhanh nhất).<br>
                <span class="qs-step">3</span><b>Hoàn tác & Hoàn thành:</b> Nhấn <b>"Undo"</b> để hủy gán chuyến đưa yêu cầu về đầu hàng đợi; hoặc nhấn <b>"Hoàn thành"</b> để kết thúc cuốc và giải phóng tài xế tại điểm trả khách.
            </div>
            <div style="font-size: 0.82rem; color: #475569; border-top: 1px dashed #CBD5E1; padding-top: 0.45rem; margin-top: 0.45rem;">
                <b>Ý nghĩa màu sắc trên bản đồ:</b> 🟢 Viền xanh lá = Xe rảnh &nbsp;|&nbsp; 🔴 Viền đỏ = Xe bận &nbsp;|&nbsp; 🟠 Viền cam = Điểm đón đang chờ &nbsp;|&nbsp; ── Xanh lá = Đón khách &nbsp;|&nbsp; ╌╌ Cam nét đứt = Chở khách
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# Placeholder cho thanh chế độ trình diễn (sẽ được tích hợp chi tiết ở Bước 5)
if st.session_state.get("demo_mode"):
    from ui.tab_dispatch import render_demo_stepper
    render_demo_stepper()

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
