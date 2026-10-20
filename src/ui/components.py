"""TV5 - Các thành phần giao diện tái sử dụng (Reusable UI Components).

Mọi chuỗi động/dữ liệu từ người dùng hoặc hệ thống đưa vào HTML đều qua `html.escape`.
Bảo đảm độ tương phản theo chuẩn WCAG AA và tương thích theme sáng mặc định.
"""
from __future__ import annotations

from dataclasses import dataclass
import html
import math
import re
import time
from typing import Callable, Iterable

import streamlit as st

from .constants import (
    ANIM_MAX_INTERVAL,
    ANIM_MAX_SECONDS,
    ANIM_MIN_INTERVAL,
    ANIM_MINUTES_PER_TICK,
    ANIM_STATUS_COMPLETED,
    ANIM_STATUS_PAUSED,
    ANIM_STATUS_PLAYING,
    ANIM_TARGET_SECONDS,
    ANIM_TICKS_PER_EDGE_MAX,
    ANIM_TICKS_PER_EDGE_MIN,
    ASSIGNED,
    BASE_TICK_DELAY_SEC,
    BUSY,
    COMPLETED,
    FREE,
    MAX_TICKS_PER_EDGE,
    MIN_TICKS_PER_EDGE,
    MINUTES_PER_TICK,
    QUEUED,
    status_label,
)


def build_page_header_html(
    icon: str,
    title: str,
    subtitle: str,
    chips: list[tuple[str, str]] | None = None,
) -> str:
    """Tạo chuỗi HTML cho header trang với icon, tiêu đề lớn, mô tả và hàng chip thông số.

    Mọi chuỗi đưa vào HTML đều qua `html.escape` để đảm bảo an toàn XSS.
    Hỗ trợ cú pháp in đậm markdown **...** và thẻ <b>, <strong> cho nhãn hoặc giá trị chip.
    """
    safe_icon = html.escape(str(icon))
    safe_title = html.escape(str(title))
    safe_subtitle = html.escape(str(subtitle))

    chips_html = ""
    if chips:
        chips_items = []
        for label, val in chips:
            safe_label = html.escape(str(label))
            safe_val = html.escape(str(val))
            label_text = safe_label if safe_label.endswith(":") else f"{safe_label}:"

            # Hỗ trợ cú pháp in đậm markdown **...** và thẻ html <b>, <strong>
            label_display = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", label_text)
            label_display = re.sub(r"&lt;b&gt;(.+?)&lt;/b&gt;", r"<strong>\1</strong>", label_display)
            label_display = re.sub(r"&lt;strong&gt;(.+?)&lt;/strong&gt;", r"<strong>\1</strong>", label_display)

            val_display = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", safe_val)
            val_display = re.sub(r"&lt;b&gt;(.+?)&lt;/b&gt;", r"<strong>\1</strong>", val_display)
            val_display = re.sub(r"&lt;strong&gt;(.+?)&lt;/strong&gt;", r"<strong>\1</strong>", val_display)

            chips_items.append(
                f'<span class="header-chip">'
                f'<span class="header-chip-label">{label_display}</span> '
                f'<span class="header-chip-val">{val_display}</span>'
                f'</span>'
            )
        chips_str = "".join(chips_items)
        chips_html = f'<div class="header-chips-wrap">{chips_str}</div>'

    return (
        f'<div class="page-header">\n'
        f'    <div class="page-header-top">\n'
        f'        <h1 class="page-header-title">\n'
        f'            <span class="page-header-icon">{safe_icon}</span>\n'
        f'            <span class="page-header-text">{safe_title}</span>\n'
        f'        </h1>\n'
        f'    </div>\n'
        f'    <div class="page-header-subtitle">{safe_subtitle}</div>\n'
        f'    {chips_html}\n'
        f'</div>'
    )


