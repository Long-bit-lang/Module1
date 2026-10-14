"""TV5 - Giao diện Streamlit. Chỉ gọi Dispatcher / JsonStorage, không chứa logic thuật toán."""
import streamlit as st

st.set_page_config(page_title="Điều phối đặt xe", layout="wide")
st.title("Hệ thống Điều phối Đặt xe Thông minh")

tab_data, tab_dispatch = st.tabs(["Quản lý dữ liệu", "Điều phối chuyến"])

with tab_data:
    st.info("TODO(TV5): quản lý tài xế, tạo yêu cầu, xem hàng đợi.")

with tab_dispatch:
    st.info("TODO(TV5): chọn thuật toán A1/A2, hiển thị tài xế, ETA, số đỉnh đã thăm, lịch sử, Undo/Redo.")
