"""TV5 - Tab "Điều phối chuyến": yêu cầu, hàng đợi FIFO, điều phối, Undo/Redo, quản lý chuyến."""
from __future__ import annotations

import html

import pandas as pd
import streamlit as st

from . import session as S
from .components import get_status_badge_html, render_empty_state, render_route_breadcrumb
from .constants import ASSIGNED, FREE, status_label

_REASON = {
    "empty_queue": "Hàng đợi yêu cầu đang trống. Vui lòng tạo yêu cầu đặt xe mới trước khi ghép chuyến.",
    "no_free_driver": "Không còn tài xế rảnh: hãy hoàn thành chuyến đang chạy bên dưới hoặc thêm tài xế mới ở tab 'Quản lý dữ liệu'.",
    "no_route": "Có tài xế rảnh nhưng không ai đi được tới điểm đón (đường một chiều hoặc đồ thị không liên thông). Yêu cầu vẫn nằm ở đầu hàng đợi FIFO.",
}


# ---------------------------------------------------------------------- callbacks
def _on_submit() -> None:
    pickup = S.item_id(st.session_state["req_pickup"])
    dropoff = S.item_id(st.session_state["req_dropoff"])
    if pickup == dropoff:
        S.flash("error", "Điểm đón và điểm trả phải khác nhau.")
        return
    ok, req = S.perform(lambda: S.dispatcher().submit_request(pickup, dropoff))
    if ok:
        S.flash("success", f"Đã tạo yêu cầu {req.id}: {S.node_label(pickup)} → {S.node_label(dropoff)}")


def _on_dispatch() -> None:
    name = st.session_state["strategy_name"]
    strategy = S.RecordingStrategy(S.strategies()[name])
    ok, trip = S.perform(lambda: S.dispatcher().dispatch_next(strategy))
    if not ok:
        return
    if trip is None:
        why = getattr(S.dispatcher(), "last_failure", None)
        S.flash("warning", "Không thể điều phối: " + _REASON.get(why, "không có tài xế phù hợp."))
        return
    st.session_state[S.K_LAST] = {"trip": trip, "strategy": name, "result": strategy.last_result}
    S.flash("success", f"Đã ghép thành công chuyến {trip.id} cho tài xế {trip.driver_id} (ETA: {trip.eta:g} phút).")


def _on_dispatch_all() -> None:
    strategy = S.RecordingStrategy(S.strategies()[st.session_state["strategy_name"]])
    ok, trips = S.perform(lambda: S.dispatcher().dispatch_all(strategy))
    if not ok:
        return
    st.session_state[S.K_LAST] = None
    why = getattr(S.dispatcher(), "last_failure", None)
    S.flash(
        "success" if trips else "warning",
        f"Đã ghép {len(trips)} chuyến. " + (_REASON.get(why, "") if why != "empty_queue" else ""),
    )


def _on_undo() -> None:
    ok, done = S.perform(lambda: S.dispatcher().undo())
    if ok:
        st.session_state[S.K_LAST] = None
        S.flash(
            "success" if done else "warning",
            "Đã hoàn tác lần điều phối gần nhất: yêu cầu đã quay lại đầu hàng đợi FIFO."
            if done
            else "Không có gì để hoàn tác.",
        )


def _on_redo() -> None:
    ok, done = S.perform(lambda: S.dispatcher().redo())
    if ok:
        S.flash(
            "success" if done else "warning",
            "Đã làm lại lần điều phối vừa hoàn tác." if done else "Không có gì để làm lại.",
        )


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


def _on_complete(trip_id: str) -> None:
    ok, done = S.perform(lambda: S.dispatcher().complete_trip(trip_id))
    if ok:
        if done:
            st.session_state[S.K_LAST] = None
        S.flash(
            "success" if done else "warning",
            f"Chuyến {trip_id} đã hoàn thành; tài xế được giải phóng tại điểm trả khách."
            if done
            else f"Không thể hoàn thành chuyến {trip_id}.",
        )


# ------------------------------------------------------------------------- render
def _queue_table(queue) -> pd.DataFrame:
    rows = [
        {
            "Thứ tự": f"#{i + 1}" if i > 0 else "Tiếp theo (#1)",
            "Mã yêu cầu": r.id,
            "Điểm đón": S.node_label(r.pickup_node),
            "Điểm trả": S.node_label(r.dropoff_node),
            "Trạng thái": status_label(r.status),
        }
        for i, r in enumerate(queue)
    ]
    return pd.DataFrame(rows, columns=["Thứ tự", "Mã yêu cầu", "Điểm đón", "Điểm trả", "Trạng thái"])


