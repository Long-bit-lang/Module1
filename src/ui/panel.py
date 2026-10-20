"""TV5 - Panel thao tác bên phải (Action Panel) ẩn/hiện.

Chứa toàn bộ các widget thao tác nghiệp vụ, bảo đảm:
1. Widget keys luôn được render duy nhất một lần và không bao giờ mất khi đổi trang.
2. Cửa sổ chính chỉ dành cho hiển thị trực quan (KPI, bản đồ, bảng, kết quả, lịch sử, benchmark).
3. Hỗ trợ bật/tắt (toggle) bằng nút nổi key="btn_toggle_panel".
"""
from __future__ import annotations

import html
import streamlit as st

from . import session as S
from .constants import ASSIGNED, BUSY, FREE, status_label


# ── Callbacks cho mục Đặt xe ──────────────────────────────────────────────────
def _on_submit() -> None:
    pickup = S.item_id(st.session_state["req_pickup"])
    dropoff = S.item_id(st.session_state["req_dropoff"])
    if pickup == dropoff:
        S.flash("error", "Điểm đón và điểm trả phải khác nhau.")
        return
    ok, req = S.perform(lambda: S.dispatcher().submit_request(pickup, dropoff))
    if ok:
        S.flash("success", f"Đã tạo yêu cầu {req.id}: {S.node_label(pickup)} → {S.node_label(dropoff)}")


def _on_cancel_request() -> None:
    val = st.session_state.get("cancel_req_select")
    if not val:
        return
    req_id = S.item_id(val)
    ok, done = S.perform(lambda: S.dispatcher().cancel_request(req_id))
    if ok and done:
        S.flash("success", f"Đã hủy yêu cầu {req_id} khỏi hàng đợi.")
    elif ok:
        S.flash("warning", f"Không thể hủy yêu cầu {req_id}.")


@st.dialog("⚠️ Xác nhận hủy yêu cầu đặt xe")
def _confirm_cancel_dialog(req_str: str) -> None:
    st.markdown(
        f"Bạn có chắc chắn muốn hủy yêu cầu **{html.escape(req_str)}** khỏi hàng đợi FIFO không?\n\n"
        "Thao tác này sẽ xóa yêu cầu khỏi hàng đợi và danh sách của hệ thống."
    )
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Xác nhận hủy", key="btn_confirm_cancel_request", type="primary", width="stretch"):
            st.session_state["show_cancel_dialog"] = False
            _on_cancel_request()
            st.rerun()
    with c2:
        if st.button("Quay lại", key="btn_abort_cancel_request", width="stretch"):
            st.session_state["show_cancel_dialog"] = False
            st.rerun()


# ── Callbacks cho mục Tài xế ──────────────────────────────────────────────────
def _on_add_driver() -> None:
    name = st.session_state["add_name"].strip()
    node = S.item_id(st.session_state["add_node"])
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


# ── Callbacks cho mục Điều phối ───────────────────────────────────────────────
_REASON = {
    "empty_queue": "Hàng đợi yêu cầu đang trống. Vui lòng tạo yêu cầu đặt xe mới trước khi ghép chuyến.",
    "no_free_driver": "Không còn tài xế rảnh: hãy hoàn thành chuyến đang chạy hoặc thêm tài xế mới.",
    "no_route": "Có tài xế rảnh nhưng không ai đi được tới điểm đón (đường một chiều hoặc đồ thị không liên thông).",
}


def _on_dispatch() -> None:
    name = st.session_state["strategy_name"]
    strategy = S.RecordingStrategy(S.strategies()[name])
    ok, trip = S.perform(lambda: S.dispatcher().dispatch_next(strategy))
    if not ok:
        return
    if trip is None:
        why = getattr(S.dispatcher(), "last_failure", None)
        reason_msg = _REASON.get(why, "Không có tài xế phù hợp trên mạng lưới.")
        # Lưu kết quả thất bại cho thẻ Hạng mục C
        st.session_state[S.K_LAST] = {
            "failed": True,
            "strategy": name,
            "reason": why,
            "message": reason_msg,
            "suggestion": "Thêm tài xế rảnh tại vị trí gần hơn hoặc hủy yêu cầu không thể tiếp cận.",
        }
        S.flash("warning", "Không thể điều phối: " + reason_msg)
        return
    st.session_state[S.K_LAST] = {
        "failed": False,
        "trip": trip,
        "strategy": name,
        "result": strategy.last_result,
        "status_tag": "Đang chạy",
    }
    S.flash("success", f"Đã ghép thành công chuyến {trip.id} cho tài xế {trip.driver_id} (ETA: {trip.eta:g} phút).")


