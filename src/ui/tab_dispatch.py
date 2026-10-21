"""TV5 - Tab "Điều phối chuyến": yêu cầu, hàng đợi FIFO, điều phối, quản lý chuyến."""
from __future__ import annotations

import html
import math

import pandas as pd
import streamlit as st

from . import session as S
from .components import get_status_badge_html, page_header, render_empty_state, render_route_breadcrumb
from .constants import ASSIGNED, CANCELLED, COMPLETED, FREE, status_label

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

    if not last.get("result") or not last.get("trip"):
        return

    # C1 & C2: Thẻ kết quả điều phối thành công nổi bật
    res = last.get("result")
    trip = last.get("trip")
    d = S.dispatcher()
    driver_name = d.drivers_snapshot().get(trip.driver_id)
    driver_str = f"{trip.driver_id} – {driver_name.name}" if driver_name else trip.driver_id
    status_tag = last.get("status_tag", "Đang chạy")

    badge_map = {
        "Chuyến đã hoàn thành": "badge-completed",
        "Chuyến đã hủy": "badge-cancelled",
        "Đang chạy": "badge-assigned",
    }
    badge_cls = badge_map.get(status_tag, "badge-default")
    status_badge_html = f'<span class="badge-status {badge_cls}">{html.escape(status_tag)}</span>'

    with st.container(key="dispatch_result_card"):
        c_title, c_hide = st.columns([5.5, 1], vertical_alignment="center")
        with c_title:
            strategy_str = html.escape(str(last.get("strategy", "")))
            st.markdown(
                f"""
                <div class="dispatch-result-header">
                    <span class="dispatch-result-title">🚕 Đã ghép chuyến {html.escape(trip.id)} ↔ {html.escape(trip.driver_id)}</span>
                    {status_badge_html}
                    <span class="dispatch-result-strategy">({strategy_str})</span>
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
    from .components import (
        AnimationTick,
        build_animation_ticks,
        render_animation_badge,
        render_animation_status_badge,
        render_graph_with_zoom,
    )
    from .constants import (
        ANIM_STATUS_COMPLETED,
        ANIM_STATUS_PAUSED,
        ANIM_STATUS_PLAYING,
    )
    from .graph_view import build_dot

    st.subheader("Bản đồ điều phối")

    last = st.session_state.get(S.K_LAST)
    trips = d.trips_snapshot()

    # 1. Xây dựng danh sách chuyến có thể phát lại / xem lại lộ trình
    trip_options = []
    trip_map = {}

    if last and last.get("trip") and not last.get("failed"):
        last_trip = last.get("trip")
        lbl_last = f"Chuyến vừa ghép: {last_trip.id} (Xe {last_trip.driver_id} ↔ Khách {last_trip.request_id})"
        trip_options.append(lbl_last)
        trip_map[lbl_last] = ("last", last_trip.id)

    for t in reversed(trips):
        last_t = last.get("trip") if (last and not last.get("failed")) else None
        if last_t and t.id == last_t.id:
            continue
        lbl_t = f"Lịch sử: Chuyến {t.id} (Xe {t.driver_id} ↔ Khách {t.request_id})"
        trip_options.append(lbl_t)
        trip_map[lbl_t] = ("history", t.id)

    # 4. Xác định chuyến được chọn để phát lại / xem lộ trình
    selected_type = None
    target_id = None
    if trip_options:
        if len(trip_options) > 1:
            sel_trip_key = st.selectbox(
                "Chọn chuyến xe để xem lại lộ trình:",
                options=trip_options,
                index=0,
                key="anim_trip_select",
                help="Chọn chuyến vừa ghép hoặc chuyến trong lịch sử để xem lại lộ trình hai chặng",
            )
            selected_type, target_id = trip_map.get(sel_trip_key, (None, None))
        else:
            selected_type, target_id = trip_map[trip_options[0]]

    # 5. Reset bước nếu đổi chuyến phát lại
    if st.session_state.get("_anim_target_id") != target_id:
        st.session_state["_anim_target_id"] = target_id
        st.session_state["anim_step"] = 0
        st.session_state["anim_playing"] = False
        st.session_state["anim_just_played"] = False
        st.session_state["_anim_timeline_cache_key"] = None

    # 6. Tự động phát sau khi ghép (anim_auto)
    if selected_type == "last" and st.session_state.get("anim_auto", False):
        if st.session_state.get("_last_autoplay_trip_id") != target_id:
            st.session_state["_last_autoplay_trip_id"] = target_id
            st.session_state["anim_step"] = 0
            st.session_state["anim_playing"] = True
            st.session_state["anim_just_played"] = True

    # 7. Xây dựng lộ trình dùng chung cho MỌI chuyến qua dispatcher.trip_route
    pickup_path: list[str] = []
    ride_path: list[str] = []
    pickup_eta: float = 0.0
    ride_eta: float | None = None
    pickup_known: bool = True
    route_note: str = "Chưa có lộ trình để hiển thị."
    route_info: dict | None = None

    selected_trip = None
    if target_id:
        selected_trip = next((t for t in trips if t.id == target_id), None)
        if selected_trip is None and last and last.get("trip") and last["trip"].id == target_id:
            selected_trip = last["trip"]

    is_cancelled = False
    if selected_trip and selected_trip.status == CANCELLED:
        is_cancelled = True
    elif last and last.get("trip") and last["trip"].id == target_id and last.get("status_tag") == "Chuyến đã hủy":
        is_cancelled = True

    if target_id:
        if hasattr(d, "trip_route"):
            route_info = d.trip_route(target_id)
        if route_info is not None:
            pickup_path = list(route_info.get("pickup_path") or [])
            ride_path = list(route_info.get("ride_path") or [])
            pickup_eta = float(route_info.get("pickup_eta", 0.0))
            ride_eta = route_info.get("ride_eta")
            pickup_known = bool(route_info.get("pickup_known", True))

            notes = []
            if pickup_path:
                notes.append(f"Xanh lá: xe đến điểm đón ({pickup_eta:g} phút)")
            if ride_path:
                if ride_eta is not None:
                    notes.append(f"Cam nét đứt: chở khách đến điểm trả ({ride_eta:g} phút)")
                else:
                    notes.append("Cam nét đứt: chở khách đến điểm trả")
            route_note = ". ".join(notes) + ("." if notes else "")
        else:
            route_note = f"Không tìm thấy dữ liệu lộ trình cho chuyến {target_id}."
    elif queue:
        free = {x.id: x.node for x in drivers.values() if x.status == FREE}
        name = st.session_state.get("strategy_name") or next(iter(S.strategies()))
        if free:
            preview_res = S.strategies()[name].find_driver(d.graph, queue[0].pickup_node, free)
            if preview_res.path:
                route_note = (
                    f"Xem trước (chưa ghép): yêu cầu {queue[0].id} sẽ do "
                    f"{preview_res.driver_id} nhận, ETA {preview_res.eta:g} phút."
                )

    routes: list[tuple[list[str], str, str]] = []
    if pickup_path:
        routes.append((pickup_path, "#16a34a", "solid"))
    if ride_path:
        routes.append((ride_path, "#ea580c", "dashed"))
    driver_start_node = pickup_path[0] if pickup_path else None

    speed_label = st.session_state.get("anim_speed", "2x")
    speed_mult = {"1x": 1.0, "2x": 2.0, "4x": 4.0}.get(speed_label, 2.0)
    avg_render_time = st.session_state.get("anim_avg_render_time", 0.0)

    # Tiền kết xuất và lưu cache chuỗi DOT cho từng tick
    if is_cancelled:
        timeline = []
    else:
        route_signature = f"{target_id}_p{len(pickup_path)}_r{len(ride_path)}_{','.join(pickup_path)}_{','.join(ride_path)}_{speed_label}"
        drivers_sig = f"{len(drivers)}_{sum(1 for drv in drivers.values() if drv.status == FREE)}"
        timeline_cache_key = f"{route_signature}_{drivers_sig}"

        if (
            st.session_state.get("_anim_timeline_cache_key") != timeline_cache_key
            or "_anim_cached_timeline" not in st.session_state
        ):
            import time
            _t0 = time.perf_counter()
            timeline = build_animation_ticks(
                pickup_path=pickup_path,
                ride_path=ride_path,
                graph_edges=d.graph.edges(),
                node_label_fn=S.node_label,
                speed_mult=speed_mult,
                drivers=drivers,
                queue=queue,
                nodes=d.graph.nodes(),
                precompute_dots=True,
                avg_render_time=avg_render_time,
            )
            _render_cost = time.perf_counter() - _t0
            st.session_state["_anim_cached_timeline"] = timeline
            st.session_state["_anim_timeline_cache_key"] = timeline_cache_key
            st.session_state["_anim_last_render_cost"] = _render_cost

            # Lưu thời gian render trung bình đo được vào session_state (YÊU CẦU 5)
            measured_render = getattr(timeline, "avg_render_time", 0.0) or getattr(timeline, "_avg_render_time", 0.0)
            if measured_render > 0:
                st.session_state["anim_avg_render_time"] = measured_render
                st.session_state["anim_render_time"] = measured_render
        else:
            timeline = st.session_state["_anim_cached_timeline"]

    total_ticks = timeline[-1].total_ticks if timeline else 0
    total_frames = len(timeline)
    max_step = max(0, total_frames - 1)

    # 8. Tính toán delay động cho run_every của st.fragment
    is_playing = st.session_state.get("anim_playing", False)
    cur_step = st.session_state.get("anim_step", 0)

    if is_playing and total_frames > 0:
        run_every_delay = timeline[min(cur_step, total_frames - 1)].tick_delay
    else:
        run_every_delay = None

    # 9. Callback functions cho các nút điều khiển
    def on_play() -> None:
        cur = st.session_state.get("anim_step", 0)
        if cur >= max_step:
            st.session_state["anim_step"] = 0
            st.session_state["_current_anim_step"] = 0
        st.session_state["anim_playing"] = True
        st.session_state["anim_just_played"] = True
        st.rerun()

    def on_pause() -> None:
        st.session_state["anim_playing"] = False
        st.session_state["anim_just_played"] = False
        st.session_state["_current_anim_step"] = st.session_state.get("anim_step", 0)
        st.rerun()

    def on_restart() -> None:
        st.session_state["anim_step"] = 0
        st.session_state["_current_anim_step"] = 0
        st.session_state["anim_playing"] = True
        st.session_state["anim_just_played"] = True
        st.rerun()

    def on_skip() -> None:
        st.session_state["anim_step"] = max_step
        st.session_state["_current_anim_step"] = max_step
        st.session_state["anim_playing"] = False
        st.session_state["anim_just_played"] = False
        st.rerun()

    def on_step_change() -> None:
        st.session_state["anim_playing"] = False
        st.session_state["anim_just_played"] = False
        st.session_state["_current_anim_step"] = st.session_state.get("anim_step", 0)
        st.rerun()

    # 10. Fragment hiển thị bản đồ và bộ điều khiển
    @st.fragment(run_every=run_every_delay)
    def _map_animation_fragment() -> None:
        # Xử lý tick đồng hồ chuyển bước
        if st.session_state.get("anim_playing", False):
            if st.session_state.get("anim_just_played", False):
                # Vừa bấm Phát hoặc Phát lại: hiển thị ngay khung hình hiện tại
                st.session_state["anim_just_played"] = False
                st.session_state["_current_anim_step"] = st.session_state.get("anim_step", 0)
            else:
                last_s = st.session_state.get("_current_anim_step", st.session_state.get("anim_step", 0))
                client_s = st.session_state.get("anim_step", last_s)
                if abs(client_s - last_s) > 1:
                    last_s = client_s

                if last_s < max_step:
                    next_s = last_s + 1
                    st.session_state["anim_step"] = next_s
                    st.session_state["_current_anim_step"] = next_s
                else:
                    # Khi đến cuối lộ trình: tự động dừng theo đúng yêu cầu
                    st.session_state["anim_playing"] = False
                    st.session_state["anim_step"] = max_step
                    st.session_state["_current_anim_step"] = max_step
                    st.rerun()

        # Cập nhật anim_step TRƯỚC KHI tạo widget slider
        if "anim_step" not in st.session_state:
            st.session_state["anim_step"] = 0
        step_idx = min(max(0, st.session_state.get("anim_step", 0)), max_step)
        st.session_state["anim_step"] = step_idx

        playing_now = st.session_state.get("anim_playing", False)
        if not playing_now and max_step > 0 and step_idx >= max_step:
            anim_status = ANIM_STATUS_COMPLETED
        elif playing_now:
            anim_status = ANIM_STATUS_PLAYING
        else:
            anim_status = ANIM_STATUS_PAUSED

        current_tick_info = timeline[step_idx] if (timeline and step_idx < len(timeline)) else None

        # Cập nhật giá trị tiến độ tổng cho anim_progress
        if current_tick_info:
            st.session_state["anim_progress"] = current_tick_info.progress_pct

        # Bảng điều khiển animation (chỉ hiển thị khi có chuyến hợp lệ)
        if total_frames > 0:
            with st.container(key="anim_controls_box", border=True):
                c1, c2, c3, c_skip, c4, c5 = st.columns([1.1, 1.2, 1.2, 1.3, 1.1, 2.3], vertical_alignment="center")
                with c1:
                    st.button(
                        "▶ Phát",
                        key="anim_play",
                        on_click=on_play,
                        disabled=(max_step <= 0 or playing_now),
                        type="primary" if not playing_now else "secondary",
                        width="stretch",
                        help="Phát lại từng tick lộ trình",
                    )
                with c2:
                    st.button(
                        "⏸ Tạm dừng",
                        key="anim_pause",
                        on_click=on_pause,
                        disabled=(not playing_now),
                        width="stretch",
                        help="Tạm dừng phát lại",
                    )
                with c3:
                    st.button(
                        "⏮ Phát lại",
                        key="anim_restart",
                        on_click=on_restart,
                        disabled=(max_step <= 0),
                        width="stretch",
                        help="Quay lại tick 0 xuất phát ban đầu và phát lại",
                    )
                with c_skip:
                    st.button(
                        "⏭ Đến cuối",
                        key="anim_skip",
                        on_click=on_skip,
                        disabled=(max_step <= 0 or step_idx >= max_step),
                        width="stretch",
                        help="Nhảy thẳng tới tick cuối cùng và hoàn tất lộ trình",
                    )
                with c4:
                    st.selectbox(
                        "Tốc độ",
                        options=["1x", "2x", "4x"],
                        index=1,
                        key="anim_speed",
                        help="Tốc độ mô phỏng lộ trình (1x / 2x / 4x)",
                    )
                with c5:
                    st.toggle(
                        "Tự động phát sau khi ghép",
                        key="anim_auto",
                        help="Tự động phát lộ trình ngay sau khi điều phối chuyến thành công",
                    )

                slider_max = max(1, max_step)
                st.slider(
                    "Tua tick lộ trình",
                    min_value=0,
                    max_value=slider_max,
                    disabled=(max_step <= 0),
                    key="anim_step",
                    on_change=(None if playing_now else on_step_change),
                    help="Kéo để tua đến tick bất kỳ trong lộ trình",
                )

                if current_tick_info:
                    # Thanh tiến độ tổng anim_progress
                    pct_val = min(1.0, max(0.0, float(current_tick_info.progress_pct)))
                    edge_lbl = current_tick_info.edge_label or "Lộ trình"
                    edge_p = round(current_tick_info.edge_pct)
                    progress_msg = f"Tiến độ toàn lộ trình: {round(pct_val * 100)}% • Đang đi: {edge_lbl} ({edge_p}%)"
                    try:
                        st.progress(pct_val, text=progress_msg, key="anim_progress")
                    except TypeError:
                        st.progress(pct_val, text=progress_msg)

                    render_animation_badge(current_tick_info, status=anim_status)

                # Dòng caption nhỏ tổng thời gian phát (YÊU CẦU 5)
                schedule_obj = getattr(timeline, "schedule", None) or getattr(timeline, "_schedule", None)
                if schedule_obj:
                    est_sec = schedule_obj.total_seconds
                else:
                    est_sec = max_step * (timeline[0].tick_delay if timeline else 0.1)
                st.caption(f"⏱️ Tổng thời gian phát ≈ {est_sec:.1f} giây")

        # Lấy DOT đồ thị đã được tiền kết xuất trong cache (YÊU CẦU 3.a)
        if total_frames > 0 and current_tick_info and current_tick_info.dot_string:
            dot_dispatch = current_tick_info.dot_string
        elif total_frames > 0 and current_tick_info:
            dot_dispatch = build_dot(
                edges=d.graph.edges(),
                drivers=drivers,
                queue=queue,
                label=S.node_label,
                nodes=d.graph.nodes(),
                routes=routes,
                layout="neato",
                highlight_node=current_tick_info.node,
                custom_edges=current_tick_info.custom_edges,
                driver_start_node=driver_start_node,
            )
        else:
            # Chế độ bản đồ tĩnh (xem lộ trình chuyến đã hủy hoặc chưa có chuyến/xem trước)
            static_routes = list(routes)
            if not static_routes and queue:
                free = {x.id: x.node for x in drivers.values() if x.status == FREE}
                name = st.session_state.get("strategy_name") or next(iter(S.strategies()))
                if free:
                    res_prev = S.strategies()[name].find_driver(d.graph, queue[0].pickup_node, free)
                    if res_prev.path:
                        static_routes.append((res_prev.path, "#2563eb", "dashed"))
            dot_dispatch = build_dot(
                edges=d.graph.edges(),
                drivers=drivers,
                queue=queue,
                label=S.node_label,
                nodes=d.graph.nodes(),
                routes=static_routes,
                layout="neato",
                driver_start_node=driver_start_node,
            )

        render_graph_with_zoom(dot_dispatch, key_prefix="map_dispatch", height=500)
        st.caption(route_note + "  Viền cam: điểm đón đang chờ.")
        if target_id and route_info is None:
            st.info(f"Không tìm thấy lộ trình cho chuyến {target_id}.")
        elif route_info is not None and not pickup_known:
            st.info("Chuyến này được tạo trước khi hệ thống lưu lộ trình đón nên chỉ hiển thị chặng chở khách.")

    _map_animation_fragment()



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
    cancelled_trips_count = sum(1 for t in trips if t.status == CANCELLED)
    available_strats = S.strategies()
    current_strat = st.session_state.get("strategy_name") or (next(iter(available_strats)) if available_strats else "A1")

    page_header(
        icon="🚕",
        title="Điều phối chuyến",
        subtitle="Nhận yêu cầu, ghép tài xế tối ưu và quản lý chuyến đi",
        chips=[
            ("Hàng đợi", f"{len(queue)}"),
            ("Xe rảnh", f"{free_count}"),
            ("Chuyến đang chạy", f"{active_trips_count}"),
            ("Đã hủy", f"{cancelled_trips_count}"),
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
                    <span class="qs-step">3</span><b>Hủy & Hoàn thành chuyến:</b> Nhấn <b>"Hủy chuyến"</b> để hủy chuyến đã ghép và giải phóng tài xế tại chỗ; hoặc nhấn <b>"Hoàn thành chuyến"</b> trong danh sách đang chạy để kết thúc cuốc khi khách tới nơi.
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
        st.caption("💡 *Đặt xe mới, hủy yêu cầu, hoặc nhấn Ghép chuyến trên **Bảng thao tác bên phải**.*")

    # Hiển thị nút giải phóng nghẽn hàng nếu nguyên nhân là no_route
    if getattr(d, "last_failure", None) == "no_route" and queue:
        st.warning(
            f"⚠️ **Yêu cầu đầu hàng ({queue[0].id}: {S.node_label(queue[0].pickup_node)} → {S.node_label(queue[0].dropoff_node)})** "
            "không có tài xế nào tiếp cận được do đường một chiều. Bạn có thể hủy yêu cầu này trên Bảng thao tác bên phải để tiếp tục xử lý các yêu cầu kế tiếp."
        )

    st.divider()

    # Khung 2: Thẻ Kết quả điều phối nổi bật (Hạng mục C)
    _render_last_result()

    # Khung 3: Danh sách các Chuyến xe (Lịch sử chỉ đọc - D3)
    st.subheader(f"Danh sách Chuyến xe ({len(trips)})")

    max_trip_eta = max((float(t.eta) for t in trips), default=10.0)
    slider_max = float(max(10.0, math.ceil(max_trip_eta)))

    with st.expander("🔍 Bộ lọc", expanded=True):
        r1_c1, r1_c2, r1_c3, r1_c4 = st.columns(4)
        with r1_c1:
            st.multiselect(
                "Trạng thái",
                options=[ASSIGNED, COMPLETED, CANCELLED],
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

    st.divider()

    # Khung 4: Bản đồ điều phối có lộ trình (xuống dưới cùng)
    _render_map(d, queue, drivers)


def render_demo_stepper() -> None:
    """Thanh hướng dẫn kịch bản trình diễn từng bước (Demo Walkthrough)."""
    # Khung giao diện sơ khởi cho demo stepper (sẽ hoàn thiện ở Bước 5)
    st.info("Chế độ trình diễn đang bật. Các bước demo sẽ hiển thị tại đây.")

