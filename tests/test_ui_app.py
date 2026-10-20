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
    # A1: Điều hướng bằng st.sidebar radio key="main_nav" thay cho st.tabs
    assert app.sidebar.radio(key="main_nav").options == [
        "Quản lý dữ liệu", "Điều phối chuyến", "Đối chuẩn thuật toán"
    ]
    assert app.session_state["main_nav"] == "Quản lý dữ liệu"


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
    app.sidebar.radio(key="main_nav").set_value("Đối chuẩn thuật toán").run()
    assert app.session_state["main_nav"] == "Đối chuẩn thuật toán"
    app.button(key="btn_bench").click().run()
    assert not app.exception
    assert any("cùng tài xế và ETA" in s.value for s in app.success)


def test_benchmark_document_case_runs_and_shows_speedup(app):
    app.sidebar.radio(key="main_nav").set_value("Đối chuẩn thuật toán").run()
    assert app.session_state["main_nav"] == "Đối chuẩn thuật toán"
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
    # Ban đầu trang mặc định là "Quản lý dữ liệu"
    assert app.session_state["main_nav"] == "Quản lý dữ liệu"

    # Người dùng chuyển trang sang "Điều phối chuyến" bằng st.sidebar.radio key="main_nav"
    app.sidebar.radio(key="main_nav").set_value("Điều phối chuyến").run()
    assert app.session_state["main_nav"] == "Điều phối chuyến"

    # Người dùng tương tác với widget bên trong Action Panel (đổi điểm trả khách)
    _pick(app, "req_dropoff", "N4")
    app.run()

    # Trang đang chọn vẫn là "Điều phối chuyến", radio không bị reset khi rerun
    assert app.session_state["main_nav"] == "Điều phối chuyến"


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
    assert app.session_state["main_nav"] == "Quản lý dữ liệu"

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
    assert app.session_state["main_nav"] == "Quản lý dữ liệu"

    # Nhấn thu nhỏ liên tục để chạm sàn 50%
    while app.session_state["map_data_zoom_level"] > 50:
        app.button(key="map_data_zoom_out").click().run()
    assert app.session_state["map_data_zoom_level"] == 50

    # Bấm thêm lần nữa -> không tụt dưới 50%
    app.button(key="map_data_zoom_out").click().run()
    assert app.session_state["map_data_zoom_level"] == 50
    assert app.session_state["main_nav"] == "Quản lý dữ liệu"


def test_map_dispatch_zoom_controls_and_tab_persistence(app):
    """Kiểm tra điều khiển zoom trên tab Điều phối chuyến và xác nhận không bị reset tab."""
    # Chuyển trang sang Điều phối chuyến
    app.sidebar.radio(key="main_nav").set_value("Điều phối chuyến").run()
    assert app.session_state["main_nav"] == "Điều phối chuyến"
    assert app.session_state.get("map_dispatch_zoom_level") == 100

    # Phóng to bản đồ điều phối
    app.button(key="map_dispatch_zoom_in").click().run()
    assert not app.exception
    assert app.session_state["map_dispatch_zoom_level"] == 120
    # Trang vẫn giữ nguyên là Điều phối chuyến, không bị văng về Quản lý dữ liệu
    assert app.session_state["main_nav"] == "Điều phối chuyến"

    # Vừa khung
    app.button(key="map_dispatch_zoom_reset").click().run()
    assert not app.exception
    assert app.session_state["map_dispatch_zoom_level"] == 100
    assert app.session_state["main_nav"] == "Điều phối chuyến"

    # Thu nhỏ
    app.button(key="map_dispatch_zoom_out").click().run()
    assert not app.exception
    assert app.session_state["map_dispatch_zoom_level"] == 80
    assert app.session_state["main_nav"] == "Điều phối chuyến"


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

    # 2. Chuyển trang sang 'Điều phối chuyến' -> kiểm tra key 'map_dispatch_canvas'
    app.sidebar.radio(key="main_nav").set_value("Điều phối chuyến").run()
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


def test_page_switch_preserves_dispatcher_and_undo(app):
    """Ràng buộc 5: Đổi trang không làm mất trạng thái dispatcher và ngăn xếp Undo/Redo."""
    # 1. Tạo yêu cầu và điều phối chuyến trên Action panel
    _pick(app, "req_pickup", "N3")
    _pick(app, "req_dropoff", "N7")
    app.button(key="btn_submit").click().run()
    app.button(key="btn_dispatch").click().run()
    assert _d(app).can_undo()
    assert len(_d(app).trips_snapshot()) == 1

    # 2. Chuyển sang trang "Quản lý dữ liệu"
    app.sidebar.radio(key="main_nav").set_value("Quản lý dữ liệu").run()
    assert app.session_state["main_nav"] == "Quản lý dữ liệu"
    assert _d(app).can_undo()
    assert len(_d(app).trips_snapshot()) == 1

    # 3. Chuyển sang trang "Đối chuẩn thuật toán"
    app.sidebar.radio(key="main_nav").set_value("Đối chuẩn thuật toán").run()
    assert app.session_state["main_nav"] == "Đối chuẩn thuật toán"
    assert _d(app).can_undo()

    # 4. Chuyển lại "Điều phối chuyến" và thực hiện Undo thành công
    app.sidebar.radio(key="main_nav").set_value("Điều phối chuyến").run()
    assert app.session_state["main_nav"] == "Điều phối chuyến"
    assert _d(app).can_undo()
    app.button(key="btn_undo").click().run()
    assert not _d(app).can_undo()
    assert len(_d(app).trips_snapshot()) == 0
    assert len(_d(app).queue_snapshot()) == 1


