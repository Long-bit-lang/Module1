"""TV5 - Tab "Đối chuẩn thuật toán": so sánh A1 và A2 trên cùng đồ thị và tài xế rảnh."""
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
            rows.append(
                {
                    "Điểm đón": pickup,
                    "Tên địa danh": S.node_label(pickup),
                    "Thuật toán": name,
                    "Tài xế": res.driver_id,
                    "ETA (phút)": res.eta,
                    "Số đỉnh đã thăm": res.visited_count,
                    "Runtime TB (ms)": statistics.fmean(times),
                }
            )
    return {"rows": rows, "free": len(free), "repeats": repeats}


def _agreement(df: pd.DataFrame) -> pd.DataFrame:
    out = []
    for pickup, grp in df.groupby("Điểm đón", sort=False):
        drivers, etas = set(grp["Tài xế"]), grp["ETA (phút)"].tolist()
        same_eta = all((e is None) == (etas[0] is None) and (e is None or abs(e - etas[0]) < 1e-6) for e in etas)
        out.append(
            {
                "Điểm đón": pickup,
                "Cùng tài xế": len(drivers) == 1,
                "Cùng ETA": same_eta,
                "Khớp": len(drivers) == 1 and same_eta,
            }
        )
    return pd.DataFrame(out)


def render() -> None:
    d = S.dispatcher()
    free_drivers = [x for x in d.drivers_snapshot().values() if x.status == FREE]
    free = len(free_drivers)

    st.subheader("Đối chuẩn Thuật toán (A1 vs A2)")
    st.info(
        "**Mục tiêu đối chuẩn:** So sánh tính đúng đắn và hiệu năng giữa hai giải thuật tìm đường:\n"
        "- **A1 (Dijkstra từ từng tài xế rảnh):** Chạy thuật toán Dijkstra độc lập xuất phát từ vị trí mỗi tài xế rảnh đến điểm đón.\n"
        "- **A2 (Dijkstra đảo chiều từ điểm đón):** Đảo chiều các cung trên đồ thị và chạy một lượt Dijkstra từ điểm đón tìm tới các tài xế rảnh."
    )

    labels = S.node_labels()
    c1, c2, c3 = st.columns([4, 2, 2], vertical_alignment="bottom")
    with c1:
        pickups = [
            S.item_id(x)
            for x in st.multiselect(
                "Chọn các điểm đón cần khảo sát",
                labels,
                default=labels,
                key="bench_pickups",
                help="Chọn các đỉnh trên đồ thị để kiểm tra thuật toán ghép tài xế",
            )
        ]
    with c2:
        repeats = st.number_input(
            "Số lần lặp đo thời gian",
            min_value=1,
            max_value=500,
            value=20,
            step=5,
            key="bench_repeats",
            help="Số lần chạy lặp để lấy trung bình thời gian thực thi (ms)",
        )
    with c3:
        run_btn = st.button(
            "Chạy đối chuẩn",
            key="btn_bench",
            type="primary",
            disabled=not pickups or free == 0,
            use_container_width=True,
        )

    if free == 0:
        st.warning("Hiện không có tài xế nào đang rảnh để thử nghiệm. Hãy hoàn thành chuyến hoặc thêm tài xế mới.")

    if run_btn:
        try:
            with st.spinner("Đang chạy đối chuẩn thuật toán trên mạng lưới giao thông..."):
                st.session_state[K_BENCH] = _run(pickups, int(repeats))
        except Exception as exc:
            st.error(f"Không chạy được đối chuẩn: {exc}")

    result = st.session_state.get(K_BENCH)
    if not result:
        return

    df = pd.DataFrame(result["rows"])

    # 1. Kiểm tra tính khớp nhau của kết quả (Agreement)
    agree = _agreement(df)
    st.divider()
    if agree["Khớp"].all():
        st.success("✅ **Tuyệt đối chính xác:** A1 và A2 cho cùng tài xế và ETA trên mọi điểm đón đã đo.")
    else:
        st.error("⚠️ Có điểm đón mà các thuật toán cho kết quả khác nhau:")
        st.dataframe(agree[~agree["Khớp"]], hide_index=True)

    # 2. Tổng hợp chỉ số hiệu năng
    st.subheader("Bảng Tổng hợp Hiệu năng")
    summary = df.groupby("Thuật toán")[["Số đỉnh đã thăm", "Runtime TB (ms)"]].mean()
    st.dataframe(summary, width="stretch")

    # Thẻ KPI so sánh
    if len(summary) >= 2:
        names = list(summary.index)
        v1, v2 = summary.loc[names[0], "Số đỉnh đã thăm"], summary.loc[names[1], "Số đỉnh đã thăm"]
        t1, t2 = summary.loc[names[0], "Runtime TB (ms)"], summary.loc[names[1], "Runtime TB (ms)"]

        kp1, kp2 = st.columns(2)
        with kp1:
            diff_v = ((v2 - v1) / v1 * 100) if v1 else 0
            st.metric(
                label=f"Số đỉnh đã thăm trung bình ({names[1]} so với {names[0]})",
                value=f"{v2:.1f} đỉnh",
                delta=f"{diff_v:+.1f}% (ít đỉnh hơn là tối ưu hơn)",
                delta_color="inverse",
            )
        with kp2:
            diff_t = ((t2 - t1) / t1 * 100) if t1 else 0
            st.metric(
                label=f"Thời gian thực thi trung bình ({names[1]} so với {names[0]})",
                value=f"{t2:.3f} ms",
                delta=f"{diff_t:+.1f}% (nhanh hơn là tối ưu hơn)",
                delta_color="inverse",
            )

    # Biểu đồ so sánh
    ca, cb = st.columns(2)
    with ca:
        with st.container(border=True):
            st.markdown("**Số đỉnh đã thăm trung bình (Càng ít càng tối ưu)**")
            st.bar_chart(summary["Số đỉnh đã thăm"], color="#3b82f6")
    with cb:
        with st.container(border=True):
            st.markdown("**Thời gian chạy trung bình (ms) (Càng nhanh càng tối ưu)**")
            st.bar_chart(summary["Runtime TB (ms)"], color="#10b981")

    # 3. Bảng dữ liệu chi tiết
    st.subheader("Dữ liệu Chi tiết từng Điểm đón")
    display_df = df[
        ["Tên địa danh", "Thuật toán", "Tài xế", "ETA (phút)", "Số đỉnh đã thăm", "Runtime TB (ms)"]
    ]
    st.dataframe(display_df, hide_index=True, width="stretch", height=240)

    st.caption(
        f"Môi trường đo: {platform.platform()} · Python {platform.python_version()} · "
        f"{os.cpu_count()} CPU logic · {result['repeats']} lần lặp/điểm đón."
    )
