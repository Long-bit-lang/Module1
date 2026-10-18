"""Đo visited_count và runtime_ms của A1, A2.

Chạy từ thư mục gốc repo:
    PYTHONPATH=src uv run python tests/benchmark_algorithms.py
Windows PowerShell:
    $env:PYTHONPATH="src"; uv run python tests/benchmark_algorithms.py
"""
from __future__ import annotations

import platform
import random
import statistics
import sys

from core.road_graph import RoadGraph
from core.strategies import DijkstraPerDriver, ReverseDijkstra

# ---- Cấu hình đồ thị ngẫu nhiên ----
NUM_NODES = 1000
NUM_EDGES = 1500
NUM_DRIVERS = 250
SEEDS = (7, 42, 2026)
TRIALS_PER_SEED = 50

# ---- Giá trị kỳ vọng của ca tài liệu ----
DOC_EXPECTED = {"driver_id": "D23", "eta": 15.0, "A1_visited": 3974, "A2_visited": 27}
DOC_REPEATS = 40


def build_random_case(rng: random.Random, nodes: list[str]):
    graph = RoadGraph()
    for node in nodes:
        graph.add_node(node)
    for _ in range(NUM_EDGES):
        u, v = rng.sample(nodes, 2)
        graph.add_edge(u, v, rng.randint(0, 20))
    drivers = {f"D{i}": rng.choice(nodes) for i in range(1, NUM_DRIVERS + 1)}
    pickup = rng.choice(nodes)
    return graph, pickup, drivers


def build_document_case():
    graph = RoadGraph()
    for i in range(200):
        graph.add_node(f"N{i:03d}")
    for i in range(200):
        u = f"N{i:03d}"
        graph.add_edge(u, f"N{(i + 1) % 200:03d}", 1 + i % 5)
        graph.add_edge(u, f"N{(i + 7) % 200:03d}", 3 + i % 7)
        graph.add_edge(u, f"N{(i + 19) % 200:03d}", 2 + i % 11)
    drivers = {f"D{d:02d}": f"N{(d * 7) % 200:03d}" for d in range(25)}
    return graph, "N199", drivers


def print_environment() -> None:
    print("## Môi trường và dữ liệu thử nghiệm")
    print()
    print(f"- Hệ điều hành: {platform.system()} {platform.release()} ({platform.version()})")
    print(f"- Python: {platform.python_version()}, {platform.architecture()[0]}")
    print(f"- CPU: {platform.processor() or platform.machine()}")
    print()


def print_random_section() -> None:
    nodes = [f"N{i}" for i in range(1, NUM_NODES + 1)]
    strategies = {"A1": DijkstraPerDriver(), "A2": ReverseDijkstra()}
    visited = {k: [] for k in strategies}
    runtime = {k: [] for k in strategies}
    total = routed = mismatches = 0

    for seed in SEEDS:
        rng = random.Random(seed)
        for _ in range(TRIALS_PER_SEED):
            graph, pickup, drivers = build_random_case(rng, nodes)
            results = {k: s.find_driver(graph, pickup, drivers) for k, s in strategies.items()}
            a1, a2 = results["A1"], results["A2"]

            total += 1
            routed += a1.driver_id is not None
            mismatches += (a1.driver_id, a1.eta) != (a2.driver_id, a2.eta)
            for k, r in results.items():
                visited[k].append(r.visited_count)
                runtime[k].append(r.runtime_ms)

    print("## Benchmark đồ thị ngẫu nhiên")
    print()
    print(f"- Đồ thị: {NUM_NODES} đỉnh, {NUM_EDGES} cạnh, {NUM_DRIVERS} tài xế, "
          f"{total} ca (seed {SEEDS})")
    print(f"- Ca có đường đi: {routed}/{total}")
    print(f"- Ca A1 ≠ A2: {mismatches}")
    print()
    print("| Thuật toán | visited_count TB | visited_count trung vị | runtime_ms TB | runtime_ms trung vị |")
    print("|---|---|---|---|---|")
    for k in strategies:
        print(
            f"| {k} | {statistics.mean(visited[k]):.1f} | {statistics.median(visited[k]):.1f} "
            f"| {statistics.mean(runtime[k]):.3f} | {statistics.median(runtime[k]):.3f} |"
        )
    print()


def print_document_section() -> None:
    graph, pickup, drivers = build_document_case()
    strategies = [
        ("A1 - Dijkstra từng tài xế", DijkstraPerDriver()),
        ("A2 - Dijkstra đảo chiều", ReverseDijkstra()),
    ]

    print("## Benchmark ca tài liệu (200 đỉnh, 25 tài xế)")
    print()
    print(f"- Đồ thị: {len(graph.nodes())} đỉnh, {len(graph.edges())} cạnh có hướng, "
          f"không có trọng số âm")
    print(f"- Tài xế: {len(drivers)} tài xế, điểm đón {pickup}")
    print(f"- Mỗi chiến lược chạy {DOC_REPEATS} lần, thời gian là trung vị của runtime_ms; "
          f"visited_count và driver lấy từ lần chạy đầu")
    print()
    print("| Chiến lược | driver_id | ETA (phút) | visited_count | Lần đầu (cold, ms) | Trung vị warm (ms) |")
    print("|---|---:|---:|---:|---:|---:|")

    all_match = True
    for name, strategy in strategies:
        runs = [strategy.find_driver(graph, pickup, drivers) for _ in range(DOC_REPEATS)]
        rep = runs[0]
        cold_ms = rep.runtime_ms
        warm_median_ms = statistics.median(r.runtime_ms for r in runs[1:])
        print(f"| {name} | {rep.driver_id} | {rep.eta:.1f} | {rep.visited_count} | {cold_ms:.4f} | {warm_median_ms:.4f} |")

        expected_visited = DOC_EXPECTED["A1_visited" if name.startswith("A1") else "A2_visited"]
        all_match &= (
            rep.driver_id == DOC_EXPECTED["driver_id"]
            and rep.eta == DOC_EXPECTED["eta"]
            and rep.visited_count == expected_visited
        )

    print()
    print(f"- Khớp kỳ vọng tài liệu: {'Có' if all_match else 'Không khớp'}")




def main() -> None:
    print("# Kiểm thử benchmark A1/A2")
    print()
    print_environment()
    print_document_section()
    print_random_section()


if __name__ == "__main__":
    main()