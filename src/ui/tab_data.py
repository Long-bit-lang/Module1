"""TV5 - Tab "Quản lý dữ liệu": tài xế, đồ thị, nạp lại dữ liệu."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from . import session as S
from .constants import status_label


def _drivers_table(drivers: dict) -> pd.DataFrame:
    rows = [{"ID": d.id, "Tên": d.name, "Vị trí": S.node_label(d.node),
             "Trạng thái": status_label(d.status)} for d in drivers.values()]
    return pd.DataFrame(rows, columns=["ID", "Tên", "Vị trí", "Trạng thái"])


def _on_add_driver() -> None:
    name, node = st.session_state["add_name"], S.item_id(st.session_state["add_node"])
    ok, drv = S.perform(lambda: S.dispatcher().add_driver(name, node))
    if ok:
        S.flash("success", f"Đã thêm tài xế {drv.id} – {drv.name}")
        st.session_state["add_name"] = ""


def _on_update_driver() -> None:
    did = S.item_id(st.session_state["edit_driver"])
    S.perform(lambda: S.dispatcher().update_driver(
        did, name=st.session_state[f"edit_name_{did}"] or None,
        node=S.item_id(st.session_state[f"edit_node_{did}"])),
        f"Đã cập nhật tài xế {did}")


def _on_remove_driver() -> None:
    did = S.item_id(st.session_state["edit_driver"])
    ok, removed = S.perform(lambda: S.dispatcher().remove_driver(did))
    if ok and removed:
        S.flash("success", f"Đã xóa tài xế {did}")
    elif ok:
        S.flash("warning", f"Không tìm thấy tài xế {did}")


def _on_reload() -> None:
    S.reload_from_disk()
    S.flash("info", "Đã nạp lại dữ liệu từ đĩa; lịch sử Undo/Redo đã được đặt lại.")


def _dot(edges) -> str:
    lines = ["digraph G { rankdir=LR; node [shape=box, style=rounded];"]
    for n in S.dispatcher().graph.nodes():
        lines.append(f'"{n}" [label="{S.node_label(n)}"];')
    lines += [f'"{u}" -> "{v}" [label="{w:g}"];' for u, v, w in edges]
    return "\n".join(lines) + "}"


def render() -> None:
    d = S.dispatcher()
    drivers = d.drivers_snapshot()
    nodes = d.graph.nodes()
    labels = S.node_labels()

    st.subheader("Tài xế")
    st.dataframe(_drivers_table(drivers), hide_index=True, width="stretch")

    col_add, col_edit = st.columns(2)
    with col_add:
        st.markdown("**Thêm tài xế**")
        with st.form("form_add_driver", border=True):
            st.text_input("Tên tài xế", key="add_name")
            st.selectbox("Vị trí hiện tại", labels, key="add_node")
            st.form_submit_button("Thêm tài xế", on_click=_on_add_driver, type="primary")
    with col_edit:
        st.markdown("**Sửa / xóa tài xế**")
        if drivers:
            with st.container(border=True):
                chosen = S.item_id(st.selectbox(
                    "Chọn tài xế", [f"{i} – {x.name}" for i, x in drivers.items()],
                    key="edit_driver"))
                cur = drivers[chosen]
                st.text_input("Tên mới (để trống = giữ nguyên)", key=f"edit_name_{chosen}", value="")
                st.selectbox("Vị trí mới", labels, key=f"edit_node_{chosen}",
                             index=nodes.index(cur.node) if cur.node in nodes else 0)
                c1, c2 = st.columns(2)
                c1.button("Lưu thay đổi", on_click=_on_update_driver, key="btn_update_driver")
                c2.button("Xóa tài xế", on_click=_on_remove_driver, key="btn_remove_driver")
        else:
            st.info("Chưa có tài xế nào.")

    st.subheader("Đồ thị giao thông")
    edges = d.graph.edges()
    c_graph, c_tables = st.columns([3, 2])
    with c_graph:
        st.graphviz_chart(_dot(edges), width="stretch")
    with c_tables:
        st.caption(f"{len(nodes)} đỉnh · {len(edges)} cạnh (trọng số = phút)")
        st.dataframe(pd.DataFrame(edges, columns=["Từ", "Đến", "Phút"]),
                     hide_index=True, width="stretch", height=260)

    st.divider()
    st.button("🔄 Tải lại dữ liệu từ đĩa", on_click=_on_reload, key="btn_reload",
              help="Bỏ trạng thái trong bộ nhớ và đọc lại JSON. Lịch sử Undo/Redo sẽ mất.")
