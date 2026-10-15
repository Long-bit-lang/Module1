"""TV5 - Entrypoint Streamlit (mỏng). Chỉ cấu hình trang và điều hướng tab.

Chạy: uv run streamlit run src/app.py
Logic giao diện nằm trong src/ui/; UI chỉ gọi Dispatcher / JsonStorage qua API công khai.
"""
import streamlit as st

from ui import session, tab_benchmark, tab_data, tab_dispatch

st.set_page_config(page_title="Điều phối đặt xe", page_icon="🚕", layout="wide")
st.title("🚕 Hệ thống Điều phối Đặt xe Thông minh")

session.init_session()

with st.sidebar:
    st.header("Trạng thái hệ thống")
    if st.session_state[session.K_MODE] == "mock":
        st.warning("Đang chạy bằng **backend giả lập** (mock): dữ liệu không ghi ra đĩa.")
        st.caption(st.session_state[session.K_NOTE])
    else:
        st.success("Đang chạy bằng **backend thật** (JsonStorage + Dispatcher).")
    d = session.dispatcher()
    st.metric("Yêu cầu đang chờ", len(d.queue_snapshot()))
    st.metric("Chuyến đã tạo", len(d.trips_snapshot()))

session.render_flash()

t_data, t_dispatch, t_bench = st.tabs(["Quản lý dữ liệu", "Điều phối chuyến", "Đối chuẩn thuật toán"])
with t_data:
    tab_data.render()
with t_dispatch:
    tab_dispatch.render()
with t_bench:
    tab_benchmark.render()