def _render_last_result() -> None:
    last = st.session_state.get(S.K_LAST)
    if not last:
        return

    # C3: Khi ghép thất bại -> hiện thẻ cảnh báo cùng vị trí với giải thích và gợi ý
    if last.get("failed"):
        strategy = html.escape(str(last.get("strategy", "")))
        reason_msg = html.escape(str(last.get("message", "Không thể điều phối chuyến.")))
        suggestion = html.escape(str(last.get("suggestion", "Kiểm tra hàng đợi và tài xế rảnh.")))

        with st.container(key="dispatch_failure_card"):
            c_header, c_hide = st.columns([5.5, 1], vertical_alignment="center")
            with c_header:
                st.markdown(
                    f"""
                    <div class="dispatch-failed-title">
                        ⚠️ <b>Không thể ghép chuyến ({strategy})</b>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            with c_hide:
                if st.button("Ẩn kết quả", key="btn_hide_last_result", help="Ẩn thông báo này"):
                    st.session_state[S.K_LAST] = None
                    st.rerun()

            st.markdown(
                f"""
                <div class="dispatch-failed-card">
                    <div style="margin-bottom: 0.4rem; font-size: 0.95rem; color: #991B1B;">
                        <b>Nguyên nhân:</b> {reason_msg}
                    </div>
                    <div style="font-size: 0.86rem; color: #7F1D1D; background: #FEE2E2; padding: 0.45rem 0.75rem; border-radius: 6px;">
                        💡 <b>Gợi ý hành động:</b> {suggestion}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        return

    if last.get("result") is None or not last.get("trip"):
        return

    # C1 & C2: Thẻ kết quả điều phối thành công nổi bật
    res, trip = last["result"], last["trip"]
    d = S.dispatcher()
    driver_name = d.drivers_snapshot().get(trip.driver_id)
    driver_str = f"{trip.driver_id} – {driver_name.name}" if driver_name else trip.driver_id
    status_tag = last.get("status_tag", "Đang chạy")

    badge_map = {
        "Đã hoàn tác": "badge-busy",
        "Chuyến đã hoàn thành": "badge-completed",
        "Đang chạy": "badge-assigned",
        "Đã làm lại (Redo)": "badge-assigned",
    }
    badge_cls = badge_map.get(status_tag, "badge-default")
    status_badge_html = f'<span class="badge-status {badge_cls}">{html.escape(status_tag)}</span>'

    with st.container(key="dispatch_result_card"):
        c_title, c_hide = st.columns([5.5, 1], vertical_alignment="center")
        with c_title:
            st.markdown(
                f"""
                <div class="dispatch-result-header">
                    <span class="dispatch-result-title">🚕 Đã ghép chuyến {html.escape(trip.id)} ↔ {html.escape(trip.driver_id)}</span>
                    {status_badge_html}
                    <span class="dispatch-result-strategy">({html.escape(last['strategy'])})</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with c_hide:
            if st.button("Ẩn kết quả", key="btn_hide_last_result", help="Ẩn thẻ kết quả này"):
                st.session_state[S.K_LAST] = None
                st.rerun()

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Tài xế nhận cuốc", driver_str)
        c2.metric("Thời gian đón (ETA)", f"{res.eta:g} phút")
        c3.metric("Số đỉnh đã duyệt", f"{res.visited_count} đỉnh")
        c4.metric("Thời gian tính toán", f"{res.runtime_ms:.3f} ms")

        if res.path:
            render_route_breadcrumb(
                res.path,
                S.node_label,
                title="Lộ trình di chuyển đón khách:",
            )


def _render_map(d, queue, drivers) -> None:
    from .components import render_graph_with_zoom
    from .graph_view import build_dot

    routes, note = [], "Chưa có lộ trình để hiển thị."
    last = st.session_state.get(S.K_LAST)
    if last and last["result"] and last["result"].path:
        routes.append((last["result"].path, "#16a34a", "solid"))
        est = d.ride_estimate(last["trip"].request_id) if hasattr(d, "ride_estimate") else None
        if est:
            routes.append((est[1], "#ea580c", "dashed"))
            note = (
                f"Xanh lá: xe đến điểm đón ({last['result'].eta:g} phút). "
                f"Cam nét đứt: chở khách đến điểm trả ({est[0]:g} phút)."
            )
        else:
            note = "Xanh lá: xe đến điểm đón."
    elif queue:
        free = {x.id: x.node for x in drivers.values() if x.status == FREE}
        name = st.session_state.get("strategy_name") or next(iter(S.strategies()))
        if free:
            res = S.strategies()[name].find_driver(d.graph, queue[0].pickup_node, free)
            if res.path:
                routes.append((res.path, "#2563eb", "dashed"))
                note = (
                    f"Xem trước (chưa ghép): yêu cầu {queue[0].id} sẽ do "
                    f"{res.driver_id} nhận, ETA {res.eta:g} phút."
                )
    st.subheader("Bản đồ điều phối")
    dot_dispatch = build_dot(d.graph.edges(), drivers, queue, S.node_label, d.graph.nodes(), routes)
    render_graph_with_zoom(dot_dispatch, key_prefix="map_dispatch", height=500)
    st.caption(note + "  Viền cam: điểm đón đang chờ.")



def render() -> None:
    d = S.dispatcher()
    labels = S.node_labels()
    queue = d.queue_snapshot()
    drivers = d.drivers_snapshot()
    trips = d.trips_snapshot()
    free_count = sum(1 for x in drivers.values() if x.status == FREE)

    # Khung 1: Hàng đợi yêu cầu FIFO
    st.subheader(f"Hàng đợi yêu cầu FIFO ({len(queue)})")
    with st.container(border=True):
        if queue:
            st.dataframe(_queue_table(queue), hide_index=True, width="stretch", height=150)
        else:
            render_empty_state(
                "📭",
                "Hàng đợi yêu cầu đang trống",
                "Hiện không có khách nào đang chờ điều phối xe.",
                "Sử dụng mục '(1) Đặt xe' trên Bảng thao tác bên phải rồi nhấn 'Gửi yêu cầu'.",
            )
        st.caption("💡 *Đặt xe mới, hủy yêu cầu, hoặc nhấn Ghép chuyến / Undo / Redo trên **Bảng thao tác bên phải**.*")

    # Hiển thị nút giải phóng nghẽn hàng nếu nguyên nhân là no_route
    if getattr(d, "last_failure", None) == "no_route" and queue:
        st.warning(
            f"⚠️ **Yêu cầu đầu hàng ({queue[0].id}: {S.node_label(queue[0].pickup_node)} → {S.node_label(queue[0].dropoff_node)})** "
            "không có tài xế nào tiếp cận được do đường một chiều. Bạn có thể hủy yêu cầu này trên Bảng thao tác bên phải để tiếp tục xử lý các yêu cầu kế tiếp."
        )

    st.divider()

    # Khung 2: Thẻ Kết quả điều phối nổi bật (Hạng mục C)
    _render_last_result()

    # Khung 3: Bản đồ điều phối có lộ trình
    _render_map(d, queue, drivers)

    st.divider()

    # Khung 4: Danh sách các Chuyến xe (Lịch sử chỉ đọc - D3)
    st.subheader(f"Danh sách Chuyến xe ({len(trips)})")
    if not trips:
        render_empty_state(
            "🚕",
            "Chưa có chuyến xe nào",
            "Hệ thống chưa tạo chuyến xe nào trong phiên làm việc này.",
            "Nhấn nút 'Ghép chuyến' trên Bảng thao tác bên phải để điều phối yêu cầu đang chờ trong hàng đợi.",
        )
        return

    with st.container(border=True):
        head = st.columns([1, 1, 2, 1, 1.5])
        for col, title in zip(head, ["Mã chuyến", "Yêu cầu", "Tài xế", "ETA (phút)", "Trạng thái"]):
            col.markdown(f"**{title}**")

        st.divider()

        for t in reversed(trips):
            row = st.columns([1, 1, 2, 1, 1.5], vertical_alignment="center")
            row[0].write(f"**{t.id}**")
            row[1].write(t.request_id)
            driver_obj = drivers.get(t.driver_id)
            row[2].write(f"{t.driver_id} – {driver_obj.name}" if driver_obj else t.driver_id)
            row[3].write(f"{t.eta:g}")
            row[4].markdown(get_status_badge_html(t.status), unsafe_allow_html=True)


def render_demo_stepper() -> None:
    """Thanh hướng dẫn kịch bản trình diễn từng bước (Demo Walkthrough)."""
    # Khung giao diện sơ khởi cho demo stepper (sẽ hoàn thiện ở Bước 5)
    st.info("Chế độ trình diễn đang bật. Các bước demo sẽ hiển thị tại đây.")

