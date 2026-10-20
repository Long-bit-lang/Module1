"""TV5 - Tab "Đối chuẩn thuật toán": so sánh A1 và A2 trên cùng đồ thị và tài xế rảnh."""
from __future__ import annotations

import os
import platform
import random
import statistics

import pandas as pd
import streamlit as st

from core.road_graph import RoadGraph
from core.strategies import STRATEGIES
from . import session as S
from .components import page_header
from .constants import FREE

K_BENCH = "benchmark_result"
K_DOC_BENCH = "doc_benchmark_result"
K_SCALING = "scaling_result"


def _run_document_case(repeats: int = 30) -> list[dict]:
    """Chạy ca thử nghiệm chuẩn hóa trong tài liệu (200 đỉnh, 600 cạnh, 25 tài xế)."""
    graph = RoadGraph()
    for i in range(200):
        graph.add_node(f"N{i:03d}")
    for i in range(200):
        u = f"N{i:03d}"
        graph.add_edge(u, f"N{(i + 1) % 200:03d}", 1 + i % 5)
        graph.add_edge(u, f"N{(i + 7) % 200:03d}", 3 + i % 7)
        graph.add_edge(u, f"N{(i + 19) % 200:03d}", 2 + i % 11)
    drivers = {f"D{d:02d}": f"N{(d * 7) % 200:03d}" for d in range(25)}
    pickup = "N199"

    rows = []
    for name, cls in STRATEGIES.items():
        times = []
        res = None
        for _ in range(repeats):
            res = cls().find_driver(graph, pickup, drivers)
            times.append(res.runtime_ms)
        rows.append(
            {
                "Thuật toán": name,
                "Tài xế chọn": res.driver_id,
                "ETA đón (phút)": res.eta,
                "Số đỉnh đã duyệt": res.visited_count,
                "Runtime trung vị (ms)": statistics.median(times),
            }
        )
    return rows


def _scaling(n_nodes=300, n_edges=1200, ks=(1, 2, 5, 10, 25, 50, 100), seed=7) -> pd.DataFrame:
    """Đo số đỉnh duyệt và thời gian khi số lượng tài xế rảnh tăng từ 1 đến 100."""
    rng = random.Random(seed)
    nodes = [f"N{i}" for i in range(n_nodes)]
    g = RoadGraph()
    for n in nodes:
        g.add_node(n)
    for i, n in enumerate(nodes):  # vòng bao đảm bảo liên thông
        g.add_edge(n, nodes[(i + 1) % n_nodes], rng.randint(1, 10))
    for _ in range(n_edges - n_nodes):
        u, v = rng.sample(nodes, 2)
        g.add_edge(u, v, rng.randint(1, 20))
    pickup, rows = rng.choice(nodes), []
    for k in ks:
        drivers = {f"D{i}": rng.choice(nodes) for i in range(k)}
        for name, cls in STRATEGIES.items():
            runs = [cls().find_driver(g, pickup, drivers) for _ in range(10)]
            rows.append(
                {
                    "Số tài xế rảnh": k,
                    "Thuật toán": name,
                    "Số đỉnh đã thăm": runs[0].visited_count,
                    "Runtime trung vị (ms)": statistics.median(r.runtime_ms for r in runs),
                }
            )
    return pd.DataFrame(rows)


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
                    "Runtime trung vị (ms)": statistics.median(times),
                }
            )
    return {"rows": rows, "free": len(free), "repeats": repeats}


def _agreement(df: pd.DataFrame) -> pd.DataFrame:
    out = []
    for pickup, grp in df.groupby("Điểm đón", sort=False):
        drivers = grp["Tài xế"].tolist()
        etas = grp["ETA (phút)"].tolist()
        same_drv = all(
            (pd.isna(d) and pd.isna(drivers[0])) or (not pd.isna(d) and not pd.isna(drivers[0]) and d == drivers[0])
            for d in drivers
        )
        same_eta = all(
            (pd.isna(e) and pd.isna(etas[0]))
            or (not pd.isna(e) and not pd.isna(etas[0]) and abs(e - etas[0]) < 1e-6)
            for e in etas
        )
        out.append(
            {
                "Điểm đón": pickup,
                "Cùng tài xế": same_drv,
                "Cùng ETA": same_eta,
                "Khớp": same_drv and same_eta,
            }
        )
    return pd.DataFrame(out)


