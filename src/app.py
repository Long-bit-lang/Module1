"""TV5 - Entrypoint Streamlit chính cho hệ thống điều phối đặt xe thông minh."""
from __future__ import annotations

import os
from pathlib import Path

import streamlit as st

from models import CANCELLED
from ui import session, tab_benchmark, tab_data, tab_dispatch
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

# ── Sidebar ───────────────────────────────────────────────────────────────────
NAV_PAGES = ["Điều phối chuyến", "Quản lý dữ liệu", "Đối chuẩn thuật toán"]

with st.sidebar:
    st.markdown("### **Hệ thống Điều phối Đặt xe Thông minh**")
    current_page = st.radio(
        "Hệ thống Điều phối Đặt xe Thông minh",
        NAV_PAGES,
        key="main_nav",
        label_visibility="collapsed",
    )

    st.divider()
    sidebar_toggle_label = "Đóng bảng thao tác" if st.session_state.get("panel_open", True) else "Mở bảng thao tác"
    if st.button(
        sidebar_toggle_label,
        key="btn_sidebar_panel_toggle",
        help="Ẩn hoặc hiện bảng thao tác nhanh bên phải",
        width="stretch",
    ):
        st.session_state["panel_open"] = not st.session_state.get("panel_open", True)
        st.rerun()

    try:
        cancelled_count = sum(1 for t in session.dispatcher().trips_snapshot() if t.status == CANCELLED)
        st.caption(f"⛔ Số chuyến đã hủy: **{cancelled_count}**")
    except Exception:
        pass

# ── Flash messages (ngay trước nội dung trang chính) ──────────────────────────
session.render_flash()

# ── Render nội dung trang được chọn (A1: Bỏ st.tabs, chỉ gọi trang được chọn) ─
if current_page == "Điều phối chuyến":
    tab_dispatch.render()
elif current_page == "Quản lý dữ liệu":
    tab_data.render()
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
        .st-key-action_panel {
            transform: translateX(0) !important;
            visibility: visible !important;
        }
        .main .block-container {
            padding-right: 380px !important;
        }
        .st-key-btn_toggle_panel {
            position: fixed !important;
            right: 0.85rem !important;
            top: 4.15rem !important;
            z-index: 99999 !important;
        }
        .st-key-btn_toggle_panel button {
            background: #EFF6FF !important;
            color: #1D4ED8 !important;
            border: 1px solid #BFDBFE !important;
            box-shadow: 0 1px 3px rgba(37, 99, 235, 0.15) !important;
            font-size: 0.8rem !important;
            font-weight: 600 !important;
            padding: 0.25rem 0.65rem !important;
            border-radius: 6px !important;
        }
        .st-key-btn_toggle_panel button:hover {
            background: #DBEAFE !important;
            color: #1E40AF !important;
            border-color: #93C5FD !important;
        }
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
        .st-key-action_panel {
            transform: translateX(100%) !important;
            pointer-events: none !important;
            box-shadow: none !important;
            visibility: hidden !important;
            transition: transform 200ms ease-in-out, visibility 200ms ease-in-out !important;
        }
        .main .block-container {
            padding-right: 1rem !important;
        }
        .st-key-btn_toggle_panel {
            position: fixed !important;
            right: 0 !important;
            top: 4.5rem !important;
            z-index: 99999 !important;
        }
        .st-key-btn_toggle_panel button {
            background: #2563EB !important;
            color: #FFFFFF !important;
            border: 1px solid #1D4ED8 !important;
            border-right: none !important;
            border-radius: 8px 0 0 8px !important;
            box-shadow: -3px 3px 12px rgba(37, 99, 235, 0.35) !important;
            font-size: 0.84rem !important;
            font-weight: 600 !important;
            padding: 0.45rem 0.9rem !important;
        }
        .st-key-btn_toggle_panel button:hover {
            background: #1D4ED8 !important;
            color: #FFFFFF !important;
            box-shadow: -4px 4px 16px rgba(37, 99, 235, 0.45) !important;
            transform: translateX(-3px) !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
