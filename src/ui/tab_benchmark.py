"""TV5 - Tab "Đối chuẩn thuật toán": so sánh A1 và A2 trên cùng đồ thị và tài xế rảnh.

Tab chỉ GỌI các chiến lược của TV2 và trình bày số liệu; không chứa thuật toán.
"""
from __future__ import annotations

import os
import platform
import statistics

import pandas as pd
import streamlit as st

from . import session as S
from .constants import FREE

K_BENCH = "benchmark_result"


def _run(pickups: list[str], repeats: int) -> dict:
    d = S.dispatcher()
    graph = d.graph
    free = {x.id: x.node for x in d.drivers_snapshot().values() if x.status == FREE}
    rows = []
    for pickup in pickups:
        for name, strategy in S.strategies().items():
            times, res = [], None
            for _ in range(repeats):
                res = strategy.find_driver(graph, pickup, free)
                times.append(res.runtime_ms)
            rows.append({"Điểm đón": pickup, "Thuật toán": name, "Tài xế": res.driver_id,
                         "ETA (phút)": res.eta, "Số đỉnh đã thăm": res.visited_count,
                         "Runtime TB (ms)": statistics.fmean(times)})
    return {"rows": rows, "free": len(free), "repeats": repeats}


def _agreement(df: pd.DataFrame) -> pd.DataFrame:
    out = []
    for pickup, grp in df.groupby("Điểm đón", sort=False):
        drivers, etas = set(grp["Tài xế"]), grp["ETA (phút)"].tolist()
        same_eta = all((e is None) == (etas[0] is None) and
                       (e is None or abs(e - etas[0]) < 1e-6) for e in etas)
        out.append({"Điểm đón": pickup, "Cùng tài xế": len(drivers) == 1,
                    "Cùng ETA": same_eta, "Khớp": len(drivers) == 1 and same_eta})
    return pd.DataFrame(out)


def render() -> None:
    d = S.dispatcher()
    nodes = d.graph.nodes()
    free = sum(1 for x in d.drivers_snapshot().values() if x.status == FREE)
    st.caption(f"Chạy mọi chiến lược trên cùng đồ thị ({len(nodes)} đỉnh) với {free} tài xế đang rảnh.")

    c1, c2 = st.columns([3, 1])
    labels = S.node_labels()
    pickups = [S.item_id(x) for x in c1.multiselect(
        "Điểm đón cần đo", labels, default=labels, key="bench_pickups")]
    repeats = c2.number_input("Số lần lặp", 1, 500, 20, key="bench_repeats")
    if st.button("▶️ Chạy đối chuẩn", key="btn_bench", type="primary",
                 disabled=not pickups or free == 0):
        try:
            st.session_state[K_BENCH] = _run(pickups, int(repeats))
        except Exception as exc:
            st.error(f"Không chạy được đối chuẩn: {exc}")
    if free == 0:
        st.warning("Không có tài xế rảnh để đo. Hãy hoàn thành chuyến hoặc thêm tài xế.")

    result = st.session_state.get(K_BENCH)
    if not result:
        return
    df = pd.DataFrame(result["rows"])
    st.subheader("Kết quả chi tiết")
    st.dataframe(df, hide_index=True, width="stretch")

    agree = _agreement(df)
    if agree["Khớp"].all():
        st.success("A1 và A2 cho cùng tài xế và ETA trên mọi điểm đón đã đo.")
    else:
        st.error("Có điểm đón mà các thuật toán cho kết quả khác nhau:")
        st.dataframe(agree[~agree["Khớp"]], hide_index=True)

    st.subheader("Tổng hợp theo thuật toán")
    summary = df.groupby("Thuật toán")[["Số đỉnh đã thăm", "Runtime TB (ms)"]].mean()
    st.dataframe(summary, width="stretch")
    ca, cb = st.columns(2)
    ca.markdown("**Số đỉnh đã thăm (trung bình)**")
    ca.bar_chart(summary["Số đỉnh đã thăm"])
    cb.markdown("**Runtime trung bình (ms)**")
    cb.bar_chart(summary["Runtime TB (ms)"])

    st.caption(f"Môi trường đo: {platform.platform()} · Python {platform.python_version()} · "
               f"{os.cpu_count()} CPU logic · {result['repeats']} lần lặp/điểm đón.")
