"""TV5 - Các thành phần giao diện tái sử dụng (Reusable UI Components).

Mọi chuỗi động/dữ liệu từ người dùng hoặc hệ thống đưa vào HTML đều qua `html.escape`.
Bảo đảm độ tương phản theo chuẩn WCAG AA và tương thích theme sáng mặc định.
"""
from __future__ import annotations

from dataclasses import dataclass
import html
import re
from typing import Callable, Iterable

import streamlit as st

from .constants import ASSIGNED, BUSY, COMPLETED, FREE, QUEUED, status_label


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
class AnimationStep:
    """Đại diện cho một khung hình trong animation phát lại lộ trình."""

    step_index: int
    total_steps: int
    node: str
    node_name: str
    phase: str
    elapsed_time: float
    step_delay: float
    custom_edges: dict[tuple[str, str], tuple[str, str, float]]
    caption: str


def build_animation_timeline(
    pickup_path: list[str] | None,
    ride_path: list[str] | None,
    graph_edges: Iterable[tuple[str, str, float]],
    node_label_fn: Callable[[str], str],
    speed_mult: float = 1.0,
) -> list[AnimationStep]:
    """Tạo chuỗi các khung hình (timeline) cho animation phát lại lộ trình.

    Quy tắc:
    - Chặng 1 (Đón khách): #16a34a (xanh lá), chặng đã đi nét liền penwidth 3.5, sắp tới #86efac nét đứt mờ penwidth 2.0.
    - Chặng 2 (Chở khách): #ea580c (cam), chặng đã đi nét liền penwidth 3.5, sắp tới #fdba74 nét đứt mờ penwidth 2.0.
    - Đỉnh hiện tại: tô nổi bật vàng sáng (#fef08a, viền #2563eb, penwidth 4.0).
    - Thời gian ảo: cộng dồn trọng số cạnh (T+xx phút).
    - Thời gian trễ mỗi bước: tỉ lệ theo trọng số cạnh kế tiếp, giới hạn [0.3, 1.2] giây.
    """
    p_path = [str(x) for x in (pickup_path or [])]
    r_path = [str(x) for x in (ride_path or [])]

    if not p_path and not r_path:
        return []

    # Ghép 2 chặng: tránh lặp đỉnh tiếp giáp nếu điểm kết thúc chặng đón trùng điểm bắt đầu chặng chở
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

    route_edges: list[tuple[str, str]] = []
    for k in range(len(full_nodes) - 1):
        route_edges.append((full_nodes[k], full_nodes[k + 1]))

    weights: dict[tuple[str, str], float] = {
        (u, v): float(w) for u, v, w in graph_edges
    }

    total_steps = len(full_nodes)
    if total_steps == 1:
        single_node = full_nodes[0]
        lbl = node_label_fn(single_node)
        return [
            AnimationStep(
                step_index=0,
                total_steps=1,
                node=single_node,
                node_name=lbl,
                phase="Điểm đón khách" if p_path else "Điểm trả khách",
                elapsed_time=0.0,
                step_delay=0.5,
                custom_edges={},
                caption=f"Bước 1/1 • {lbl} • T+0 phút",
            )
        ]

    # Tính thời gian ảo tích lũy tại từng đỉnh
    elapsed_times: list[float] = [0.0]
    running_t = 0.0
    for edge in route_edges:
        w = weights.get(edge, 1.0)
        running_t += w
        elapsed_times.append(running_t)

    steps: list[AnimationStep] = []
    speed = max(0.1, float(speed_mult))

    for i, curr_node in enumerate(full_nodes):
        # Xác định giai đoạn (phase)
        if num_pickup_edges > 0:
            if i < num_pickup_edges:
                phase = "Đón khách"
            elif i == num_pickup_edges:
                phase = "Điểm đón khách" if num_ride_edges > 0 else "Đón khách"
            else:
                phase = "Chở khách"
        else:
            phase = "Chở khách"

        # Tính độ trễ cho bước này (dựa trên cạnh chuẩn bị đi nếu i < M - 1)
        if i < len(route_edges):
            next_edge_w = weights.get(route_edges[i], 1.0)
            raw_delay = (0.3 + 0.07 * next_edge_w) / speed
            step_delay = max(0.3, min(1.2, raw_delay))
        else:
            step_delay = 0.5

        # Xác định kiểu cạnh cho khung hình này
        # Chặng đã đi (k < i): nét liền (solid), penwidth=3.5
        # Chặng sắp tới (k >= i): nét đứt mờ (dashed), penwidth=2.0
        custom_edges: dict[tuple[str, str], tuple[str, str, float]] = {}
        for k, (u, v) in enumerate(route_edges):
            is_pickup = k < num_pickup_edges
            if is_pickup:
                if k < i:
                    custom_edges[(u, v)] = ("#16a34a", "solid", 3.5)
                else:
                    custom_edges[(u, v)] = ("#86efac", "dashed", 2.0)
            else:
                if k < i:
                    custom_edges[(u, v)] = ("#ea580c", "solid", 3.5)
                else:
                    custom_edges[(u, v)] = ("#fdba74", "dashed", 2.0)

        t_min = elapsed_times[i]
        t_str = f"T+{round(t_min, 1):g} phút" if t_min > 0 else "T+0 phút"
        node_name = node_label_fn(curr_node)
        caption = f"Bước {i + 1}/{total_steps} • {node_name} • {t_str}"

        steps.append(
            AnimationStep(
                step_index=i,
                total_steps=total_steps,
                node=curr_node,
                node_name=node_name,
                phase=phase,
                elapsed_time=t_min,
                step_delay=step_delay,
                custom_edges=custom_edges,
                caption=caption,
            )
        )

    return steps


def render_animation_badge(step: AnimationStep) -> None:
    """Hiển thị huy hiệu trạng thái bước phát lại đẹp mắt, tương phản cao."""
    safe_step = html.escape(f"Bước {step.step_index + 1}/{step.total_steps}")
    safe_node = html.escape(step.node_name)
    t_min = step.elapsed_time
    t_str = f"T+{round(t_min, 1):g} phút" if t_min > 0 else "T+0 phút"
    safe_time = html.escape(t_str)
    safe_phase = html.escape(step.phase)

    phase_cls = "badge-assigned" if "Đón" in step.phase else "badge-completed"

    badge_html = f"""
    <div class="anim-step-badge">
        <span class="anim-step-count">🚩 <b>{safe_step}</b></span>
        <span class="anim-sep">•</span>
        <span class="anim-step-node">📍 <b>{safe_node}</b></span>
        <span class="anim-sep">•</span>
        <span class="anim-step-time">⏱️ <b>{safe_time}</b></span>
        <span class="badge-status {phase_cls}" style="margin-left: 0.5rem;">{safe_phase}</span>
    </div>
    """
    st.markdown(badge_html, unsafe_allow_html=True)

