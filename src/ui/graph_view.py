"""TV5 - Bản đồ Graphviz: trạng thái tài xế, điểm đón đang chờ, lộ trình tô sáng."""
from __future__ import annotations

from typing import Callable, Iterable

from .constants import FREE


def _q(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"')


def build_dot(edges, drivers: dict, queue, label: Callable[[str], str],
              nodes: Iterable[str], routes: list[tuple[list[str], str, str]] | None = None) -> str:
    """routes: [(path, màu, nét)] với nét là solid hoặc dashed."""
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

    lines = [
        "digraph G {", "  rankdir=LR; bgcolor=\"transparent\";",
        '  node [fontname="Helvetica", fontsize=11, shape=box, style="rounded,filled", margin="0.2,0.1"];',
        '  edge [fontname="Helvetica", fontsize=10, arrowsize=0.8];',
    ]
    for n in nodes:
        free = [d.name for d in at.get(n, []) if d.status == FREE]
        busy = [d.name for d in at.get(n, []) if d.status != FREE]
        parts = [label(n)]
        if free:
            parts.append("Xe rảnh: " + ", ".join(free))
        if busy:
            parts.append("Xe bận: " + ", ".join(busy))
        if n in waiting:
            parts.append("Chờ đón: " + ", ".join(waiting[n]))
        fill, border, pen = "#f8fafc", "#cbd5e1", 1.2
        if busy:
            fill, border, pen = "#fef2f2", "#ef4444", 2.0
        if free:
            fill, border, pen = "#ecfdf5", "#10b981", 2.0
        if n in waiting:
            border, pen = "#f59e0b", 3.5
        text = "\\n".join(_q(p) for p in parts)
        lines.append(f'  "{_q(n)}" [label="{text}", fillcolor="{fill}", color="{border}", penwidth={pen}];')
    for u, v, w in edges:
        color, style = hot.get((u, v), ("#64748b", "solid"))
        pen = 3.5 if (u, v) in hot else 1.3
        lines.append(f'  "{_q(u)}" -> "{_q(v)}" [label="{w:g}p", color="{color}", '
                     f'fontcolor="{color}", style={style}, penwidth={pen}];')
    lines.append("}")
    return "\n".join(lines)