def page_header(
    icon: str,
    title: str,
    subtitle: str,
    chips: list[tuple[str, str]] | None = None,
) -> None:
    """Hiển thị header chuẩn hóa cho từng trang nghiệp vụ."""
    st.markdown(build_page_header_html(icon, title, subtitle, chips), unsafe_allow_html=True)



def render_kpi_card(
    title: str,
    value: str | int,
    subtext: str = "",
    icon: str = "📊",
    help_text: str = "",
) -> None:
    """Hiển thị một thẻ KPI gọn gàng, trực quan với độ tương phản cao."""
    safe_title = html.escape(str(title))
    safe_value = html.escape(str(value))
    safe_subtext = html.escape(str(subtext)) if subtext else ""
    safe_icon = html.escape(str(icon))
    tooltip_attr = f' title="{html.escape(help_text)}"' if help_text else ""

    sub_html = f'<div class="kpi-subtext">{safe_subtext}</div>' if safe_subtext else ""

    card_html = f"""
    <div class="kpi-card"{tooltip_attr}>
        <div class="kpi-icon-wrap">{safe_icon}</div>
        <div class="kpi-body">
            <div class="kpi-label">{safe_title}</div>
            <div class="kpi-value">{safe_value}</div>
            {sub_html}
        </div>
    </div>
    """
    st.markdown(card_html, unsafe_allow_html=True)


def get_status_badge_html(status: str) -> str:
    """Trả về chuỗi HTML huy hiệu (badge) trạng thái có màu sắc chuẩn hóa."""
    cls_map = {
        FREE: "badge-free",
        BUSY: "badge-busy",
        QUEUED: "badge-queued",
        ASSIGNED: "badge-assigned",
        COMPLETED: "badge-completed",
    }
    css_cls = cls_map.get(status, "badge-default")
    label = status_label(status)
    safe_label = html.escape(label)
    return f'<span class="badge-status {css_cls}">{safe_label}</span>'


def render_empty_state(
    icon: str,
    title: str,
    description: str,
    action_hint: str = "",
) -> None:
    """Hiển thị khung trạng thái rỗng thân thiện, kèm gợi ý hành động tiếp theo."""
    safe_icon = html.escape(icon)
    safe_title = html.escape(title)
    safe_desc = html.escape(description)
    safe_hint = html.escape(action_hint) if action_hint else ""

    hint_html = f'<div class="empty-hint">💡 <b>Gợi ý:</b> {safe_hint}</div>' if safe_hint else ""

    html_code = f"""
    <div class="empty-state-box">
        <div class="empty-icon">{safe_icon}</div>
        <div class="empty-title">{safe_title}</div>
        <div class="empty-desc">{safe_desc}</div>
        {hint_html}
    </div>
    """
    st.markdown(html_code, unsafe_allow_html=True)


def render_map_legend() -> None:
    """Hiển thị chú giải trực quan (legend) ngay dưới bản đồ Graphviz."""
    legend_items = [
        ("legend-dot-free", "🟢 Xe sẵn sàng (Viền xanh lá)"),
        ("legend-dot-busy", "🔴 Xe đang bận (Viền đỏ)"),
        ("legend-dot-waiting", "🟠 Chờ đón (Viền cam)"),
        ("legend-line-solid", "── Đón khách (Xanh lá)"),
        ("legend-line-dashed", "╌╌ Trả khách (Cam nét đứt)"),
    ]
    pills = "".join(
        f'<span class="legend-pill"><span class="legend-indicator {cls}"></span>{html.escape(label)}</span>'
        for cls, label in legend_items
    )
    legend_html = f"""
    <div class="map-legend-container">
        <div class="legend-title">Chú giải bản đồ:</div>
        <div class="legend-pills-wrap">{pills}</div>
    </div>
    """
    st.markdown(legend_html, unsafe_allow_html=True)


