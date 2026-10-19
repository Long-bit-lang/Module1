"""TV5 - Tab "Quản lý dữ liệu": tài xế, đồ thị giao thông, nạp lại dữ liệu."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from . import session as S
from .components import render_empty_state, render_graph_with_zoom
from .constants import BUSY, FREE, status_label
from .graph_view import build_dot


def _drivers_table(drivers: dict) -> pd.DataFrame:
    rows = [
        {
            "ID": d.id,
            "Tên tài xế": d.name,
            "Vị trí hiện tại": S.node_label(d.node),
            "Trạng thái": status_label(d.status),
        }
        for d in drivers.values()
    ]
    return pd.DataFrame(rows, columns=["ID", "Tên tài xế", "Vị trí hiện tại", "Trạng thái"])


def _on_add_driver() -> None:
    name, node = st.session_state["add_name"].strip(), S.item_id(st.session_state["add_node"])
    if not name:
        S.flash("error", "Vui lòng nhập tên tài xế.")
        return
    ok, drv = S.perform(lambda: S.dispatcher().add_driver(name, node))
    if ok:
        S.flash("success", f"Đã thêm tài xế {drv.id} – {drv.name} tại {S.node_label(node)}")
        st.session_state["add_name"] = ""


def _on_update_driver() -> None:
    did = S.item_id(st.session_state["edit_driver"])
    name_val = st.session_state.get(f"edit_name_{did}", "").strip()
    cur_drv = S.dispatcher().drivers.get(did)
    cur_node = cur_drv.node if cur_drv is not None else None
    node_raw = st.session_state.get(f"edit_node_{did}_{cur_node}")
    if node_raw is None:
        node_raw = st.session_state.get(f"edit_node_{did}")
    ok, _ = S.perform(
        lambda: S.dispatcher().update_driver(
            did,
            name=name_val or None,
            node=S.item_id(node_raw) if node_raw else None,
        ),
        f"Đã cập nhật thông tin tài xế {did}",
    )
    if ok:
        st.session_state[S.K_LAST] = None


def _on_remove_driver() -> None:
    did = S.item_id(st.session_state["edit_driver"])
    ok, removed = S.perform(lambda: S.dispatcher().remove_driver(did))
    if ok and removed:
        st.session_state[S.K_LAST] = None
        S.flash("success", f"Đã xóa tài xế {did}")
    elif ok:
        S.flash("warning", f"Không tìm thấy tài xế {did}")


def _on_reload() -> None:
    ok, _ = S.perform(S.reload_from_disk)
    if ok:
        st.session_state[S.K_LAST] = None
        S.flash("info", "Đã nạp lại dữ liệu từ đĩa runtime; lịch sử Undo/Redo đã được đặt lại.")


def _on_reset_seed() -> None:
    ok, _ = S.perform(S.reset_to_seed)
    if ok:
        st.session_state[S.K_LAST] = None
        S.flash("success", "Đã khôi phục toàn bộ dữ liệu mẫu ban đầu (Seed); lịch sử Undo/Redo đã được làm mới.")


@st.dialog("⚠️ Xác nhận xóa tài xế")
def _confirm_remove_driver_dialog(did: str, dname: str) -> None:
    st.markdown(
        f"Bạn có chắc chắn muốn xóa tài xế **{did} – {dname}** khỏi hệ thống không?\n\n"
        "*(Lưu ý: Chỉ tài xế đang rảnh và chưa từng có lịch sử chuyến đi mới có thể xóa được)*."
    )
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Xác nhận xóa", key="btn_confirm_remove_driver", type="primary", width="stretch"):
            st.session_state["show_remove_driver_dialog"] = False
            _on_remove_driver()
            st.rerun()
    with c2:
        if st.button("Hủy bỏ", key="btn_cancel_remove_driver", width="stretch"):
            st.session_state["show_remove_driver_dialog"] = False
            st.rerun()


@st.dialog("⚠️ Xác nhận khôi phục dữ liệu mẫu (Seed)")
def _confirm_reset_seed_dialog() -> None:
    st.markdown(
        "**Bạn có chắc chắn muốn khôi phục toàn bộ dữ liệu mẫu (Seed)?**\n\n"
        "Thao tác này sẽ:\n"
        "- Xóa toàn bộ thay đổi dữ liệu trong thư mục `data/runtime/`.\n"
        "- Khôi phục lại 6 địa danh Đà Nẵng, 3 tài xế ban đầu (D1, D2 rảnh; D3 bận).\n"
        "- Khôi phục lại 2 yêu cầu đang chờ: R3 (đón tại N4) và R4 (đón tại N5).\n"
        "- Làm mới toàn bộ lịch sử Undo/Redo và các chuyến xe đã chạy.\n\n"
        "*Thích hợp khi bắt đầu phiên thuyết trình hoặc muốn chạy lại kịch bản từ đầu.*"
    )
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Xác nhận khôi phục", key="btn_confirm_reset_seed", type="primary", width="stretch"):
            st.session_state["show_reset_dialog"] = False
            _on_reset_seed()
            st.rerun()
    with c2:
        if st.button("Hủy bỏ", key="btn_cancel_reset_seed", width="stretch"):
            st.session_state["show_reset_dialog"] = False
            st.rerun()



def render() -> None:
    d = S.dispatcher()
    drivers = d.drivers_snapshot()
    nodes = d.graph.nodes()
    labels = S.node_labels()
    edges = d.graph.edges()

    free_count = sum(1 for x in drivers.values() if x.status == FREE)
    busy_count = len(drivers) - free_count

    # 1. Thống kê tổng quan mạng lưới
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Điểm giao thông", f"{len(nodes)} đỉnh", help="Số nút giao thông trên bản đồ")
    m2.metric("Tuyến kết nối", f"{len(edges)} cung", help="Số đoạn đường một chiều")
    m3.metric("Tài xế sẵn sàng", f"{free_count} xe", help="Tài xế đang ở trạng thái rảnh")
    m4.metric("Tài xế đang bận", f"{busy_count} xe", help="Tài xế đang thực hiện cuốc")

    st.divider()

    # 2. Bản đồ giao thông
    st.subheader("Bản đồ Mạng lưới Giao thông")
    st.caption("Các đỉnh màu xanh lá có tài xế sẵn sàng nhận cuốc; màu đỏ có tài xế đang bận.")

    dot_map = build_dot(edges, drivers, d.queue_snapshot(), S.node_label, nodes)
    render_graph_with_zoom(dot_map, key_prefix="map_data", height=500)

    with st.expander(f"📋 Danh sách Tuyến đường ({len(edges)} cung kết nối)", expanded=False):
        df_edges = pd.DataFrame(
            [
                {"Điểm đi": S.node_label(u), "Điểm đến": S.node_label(v), "Thời gian (phút)": f"{w:g}"}
                for u, v, w in edges
            ]
        )
        st.dataframe(df_edges, hide_index=True, width="stretch", height=280)


    st.divider()

    # 3. Quản lý Tài xế
    st.subheader("Quản lý Đội ngũ Tài xế")
    st.dataframe(_drivers_table(drivers), hide_index=True, width="stretch")

    col_add, col_edit = st.columns(2)
    with col_add:
        st.markdown("##### Thêm tài xế mới")
        with st.form("form_add_driver", border=True):
            st.text_input("Tên tài xế", key="add_name", placeholder="Nhập họ tên tài xế...")
            st.selectbox("Vị trí xuất phát", labels, key="add_node")
            st.form_submit_button("Thêm tài xế", on_click=_on_add_driver, type="primary", width="stretch")

    with col_edit:
        st.markdown("##### Cập nhật hoặc Xóa tài xế")
        if drivers:
            with st.container(border=True):
                chosen = S.item_id(
                    st.selectbox(
                        "Chọn tài xế",
                        [f"{i} – {x.name}" for i, x in drivers.items()],
                        key="edit_driver",
                    )
                )
                cur = drivers[chosen]
                st.text_input(
                    "Tên tài xế",
                    key=f"edit_name_{chosen}",
                    value=cur.name,
                )
                st.selectbox(
                    "Vị trí",
                    labels,
                    key=f"edit_node_{chosen}_{cur.node}",
                    index=nodes.index(cur.node) if cur.node in nodes else 0,
                    disabled=cur.status == BUSY,
                )
                c1, c2 = st.columns(2)
                c1.button("Lưu thay đổi", on_click=_on_update_driver, key="btn_update_driver", width="stretch")
                if c2.button(
                    "Xóa tài xế",
                    key="btn_remove_driver",
                    type="secondary",
                    disabled=cur.status == BUSY,
                    width="stretch",
                    help="Xóa tài xế khỏi danh sách nếu chưa có lịch sử chuyến",
                ):
                    st.session_state["show_remove_driver_dialog"] = True

                if st.session_state.get("show_remove_driver_dialog"):
                    _confirm_remove_driver_dialog(cur.id, cur.name)

                st.caption("Tài xế đang bận hoặc đã có lịch sử chuyến không thể xóa.")
        else:
            render_empty_state(
                "👥",
                "Chưa có tài xế nào",
                "Mạng lưới giao thông hiện chưa có tài xế nào được đăng ký.",
                "Sử dụng form 'Thêm tài xế mới' bên cạnh để tạo tài xế xuất phát tại một nút giao.",
            )

    st.divider()
    c_btn1, c_btn2 = st.columns(2)
    with c_btn1:
        st.button(
            "🔄 Tải lại dữ liệu từ runtime",
            on_click=_on_reload,
            key="btn_reload",
            help="Nạp lại dữ liệu từ file trong data/runtime/ (bỏ các thay đổi chưa lưu; làm mới Undo/Redo).",
            width="stretch",
        )
    with c_btn2:
        if st.button(
            "🌱 Reset về dữ liệu mẫu (Seed)",
            key="btn_reset_seed",
            type="secondary",
            help="Khôi phục toàn bộ dữ liệu runtime về trạng thái ban đầu từ data/seed/. Phù hợp khi bắt đầu demo.",
            width="stretch",
        ):
            st.session_state["show_reset_dialog"] = True

    if st.session_state.get("show_reset_dialog"):
        _confirm_reset_seed_dialog()