def test_panel_toggle_changes_panel_open(app):
    """Ràng buộc 5: Nhấn nút nổi btn_toggle_panel làm đổi trạng thái session_state['panel_open']."""
    assert app.session_state.get("panel_open", True) is True
    # Nhấn toggle để đóng panel
    app.button(key="btn_toggle_panel").click().run()
    assert app.session_state["panel_open"] is False

    # Nhấn toggle lần nữa để mở lại panel
    app.button(key="btn_toggle_panel").click().run()
    assert app.session_state["panel_open"] is True


def test_success_notification_persists_after_one_rerun(app):
    """Ràng buộc 5: Thông báo success còn tồn tại sau một rerun trong trung tâm thông báo."""
    # 1. Thực hiện thao tác tạo yêu cầu đặt xe thành công qua widget
    _pick(app, "req_pickup", "N3")
    _pick(app, "req_dropoff", "N7")
    app.button(key="btn_submit").click().run()

    # Kiểm tra ngay sau thao tác: có thông báo success đang active
    notifs = app.session_state["notifications"]
    assert any(n["kind"] == "success" and "Đã tạo yêu cầu" in n["message"] and n["active"] for n in notifs)

    # 2. Sau thêm một lần rerun nữa (chưa quá 8s), thông báo success vẫn tồn tại và active
    app.run()
    notifs_after = app.session_state["notifications"]
    assert any(n["kind"] == "success" and "Đã tạo yêu cầu" in n["message"] and n["active"] for n in notifs_after)


def test_table_filtering_reduces_rows_and_reset_restores(app):
    """Ràng buộc 5: Bộ lọc làm giảm số dòng hiển thị và nút xóa lọc khôi phục lại dữ liệu ban đầu."""
    # 1. Kiểm tra bộ lọc trên bảng Tài xế (Quản lý dữ liệu)
    assert app.session_state["main_nav"] == "Quản lý dữ liệu"
    drivers_df = app.dataframe[1].value
    initial_driver_count = len(drivers_df)
    assert initial_driver_count == 3

    # Lọc tài xế theo tên/ID "D1" -> bảng giảm còn 1 dòng
    app.text_input(key="flt_drivers_search").input("D1").run()
    assert not app.exception
    assert len(app.dataframe[1].value) == 1
    assert app.dataframe[1].value.iloc[0]["ID"] == "D1"

    # Nhấn "Xóa bộ lọc" -> khôi phục lại 3 tài xế
    app.button(key="flt_drivers_reset").click().run()
    assert not app.exception
    assert len(app.dataframe[1].value) == initial_driver_count
    assert app.session_state["flt_drivers_search"] == ""

    # 2. Kiểm tra bộ lọc trên bảng Tuyến đường (Quản lý dữ liệu)
    edges_df = app.dataframe[0].value
    initial_edge_count = len(edges_df)
    assert initial_edge_count == 21

    app.text_input(key="flt_edges_search").input("Cầu Rồng").run()
    assert not app.exception
    assert len(app.dataframe[0].value) < initial_edge_count
    assert len(app.dataframe[0].value) == 6

    app.button(key="flt_edges_reset").click().run()
    assert not app.exception
    assert len(app.dataframe[0].value) == initial_edge_count

    # 3. Kiểm tra bộ lọc Hàng đợi yêu cầu (Điều phối chuyến)
    app.sidebar.radio(key="main_nav").set_value("Điều phối chuyến").run()

    # Tạo 2 yêu cầu đặt xe
    _pick(app, "req_pickup", "N3")
    _pick(app, "req_dropoff", "N7")
    app.button(key="btn_submit").click().run()

    _pick(app, "req_pickup", "N4")
    _pick(app, "req_dropoff", "N6")
    app.button(key="btn_submit").click().run()

    assert len(app.dataframe[0].value) == 2

    # Lọc theo địa danh "Cầu Rồng" (N3)
    app.text_input(key="flt_queue_search").input("Cầu Rồng").run()
    assert not app.exception
    assert len(app.dataframe[0].value) == 1

    # Xóa bộ lọc hàng đợi
    app.button(key="flt_queue_reset").click().run()
    assert not app.exception
    assert len(app.dataframe[0].value) == 2

    # 4. Kiểm tra bộ lọc Lịch sử chuyến xe (Điều phối chuyến)
    # Ghép 2 chuyến
    app.button(key="btn_dispatch").click().run()
    app.button(key="btn_dispatch").click().run()
    assert len(_d(app).trips_snapshot()) == 2

    # Lọc chuyến theo mã tìm kiếm
    app.text_input(key="flt_trips_search").input("T1").run()
    assert not app.exception
    # Kiểm tra nút xóa lọc chuyến
    app.button(key="flt_trips_reset").click().run()
    assert not app.exception
    assert app.session_state["flt_trips_search"] == ""