def render_route_breadcrumb(
    path: Iterable[str],
    label_func: Callable[[str], str],
    title: str = "Lộ trình di chuyển đón khách:",
) -> None:
    """Hiển thị chuỗi breadcrumb đẹp mắt cho lộ trình đón hoặc chở khách."""
    nodes = list(path)
    if not nodes:
        return
    safe_title = html.escape(title)
    node_spans = [
        f'<span class="route-node">{html.escape(label_func(n))}</span>'
        for n in nodes
    ]
    path_html = ' <span class="route-arrow">➔</span> '.join(node_spans)
    full_html = f"""
    <div class="route-path">
        <span class="route-title"><b>{safe_title}</b></span>
        <div class="route-nodes-wrap">{path_html}</div>
    </div>
    """
    st.markdown(full_html, unsafe_allow_html=True)


def render_graph_with_zoom(
    dot: str,
    key_prefix: str,
    height: int = 500,
) -> None:
    """Hiển thị đồ thị Graphviz kèm thanh điều khiển Phóng to / Thu nhỏ / Vừa khung thuần Streamlit.

    - Không phụ thuộc thư viện ngoài hoặc CDN (hoạt động offline).
    - Cụm điều khiển gồm:
        + Nút Thu nhỏ (-): key=f"{key_prefix}_zoom_out"
        + Nút Phóng to (+): key=f"{key_prefix}_zoom_in"
        + Nút Vừa khung (100%): key=f"{key_prefix}_zoom_reset"
        + Slider điều chỉnh mức zoom: key=f"{key_prefix}_zoom_level" (50% - 300%)
    - Khung bản đồ dùng st.container(height=height, border=True) cuộn mượt mà khi phóng to.
    """
    zoom_key = f"{key_prefix}_zoom_level"
    if zoom_key not in st.session_state:
        st.session_state[zoom_key] = 100

    def _zoom_in() -> None:
        cur = st.session_state.get(zoom_key, 100)
        st.session_state[zoom_key] = min(300, cur + 20)

    def _zoom_out() -> None:
        cur = st.session_state.get(zoom_key, 100)
        st.session_state[zoom_key] = max(50, cur - 20)

    def _zoom_reset() -> None:
        st.session_state[zoom_key] = 100

    zoom_val = st.session_state.get(zoom_key, 100)

    col_out, col_in, col_reset, col_badge, col_slider = st.columns([1.1, 1.1, 1.3, 1.0, 4.5])
    with col_out:
        st.button(
            "➖ Thu nhỏ",
            key=f"{key_prefix}_zoom_out",
            on_click=_zoom_out,
            width="stretch",
            help="Thu nhỏ bản đồ (giảm 20%, tối thiểu 50%)",
        )
    with col_in:
        st.button(
            "➕ Phóng to",
            key=f"{key_prefix}_zoom_in",
            on_click=_zoom_in,
            width="stretch",
            help="Phóng to bản đồ (tăng 20%, tối đa 300%)",
        )
    with col_reset:
        st.button(
            "🔄 Vừa khung",
            key=f"{key_prefix}_zoom_reset",
            on_click=_zoom_reset,
            width="stretch",
            help="Đặt lại mức phóng to về 100% (vừa khung chứa)",
        )
    with col_badge:
        st.markdown(
            f'<div class="zoom-badge-indicator" title="Mức phóng to hiện tại">{zoom_val}%</div>',
            unsafe_allow_html=True,
        )
    with col_slider:
        st.slider(
            "Mức phóng to",
            min_value=50,
            max_value=300,
            step=10,
            format="%d%%",
            key=zoom_key,
            label_visibility="collapsed",
            help="Kéo để điều chỉnh mức phóng to từ 50% đến 300%",
        )

    canvas_key = f"{key_prefix}_canvas"
    with st.container(height=height, border=True, key=canvas_key):
        if zoom_val == 100:
            st.graphviz_chart(dot, width="stretch")
        else:
            calc_w = int(900 * (zoom_val / 100.0))
            st.graphviz_chart(dot, width=calc_w)


