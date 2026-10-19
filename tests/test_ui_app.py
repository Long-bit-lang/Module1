"""TV5 - Kiểm thử giao diện bằng Streamlit AppTest (chạy trên backend mock, không ghi đĩa)."""
import os
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parents[1] / "src" / "app.py")


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setenv("RIDE_DISPATCH_BACKEND", "mock")
    return AppTest.from_file(APP, default_timeout=30).run()


def _pick(at, key, item_id):
    """Chọn mục trong selectbox theo ID (nhãn hiển thị có dạng "N3 – Cầu Rồng")."""
    box = at.selectbox(key=key)
    label = next(o for o in box.options if o.split(" – ")[0] == item_id)
    box.select(label)


def _d(at):
    return at.session_state["dispatcher"]


def test_app_starts_without_exception(app):
    assert not app.exception
    assert [t.label for t in app.tabs] == [
        "Quản lý dữ liệu", "Điều phối chuyến", "Đối chuẩn thuật toán"]


def test_full_flow_submit_dispatch_undo_redo_complete(app):
    # Tạo yêu cầu qua giao diện
    _pick(app, "req_pickup", "N3")
    _pick(app, "req_dropoff", "N7")
    app.button(key="btn_submit").click().run()
    assert len(_d(app).queue_snapshot()) == 1

    # Điều phối -> có chuyến, tài xế bận
    app.button(key="btn_dispatch").click().run()
    assert not app.exception
    assert len(_d(app).trips_snapshot()) == 1 and len(_d(app).queue_snapshot()) == 0
    assert app.session_state["storage"].save_count >= 2  # tự lưu sau mỗi thao tác

    # Undo -> yêu cầu về đầu hàng, tài xế rảnh; Redo -> ngược lại
    app.button(key="btn_undo").click().run()
    assert len(_d(app).trips_snapshot()) == 0 and len(_d(app).queue_snapshot()) == 1
    app.button(key="btn_redo").click().run()
    trip = _d(app).trips_snapshot()[0]

    # Hoàn thành chuyến
    app.button(key=f"btn_complete_{trip.id}").click().run()
    assert _d(app).trips_snapshot()[0].status == "completed"


def test_dispatcher_survives_rerun_so_undo_history_is_kept(app):
    app.button(key="btn_submit").click().run()
    app.button(key="btn_dispatch").click().run()
    assert _d(app).can_undo()
    app.run()  # rerun thuần túy không được làm mất lịch sử Undo
    assert _d(app).can_undo()


def test_same_pickup_dropoff_shows_error(app):
    _pick(app, "req_pickup", "N2")
    _pick(app, "req_dropoff", "N2")
    app.button(key="btn_submit").click().run()
    assert any("khác nhau" in e.value for e in app.error)
    assert len(_d(app).queue_snapshot()) == 0


def test_busy_driver_cannot_be_removed(app):
    app.button(key="btn_submit").click().run()
    app.button(key="btn_dispatch").click().run()
    busy = next(d for d in _d(app).drivers_snapshot().values() if d.status == "busy")
    _pick(app, "edit_driver", busy.id)
    btn = app.button(key="btn_remove_driver")
    assert btn.disabled
    assert busy.id in _d(app).drivers_snapshot()


def test_benchmark_tab_runs_and_strategies_agree(app):
    app.button(key="btn_bench").click().run()
    assert not app.exception
    assert any("cùng tài xế và ETA" in s.value for s in app.success)


def test_benchmark_document_case_runs_and_shows_speedup(app):
    app.button(key="btn_run_doc_bench").click().run()
    assert not app.exception
    assert any("Giảm số đỉnh duyệt" in s.value for s in app.success)



@pytest.fixture
def real_app(monkeypatch, tmp_path):
    monkeypatch.setenv("RIDE_DISPATCH_BACKEND", "real")
    monkeypatch.setenv("RIDE_DISPATCH_RUNTIME_DIR", str(tmp_path))
    return AppTest.from_file(APP, default_timeout=30).run()


def test_real_backend_dispatch_persists_and_tiebreaks(real_app, tmp_path):
    assert not real_app.exception
    real_app.button(key="btn_dispatch").click().run()  # R3: pickup N4, D1 và D2 cùng ETA 6
    trip = _d(real_app).trips_snapshot()[-1]
    assert (trip.driver_id, trip.eta) == ("D1", 6.0)  # hòa ETA thì chọn ID nhỏ nhất
    assert '"T3"' in (tmp_path / "trips.json").read_text(encoding="utf-8")


