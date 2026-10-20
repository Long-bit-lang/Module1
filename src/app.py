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
NAV_PAGES = ["Quản lý dữ liệu", "Điều phối chuyến", "Đối chuẩn thuật toán"]

with st.sidebar:
    st.markdown("### 🧭 Điều hướng Hệ thống")
    current_page = st.radio(
        "Điều hướng hệ thống",
        NAV_PAGES,
        key="main_nav",
        label_visibility="collapsed",
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
                <span class="qs-step">1</span><b>Đặt xe mới:</b> Mở panel thao tác bên phải → chọn điểm đón & trả khách tại mục <i>"(1) Đặt xe"</i> → nhấn <b>"Gửi yêu cầu"</b>.<br>
                <span class="qs-step">2</span><b>Ghép chuyến tối ưu:</b> Tại mục <i>"(3) Điều phối"</i> chọn thuật toán <b>A1</b> (Dijkstra từng tài xế) hoặc <b>A2</b> (Dijkstra đảo chiều) → nhấn <b>"Ghép chuyến"</b>.<br>
                <span class="qs-step">3</span><b>Hoàn tác & Hoàn thành:</b> Nhấn <b>"Undo"</b> để hủy gán chuyến; hoặc nhấn <b>"Hoàn thành chuyến"</b> trong danh sách đang chạy để kết thúc cuốc và giải phóng tài xế.
            </div>
            <div style="font-size: 0.82rem; color: #475569; border-top: 1px dashed #CBD5E1; padding-top: 0.45rem; margin-top: 0.45rem;">
                <b>Ý nghĩa màu sắc trên bản đồ:</b> 🟢 Viền xanh lá = Xe rảnh &nbsp;|&nbsp; 🔴 Viền đỏ = Xe bận &nbsp;|&nbsp; 🟠 Viền cam = Điểm đón đang chờ &nbsp;|&nbsp; ── Xanh lá = Đón khách &nbsp;|&nbsp; ╌╌ Cam nét đứt = Chở khách
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ── Flash messages (ngay trước nội dung trang chính) ──────────────────────────
session.render_flash()

# ── Render nội dung trang được chọn (A1: Bỏ st.tabs, chỉ gọi trang được chọn) ─
if current_page == "Quản lý dữ liệu":
    tab_data.render()
elif current_page == "Điều phối chuyến":
    tab_dispatch.render()
else:
    tab_benchmark.render()

# ── Panel thao tác bên phải (A2: Luôn render để widget keys không bị mất) ─────
from ui.panel import render_action_panel
render_action_panel()

# Bố cục phản hồi: điều chỉnh khoảng cách đệm (padding) của vùng chính theo trạng thái panel
if st.session_state.get("panel_open", True):
    st.markdown(
        """
        <style>
        .st-key-action_panel { transform: translateX(0) !important; }
        .main .block-container { padding-right: 380px !important; }
        @media (max-width: 1024px) {
            .main .block-container { padding-right: 1rem !important; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
else:
    st.markdown(
        """
        <style>
        .st-key-action_panel { transform: translateX(100%) !important; pointer-events: none !important; box-shadow: none !important; }
        .main .block-container { padding-right: 1rem !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )
