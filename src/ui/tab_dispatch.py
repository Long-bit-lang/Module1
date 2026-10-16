"""TV5 - Tab "Điều phối chuyến": yêu cầu, hàng đợi, điều phối, Undo/Redo, chuyến đi."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from . import session as S
from .constants import ASSIGNED, FREE, status_label


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
        S.flash("warning", "Không điều phối được: không có tài xế rảnh hoặc không có đường đi "
                           "tới điểm đón. Yêu cầu vẫn nằm ở đầu hàng đợi.")
        return
    st.session_state[S.K_LAST] = {"trip": trip, "strategy": name, "result": strategy.last_result}
    S.flash("success", f"Đã tạo chuyến {trip.id} cho tài xế {trip.driver_id} (ETA {trip.eta:g} phút).")


def _on_undo() -> None:
    ok, done = S.perform(lambda: S.dispatcher().undo())
    if ok:
        st.session_state[S.K_LAST] = None
        S.flash("success" if done else "warning",
                "Đã hoàn tác lần điều phối gần nhất." if done else "Không có gì để hoàn tác.")


def _on_redo() -> None:
    ok, done = S.perform(lambda: S.dispatcher().redo())
    if ok:
        S.flash("success" if done else "warning",
                "Đã làm lại lần điều phối vừa hoàn tác." if done else "Không có gì để làm lại.")


def _on_complete(trip_id: str) -> None:
    ok, done = S.perform(lambda: S.dispatcher().complete_trip(trip_id))
    if ok:
        S.flash("success" if done else "warning",
                f"Chuyến {trip_id} đã hoàn thành; tài xế được giải phóng." if done
                else f"Không thể hoàn thành chuyến {trip_id}.")


# ------------------------------------------------------------------------- render
def _queue_table(queue) -> pd.DataFrame:
    rows = [{"Thứ tự": i + 1, "ID": r.id, "Điểm đón": S.node_label(r.pickup_node),
             "Điểm trả": S.node_label(r.dropoff_node), "Trạng thái": status_label(r.status)}
            for i, r in enumerate(queue)]
    return pd.DataFrame(rows, columns=["Thứ tự", "ID", "Điểm đón", "Điểm trả", "Trạng thái"])


def _render_last_result() -> None:
    last = st.session_state.get(S.K_LAST)
    if not last or last["result"] is None:
        return
    res, trip = last["result"], last["trip"]
    st.markdown(f"**Kết quả điều phối {trip.id}** · {last['strategy']}")
    c = st.columns(4)
    c[0].metric("Tài xế", res.driver_id)
    c[1].metric("ETA (phút)", f"{res.eta:g}")
    c[2].metric("Số đỉnh đã thăm", res.visited_count)
    c[3].metric("Thời gian chạy (ms)", f"{res.runtime_ms:.3f}")
    if res.path:
        st.caption("Lộ trình đón: " + " → ".join(S.node_label(n) for n in res.path))


def render() -> None:
    d = S.dispatcher()
    labels = S.node_labels()
    queue, drivers = d.queue_snapshot(), d.drivers_snapshot()
    free_count = sum(1 for x in drivers.values() if x.status == FREE)

    left, right = st.columns([2, 3])
    with left:
        st.subheader("Tạo yêu cầu đặt xe")
        with st.container(border=True):
            st.selectbox("Điểm đón", labels, key="req_pickup")
            st.selectbox("Điểm trả", labels, key="req_dropoff", index=min(1, len(labels) - 1))
            st.button("Gửi yêu cầu", on_click=_on_submit, key="btn_submit", type="primary")
    with right:
        st.subheader(f"Hàng đợi FIFO ({len(queue)})")
        if queue:
            st.dataframe(_queue_table(queue), hide_index=True, width="stretch")
        else:
            st.info("Hàng đợi trống.")

    st.subheader("Điều phối")
    c1, c2, c3, c4 = st.columns([3, 2, 1, 1])
    c1.selectbox("Thuật toán", list(S.strategies()), key="strategy_name")
    c2.button(f"🚕 Điều phối yêu cầu đầu hàng ({free_count} tài xế rảnh)",
              on_click=_on_dispatch, key="btn_dispatch", type="primary",
              disabled=not queue, width="stretch")
    c3.button("↩️ Undo", on_click=_on_undo, key="btn_undo", disabled=not d.can_undo(),
              width="stretch")
    c4.button("↪️ Redo", on_click=_on_redo, key="btn_redo", disabled=not d.can_redo(),
              width="stretch")
    _render_last_result()

    st.subheader("Danh sách chuyến")
    trips = d.trips_snapshot()
    if not trips:
        st.info("Chưa có chuyến nào.")
        return
    head = st.columns([1, 1, 1, 1, 2, 2])
    for col, title in zip(head, ["Chuyến", "Yêu cầu", "Tài xế", "ETA", "Trạng thái", ""]):
        col.markdown(f"**{title}**")
    for t in reversed(trips):
        row = st.columns([1, 1, 1, 1, 2, 2])
        row[0].write(t.id)
        row[1].write(t.request_id)
        row[2].write(t.driver_id)
        row[3].write(f"{t.eta:g}")
        row[4].write(status_label(t.status))
        if t.status == ASSIGNED:
            row[5].button("Hoàn thành chuyến", key=f"btn_complete_{t.id}",
                          on_click=_on_complete, args=(t.id,))