# -----------------------------------------------------------------------------
# Phát lại lộ trình (Route Replay / Animation)
# -----------------------------------------------------------------------------
@dataclass
class AnimationTick:
    """Đại diện cho một tick (bước chia nhỏ) trong animation phát lại lộ trình."""

    tick_index: int
    total_ticks: int
    node: str
    node_name: str
    phase: str
    elapsed_time: float
    tick_delay: float
    custom_edges: dict[tuple[str, str], tuple[str, str, float]]
    caption: str
    progress_pct: float
    edge_pct: float
    edge_label: str
    dot_string: str = ""

    # Thuộc tính tương thích ngược với AnimationStep cũ
    @property
    def step_index(self) -> int:
        return self.tick_index

    @property
    def total_steps(self) -> int:
        return self.total_ticks + 1

    @property
    def step_delay(self) -> float:
        return self.tick_delay


# Alias tương thích ngược
AnimationStep = AnimationTick


class AnimationTimeline(list):
    """Danh sách các khung hình animation kèm metadata về lịch phát và thời gian render."""

    def __init__(
        self,
        iterable: Iterable[AnimationTick] = (),
        avg_render_time: float = 0.0,
        schedule: PlaybackSchedule | None = None,
    ) -> None:
        super().__init__(iterable)
        self.avg_render_time = avg_render_time
        self.schedule = schedule

    @property
    def _avg_render_time(self) -> float:
        return self.avg_render_time

    @_avg_render_time.setter
    def _avg_render_time(self, val: float) -> None:
        self.avg_render_time = val

    @property
    def _schedule(self) -> PlaybackSchedule | None:
        return self.schedule

    @_schedule.setter
    def _schedule(self, val: PlaybackSchedule | None) -> None:
        self.schedule = val


@dataclass
class PlaybackSchedule:
    """Lịch phát animation theo ngân sách thời gian."""

    total_ticks: int
    step_stride: int       # k: bước nhảy tick (1 nếu phát đủ, >1 nếu bỏ bớt khung)
    num_frames: int        # Số lượng khung hình phát
    interval: float        # Khoảng thời gian giữa 2 khung hình (giây)
    total_seconds: float   # Tổng thời gian phát dự kiến (giây)
    speed_mult: float      # Hệ số tốc độ (1.0, 2.0, 4.0)


def compute_edge_ticks(
    weight: float,
    min_minutes_per_tick: float = ANIM_MINUTES_PER_TICK,
    min_ticks: int = ANIM_TICKS_PER_EDGE_MIN,
    max_ticks: int = ANIM_TICKS_PER_EDGE_MAX,
) -> int:
    """Tính số tick chia nhỏ cho một cạnh: n = clamp(round(weight / 1.0), 2, 6)."""
    raw = round(weight / min_minutes_per_tick) if min_minutes_per_tick > 0 else min_ticks
    return max(min_ticks, min(max_ticks, int(raw)))


