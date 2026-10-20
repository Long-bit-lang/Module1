"""TV5 - Tab "Quản lý dữ liệu": tài xế, đồ thị giao thông, nạp lại dữ liệu."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from . import session as S
from .components import page_header, render_empty_state, render_graph_with_zoom
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



def _on_reset_drivers_filter() -> None:
    st.session_state["flt_drivers_status"] = []
    st.session_state["flt_drivers_search"] = ""
    st.session_state["flt_drivers_node"] = []


def _on_reset_edges_filter() -> None:
    st.session_state["flt_edges_search"] = ""


def _filter_drivers(drivers: dict, nodes: list) -> dict:
    statuses = st.session_state.get("flt_drivers_status", [])
    search = st.session_state.get("flt_drivers_search", "").strip().lower()
    nodes_sel = st.session_state.get("flt_drivers_node", [])

    filtered = {}
    for did, d in drivers.items():
        if statuses and d.status not in statuses:
            continue
        if search and (search not in d.id.lower() and search not in d.name.lower()):
            continue
        if nodes_sel and d.node not in nodes_sel:
            continue
        filtered[did] = d
    return filtered


def _filter_edges(edges: list[tuple[str, str, float]]) -> list[tuple[str, str, float]]:
    search = st.session_state.get("flt_edges_search", "").strip().lower()
    if not search:
        return edges
    filtered = []
    for u, v, w in edges:
        u_label = S.node_label(u).lower()
        v_label = S.node_label(v).lower()
        if search in u_label or search in v_label or search in u.lower() or search in v.lower():
            filtered.append((u, v, w))
    return filtered


def render() -> None:
    d = S.dispatcher()
    drivers = d.drivers_snapshot()
    nodes = d.graph.nodes()
    labels = S.node_labels()
    edges = d.graph.edges()

    free_count = sum(1 for x in drivers.values() if x.status == FREE)
    busy_count = len(drivers) - free_count

    page_header(
        icon="🗺️",
        title="Quản lý dữ liệu",
        subtitle="Mạng lưới giao thông và đội ngũ tài xế",
        chips=[
            ("**Số đỉnh**", f"{len(nodes)}"),
            ("**Số cung**", f"{len(edges)}"),
            ("**Xe rảnh**", f"{free_count}"),
            ("**Xe bận**", f"{busy_count}"),
        ],
    )

    # 1. Danh sách Tuyến đường
    with st.expander(f"📋 Danh sách Tuyến đường ({len(edges)} cung kết nối)", expanded=True):
        with st.expander("🔍 Bộ lọc", expanded=True):
            c_f1, c_f2 = st.columns([4, 1], vertical_alignment="bottom")
            with c_f1:
                st.text_input(
                    "Tìm kiếm theo địa danh",
                    key="flt_edges_search",
                    placeholder="Nhập tên điểm đi hoặc điểm đến...",
                )
            with c_f2:
                st.button(
                    "Xóa bộ lọc",
                    key="flt_edges_reset",
                    on_click=_on_reset_edges_filter,
                    width="stretch",
                )

        filtered_edges = _filter_edges(edges)
        st.caption(f"Hiển thị {len(filtered_edges)}/{len(edges)} bản ghi")

        if not filtered_edges:
            render_empty_state(
                "🔍",
                "Không tìm thấy tuyến đường",
                "Không có tuyến đường nào khớp với từ khóa tìm kiếm.",
                "Thử tìm với tên địa danh khác hoặc nhấn 'Xóa bộ lọc'.",
            )
        else:
            df_edges = pd.DataFrame(
                [
                    {"Điểm đi": S.node_label(u), "Điểm đến": S.node_label(v), "Thời gian (phút)": f"{w:g}"}
                    for u, v, w in filtered_edges
                ]
            )
            st.dataframe(df_edges, hide_index=True, width="stretch", height=280)

    st.divider()

    # 2. Quản lý Tài xế
    st.subheader("Quản lý Đội ngũ Tài xế")

    with st.expander("🔍 Bộ lọc", expanded=True):
        c1, c2, c3, c4 = st.columns([1.5, 2, 2, 1], vertical_alignment="bottom")
        with c1:
            st.multiselect(
                "Trạng thái",
                options=[FREE, BUSY],
                format_func=status_label,
                key="flt_drivers_status",
            )
        with c2:
            st.text_input(
                "Tìm theo tên/ID",
                key="flt_drivers_search",
                placeholder="VD: D1, An...",
            )
        with c3:
            st.multiselect(
                "Vị trí",
                options=nodes,
                format_func=S.node_label,
                key="flt_drivers_node",
            )
        with c4:
            st.button(
                "Xóa bộ lọc",
                key="flt_drivers_reset",
                on_click=_on_reset_drivers_filter,
                width="stretch",
            )

    filtered_drivers = _filter_drivers(drivers, nodes)
    st.caption(f"Hiển thị {len(filtered_drivers)}/{len(drivers)} bản ghi")

    if not drivers:
        render_empty_state("🚗", "Chưa có tài xế", "Hệ thống chưa có dữ liệu tài xế nào.")
    elif not filtered_drivers:
        render_empty_state(
            "🔍",
            "Không tìm thấy tài xế",
            "Không có tài xế nào khớp với các tiêu chí bộ lọc đã chọn.",
            "Thử điều chỉnh điều kiện lọc hoặc nhấn 'Xóa bộ lọc' để xem lại toàn bộ.",
        )
    else:
        st.dataframe(_drivers_table(filtered_drivers), hide_index=True, width="stretch")

    st.caption("💡 *Để thêm tài xế mới, sửa thông tin hoặc xóa tài xế, sử dụng mục **(2) Quản lý Tài xế** trên Bảng thao tác bên phải.*")

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

    st.divider()

    # 3. Bản đồ Mạng lưới Giao thông (xuống dưới cùng)
    st.subheader("Bản đồ Mạng lưới Giao thông")
    st.caption("Các đỉnh màu xanh lá có tài xế sẵn sàng nhận cuốc; màu đỏ có tài xế đang bận.")

    dot_map = build_dot(edges, drivers, d.queue_snapshot(), S.node_label, nodes)
    render_graph_with_zoom(dot_map, key_prefix="map_data", height=500)
