"""TV5 - Tab "Điều phối chuyến": yêu cầu, hàng đợi FIFO, điều phối, Undo/Redo, quản lý chuyến."""
from __future__ import annotations

import html
import math

import pandas as pd
import streamlit as st

from . import session as S
from .components import get_status_badge_html, page_header, render_empty_state, render_route_breadcrumb
from .constants import ASSIGNED, COMPLETED, FREE, status_label

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



def _on_reset_queue_filter() -> None:
    st.session_state["flt_queue_search"] = ""


def _filter_queue(queue: list) -> list:
    search = st.session_state.get("flt_queue_search", "").strip().lower()
    if not search:
        return list(queue)
    filtered = []
    for r in queue:
        p_label = S.node_label(r.pickup_node).lower()
        d_label = S.node_label(r.dropoff_node).lower()
        if (
            search in p_label
            or search in d_label
            or search in r.id.lower()
            or search in r.pickup_node.lower()
            or search in r.dropoff_node.lower()
        ):
            filtered.append(r)
    return filtered


def _on_reset_trips_filter(slider_max: float) -> None:
    st.session_state["flt_trips_status"] = []
    st.session_state["flt_trips_driver"] = []
    st.session_state["flt_trips_search"] = ""
    st.session_state["flt_trips_locations"] = []
    st.session_state["flt_trips_eta"] = (0.0, slider_max)
    st.session_state["flt_trips_sort"] = "Mới nhất trước"
    st.session_state["flt_trips_page"] = 1


def _filter_and_sort_trips(trips: list, all_requests: dict) -> list:
    status_sel = st.session_state.get("flt_trips_status", [])
    driver_sel = st.session_state.get("flt_trips_driver", [])
    search = st.session_state.get("flt_trips_search", "").strip().lower()
    loc_sel = st.session_state.get("flt_trips_locations", [])
    eta_range = st.session_state.get("flt_trips_eta")
    sort_order = st.session_state.get("flt_trips_sort", "Mới nhất trước")

    filtered = []
    for t in trips:
        if status_sel and t.status not in status_sel:
            continue
        if driver_sel and t.driver_id not in driver_sel:
            continue
        if search:
            if search not in t.id.lower() and search not in t.request_id.lower():
                continue
        if loc_sel:
            req = all_requests.get(t.request_id)
            if not req or (req.pickup_node not in loc_sel and req.dropoff_node not in loc_sel):
                continue
        if eta_range and isinstance(eta_range, (tuple, list)) and len(eta_range) == 2:
            min_eta, max_eta = eta_range
            if not (min_eta <= t.eta <= max_eta):
                continue
        filtered.append(t)

    if sort_order == "Cũ nhất trước":
        return list(filtered)
    return list(reversed(filtered))