def calculate_playback_schedule(
    total_ticks: int,
    speed_mult: float = 2.0,
    num_nodes: int = 0,
    avg_render_time: float = 0.0,
    target_seconds: float = ANIM_TARGET_SECONDS,
    max_seconds: float = ANIM_MAX_SECONDS,
    min_interval: float = ANIM_MIN_INTERVAL,
    max_interval: float = ANIM_MAX_INTERVAL,
) -> PlaybackSchedule:
    """Tính toán ngân sách thời gian, khoảng giữa 2 khung hình và tỷ lệ bỏ khung (k).

    Quy tắc (YÊU CẦU 2 & 5):
    - Khoảng giữa hai khung = clamp(target / total_ticks / speed_mult, effective_min, max_interval).
    - effective_min = max(min_interval, avg_render_time).
    - Nếu tổng thời gian vượt max_seconds / speed_mult, bỏ bớt khung hình (mỗi k tick, k = ceil(tổng / max_sec)).
    - Không rút khoảng giữa các khung dưới effective_min.
    - Duy trì tối thiểu 8 khung hình cho lộ trình >= 3 đỉnh nếu có thể.
    """
    if total_ticks <= 0:
        return PlaybackSchedule(
            total_ticks=0,
            step_stride=1,
            num_frames=1 if num_nodes > 0 else 0,
            interval=min_interval,
            total_seconds=0.0,
            speed_mult=speed_mult,
        )

    speed = max(0.1, float(speed_mult))
    eff_min = max(min_interval, float(avg_render_time))
    target_dur = target_seconds / speed
    max_dur = max_seconds / speed

    raw_interval = target_dur / max(1, total_ticks)
    interval = max(eff_min, min(max_interval, raw_interval))

    total_time = total_ticks * interval
    k = 1

    # Kiểm tra vượt trần thời gian hoặc cần tăng tốc cho 4x khi interval bị clamp ở min
    if total_time > max_dur:
        k = math.ceil(total_time / max_dur)
        if num_nodes >= 3:
            max_k = max(1, total_ticks // 7)
            k = min(k, max_k)
    elif speed >= 3.5:
        # Ở tốc độ 4x, nếu interval bị kẹp ở min khiến thời gian chưa đạt ~1/4 mục tiêu, nhảy bước k
        if total_time > target_dur * 1.3:
            k_speed = max(1, round(total_time / target_dur))
            if num_nodes >= 3:
                max_k = max(1, total_ticks // 7)
                k = min(k_speed, max_k)
            else:
                k = k_speed

    num_frames = math.ceil(total_ticks / k) + 1
    final_time = (num_frames - 1) * interval

    return PlaybackSchedule(
        total_ticks=total_ticks,
        step_stride=k,
        num_frames=num_frames,
        interval=interval,
        total_seconds=final_time,
        speed_mult=speed,
    )


def build_animation_ticks(
    pickup_path: list[str] | None,
    ride_path: list[str] | None,
    graph_edges: Iterable[tuple[str, str, float]],
    node_label_fn: Callable[[str], str],
    speed_mult: float = 2.0,
    drivers: dict | None = None,
    queue: list | None = None,
    nodes: Iterable[str] | None = None,
    precompute_dots: bool = False,
    avg_render_time: float = 0.0,
) -> list[AnimationTick]:
    """Tạo chuỗi các tick (khung hình chia nhỏ) cho animation phát lại lộ trình theo ngân sách thời gian."""
    p_path = [str(x) for x in (pickup_path or [])]
    r_path = [str(x) for x in (ride_path or [])]

    if not p_path and not r_path:
        return AnimationTimeline([])

    # Ghép 2 chặng: tránh lặp đỉnh tiếp giáp nếu điểm đón trùng điểm bắt đầu chở
    if p_path and r_path:
        if p_path[-1] == r_path[0]:
            full_nodes = p_path + r_path[1:]
        else:
            full_nodes = p_path + r_path
    elif p_path:
        full_nodes = p_path
    else:
        full_nodes = r_path

    num_pickup_edges = max(0, len(p_path) - 1) if p_path else 0
    num_ride_edges = max(0, len(r_path) - 1) if r_path else 0
    has_both_phases = (num_pickup_edges > 0 and num_ride_edges > 0)

    route_edges: list[tuple[str, str]] = []
    for k_edge in range(len(full_nodes) - 1):
        route_edges.append((full_nodes[k_edge], full_nodes[k_edge + 1]))

    weights: dict[tuple[str, str], float] = {
        (u, v): float(w) for u, v, w in graph_edges
    }

    # Xử lý biên: lộ trình chỉ có 1 đỉnh
    if len(full_nodes) == 1:
        single_node = full_nodes[0]
        lbl = node_label_fn(single_node)
        single_tick = AnimationTick(
            tick_index=0,
            total_ticks=0,
            node=single_node,
            node_name=lbl,
            phase="Điểm đón khách" if p_path else "Điểm trả khách",
            elapsed_time=0.0,
            tick_delay=ANIM_MIN_INTERVAL,
            custom_edges={},
            caption=f"Điểm dừng • {lbl} • 100% • T+0.0 phút",
            progress_pct=1.0,
            edge_pct=100.0,
            edge_label=lbl,
        )
        if precompute_dots and drivers is not None:
            from .graph_view import build_dot

            t_render_start = time.perf_counter()
            single_tick.dot_string = build_dot(
                edges=graph_edges,
                drivers=drivers,
                queue=queue or [],
                label=node_label_fn,
                nodes=nodes,
                routes=None,
                layout="neato",
                highlight_node=single_node,
                custom_edges={},
            )
            render_cost = time.perf_counter() - t_render_start
            return AnimationTimeline([single_tick], avg_render_time=render_cost)
        return AnimationTimeline([single_tick])

    # Tính số tick cho từng cạnh theo ngân sách mới [2, 6]
    edge_tick_counts: list[int] = []
    for edge in route_edges:
        w = weights.get(edge, 1.0)
        edge_tick_counts.append(compute_edge_ticks(w))

    # YÊU CẦU 6: Duy trì tối thiểu 8 khung hình cho lộ trình từ 3 đỉnh trở lên
    if len(full_nodes) >= 3:
        while sum(edge_tick_counts) < 8 and any(t < ANIM_TICKS_PER_EDGE_MAX for t in edge_tick_counts):
            min_idx = edge_tick_counts.index(min(edge_tick_counts))
            edge_tick_counts[min_idx] += 1

    total_ticks = sum(edge_tick_counts)

    # Tính toán lịch phát theo ngân sách thời gian
    schedule = calculate_playback_schedule(
        total_ticks=total_ticks,
        speed_mult=speed_mult,
        num_nodes=len(full_nodes),
        avg_render_time=avg_render_time,
    )
    tick_delay = schedule.interval
    k_stride = schedule.step_stride

    # Khung hình 0 (Tick 0: Xuất phát)
    first_node = full_nodes[0]
    first_lbl = node_label_fn(first_node)
    next_lbl = node_label_fn(full_nodes[1])
    first_edge_label = f"{first_lbl} → {next_lbl}"

    init_custom_edges: dict[tuple[str, str], tuple[str, str, float]] = {}
    for idx, edge in enumerate(route_edges):
        is_pickup = idx < num_pickup_edges
        color = "#86efac" if is_pickup else "#fdba74"
        init_custom_edges[edge] = (color, "dashed", 2.0)

    phase_0_prefix = "Chặng 1/2" if has_both_phases else ("Chặng 1/1" if (num_pickup_edges > 0 or num_ride_edges > 0) else "")
    caption_0 = f"{phase_0_prefix} • Xuất phát tại {first_lbl} • 0% • T+0.0 phút" if phase_0_prefix else f"Xuất phát tại {first_lbl} • 0% • T+0.0 phút"

    all_ticks: list[AnimationTick] = [
        AnimationTick(
            tick_index=0,
            total_ticks=total_ticks,
            node=first_node,
            node_name=first_lbl,
            phase="Đón khách" if num_pickup_edges > 0 else "Chở khách",
            elapsed_time=0.0,
            tick_delay=tick_delay,
            custom_edges=init_custom_edges,
            caption=caption_0,
            progress_pct=0.0,
            edge_pct=0.0,
            edge_label=first_edge_label,
        )
    ]

    # Sinh các tick cho từng cạnh
    global_tick = 0
    t_prev = 0.0

    for k, (u, v) in enumerate(route_edges):
        n_k = edge_tick_counts[k]
        w_k = weights.get((u, v), 1.0)
        is_pickup = k < num_pickup_edges
        u_name = node_label_fn(u)
        v_name = node_label_fn(v)
        cur_edge_label = f"{u_name} → {v_name}"

        if has_both_phases:
            phase_prefix = "Chặng 1/2" if is_pickup else "Chặng 2/2"
            phase_name = "Đón khách" if is_pickup else "Chở khách"
        else:
            phase_prefix = "Chặng 1/1"
            phase_name = "Đón khách" if is_pickup else "Chở khách"

        for j in range(1, n_k + 1):
            global_tick += 1
            frac = j / n_k
            edge_pct = frac * 100.0
            elapsed_t = t_prev + (frac * w_k)
            progress_pct = global_tick / total_ticks

            # Cấu hình custom_edges cho tick này
            custom_edges: dict[tuple[str, str], tuple[str, str, float]] = {}
            for idx, edge_kv in enumerate(route_edges):
                edge_is_pickup = idx < num_pickup_edges
                if idx < k:
                    # Cạnh đã đi qua: solid, 3.5
                    color = "#16a34a" if edge_is_pickup else "#ea580c"
                    custom_edges[edge_kv] = (color, "solid", 3.5)
                elif idx == k:
                    # Cạnh đang đi: luân phiên nét đặc (solid, 5.0) và đứt (dashed, 3.5) theo tick chẵn/lẻ
                    active_color = "#16a34a" if edge_is_pickup else "#ea580c"
                    if global_tick % 2 == 0:
                        custom_edges[edge_kv] = (active_color, "solid", 5.0)
                    else:
                        custom_edges[edge_kv] = (active_color, "dashed", 3.5)
                else:
                    # Cạnh chưa đi: mờ nét đứt (dashed, 2.0)
                    faint_color = "#86efac" if edge_is_pickup else "#fdba74"
                    custom_edges[edge_kv] = (faint_color, "dashed", 2.0)

            # Đỉnh hiện tại
            curr_node = v if j == n_k else u
            curr_node_name = node_label_fn(curr_node)

            # Chú thích khung hình
            t_str = f"T+{elapsed_t:.1f} phút"
            pct_int = round(edge_pct)
            if global_tick == total_ticks:
                caption = f"{phase_prefix} • Đã đến {v_name} • 100% • {t_str}"
            elif j == n_k and is_pickup and k == num_pickup_edges - 1 and has_both_phases:
                caption = f"{phase_prefix} • Đã đón khách tại {v_name} • 100% • {t_str}"
            else:
                caption = f"{phase_prefix} • {cur_edge_label} • {pct_int}% • {t_str}"

            all_ticks.append(
                AnimationTick(
                    tick_index=global_tick,
                    total_ticks=total_ticks,
                    node=curr_node,
                    node_name=curr_node_name,
                    phase=phase_name,
                    elapsed_time=elapsed_t,
                    tick_delay=tick_delay,
                    custom_edges=custom_edges,
                    caption=caption,
                    progress_pct=progress_pct,
                    edge_pct=edge_pct,
                    edge_label=cur_edge_label,
                )
            )

        t_prev += w_k

    # YÊU CẦU 2: Bỏ bớt khung hình nếu k_stride > 1 (phát mỗi k tick)
    if k_stride > 1 and len(all_ticks) > 1:
        filtered_ticks: list[AnimationTick] = [all_ticks[0]]
        for idx in range(k_stride, len(all_ticks), k_stride):
            filtered_ticks.append(all_ticks[idx])
        # Luôn đảm bảo khung hình cuối cùng (đích đến) có mặt
        if filtered_ticks[-1] != all_ticks[-1]:
            filtered_ticks.append(all_ticks[-1])
        final_ticks = filtered_ticks
    else:
        final_ticks = all_ticks

    # Cập nhật tick_delay đồng bộ
    for t in final_ticks:
        t.tick_delay = tick_delay

    # Tiền kết xuất chuỗi DOT nếu được yêu cầu & đo thời gian render thực tế
    avg_measured_render = 0.0
    if precompute_dots and drivers is not None:
        from .graph_view import build_dot

        t_render_start = time.perf_counter()
        for t in final_ticks:
            t.dot_string = build_dot(
                edges=graph_edges,
                drivers=drivers,
                queue=queue or [],
                label=node_label_fn,
                nodes=nodes,
                routes=None,
                layout="neato",
                highlight_node=t.node,
                custom_edges=t.custom_edges,
            )
        t_render_total = time.perf_counter() - t_render_start
        avg_measured_render = t_render_total / max(1, len(final_ticks))
    return AnimationTimeline(
        final_ticks,
        avg_render_time=avg_measured_render,
        schedule=schedule,
    )


def build_animation_timeline(
    pickup_path: list[str] | None,
    ride_path: list[str] | None,
    graph_edges: Iterable[tuple[str, str, float]],
    node_label_fn: Callable[[str], str],
    speed_mult: float = 2.0,
    avg_render_time: float = 0.0,
) -> list[AnimationTick]:
    """Tương thích ngược: chuyển tiếp tới build_animation_ticks."""
    return build_animation_ticks(
        pickup_path=pickup_path,
        ride_path=ride_path,
        graph_edges=graph_edges,
        node_label_fn=node_label_fn,
        speed_mult=speed_mult,
        avg_render_time=avg_render_time,
    )


def render_animation_status_badge(status: str) -> str:
    """Tạo mã HTML cho badge trạng thái animation (Đang phát / Tạm dừng / Hoàn tất)."""
    if status == ANIM_STATUS_PLAYING:
        return (
            '<span class="anim-status-badge anim-status-playing">'
            '<span class="anim-pulse-dot"></span> ● Đang phát'
            '</span>'
        )
    elif status == ANIM_STATUS_COMPLETED:
        return (
            '<span class="anim-status-badge anim-status-completed">'
            '✔ Hoàn tất'
            '</span>'
        )
    else:  # paused
        return (
            '<span class="anim-status-badge anim-status-paused">'
            '⏸ Tạm dừng'
            '</span>'
        )


def render_animation_badge(tick: AnimationTick, status: str = ANIM_STATUS_PAUSED) -> None:
    """Hiển thị huy hiệu trạng thái bước phát lại đẹp mắt, tương phản cao kèm badge trạng thái động."""
    status_badge_html = render_animation_status_badge(status)
    safe_caption = html.escape(tick.caption)
    safe_node = html.escape(tick.node_name)
    safe_time = html.escape(f"T+{tick.elapsed_time:.1f} phút")
    safe_phase = html.escape(tick.phase)
    phase_cls = "badge-assigned" if "Đón" in tick.phase else "badge-completed"
    tick_info = f"Tick {tick.tick_index}/{tick.total_ticks}" if tick.total_ticks > 0 else "Tick 0/0"
    edge_info = f"{html.escape(tick.edge_label)} ({round(tick.edge_pct)}%)" if tick.edge_label else ""

    badge_html = f"""
    <div class="anim-step-badge">
        {status_badge_html}
        <span class="anim-sep">•</span>
        <span class="anim-step-count">⏱️ <b>{html.escape(tick_info)}</b></span>
        <span class="anim-sep">•</span>
        <span class="anim-step-node">📍 <b>{safe_node}</b></span>
        <span class="anim-sep">•</span>
        <span class="anim-step-time">🕒 <b>{safe_time}</b></span>
        <span class="badge-status {phase_cls}" style="margin-left: 0.35rem;">{safe_phase}</span>
        {"<span class='anim-sep'>•</span> <span style='font-size: 0.82rem; color: #475569; font-weight: 500;'>" + edge_info + "</span>" if edge_info else ""}
    </div>
    """
    st.markdown(badge_html, unsafe_allow_html=True)