def _build_side_by_side_table(df: pd.DataFrame) -> pd.DataFrame:
    """Tạo bảng đối chiếu song song trực quan giữa A1 và A2 cho từng điểm đón."""
    rows = []
    for _, grp in df.groupby("Điểm đón", sort=False):
        a1_row = grp[grp["Thuật toán"].str.startswith("A1")]
        a2_row = grp[grp["Thuật toán"].str.startswith("A2")]
        if a1_row.empty or a2_row.empty:
            continue
        r1, r2 = a1_row.iloc[0], a2_row.iloc[0]

        same_drv = (
            (pd.isna(r1["Tài xế"]) and pd.isna(r2["Tài xế"]))
            or (not pd.isna(r1["Tài xế"]) and not pd.isna(r2["Tài xế"]) and r1["Tài xế"] == r2["Tài xế"])
        )
        same_eta = (
            (pd.isna(r1["ETA (phút)"]) and pd.isna(r2["ETA (phút)"]))
            or (
                not pd.isna(r1["ETA (phút)"])
                and not pd.isna(r2["ETA (phút)"])
                and abs(r1["ETA (phút)"] - r2["ETA (phút)"]) < 1e-6
            )
        )

        eta_str = "Không tới được" if pd.isna(r1["ETA (phút)"]) else f"{r1['ETA (phút)']:g} phút"
        drv_str = "Không có xe" if pd.isna(r1["Tài xế"]) else str(r1["Tài xế"])
        r2_drv_str = "Không có xe" if pd.isna(r2["Tài xế"]) else str(r2["Tài xế"])
        eta_mismatch_str = f"{'N/A' if pd.isna(r1['ETA (phút)']) else r1['ETA (phút)']} vs {'N/A' if pd.isna(r2['ETA (phút)']) else r2['ETA (phút)']}"

        rows.append(
            {
                "Điểm đón": r1["Tên địa danh"],
                "Tài xế chọn (A1 / A2)": f"{drv_str} 🤝 {r2_drv_str}" if not same_drv else f"{drv_str} (Khớp)",
                "ETA đón (A1 / A2)": eta_str if same_eta else eta_mismatch_str,
                "Đỉnh duyệt: A1": r1["Số đỉnh đã thăm"],
                "Đỉnh duyệt: A2": r2["Số đỉnh đã thăm"],
                "Chênh lệch đỉnh (A2 - A1)": f"{r2['Số đỉnh đã thăm'] - r1['Số đỉnh đã thăm']:+d}",
                "Thời gian A1 (ms)": f"{r1['Runtime trung vị (ms)']:.3f}",
                "Thời gian A2 (ms)": f"{r2['Runtime trung vị (ms)']:.3f}",
                "Trạng thái": "Khớp 100% ✅" if (same_drv and same_eta) else "Khác nhau ⚠️",
            }
        )
    return pd.DataFrame(rows)