def test_tab_selection_persists_on_widget_interaction(app):
    # Ban đầu tab mặc định là "Quản lý dữ liệu"
    assert app.session_state["active_tab"] == "Quản lý dữ liệu"

    # Người dùng chuyển tab bằng cách chọn "Điều phối chuyến" trên widget st.tabs (key="main_tabs")
    app.session_state["main_tabs"] = "Điều phối chuyến"
    app.run()
    assert app.session_state["active_tab"] == "Điều phối chuyến"

    # Người dùng tương tác với widget bên trong tab (đổi điểm trả khách)
    _pick(app, "req_dropoff", "N4")
    app.run()

    # Tab đang chọn vẫn là "Điều phối chuyến", không bị reset về tab đầu tiên "Quản lý dữ liệu"
    assert app.session_state["active_tab"] == "Điều phối chuyến"
    assert app.session_state["main_tabs"] == "Điều phối chuyến"


def test_reset_to_seed_restores_data(real_app, tmp_path):
    assert not real_app.exception
    # 1. Điều phối một chuyến để làm thay đổi dữ liệu runtime trên đĩa
    real_app.button(key="btn_dispatch").click().run()
    assert '"T3"' in (tmp_path / "trips.json").read_text(encoding="utf-8")

    # 2. Nhấn nút Reset về dữ liệu mẫu (Seed) và xác nhận trong dialog
    real_app.button(key="btn_reset_seed").click().run()
    real_app.button(key="btn_confirm_reset_seed").click().run()
    assert not real_app.exception

    # 3. File trips.json trên đĩa runtime được phục hồi về nguyên bản (chỉ có T1, T2 từ seed, không còn T3)
    content_trips = (tmp_path / "trips.json").read_text(encoding="utf-8")
    assert '"T3"' not in content_trips
    assert len(_d(real_app).trips_snapshot()) == 2


def test_map_data_zoom_buttons_and_limits(app):
    """Kiểm tra nút phóng to/thu nhỏ/vừa khung trên bản đồ dữ liệu và giới hạn 50% - 300%."""
    assert app.session_state.get("map_data_zoom_level") == 100

    # Phóng to (+20%)
    app.button(key="map_data_zoom_in").click().run()
    assert not app.exception
    assert app.session_state["map_data_zoom_level"] == 120
    assert app.session_state["active_tab"] == "Quản lý dữ liệu"

    # Nhấn phóng to liên tục để chạm trần 300%
    while app.session_state["map_data_zoom_level"] < 300:
        app.button(key="map_data_zoom_in").click().run()
    assert app.session_state["map_data_zoom_level"] == 300

    # Bấm thêm lần nữa -> không vượt quá 300%
    app.button(key="map_data_zoom_in").click().run()
    assert app.session_state["map_data_zoom_level"] == 300

    # Đặt lại về vừa khung (100%)
    app.button(key="map_data_zoom_reset").click().run()
    assert not app.exception
    assert app.session_state["map_data_zoom_level"] == 100
    assert app.session_state["active_tab"] == "Quản lý dữ liệu"

    # Nhấn thu nhỏ liên tục để chạm sàn 50%
    while app.session_state["map_data_zoom_level"] > 50:
        app.button(key="map_data_zoom_out").click().run()
    assert app.session_state["map_data_zoom_level"] == 50

    # Bấm thêm lần nữa -> không tụt dưới 50%
    app.button(key="map_data_zoom_out").click().run()
    assert app.session_state["map_data_zoom_level"] == 50
    assert app.session_state["active_tab"] == "Quản lý dữ liệu"


def test_map_dispatch_zoom_controls_and_tab_persistence(app):
    """Kiểm tra điều khiển zoom trên tab Điều phối chuyến và xác nhận không bị reset tab."""
    # Chuyển tab sang Điều phối chuyến
    app.session_state["main_tabs"] = "Điều phối chuyến"
    app.run()
    assert app.session_state["active_tab"] == "Điều phối chuyến"
    assert app.session_state.get("map_dispatch_zoom_level") == 100

    # Phóng to bản đồ điều phối
    app.button(key="map_dispatch_zoom_in").click().run()
    assert not app.exception
    assert app.session_state["map_dispatch_zoom_level"] == 120
    # Tab vẫn giữ nguyên là Điều phối chuyến, không bị văng về Quản lý dữ liệu
    assert app.session_state["active_tab"] == "Điều phối chuyến"

    # Vừa khung
    app.button(key="map_dispatch_zoom_reset").click().run()
    assert not app.exception
    assert app.session_state["map_dispatch_zoom_level"] == 100
    assert app.session_state["active_tab"] == "Điều phối chuyến"

    # Thu nhỏ
    app.button(key="map_dispatch_zoom_out").click().run()
    assert not app.exception
    assert app.session_state["map_dispatch_zoom_level"] == 80
    assert app.session_state["active_tab"] == "Điều phối chuyến"


