"""TV5 - Các thành phần giao diện tái sử dụng (Reusable UI Components).

Mọi chuỗi động/dữ liệu từ người dùng hoặc hệ thống đưa vào HTML đều qua `html.escape`.
Bảo đảm độ tương phản theo chuẩn WCAG AA và tương thích theme sáng mặc định.
"""
from __future__ import annotations

import html
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
            label_display = safe_label if safe_label.endswith(":") else f"{safe_label}:"
            chips_items.append(
                f'<span class="header-chip">'
                f'<span class="header-chip-label">{label_display}</span> '
                f'<span class="header-chip-val">{safe_val}</span>'
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