def render() -> None:
    d = S.dispatcher()
    labels = S.node_labels()
    queue = d.queue_snapshot()
    drivers = d.drivers_snapshot()
    trips = d.trips_snapshot()
    free_count = sum(1 for x in drivers.values() if x.status == FREE)
    active_trips_count = sum(1 for t in trips if t.status == ASSIGNED)
    available_strats = S.strategies()
    current_strat = st.session_state.get("strategy_name") or (next(iter(available_strats)) if available_strats else "A1")

    page_header(
        icon="🚕",
        title="Điều phối chuyến",
        subtitle="Nhận yêu cầu, ghép tài xế tối ưu và hoàn tác thao tác",
        chips=[
            ("Hàng đợi", f"{len(queue)}"),
            ("Xe rảnh", f"{free_count}"),
            ("Chuyến đang chạy", f"{active_trips_count}"),
            ("Chiến lược", f"{current_strat}"),
        ],
    )

    with st.expander("🚀 Bắt đầu nhanh (3 bước trải nghiệm luồng nghiệp vụ)", expanded=False):
        st.markdown(
            """
            <div class="quick-start-box">
                <div style="margin-bottom: 0.6rem; line-height: 1.65;">
                    <span class="qs-step">1</span><b>Đặt xe mới:</b> Mở bảng thao tác bên phải → chọn điểm đón & trả khách tại mục <i>"(1) Đặt xe"</i> → nhấn <b>"Gửi yêu cầu"</b>.<br>
                    <span class="qs-step">2</span><b>Ghép chuyến tối ưu:</b> Tại mục <i>"(3) Điều phối"</i> chọn thuật toán <b>A1</b> hoặc <b>A2</b> → nhấn <b>"Ghép chuyến"</b>.<br>
                    <span class="qs-step">3</span><b>Hoàn tác & Hoàn thành:</b> Nhấn <b>"Undo"</b> để hủy gán chuyến; hoặc nhấn <b>"Hoàn thành chuyến"</b> trong danh sách đang chạy để kết thúc cuốc và giải phóng tài xế.
                </div>
                <div style="font-size: 0.82rem; color: #475569; border-top: 1px dashed #CBD5E1; padding-top: 0.45rem; margin-top: 0.45rem;">
                    <b>Ý nghĩa màu sắc trên bản đồ:</b> 🟢 Viền xanh lá = Xe rảnh &nbsp;|&nbsp; 🔴 Viền đỏ = Xe bận &nbsp;|&nbsp; 🟠 Viền cam = Điểm đón đang chờ &nbsp;|&nbsp; ── Xanh lá = Đón khách &nbsp;|&nbsp; ╌╌ Cam nét đứt = Chở khách
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Khung 1: Hàng đợi yêu cầu FIFO
    st.subheader(f"Hàng đợi yêu cầu FIFO ({len(queue)})")
    with st.container(border=True):
        with st.expander("🔍 Bộ lọc", expanded=True):
            c_q1, c_q2 = st.columns([4, 1], vertical_alignment="bottom")
            with c_q1:
                st.text_input(
                    "Tìm theo địa danh",
                    key="flt_queue_search",
                    placeholder="Nhập tên điểm đón, điểm trả hoặc mã yêu cầu...",
                )
            with c_q2:
                st.button(
                    "Xóa bộ lọc",
                    key="flt_queue_reset",
                    on_click=_on_reset_queue_filter,
                    width="stretch",
                )

        filtered_queue = _filter_queue(queue)
        st.caption(f"Hiển thị {len(filtered_queue)}/{len(queue)} bản ghi")

        if not queue:
            render_empty_state(
                "📭",
                "Hàng đợi yêu cầu đang trống",
                "Hiện không có khách nào đang chờ điều phối xe.",
                "Sử dụng mục '(1) Đặt xe' trên Bảng thao tác bên phải rồi nhấn 'Gửi yêu cầu'.",
            )
        elif not filtered_queue:
            render_empty_state(
                "🔍",
                "Không tìm thấy yêu cầu",
                "Không có yêu cầu nào trong hàng đợi khớp với tiêu chí tìm kiếm.",
                "Thử đổi từ khóa hoặc nhấn 'Xóa bộ lọc'.",
            )
        else:
            st.dataframe(_queue_table(filtered_queue), hide_index=True, width="stretch", height=150)
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

    max_trip_eta = max((float(t.eta) for t in trips), default=10.0)
    slider_max = float(max(10.0, math.ceil(max_trip_eta)))

    with st.expander("🔍 Bộ lọc", expanded=True):
        r1_c1, r1_c2, r1_c3, r1_c4 = st.columns(4)
        with r1_c1:
            st.multiselect(
                "Trạng thái",
                options=[ASSIGNED, COMPLETED],
                format_func=status_label,
                key="flt_trips_status",
            )
        with r1_c2:
            st.multiselect(
                "Tài xế",
                options=sorted(drivers.keys()),
                format_func=lambda did: f"{did} – {drivers[did].name}" if did in drivers else did,
                key="flt_trips_driver",
            )
        with r1_c3:
            st.text_input(
                "Tìm mã chuyến / yêu cầu",
                key="flt_trips_search",
                placeholder="VD: T1, R2...",
            )
        with r1_c4:
            st.multiselect(
                "Điểm đón / Điểm trả",
                options=d.graph.nodes(),
                format_func=S.node_label,
                key="flt_trips_locations",
            )

        r2_c1, r2_c2, r2_c3 = st.columns([2.5, 1.5, 1], vertical_alignment="bottom")
        with r2_c1:
            if "flt_trips_eta" not in st.session_state:
                st.session_state["flt_trips_eta"] = (0.0, slider_max)
            st.slider(
                "Khoảng ETA (phút)",
                min_value=0.0,
                max_value=slider_max,
                step=0.5,
                key="flt_trips_eta",
            )
        with r2_c2:
            st.selectbox(
                "Sắp xếp",
                options=["Mới nhất trước", "Cũ nhất trước"],
                index=0,
                key="flt_trips_sort",
            )
        with r2_c3:
            st.button(
                "Xóa bộ lọc",
                key="flt_trips_reset",
                on_click=_on_reset_trips_filter,
                args=(slider_max,),
                width="stretch",
            )

    sorted_trips = _filter_and_sort_trips(trips, d.all_requests)

    page_size = st.session_state.get("flt_trips_page_size", 10)
    total_items = len(sorted_trips)
    total_pages = max(1, math.ceil(total_items / page_size)) if total_items > 0 else 1
    cur_page = min(max(1, st.session_state.get("flt_trips_page", 1)), total_pages)
    start_idx = (cur_page - 1) * page_size
    end_idx = min(start_idx + page_size, total_items)
    paged_trips = sorted_trips[start_idx:end_idx]

    st.caption(f"Hiển thị {total_items}/{len(trips)} bản ghi (Trang {cur_page}/{total_pages})")

    if not trips:
        render_empty_state(
            "🚕",
            "Chưa có chuyến xe nào",
            "Hệ thống chưa tạo chuyến xe nào trong phiên làm việc này.",
            "Nhấn nút 'Ghép chuyến' trên Bảng thao tác bên phải để điều phối yêu cầu đang chờ trong hàng đợi.",
        )
    elif not sorted_trips:
        render_empty_state(
            "🔍",
            "Không tìm thấy chuyến xe",
            "Không có chuyến xe nào khớp với các tiêu chí bộ lọc đã chọn.",
            "Thử nới lỏng khoảng ETA hoặc nhấn 'Xóa bộ lọc' để xem toàn bộ danh sách.",
        )
    else:
        with st.container(border=True):
            head = st.columns([1, 1.8, 2, 1, 1.5])
            for col, title in zip(head, ["Mã chuyến", "Yêu cầu", "Tài xế", "ETA (phút)", "Trạng thái"]):
                col.markdown(f"**{title}**")

            st.divider()

            for t in paged_trips:
                row = st.columns([1, 1.8, 2, 1, 1.5], vertical_alignment="center")
                row[0].write(f"**{t.id}**")
                req = d.all_requests.get(t.request_id)
                if req:
                    req_text = f"{t.request_id} ({S.node_label(req.pickup_node)} → {S.node_label(req.dropoff_node)})"
                else:
                    req_text = t.request_id
                row[1].write(req_text)
                driver_obj = drivers.get(t.driver_id)
                row[2].write(f"{t.driver_id} – {driver_obj.name}" if driver_obj else t.driver_id)
                row[3].write(f"{t.eta:g}")
                row[4].markdown(get_status_badge_html(t.status), unsafe_allow_html=True)

        c_ps, c_pg, _ = st.columns([1.5, 1.5, 5])
        with c_ps:
            st.selectbox("Số dòng / trang", options=[10, 25, 50], key="flt_trips_page_size")
        with c_pg:
            st.number_input("Trang", min_value=1, max_value=total_pages, key="flt_trips_page", step=1)


def render_demo_stepper() -> None:
    """Thanh hướng dẫn kịch bản trình diễn từng bước (Demo Walkthrough)."""
    # Khung giao diện sơ khởi cho demo stepper (sẽ hoàn thiện ở Bước 5)
    st.info("Chế độ trình diễn đang bật. Các bước demo sẽ hiển thị tại đây.")