def test_build_dot_validity_and_escaping():
    """Kiểm thử đơn vị build_dot: cấu trúc DOT hợp lệ, layout, escape ký tự đặc biệt."""
    from src.ui.graph_view import build_dot

    # 1. Kiểm tra cấu trúc DOT cơ bản và layout mặc định (neato)
    edges = [("N1", "N2", 4.5), ("N2", "N3", 2.0)]
    nodes = ["N1", "N2", "N3"]

    class DummyDriver:
        def __init__(self, id, name, node, status):
            self.id = id
            self.name = name
            self.node = node
            self.status = status

    class DummyReq:
        def __init__(self, id, pickup_node):
            self.id = id
            self.pickup_node = pickup_node

    drivers = {"D1": DummyDriver("D1", "Nguyễn Văn An", "N1", "free")}
    queue = [DummyReq("R1", "N2")]

    dot = build_dot(edges, drivers, queue, lambda n: f"{n} – Vị trí {n}", nodes)
    assert dot.startswith("digraph G {")
    assert dot.strip().endswith("}")
    assert 'layout="neato"' in dot
    assert "overlap=false" in dot
    assert "splines=true" in dot
    assert 'sep="+8"' in dot
    assert '"N1"' in dot and '"N2"' in dot and '"N3"' in dot
    assert '"N1" -> "N2"' in dot
    assert '"4.5p"' in dot or '4.5p' in dot
    assert "Rảnh: D1 (An)" in dot
    assert "Chờ: R1" in dot

    # 2. Kiểm tra các layout khác
    dot_fdp = build_dot(edges, drivers, queue, str, nodes, layout="fdp")
    assert 'layout="fdp"' in dot_fdp

    dot_tb = build_dot(edges, drivers, queue, str, nodes, layout="TB")
    assert 'rankdir=TB' in dot_tb

    dot_lr = build_dot(edges, drivers, queue, str, nodes, layout="LR")
    assert 'rankdir=LR' in dot_lr

    # 3. Ký tự đặc biệt và dấu nháy kép (quotes, backslashes, XML brackets)
    special_node = 'N"1" <Special> & \\Backslash'
    d_special = DummyDriver('D"99"', 'Lê "Văn" Cường', special_node, "busy")
    r_special = DummyReq('R"77"', special_node)
    special_edges = [(special_node, "N2", 12.0)]
    special_nodes = [special_node, "N2"]

    dot_escaped = build_dot(
        special_edges,
        {'D"99"': d_special},
        [r_special],
        lambda n: f'Tên "đặc biệt" <{n}>',
        special_nodes,
    )
    assert dot_escaped.startswith("digraph G {")
    # Đỉnh được escape đúng dạng \"
    assert '\\"1\\"' in dot_escaped
    assert '\\\\Backslash' in dot_escaped
    assert 'Tên \\"đặc biệt\\"' in dot_escaped
    assert 'Bận: D\\"99\\" (Cường)' in dot_escaped
    assert 'Chờ: R\\"77\\"' in dot_escaped


def test_map_canvas_containers_and_zoom_levels(app):
    """Kiểm tra khung bản đồ có key {key_prefix}_canvas và không phát sinh lỗi ở 50%, 100%, 300%."""
    # 1. Tab mặc định là 'Quản lý dữ liệu' -> kiểm tra key 'map_data_canvas'
    assert not app.exception
    container_keys = [c.key for c in app.container if c.key]
    assert "map_data_canvas" in container_keys

    # Kiểm tra ở mức zoom 100% (mặc định)
    assert app.session_state["map_data_zoom_level"] == 100
    assert not app.exception

    # Kiểm tra ở mức zoom 50%
    app.session_state["map_data_zoom_level"] = 50
    app.run()
    assert not app.exception
    assert app.session_state["map_data_zoom_level"] == 50
    container_keys = [c.key for c in app.container if c.key]
    assert "map_data_canvas" in container_keys

    # Kiểm tra ở mức zoom 300%
    app.session_state["map_data_zoom_level"] = 300
    app.run()
    assert not app.exception
    assert app.session_state["map_data_zoom_level"] == 300
    container_keys = [c.key for c in app.container if c.key]
    assert "map_data_canvas" in container_keys

    # 2. Chuyển tab sang 'Điều phối chuyến' -> kiểm tra key 'map_dispatch_canvas'
    app.session_state["main_tabs"] = "Điều phối chuyến"
    app.run()
    assert not app.exception
    container_keys = [c.key for c in app.container if c.key]
    assert "map_dispatch_canvas" in container_keys

    # Kiểm tra zoom 50% trên map_dispatch
    app.session_state["map_dispatch_zoom_level"] = 50
    app.run()
    assert not app.exception
    assert app.session_state["map_dispatch_zoom_level"] == 50
    container_keys = [c.key for c in app.container if c.key]
    assert "map_dispatch_canvas" in container_keys

    # Kiểm tra zoom 300% trên map_dispatch
    app.session_state["map_dispatch_zoom_level"] = 300
    app.run()
    assert not app.exception
    assert app.session_state["map_dispatch_zoom_level"] == 300
    container_keys = [c.key for c in app.container if c.key]
    assert "map_dispatch_canvas" in container_keys