def render() -> None:
    d = S.dispatcher()
    free_drivers = [x for x in d.drivers_snapshot().values() if x.status == FREE]
    free = len(free_drivers)
    nodes = d.graph.nodes()
    edges = d.graph.edges()

    page_header(
        icon="📊",
        title="Đối chuẩn thuật toán",
        subtitle="So sánh A1 và A2 về kết quả và hiệu năng",
        chips=[
            ("Xe rảnh", f"{free}"),
            ("Số đỉnh", f"{len(nodes)}"),
            ("Số cung", f"{len(edges)}"),
        ],
    )

    # ── PHẦN 1: GIẢI THÍCH TRỰC QUAN BẢN CHẤT HAI THUẬT TOÁN ──────────────────
    c_a1, c_a2, c_rule = st.columns(3)
    with c_a1:
        with st.container(border=True):
            st.markdown("#### 🚗 Chiến lược A1\n**Dijkstra từ từng tài xế**")
            st.markdown(
                "- **Cơ chế:** Chạy thuật toán Dijkstra độc lập xuất phát từ vị trí của **từng tài xế rảnh** đến điểm đón.\n"
                "- **Số lần chạy Dijkstra:** **$k$ lần** ($k$ = số tài xế rảnh).\n"
                "- **Độ phức tạp:** $O(k \\cdot (E + V \\log V))$.\n"
                "- **Ưu/Nhược điểm:** Đơn giản, không cần sửa đồ thị; nhưng khối lượng tính toán tăng vọt theo số tài xế."
            )
    with c_a2:
        with st.container(border=True):
            st.markdown("#### 🔄 Chiến lược A2\n**Dijkstra trên đồ thị đảo chiều**")
            st.markdown(
                "- **Cơ chế:** Đảo ngược tất cả các cung đường ($u \\to v$ thành $v \\to u$), chạy **1 lần duy nhất** từ điểm đón tỏa ra các tài xế.\n"
                "- **Số lần chạy Dijkstra:** **1 lần duy nhất**.\n"
                "- **Độ phức tạp:** $O(E + V \\log V)$.\n"
                "- **Ưu/Nhược điểm:** Tối ưu vượt trội khi có nhiều tài xế rảnh; cần 1 bước đảo chiều đồ thị."
            )
    with c_rule:
        with st.container(border=True):
            st.markdown("#### 🎯 Mục tiêu Đối chuẩn\n**Đảm bảo tính nhất quán**")
            st.markdown(
                "- **Tính đúng đắn:** Cả hai thuật toán **bắt buộc** phải tìm ra **cùng một tài xế tối ưu** và **cùng một ETA đón**.\n"
                "- **Giải quyết hòa ETA (Tie-breaking):** Nếu hai tài xế có cùng ETA, cả A1 và A2 đều chọn `driver_id` nhỏ nhất theo thứ tự từ điển.\n"
                "- **Hiệu năng:** Đánh giá số đỉnh duyệt và thời gian thực thi."
            )

    # ── BẢNG SO SÁNH LÝ THUYẾT ───────────────────────────────────────────────
    with st.expander("📖 Xem bảng tóm tắt so sánh lý thuyết và độ phức tạp", expanded=False):
        df_theory = pd.DataFrame(
            [
                {
                    "Tiêu chí": "Hướng tìm đường",
                    "A1 (Dijkstra từng tài xế)": "Từ từng xe rảnh ➔ Điểm đón",
                    "A2 (Dijkstra đảo chiều)": "Từ điểm đón ➔ Tỏa ra mọi xe rảnh (đồ thị đảo)",
                    "Ý nghĩa": "A2 đảo góc nhìn bài toán",
                },
                {
                    "Tiêu chí": "Số lần chạy Dijkstra",
                    "A1 (Dijkstra từng tài xế)": "$k$ lần ($k$ tài xế rảnh)",
                    "A2 (Dijkstra đảo chiều)": "1 lần duy nhất",
                    "Ý nghĩa": "A2 tiết kiệm CPU khi $k$ lớn",
                },
                {
                    "Tiêu chí": "Độ phức tạp thời gian",
                    "A1 (Dijkstra từng tài xế)": "$O(k \\cdot (E + V \\log V))$",
                    "A2 (Dijkstra đảo chiều)": "$O(E + V \\log V)$",
                    "Ý nghĩa": "A2 độc lập với số tài xế",
                },
                {
                    "Tiêu chí": "Chi phí phụ trợ",
                    "A1 (Dijkstra từng tài xế)": "Không có",
                    "A2 (Dijkstra đảo chiều)": "1 lần đảo chiều đồ thị $O(E)$",
                    "Ý nghĩa": "A1 lợi thế khi chỉ có 1 xe",
                },
                {
                    "Tiêu chí": "Khuyến nghị sử dụng",
                    "A1 (Dijkstra từng tài xế)": "Khi $k \\le 2$ hoặc đồ thị đổi liên tục",
                    "A2 (Dijkstra đảo chiều)": "Hệ thống thực tế ($k \\gg 1$, hàng chục/trăm xe)",
                    "Ý nghĩa": "Chuẩn mực gọi xe thông minh",
                },
            ]
        )
        st.dataframe(df_theory, hide_index=True, width="stretch")

    st.divider()

    # ── PHẦN 2: ĐỐI CHUẨN THỰC NGHIỆM TRÊN MẠNG LƯỚI HIỆN TẠI ────────────────
    st.markdown("### 🧪 Thử nghiệm 1: Đối chuẩn trên Mạng lưới Giao thông Hiện tại")
    st.caption(
        f"Đồ thị hiện hành có {len(d.graph.nodes())} đỉnh, {len(d.graph.edges())} cung và "
        f"**{free} tài xế rảnh** ({', '.join(x.id for x in free_drivers) if free_drivers else 'không có'})."
    )

    labels = S.node_labels()
    c1, c2, c3 = st.columns([4, 2, 2], vertical_alignment="bottom")
    with c1:
        pickups = [
            S.item_id(x)
            for x in st.multiselect(
                "Chọn các điểm đón khách cần khảo sát",
                labels,
                default=labels,
                key="bench_pickups",
                help="Chọn các nút giao thông trong thành phố để khảo sát thuật toán ghép xe",
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
            help="Số lần chạy lặp để lấy thời gian thực thi trung vị (ms)",
        )
    with c3:
        run_btn = st.button(
            "Chạy đối chuẩn mạng lưới",
            key="btn_bench",
            type="primary",
            disabled=not pickups or free == 0,
            width="stretch",
        )

    if free == 0:
        st.warning("⚠️ Hiện không có tài xế nào đang rảnh để thử nghiệm. Hãy hoàn thành chuyến hoặc thêm tài xế mới.")

    if run_btn:
        try:
            with st.spinner("Đang chạy đối chuẩn thuật toán trên mạng lưới giao thông..."):
                st.session_state[K_BENCH] = _run(pickups, int(repeats))
        except Exception as exc:
            st.error(f"Không chạy được đối chuẩn: {exc}")

    result = st.session_state.get(K_BENCH)
    if result:
        df = pd.DataFrame(result["rows"])
        agree = _agreement(df)

        # 1. Banner kết quả đồng thuận
        total_tested = len(agree)
        matched_tested = int(agree["Khớp"].sum())
        if agree["Khớp"].all():
            st.success(f"✅ **Khớp trên {matched_tested}/{total_tested} điểm đón đã đo:** A1 và A2 cho cùng tài xế và ETA.")
        else:
            st.error(f"⚠️ Chỉ khớp {matched_tested}/{total_tested} điểm đón. Có điểm đón mà các thuật toán cho kết quả khác nhau:")
            st.dataframe(agree[~agree["Khớp"]], hide_index=True)

        # 2. Thẻ KPI tổng hợp
        summary = df.groupby("Thuật toán")[["Số đỉnh đã thăm", "Runtime trung vị (ms)"]].median()
        names = list(summary.index)

        kp1, kp2, kp3 = st.columns(3)
        with kp1:
            st.metric("Tỷ lệ khớp kết quả", f"{agree['Khớp'].mean() * 100:.0f}%", f"Khớp trên {matched_tested}/{total_tested} điểm đón đã đo")
        with kp2:
            if len(names) >= 2:
                v1, v2 = summary.loc[names[0], "Số đỉnh đã thăm"], summary.loc[names[1], "Số đỉnh đã thăm"]
                diff_v = ((v2 - v1) / v1 * 100) if v1 else 0
                st.metric(
                    label="Số đỉnh duyệt trung vị (A1 vs A2)",
                    value=f"{v1:.0f} vs {v2:.0f} đỉnh",
                    delta=f"{diff_v:+.1f}% (A2 duyệt ít hơn)" if diff_v <= 0 else f"{diff_v:+.1f}%",
                    delta_color="inverse",
                )
        with kp3:
            if len(names) >= 2:
                t1, t2 = summary.loc[names[0], "Runtime trung vị (ms)"], summary.loc[names[1], "Runtime trung vị (ms)"]
                diff_t = ((t2 - t1) / t1 * 100) if t1 else 0
                st.metric(
                    label="Runtime trung vị (A1 vs A2)",
                    value=f"{t1:.3f} vs {t2:.3f} ms",
                    delta=f"{diff_t:+.1f}% (A2 nhanh hơn)" if diff_t <= 0 else f"{diff_t:+.1f}%",
                    delta_color="inverse",
                )

        # 3. Bảng đối chiếu song song A1 vs A2
        st.markdown("##### 📋 Bảng Đối chiếu Song song cho từng Điểm đón")
        st.caption("So sánh trực tiếp tài xế ghép, ETA, số đỉnh duyệt và thời gian chạy giữa A1 và A2 trên từng vị trí.")
        side_table = _build_side_by_side_table(df)
        st.dataframe(side_table, hide_index=True, width="stretch")

        # 4. Biểu đồ trực quan so sánh
        c_chart1, c_chart2 = st.columns(2)
        with c_chart1:
            with st.container(border=True):
                st.markdown("**Số đỉnh đã duyệt theo điểm đón (Càng ít càng tối ưu)**")
                chart_nodes = df.pivot(index="Tên địa danh", columns="Thuật toán", values="Số đỉnh đã thăm")
                st.bar_chart(chart_nodes)
        with c_chart2:
            with st.container(border=True):
                st.markdown("**Thời gian chạy trung vị theo điểm đón (ms) (Càng thấp càng tối ưu)**")
                chart_time = df.pivot(index="Tên địa danh", columns="Thuật toán", values="Runtime trung vị (ms)")
                st.bar_chart(chart_time)

        max_measured_t = df["Runtime trung vị (ms)"].max()
        st.info(
            f"ℹ️ **Ghi chú phân tích & Giải thích kết quả:**\n"
            f"- **Quy mô đồ thị mẫu:** Mạng lưới seed hiện hành chỉ có {len(d.graph.nodes())} đỉnh và {free} xe rảnh ($k={free}$). "
            f"Thời gian chạy của cả hai giải thuật đều rất nhỏ (tối đa ~{max_measured_t:.3f} ms), do đó ở Thử nghiệm 1, A2 chưa tạo ra sự cách biệt lớn so với A1.\n"
            f"- **Trạng thái warm:** A2 sử dụng cơ chế cache đồ thị đảo của `RoadGraph`, số đo lặp lại phản ánh thời gian thực thi ở trạng thái warm (đồ thị đảo đã nạp sẵn trong bộ nhớ).\n"
            f"- **Tính công bằng thuật toán:** Bản cài đặt A1 hiện chạy Dijkstra từng xe rảnh cho đến khi tìm được điểm đón (chưa áp dụng cắt tỉa dựa trên `best_eta`), "
            f"còn A2 chạy Dijkstra từ điểm đón trên đồ thị đảo và dừng sớm ngay khi đỉnh đầu tiên trong min-heap vượt quá `best_eta`. "
            f"Lợi thế vượt trội của A2 chỉ thể hiện rõ rệt khi số lượng tài xế rảnh $k$ lớn (xem Thử nghiệm 2 bên dưới)."
        )

    st.divider()

    # ── PHẦN 3: ĐỐI CHUẨN QUY MÔ LỚN (MINH CHỨNG SỨC MẠNH A2 KHI K TĂNG) ──────
    st.markdown("### 🚀 Thử nghiệm 2: Minh chứng Vượt trội khi Mở rộng Quy mô (Scalability)")
    st.markdown(
        "Khi mạng lưới có hàng chục hoặc hàng trăm tài xế rảnh ($k \\gg 1$), A1 phải chạy $k$ lượt Dijkstra khiến "
        "thời gian tính toán tăng tuyến tính $O(k)$ theo số tài xế rảnh, trong khi A2 chỉ chạy 1 lượt duy nhất từ điểm đón "
        "trên đồ thị đảo nên không bị phụ thuộc tuyến tính vào $k$ (thậm chí dừng sớm hơn khi $k$ tăng)."
    )

    choice_scale = st.radio(
        "Chọn chế độ thử nghiệm:",
        ["Ca thử nghiệm chuẩn (200 đỉnh, 25 tài xế)", "Mô phỏng mở rộng (k = 1 ➔ 100 tài xế)"],
        horizontal=True,
        key="radio_scaling_mode",
    )

    if choice_scale == "Ca thử nghiệm chuẩn (200 đỉnh, 25 tài xế)":
        st.markdown(
            "Ca thử nghiệm chuẩn từ báo cáo kỹ thuật [ALGORITHM_BENCHMARK.md](docs/ALGORITHM_BENCHMARK.md): "
            "**200 đỉnh**, **600 cung đường**, **25 tài xế rảnh**, điểm đón `N199`. "
            "*(Số đo phản ánh trạng thái warm khi đồ thị đảo đã được nạp)*."
        )
        if st.button("Chạy ca kiểm thử 200 đỉnh chuẩn", key="btn_run_doc_bench", type="primary"):
            with st.spinner("Đang chạy đối chuẩn trên đồ thị 200 đỉnh và 25 tài xế..."):
                st.session_state[K_DOC_BENCH] = _run_document_case()

        doc_res = st.session_state.get(K_DOC_BENCH)
        if doc_res:
            df_doc = pd.DataFrame(doc_res)
            st.dataframe(df_doc, hide_index=True, width="stretch")

            r1, r2 = doc_res[0], doc_res[1]
            ratio_v = r1["Số đỉnh đã duyệt"] / r2["Số đỉnh đã duyệt"] if r2["Số đỉnh đã duyệt"] else 1
            pct_saved = ((r1["Số đỉnh đã duyệt"] - r2["Số đỉnh đã duyệt"]) / r1["Số đỉnh đã duyệt"] * 100) if r1["Số đỉnh đã duyệt"] else 0
            ratio_t = (
                float(r1["Runtime trung vị (ms)"]) / float(r2["Runtime trung vị (ms)"])
                if float(r2["Runtime trung vị (ms)"])
                else 1
            )

            d1, d2 = st.columns(2)
            with d1:
                if r2["Số đỉnh đã duyệt"] < r1["Số đỉnh đã duyệt"]:
                    st.success(
                        f"🏆 **Giảm số đỉnh duyệt:** A2 chỉ duyệt **{r2['Số đỉnh đã duyệt']}** đỉnh so với "
                        f"**{r1['Số đỉnh đã duyệt']:,}** đỉnh của A1 (**giảm {ratio_v:.1f} lần** — tiết kiệm {pct_saved:.1f}% số đỉnh duyệt)!"
                    )
                else:
                    st.info(
                        f"📊 **Số đỉnh đã duyệt:** A2 duyệt **{r2['Số đỉnh đã duyệt']}** đỉnh so với "
                        f"**{r1['Số đỉnh đã duyệt']:,}** đỉnh của A1."
                    )
            with d2:
                if ratio_t > 1.05:
                    st.success(
                        f"⚡ **Tăng tốc xử lý:** A2 chạy trong **{r2['Runtime trung vị (ms)']:.3f} ms** (warm) so với "
                        f"**{r1['Runtime trung vị (ms)']:.3f} ms** của A1 (**nhanh hơn ~{ratio_t:.1f} lần**), cùng chọn tài xế `{r2['Tài xế chọn']}`."
                    )
                else:
                    st.info(
                        f"⏱️ **Thời gian xử lý:** A2 chạy trong **{r2['Runtime trung vị (ms)']:.3f} ms** (warm), A1 chạy trong "
                        f"**{r1['Runtime trung vị (ms)']:.3f} ms**, cùng chọn tài xế `{r2['Tài xế chọn']}`."
                    )

    else:
        st.markdown(
            "Mô phỏng khảo sát độ mở rộng trên mạng lưới 300 nút giao thông, tăng dần số tài xế rảnh từ "
            "**$k = 1$** đến **$k = 100$ xe**:"
        )
        if st.button("Chạy mô phỏng tăng số lượng tài xế (k = 1 ➔ 100)", key="btn_scaling", width="stretch"):
            with st.spinner("Đang mô phỏng trên đồ thị 300 đỉnh với k từ 1 đến 100..."):
                st.session_state[K_SCALING] = _scaling()

        sc = st.session_state.get(K_SCALING)
        if sc is not None:
            c_sc1, c_sc2 = st.columns(2)
            with c_sc1:
                with st.container(border=True):
                    st.markdown("**Số đỉnh duyệt qua Min-Heap theo số tài xế rảnh ($k$)**")
                    piv_nodes = sc.pivot(index="Số tài xế rảnh", columns="Thuật toán", values="Số đỉnh đã thăm")
                    st.line_chart(piv_nodes)
                    st.caption("📈 **Nhận xét:** Đường A1 tăng xấp xỉ tuyến tính theo số tài xế rảnh $k$, trong khi A2 không phụ thuộc tuyến tính vào $k$ (thậm chí có xu hướng giảm khi $k$ lớn do thuật toán gặp tài xế gần và dừng sớm hơn).")
            with c_sc2:
                with st.container(border=True):
                    st.markdown("**Thời gian chạy trung vị (ms) theo số tài xế rảnh ($k$)**")
                    piv_time = sc.pivot(index="Số tài xế rảnh", columns="Thuật toán", values="Runtime trung vị (ms)")
                    st.line_chart(piv_time)
                    st.caption("⚡ **Nhận xét:** Thời gian chạy của A2 duy trì ở mức thấp và không bị tăng xấp xỉ tuyến tính theo số lượng tài xế rảnh $k$ như A1.")

    st.divider()

    # ── PHẦN 4: TỔNG KẾT & KHUYẾN NGHỊ ────────────────────────────────────────
    with st.container(border=True):
        st.markdown("### 💡 Kết luận & Khuyến nghị Thực tế")
        st.markdown(
            "1. **Tính tương đương nghiệp vụ:** Cả A1 và A2 đều tuân thủ chặt chẽ nguyên tắc tối ưu ETA và tie-breaking, "
            "đảm bảo khách hàng luôn nhận được cuốc xe nhanh nhất và tài xế chính xác.\n"
            "2. **Điểm bùng phát hiệu năng:** Khi $k \\le 2$, A1 có thời gian tương đương do không tốn chi phí đảo đồ thị. "
            "Tuy nhiên trong các thử nghiệm của nhóm khi $k \\ge 5$, **A2 thể hiện ưu thế vượt trội về số phép toán và thời gian tính toán**.\n"
            "3. **Ứng dụng thực tế:** Trong các hệ thống điều phối xe công nghệ quy mô thành phố lớn (hàng nghìn tài xế rảnh), "
            "**A2 (Dijkstra đảo chiều)** là giải pháp được nhóm khuyến nghị nhằm giảm tải CPU cho server và phản hồi người dùng tức thì."
        )
