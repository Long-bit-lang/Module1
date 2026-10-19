"""TV5 - Bản đồ Graphviz: trạng thái tài xế, điểm đón đang chờ, lộ trình tô sáng."""
from __future__ import annotations

from typing import Callable, Iterable

from .constants import FREE


def _q(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"')


def _compact_label(raw: str) -> str:
    """Rút gọn nhãn đỉnh: ngắt dòng nếu tên địa danh dài để hộp đỉnh không bị kéo dãn ngang."""
    if " – " in raw:
        nid, name = raw.split(" – ", 1)
        if len(name) > 14 and " " in name:
            words = name.split()
            mid = max(1, len(words) // 2)
            name = " ".join(words[:mid]) + "\n" + " ".join(words[mid:])
        return f"{nid}: {name}"
    return raw


def _short_driver_name(d) -> str:
    """Lấy tên rút gọn của tài xế (mã ID + tên gọi chính) để dòng trạng thái không quá dài."""
    name = getattr(d, "name", str(d))
    did = getattr(d, "id", "")
    parts = name.split()
    last = parts[-1] if parts else name
    return f"{did} ({last})" if did else last


def build_dot(
    edges,
    drivers: dict,
    queue,
    label: Callable[[str], str],
    nodes: Iterable[str],
    routes: list[tuple[list[str], str, str]] | None = None,
    layout: str = "neato",
) -> str:
    """routes: [(path, màu, nét)] với nét là solid hoặc dashed.

    layout: 'neato' (mặc định - bố cục 2D cân đối, lấp đầy khung),
            'fdp' (lực đẩy cân bằng),
            'LR' hoặc 'dot' (luồng ngang phân cấp),
            'TB' (luồng dọc).
    """
    hot: dict[tuple[str, str], tuple[str, str]] = {}
    for path, color, style in routes or []:
        for u, v in zip(path, path[1:]):
            hot[(u, v)] = (color, style)
    at: dict[str, list] = {}
    for d in drivers.values():
        at.setdefault(d.node, []).append(d)
    waiting: dict[str, list[str]] = {}
    for r in queue:
        waiting.setdefault(r.pickup_node, []).append(r.id)

    if layout in ("dot", "LR"):
        graph_attrs = '  layout="dot"; rankdir=LR; bgcolor="transparent";'
    elif layout == "TB":
        graph_attrs = '  layout="dot"; rankdir=TB; nodesep=0.25; ranksep=0.35; bgcolor="transparent";'
    elif layout == "fdp":
        graph_attrs = '  layout="fdp"; overlap=false; splines=true; sep="+8"; bgcolor="transparent";'
    else:  # neato is default
        graph_attrs = '  layout="neato"; overlap=false; splines=true; sep="+8"; bgcolor="transparent";'

    lines = [
        "digraph G {",
        graph_attrs,
        '  node [fontname="Helvetica", fontsize=12, shape=box, style="rounded,filled", margin="0.16,0.09"];',
        '  edge [fontname="Helvetica", fontsize=11, arrowsize=0.85];',
    ]
    for n in nodes:
        free_drivers = [d for d in at.get(n, []) if d.status == FREE]
        busy_drivers = [d for d in at.get(n, []) if d.status != FREE]

        parts = [_compact_label(label(n))]
        if free_drivers:
            parts.append("Rảnh: " + ", ".join(_short_driver_name(d) for d in free_drivers))
        if busy_drivers:
            parts.append("Bận: " + ", ".join(_short_driver_name(d) for d in busy_drivers))
        if n in waiting:
            parts.append("Chờ: " + ", ".join(waiting[n]))

        fill, border, pen = "#f8fafc", "#cbd5e1", 1.2
        if busy_drivers:
            fill, border, pen = "#fef2f2", "#ef4444", 2.0
        if free_drivers:
            fill, border, pen = "#ecfdf5", "#10b981", 2.0
        if n in waiting:
            border, pen = "#f59e0b", 3.5

        lines_of_node = []
        for p in parts:
            lines_of_node.extend(p.split("\n"))
        text = "\\n".join(_q(sub) for sub in lines_of_node)
        lines.append(f'  "{_q(n)}" [label="{text}", fillcolor="{fill}", color="{border}", penwidth={pen}];')

    for u, v, w in edges:
        color, style = hot.get((u, v), ("#64748b", "solid"))
        pen = 3.5 if (u, v) in hot else 1.3
        lines.append(f'  "{_q(u)}" -> "{_q(v)}" [label="{w:g}p", color="{color}", '
                     f'fontcolor="{color}", style={style}, penwidth={pen}];')
    lines.append("}")
    return "\n".join(lines)