def _on_dispatch_all() -> None:
    strategy_name = st.session_state["strategy_name"]
    strategy = S.RecordingStrategy(S.strategies()[strategy_name])
    ok, trips = S.perform(lambda: S.dispatcher().dispatch_all(strategy))
    if not ok:
        return
    why = getattr(S.dispatcher(), "last_failure", None)
    if trips:
        last_trip = trips[-1]
        st.session_state[S.K_LAST] = {
            "failed": False,
            "trip": last_trip,
            "strategy": strategy_name,
            "result": strategy.last_result,
            "status_tag": f"Đã ghép hàng loạt ({len(trips)} chuyến)",
        }
    S.flash(
        "success" if trips else "warning",
        f"Đã ghép {len(trips)} chuyến. " + (_REASON.get(why, "") if why != "empty_queue" else ""),
    )


def _on_undo() -> None:
    ok, done = S.perform(lambda: S.dispatcher().undo())
    if ok:
        if done and st.session_state.get(S.K_LAST):
            st.session_state[S.K_LAST]["status_tag"] = "Đã hoàn tác"
        S.flash(
            "success" if done else "warning",
            "Đã hoàn tác lần điều phối gần nhất: yêu cầu đã quay lại đầu hàng đợi FIFO."
            if done
            else "Không có gì để hoàn tác.",
        )


def _on_redo() -> None:
    ok, done = S.perform(lambda: S.dispatcher().redo())
    if ok:
        if done and st.session_state.get(S.K_LAST):
            st.session_state[S.K_LAST]["status_tag"] = "Đã làm lại (Redo)"
        S.flash(
            "success" if done else "warning",
            "Đã làm lại lần điều phối vừa hoàn tác." if done else "Không có gì để làm lại.",
        )


def _on_complete(trip_id: str) -> None:
    ok, done = S.perform(lambda: S.dispatcher().complete_trip(trip_id))
    if ok:
        if done and st.session_state.get(S.K_LAST):
            if st.session_state[S.K_LAST].get("trip") and st.session_state[S.K_LAST]["trip"].id == trip_id:
                st.session_state[S.K_LAST]["status_tag"] = "Chuyến đã hoàn thành"
        S.flash(
            "success" if done else "warning",
            f"Chuyến {trip_id} đã hoàn thành; tài xế được giải phóng tại điểm trả khách."
            if done
            else f"Không thể hoàn thành chuyến {trip_id}.",
        )


def _toggle_panel() -> None:
    st.session_state["panel_open"] = not st.session_state.get("panel_open", True)


def render_action_panel() -> None:
    """Render panel thao tác cố định bên phải (Action Panel)."""
    if "panel_open" not in st.session_state:
        st.session_state["panel_open"] = True

    is_open = st.session_state["panel_open"]

    d = S.dispatcher()
    labels = S.node_labels()
    nodes = list(d.graph.nodes())
    queue = d.queue_snapshot()
    drivers = d.drivers_snapshot()
    trips = d.trips_snapshot()
    free_count = sum(1 for x in drivers.values() if x.status == FREE)
    active_trips = [t for t in trips if t.status == ASSIGNED]

    # Nút nổi bật tắt panel luôn ở DOM với nhãn trực quan
    toggle_label = "✕ Thu gọn bảng" if is_open else "⚡ Bảng thao tác ◀"
    st.button(
        toggle_label,
        key="btn_toggle_panel",
        on_click=_toggle_panel,
        help="Ẩn hoặc hiện bảng thao tác nhanh bên phải",
    )

    with st.container(key="action_panel"):
        st.markdown(
            """
            <div class="panel-header">
                <span class="panel-header-title">⚡ BẢNG THAO TÁC NHANH</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # ── (1) Mục ĐẶT XE ────────────────────────────────────────────────────
        with st.expander("🚕 (1) Đặt xe mới & Hủy yêu cầu", expanded=True):
            st.selectbox(
                "Điểm đón khách",
                labels,
                key="req_pickup",
                help="Chọn vị trí đón khách",
            )
            st.selectbox(
                "Điểm trả khách",
                labels,
                key="req_dropoff",
                index=min(1, len(labels) - 1),
                help="Chọn địa điểm đến của khách",
            )

            cur_p = S.item_id(st.session_state.get("req_pickup", labels[0]))
            cur_d = S.item_id(st.session_state.get("req_dropoff", labels[min(1, len(labels) - 1)]))
            if cur_p == cur_d:
                st.caption("⚠️ Điểm đón và trả trùng nhau.")
            else:
                est = d.ride_estimate(cur_p, cur_d) if hasattr(d, "ride_estimate") else None
                if est:
                    st.caption(f"⏱️ Dự kiến: ~{est[0]:g} phút ({len(est[1]) - 1} chặng)")
                else:
                    st.caption("⚠️ Không có đường đi giữa 2 điểm này.")

            st.button(
                "Gửi yêu cầu",
                on_click=_on_submit,
                key="btn_submit",
                type="primary",
                width="stretch",
                help="Đưa yêu cầu vào hàng đợi FIFO",
            )

            if queue:
                st.divider()
                st.caption(f"Hàng đợi ({len(queue)} yêu cầu)")
                st.selectbox(
                    "Chọn yêu cầu hủy",
                    [f"{r.id} ({S.node_label(r.pickup_node)} → {S.node_label(r.dropoff_node)})" for r in queue],
                    key="cancel_req_select",
                )
                if st.button("Hủy yêu cầu", key="btn_cancel_request", width="stretch"):
                    st.session_state["show_cancel_dialog"] = True
                if st.session_state.get("show_cancel_dialog"):
                    req_val = st.session_state.get("cancel_req_select", "")
                    _confirm_cancel_dialog(req_val)

        # ── (2) Mục TÀI XẾ ────────────────────────────────────────────────────
        with st.expander("👤 (2) Quản lý Tài xế", expanded=False):
            st.markdown("<b>Thêm tài xế mới:</b>", unsafe_allow_html=True)
            with st.form("form_add_driver", border=True):
                st.text_input("Tên tài xế", key="add_name", placeholder="Nhập họ tên...")
                st.selectbox("Vị trí xuất phát", labels, key="add_node")
                st.form_submit_button("Thêm tài xế", on_click=_on_add_driver, type="primary", width="stretch")

            st.divider()
            st.markdown("<b>Sửa / Xóa tài xế:</b>", unsafe_allow_html=True)
            if drivers:
                chosen = S.item_id(
                    st.selectbox(
                        "Chọn tài xế",
                        [f"{i} – {x.name}" for i, x in drivers.items()],
                        key="edit_driver",
                    )
                )
                cur = drivers[chosen]
                st.text_input("Tên tài xế", key=f"edit_name_{chosen}", value=cur.name)
                st.selectbox(
                    "Vị trí",
                    labels,
                    key=f"edit_node_{chosen}_{cur.node}",
                    index=nodes.index(cur.node) if cur.node in nodes else 0,
                    disabled=cur.status == BUSY,
                )
                c_u, c_r = st.columns(2)
                c_u.button("Lưu thay đổi", on_click=_on_update_driver, key="btn_update_driver", width="stretch")
                if c_r.button(
                    "Xóa tài xế",
                    key="btn_remove_driver",
                    type="secondary",
                    disabled=cur.status == BUSY,
                    width="stretch",
                ):
                    st.session_state["show_remove_driver_dialog"] = True

                if st.session_state.get("show_remove_driver_dialog"):
                    _confirm_remove_driver_dialog(cur.id, cur.name)
            else:
                st.caption("Chưa có tài xế nào.")

        # ── (3) Mục ĐIỀU PHỐI ────────────────────────────────────────────────
        with st.expander("⚡ (3) Điều phối & Chuyến đang chạy", expanded=True):
            st.selectbox(
                "Chiến lược điều phối",
                list(S.strategies()),
                key="strategy_name",
                help="A1: Dijkstra từng tài xế | A2: Dijkstra đảo chiều",
            )
            col_d1, col_d2 = st.columns(2)
            with col_d1:
                st.button(
                    f"Ghép ({free_count} rảnh)",
                    on_click=_on_dispatch,
                    key="btn_dispatch",
                    type="primary",
                    disabled=not queue,
                    width="stretch",
                )
            with col_d2:
                st.button(
                    f"Ghép hết ({len(queue)})",
                    on_click=_on_dispatch_all,
                    key="btn_dispatch_all",
                    disabled=not queue,
                    width="stretch",
                )

            st.caption("Lịch sử hoàn tác (Undo / Redo):")
            col_un, col_re = st.columns(2)
            with col_un:
                st.button(
                    "↩ Undo",
                    on_click=_on_undo,
                    key="btn_undo",
                    disabled=not d.can_undo(),
                    width="stretch",
                )
            with col_re:
                st.button(
                    "↪ Redo",
                    on_click=_on_redo,
                    key="btn_redo",
                    disabled=not d.can_redo(),
                    width="stretch",
                )

            st.divider()
            st.markdown(f"<b>Chuyến đang chạy ({len(active_trips)}):</b>", unsafe_allow_html=True)
            if active_trips:
                for t in active_trips:
                    dr_obj = drivers.get(t.driver_id)
                    dr_label = f"{t.driver_id} ({dr_obj.name})" if dr_obj else t.driver_id
                    st.markdown(
                        f"""
                        <div style="background:#F1F5F9; padding:0.4rem 0.6rem; border-radius:6px; margin-bottom:0.35rem; font-size:0.83rem;">
                            <b>Chuyến {html.escape(t.id)}</b>: Khách {html.escape(t.request_id)} ➔ Xe {html.escape(dr_label)}<br>
                            <span style="color:#64748B;">ETA: {t.eta:g} phút</span>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                    st.button(
                        f"Hoàn thành chuyến {t.id}",
                        key=f"btn_complete_{t.id}",
                        on_click=_on_complete,
                        args=(t.id,),
                        type="secondary",
                        width="stretch",
                    )
            else:
                st.caption("Không có chuyến nào đang hoạt động.")
