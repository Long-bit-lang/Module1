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
        "Điều phối chuyến", "Quản lý dữ liệu", "Đối chuẩn thuật toán"
    ]
    assert app.session_state["main_nav"] == "Điều phối chuyến"


def test_full_flow_submit_dispatch_cancel_and_complete(app):
    # 1. Tạo yêu cầu qua giao diện
    _pick(app, "req_pickup", "N3")
    _pick(app, "req_dropoff", "N7")
    app.button(key="btn_submit").click().run()
    assert len(_d(app).queue_snapshot()) == 1

    # 2. Điều phối -> có chuyến, tài xế bận
    app.button(key="btn_dispatch").click().run()
    assert not app.exception
    assert len(_d(app).trips_snapshot()) == 1 and len(_d(app).queue_snapshot()) == 0
    assert app.session_state["storage"].save_count >= 2  # tự lưu sau mỗi thao tác

    trip = _d(app).trips_snapshot()[0]
    # Xác nhận không có nút Undo/Redo nào
    assert not any(b.key in ("btn_undo", "btn_redo") for b in app.button)

    # 3. Hủy chuyến qua giao diện với bước xác nhận
    app.button(key=f"btn_cancel_trip_{trip.id}").click().run()
    assert not app.exception
    # Dialog xác nhận xuất hiện -> nhấn xác nhận hủy
    app.button(key=f"btn_confirm_cancel_trip_{trip.id}").click().run()
    assert not app.exception

    # Kiểm tra trạng thái sau khi hủy (D1 = A: request chuyển CANCELLED, KHÔNG quay lại queue)
    cancelled_trip = _d(app).trips_snapshot()[0]
    assert cancelled_trip.status == "cancelled"
    assert _d(app).drivers_snapshot()[cancelled_trip.driver_id].status == "free"
    assert _d(app).all_requests[cancelled_trip.request_id].status == "cancelled"
    assert len(_d(app).queue_snapshot()) == 0

    # Chuyến đã hủy không còn nút Hoàn thành hay Hủy chuyến
    assert not any(b.key == f"btn_complete_{trip.id}" for b in app.button)
    assert not any(b.key == f"btn_cancel_trip_{trip.id}" for b in app.button)


def test_dispatcher_survives_rerun_state_preserved(app):
    _pick(app, "req_pickup", "N3")
    _pick(app, "req_dropoff", "N7")
    app.button(key="btn_submit").click().run()
    app.button(key="btn_dispatch").click().run()
    assert len(_d(app).trips_snapshot()) == 1
    app.run()  # rerun thuần túy bảo toàn trạng thái dispatcher
    assert len(_d(app).trips_snapshot()) == 1
    assert not any(b.key in ("btn_undo", "btn_redo") for b in app.button)



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


def test_real_backend_cancel_assigned_trip_persists(real_app, tmp_path):
    """UI AppTest với backend real: Hủy chuyến T2 (ASSIGNED trong seed) qua dialog xác nhận và lưu vào đĩa."""
    assert not real_app.exception
    # Seed data có T2 đang ASSIGNED cho D3
    assigned_trips = [t for t in _d(real_app).trips_snapshot() if t.status == "assigned"]
    assert any(t.id == "T2" for t in assigned_trips)
    assert _d(real_app).drivers_snapshot()["D3"].status == "busy"

    # Nhấn Hủy chuyến T2
    real_app.button(key="btn_cancel_trip_T2").click().run()
    assert not real_app.exception
    # Xác nhận trong dialog
    real_app.button(key="btn_confirm_cancel_trip_T2").click().run()
    assert not real_app.exception

    # Kiểm tra trạng thái trong bộ nhớ
    t2 = next(t for t in _d(real_app).trips_snapshot() if t.id == "T2")
    assert t2.status == "cancelled"
    assert _d(real_app).drivers_snapshot()["D3"].status == "free"
    assert _d(real_app).all_requests["R2"].status == "cancelled"
    assert not any(r.id == "R2" for r in _d(real_app).queue_snapshot())

    # Kiểm tra trạng thái đã lưu vào file trips.json và requests.json trên đĩa
    trips_json = (tmp_path / "trips.json").read_text(encoding="utf-8")
    assert '"status": "cancelled"' in trips_json
    requests_json = (tmp_path / "requests.json").read_text(encoding="utf-8")
    assert '"R2"' in requests_json

    # Nút thao tác hoàn thành/hủy cho T2 không còn hiển thị
    assert not any(b.key == "btn_cancel_trip_T2" for b in real_app.button)
    assert not any(b.key == "btn_complete_T2" for b in real_app.button)
    # Không còn widget undo/redo nào
    assert not any(b.key in ("btn_undo", "btn_redo") for b in real_app.button)



def test_tab_selection_persists_on_widget_interaction(app):
    # Ban đầu trang mặc định là "Điều phối chuyến"
    assert app.session_state["main_nav"] == "Điều phối chuyến"

    # Người dùng chuyển trang sang "Quản lý dữ liệu" bằng st.sidebar.radio key="main_nav"
    app.sidebar.radio(key="main_nav").set_value("Quản lý dữ liệu").run()
    assert app.session_state["main_nav"] == "Quản lý dữ liệu"

    # Người dùng tương tác với widget bên trong Action Panel (đổi điểm trả khách)
    _pick(app, "req_dropoff", "N4")
    app.run()

    # Trang đang chọn vẫn là "Quản lý dữ liệu", radio không bị reset khi rerun
    assert app.session_state["main_nav"] == "Quản lý dữ liệu"


def test_reset_to_seed_restores_data(real_app, tmp_path):
    assert not real_app.exception
    # 1. Điều phối một chuyến để làm thay đổi dữ liệu runtime trên đĩa
    real_app.button(key="btn_dispatch").click().run()
    assert '"T3"' in (tmp_path / "trips.json").read_text(encoding="utf-8")

    # 2. Chuyển sang Quản lý dữ liệu, nhấn nút Reset về dữ liệu mẫu (Seed) và xác nhận trong dialog
    real_app.sidebar.radio(key="main_nav").set_value("Quản lý dữ liệu").run()
    real_app.button(key="btn_reset_seed").click().run()
    real_app.button(key="btn_confirm_reset_seed").click().run()
    assert not real_app.exception

    # 3. File trips.json trên đĩa runtime được phục hồi về nguyên bản (chỉ có T1, T2 từ seed, không còn T3)
    content_trips = (tmp_path / "trips.json").read_text(encoding="utf-8")
    assert '"T3"' not in content_trips
    assert len(_d(real_app).trips_snapshot()) == 2


def test_map_data_zoom_buttons_and_limits(app):
    """Kiểm tra nút phóng to/thu nhỏ/vừa khung trên bản đồ dữ liệu và giới hạn 50% - 300%."""
    app.sidebar.radio(key="main_nav").set_value("Quản lý dữ liệu").run()
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
    # 1. Chuyển sang 'Quản lý dữ liệu' -> kiểm tra key 'map_data_canvas'
    app.sidebar.radio(key="main_nav").set_value("Quản lý dữ liệu").run()
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


def test_page_switch_preserves_dispatcher_state_and_allows_cancel(app):
    """Ràng buộc 5: Đổi trang không làm mất trạng thái dispatcher và cho phép hủy chuyến."""
    # 1. Tạo yêu cầu và điều phối chuyến trên Action panel
    _pick(app, "req_pickup", "N3")
    _pick(app, "req_dropoff", "N7")
    app.button(key="btn_submit").click().run()
    app.button(key="btn_dispatch").click().run()
    assert len(_d(app).trips_snapshot()) == 1

    # 2. Chuyển sang trang "Quản lý dữ liệu"
    app.sidebar.radio(key="main_nav").set_value("Quản lý dữ liệu").run()
    assert app.session_state["main_nav"] == "Quản lý dữ liệu"
    assert len(_d(app).trips_snapshot()) == 1

    # 3. Chuyển sang trang "Đối chuẩn thuật toán"
    app.sidebar.radio(key="main_nav").set_value("Đối chuẩn thuật toán").run()
    assert app.session_state["main_nav"] == "Đối chuẩn thuật toán"
    assert len(_d(app).trips_snapshot()) == 1

    # 4. Chuyển lại "Điều phối chuyến" và thực hiện Hủy chuyến thành công
    app.sidebar.radio(key="main_nav").set_value("Điều phối chuyến").run()
    assert app.session_state["main_nav"] == "Điều phối chuyến"
    trip = _d(app).trips_snapshot()[0]
    app.button(key=f"btn_cancel_trip_{trip.id}").click().run()
    app.button(key=f"btn_confirm_cancel_trip_{trip.id}").click().run()
    assert _d(app).trips_snapshot()[0].status == "cancelled"



def test_panel_toggle_changes_panel_open(app):
    """Ràng buộc 5: Nhấn nút nổi btn_toggle_panel làm đổi trạng thái session_state['panel_open']."""
    assert app.session_state.get("panel_open", True) is True
    # Nhấn toggle để đóng panel
    app.button(key="btn_toggle_panel").click().run()
    assert app.session_state["panel_open"] is False

    # Nhấn toggle lần nữa để mở lại panel
    app.button(key="btn_toggle_panel").click().run()
    assert app.session_state["panel_open"] is True

def test_sidebar_panel_toggle_changes_panel_open(app):
    """Nút toggle trong sidebar st.sidebar cũng thay đổi trạng thái session_state['panel_open']."""
    assert app.session_state.get("panel_open", True) is True
    app.button(key="btn_sidebar_panel_toggle").click().run()
    assert app.session_state["panel_open"] is False

    app.button(key="btn_sidebar_panel_toggle").click().run()
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
    app.sidebar.radio(key="main_nav").set_value("Quản lý dữ liệu").run()
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


def test_page_headers_distinct_per_page(app):
    """Kiểm tra AppTest: ở mỗi trang, header chứa đúng tiêu đề trang đó và KHÔNG chứa tiêu đề hai trang còn lại.

    Phương pháp kiểm tra: Qua `app.markdown`, trích xuất markdown có class 'page-header' và kiểm tra tiêu đề.
    """
    # 1. Trang mặc định ban đầu: "Điều phối chuyến"
    assert app.session_state["main_nav"] == "Điều phối chuyến"
    headers = [m.value for m in app.markdown if '<div class="page-header">' in m.value]
    assert len(headers) == 1
    assert "Điều phối chuyến" in headers[0]
    assert "Quản lý dữ liệu" not in headers[0]
    assert "Đối chuẩn thuật toán" not in headers[0]

    # 2. Chuyển sang "Quản lý dữ liệu"
    app.sidebar.radio(key="main_nav").set_value("Quản lý dữ liệu").run()
    assert not app.exception
    headers = [m.value for m in app.markdown if '<div class="page-header">' in m.value]
    assert len(headers) == 1
    assert "Quản lý dữ liệu" in headers[0]
    assert "Điều phối chuyến" not in headers[0]
    assert "Đối chuẩn thuật toán" not in headers[0]

    # 3. Chuyển sang "Đối chuẩn thuật toán"
    app.sidebar.radio(key="main_nav").set_value("Đối chuẩn thuật toán").run()
    assert not app.exception
    headers = [m.value for m in app.markdown if '<div class="page-header">' in m.value]
    assert len(headers) == 1
    assert "Đối chuẩn thuật toán" in headers[0]
    assert "Quản lý dữ liệu" not in headers[0]
    assert "Điều phối chuyến" not in headers[0]


def test_dispatch_header_queue_chip_updates_after_submit(app):
    """Test chip phản ánh đúng dữ liệu: sau khi gửi yêu cầu (btn_submit), chip 'Hàng đợi' tăng đúng 1."""
    app.sidebar.radio(key="main_nav").set_value("Điều phối chuyến").run()
    assert not app.exception

    # Lấy giá trị ban đầu của chip Hàng đợi
    headers = [m.value for m in app.markdown if '<div class="page-header">' in m.value]
    assert len(headers) == 1
    initial_queue_len = len(_d(app).queue_snapshot())
    assert f'Hàng đợi:</span> <span class="header-chip-val">{initial_queue_len}' in headers[0]

    # Gửi một yêu cầu đặt xe mới
    _pick(app, "req_pickup", "N3")
    _pick(app, "req_dropoff", "N7")
    app.button(key="btn_submit").click().run()
    assert not app.exception

    # Kiểm tra chip Hàng đợi sau khi gửi: tăng đúng 1
    headers_after = [m.value for m in app.markdown if '<div class="page-header">' in m.value]
    assert len(headers_after) == 1
    expected_new_len = initial_queue_len + 1
    assert f'Hàng đợi:</span> <span class="header-chip-val">{expected_new_len}' in headers_after[0]


def test_page_header_html_escaping_with_special_characters():
    """Test unit cho page_header (build_page_header_html) với các ký tự đặc biệt (<, &, ") để xác nhận đã escape."""
    from ui.components import build_page_header_html

    raw_icon = '<script>alert("hack")</script>'
    raw_title = 'Tiêu đề <Quản lý> & "Test"'
    raw_subtitle = 'Mô tả có ký tự & <đặc biệt> "nháy kép"'
    raw_chips = [
        ('Hàng đợi <chờ>', '1 & 2 "khách"'),
        ('<span class="bad">', '"100%" & <an toàn>'),
    ]

    html_out = build_page_header_html(raw_icon, raw_title, raw_subtitle, raw_chips)

    # Đảm bảo không chứa thẻ HTML thô chưa escape
    assert '<script>' not in html_out
    assert '<Quản lý>' not in html_out
    assert '<đặc biệt>' not in html_out
    assert '<span class="bad">' not in html_out
    assert '<an toàn>' not in html_out
    assert 'alert("hack")' not in html_out

    # Đảm bảo các ký tự đặc biệt đã được chuyển đổi thành HTML entities an toàn
    assert '&lt;script&gt;' in html_out
    assert '&lt;Quản lý&gt;' in html_out
    assert '&amp;' in html_out
    assert '&quot;Test&quot;' in html_out
    assert '&quot;nháy kép&quot;' in html_out
    assert '&lt;chờ&gt;' in html_out
    assert '&quot;khách&quot;' in html_out
    assert '&quot;100%&quot;' in html_out


# -----------------------------------------------------------------------------
# Kiểm thử chức năng phát lại (Animation / Timelapse) lộ trình điều phối
# -----------------------------------------------------------------------------
def test_map_animation_no_trip_no_exception(app):
    """Kiểm thử biên: chưa có chuyến nào ghép, mở bản đồ điều phối không sinh exception."""
    app.sidebar.radio(key="main_nav").set_value("Điều phối chuyến").run()
    assert not app.exception
    # Khi chưa có chuyến nào, các nút điều khiển animation không hiển thị hoặc không gây lỗi
    assert not any(b.key == "anim_play" for b in app.button)


def test_map_animation_dispatch_and_slider_scrub(app):
    """Kiểm thử: sau khi ghép chuyến, thanh slider anim_step xuất hiện và cập nhật đúng khi tua."""
    app.sidebar.radio(key="main_nav").set_value("Điều phối chuyến").run()
    assert not app.exception

    # Gửi yêu cầu đặt xe rồi ghép chuyến
    _pick(app, "req_pickup", "N3")
    _pick(app, "req_dropoff", "N7")
    app.button(key="btn_submit").click().run()
    assert not app.exception

    app.button(key="btn_dispatch").click().run()
    assert not app.exception

    # Kiểm tra slider anim_step xuất hiện
    sliders = [s for s in app.slider if s.key == "anim_step"]
    assert len(sliders) == 1
    slider = sliders[0]
    assert slider.max >= 1.0

    # Tua slider đến bước 1
    app.slider(key="anim_step").set_value(1).run()
    assert not app.exception
    assert app.session_state["anim_step"] == 1


def test_map_animation_play_and_auto_stop_at_end(app):
    """Kiểm thử: nhấn Phát (anim_play) chạy từng bước mượt mà và tự động dừng khi đến tick cuối cùng."""
    app.sidebar.radio(key="main_nav").set_value("Điều phối chuyến").run()
    assert not app.exception

    # Gửi yêu cầu đặt xe rồi ghép chuyến
    _pick(app, "req_pickup", "N3")
    _pick(app, "req_dropoff", "N7")
    app.button(key="btn_submit").click().run()
    assert not app.exception

    app.button(key="btn_dispatch").click().run()
    assert not app.exception

    # Nhấn Phát
    app.button(key="anim_play").click().run()
    assert not app.exception
    assert app.session_state.get("anim_playing") is True

    # Cho chạy qua các tick cho đến khi hết bước (chạy liên tục, không bị ngắt giữa chừng)
    max_ticks = 60
    ticks = 0
    while app.session_state.get("anim_playing", False) and ticks < max_ticks:
        app.run()
        assert not app.exception
        ticks += 1

    # Đã tự động dừng khi đến bước cuối cùng
    assert app.session_state["anim_playing"] is False
    slider = [s for s in app.slider if s.key == "anim_step"][0]
    assert app.session_state["anim_step"] == slider.max


def test_map_animation_pause_stops_playback(app):
    """Kiểm thử: khi đang phát, bấm Tạm dừng (anim_pause) thì dừng ngay tại tick hiện tại."""
    app.sidebar.radio(key="main_nav").set_value("Điều phối chuyến").run()
    assert not app.exception

    _pick(app, "req_pickup", "N3")
    _pick(app, "req_dropoff", "N7")
    app.button(key="btn_submit").click().run()
    app.button(key="btn_dispatch").click().run()

    app.button(key="anim_play").click().run()
    assert app.session_state.get("anim_playing") is True

    # Chạy 3 tick
    for _ in range(3):
        app.run()
        assert app.session_state.get("anim_playing") is True

    # Nhấn Tạm dừng
    app.button(key="anim_pause").click().run()
    assert not app.exception
    assert app.session_state["anim_playing"] is False
    assert 0 < app.session_state["anim_step"] < 30


def test_map_animation_cancel_trip_hides_playback_controls(app):
    """Kiểm thử xử lý biên: sau khi Hủy chuyến thì ẩn nút phát (anim_play) và cập nhật thẻ kết quả."""
    app.sidebar.radio(key="main_nav").set_value("Điều phối chuyến").run()
    assert not app.exception

    # Gửi yêu cầu đặt xe rồi ghép chuyến
    _pick(app, "req_pickup", "N3")
    _pick(app, "req_dropoff", "N7")
    app.button(key="btn_submit").click().run()
    assert not app.exception

    app.button(key="btn_dispatch").click().run()
    assert not app.exception
    assert any(b.key == "anim_play" for b in app.button)

    trip = _d(app).trips_snapshot()[0]
    # Nhấn Hủy chuyến và xác nhận
    app.button(key=f"btn_cancel_trip_{trip.id}").click().run()
    app.button(key=f"btn_confirm_cancel_trip_{trip.id}").click().run()
    assert not app.exception

    # Nút phát anim_play phải bị ẩn sau khi hủy chuyến
    assert not any(b.key == "anim_play" for b in app.button)

    # Thẻ kết quả điều phối gắn nhãn 'Chuyến đã hủy'
    assert app.session_state.get("last_dispatch", {}).get("status_tag") == "Chuyến đã hủy"




def test_build_animation_ticks_unit_contract():
    """Kiểm thử đơn vị hàm tạo tick: số tick mỗi cạnh trong [2, 6], tổng tick = tổng các cạnh, tick cuối trùng đỉnh đích."""
    from ui.components import build_animation_ticks, compute_edge_ticks
    from ui.constants import (
        ANIM_MAX_INTERVAL,
        ANIM_MIN_INTERVAL,
        ANIM_TICKS_PER_EDGE_MAX,
        ANIM_TICKS_PER_EDGE_MIN,
    )

    # 1. Kiểm tra hàm compute_edge_ticks: luôn trong [2, 6]
    test_weights = [0.1, 0.5, 1.0, 2.0, 3.5, 5.0, 6.0, 10.0, 25.0]
    for w in test_weights:
        n = compute_edge_ticks(w)
        assert ANIM_TICKS_PER_EDGE_MIN <= n <= ANIM_TICKS_PER_EDGE_MAX
        assert isinstance(n, int)

    # Trọng số cụ thể theo công thức clamp(round(w / 1.0), 2, 6)
    assert compute_edge_ticks(0.5) == 2
    assert compute_edge_ticks(2.0) == 2
    assert compute_edge_ticks(4.0) == 4
    assert compute_edge_ticks(6.0) == 6

    # 2. Kiểm tra build_animation_ticks cho lộ trình gồm đón khách và chở khách
    edges = [("A", "B", 4.0), ("B", "C", 6.0), ("C", "D", 2.0)]
    def lbl(x): return f"Đỉnh {x}"

    timeline = build_animation_ticks(["A", "B"], ["B", "C", "D"], edges, lbl, speed_mult=1.0)
    # Cạnh A->B: w=4.0 -> 4 tick; B->C: w=6.0 -> 6 tick; C->D: w=2.0 -> 2 tick
    # Tổng số tick = 4 + 6 + 2 = 12 tick.
    # Số khung hình = 12 + 1 = 13 (từ tick 0 đến tick 12).
    total_ticks = 4 + 6 + 2
    assert len(timeline) == total_ticks + 1
    assert timeline[0].total_ticks == total_ticks
    assert timeline[-1].total_ticks == total_ticks

    # Tick 0: tại A, xuất phát, T+0, 0%
    assert timeline[0].tick_index == 0
    assert timeline[0].node == "A"
    assert timeline[0].elapsed_time == 0.0
    assert timeline[0].progress_pct == 0.0
    assert "Xuất phát" in timeline[0].caption or "0%" in timeline[0].caption

    # Tick cuối: tại D (trùng đỉnh đích!), T+12 (4 + 6 + 2), 100%
    assert timeline[-1].tick_index == total_ticks
    assert timeline[-1].node == "D"
    assert timeline[-1].elapsed_time == 12.0
    assert timeline[-1].progress_pct == 1.0
    assert "Đã đến Đỉnh D" in timeline[-1].caption or "100%" in timeline[-1].caption

    # Cạnh đang đi luân phiên nét nét đặc (solid 5.0) và nét đứt (dashed 3.5)
    # Tick 1 (chẵn=False) -> dashed 3.5; Tick 2 (chẵn=True) -> solid 5.0
    assert timeline[1].custom_edges[("A", "B")][1] == "dashed"
    assert timeline[1].custom_edges[("A", "B")][2] == 3.5
    assert timeline[2].custom_edges[("A", "B")][1] == "solid"
    assert timeline[2].custom_edges[("A", "B")][2] == 5.0

    # Cạnh đã đi qua nét liền penwidth 3.5
    # Tại tick 5 (đã qua 4 tick cạnh A->B và đang ở cạnh B->C):
    assert timeline[5].custom_edges[("A", "B")][1] == "solid"
    assert timeline[5].custom_edges[("A", "B")][2] == 3.5

    # 3. Giới hạn độ trễ thực tế giữa các tick: trong khoảng [ANIM_MIN_INTERVAL, ANIM_MAX_INTERVAL]
    for tick in timeline:
        assert ANIM_MIN_INTERVAL <= tick.tick_delay <= ANIM_MAX_INTERVAL

    # 4. Xử lý biên: lộ trình 1 đỉnh trả danh sách an toàn 1 khung hình
    t_single = build_animation_ticks(["A"], None, edges, lbl)
    assert len(t_single) == 1
    assert t_single[0].node == "A"
    assert t_single[0].elapsed_time == 0.0

    # 5. Xử lý biên: lộ trình rỗng trả danh sách rỗng
    t_empty = build_animation_ticks([], None, edges, lbl)
    assert len(t_empty) == 0


def test_playback_schedule_short_medium_long_routes_contract():
    """Kiểm thử ngân sách thời gian: lộ trình ngắn (3), vừa (6), dài (15) ở 1x in [2, 8s], ở 4x ≈ 1/4, số khung ≥ 8."""
    from ui.components import build_animation_ticks
    from ui.constants import ANIM_MAX_SECONDS, ANIM_MIN_INTERVAL

    edges = [(f"N{i}", f"N{i+1}", 2.0) for i in range(1, 16)]
    lbl = lambda x: f"Đỉnh {x}"

    routes = [
        ("short", [f"N{i}" for i in range(1, 4)]),   # 3 đỉnh
        ("medium", [f"N{i}" for i in range(1, 7)]),  # 6 đỉnh
        ("long", [f"N{i}" for i in range(1, 16)]),  # 15 đỉnh
    ]

    for name, path in routes:
        # Tốc độ 1x
        t_1x = build_animation_ticks(path, None, edges, lbl, speed_mult=1.0)
        dur_1x = (len(t_1x) - 1) * t_1x[0].tick_delay
        assert 2.0 <= dur_1x <= ANIM_MAX_SECONDS, f"{name} 1x thời gian {dur_1x}s nằm ngoài [2.0, {ANIM_MAX_SECONDS}]"
        assert len(t_1x) >= 8, f"{name} 1x số khung {len(t_1x)} < 8"
        assert t_1x[0].tick_delay >= ANIM_MIN_INTERVAL

        # Tốc độ 4x
        t_4x = build_animation_ticks(path, None, edges, lbl, speed_mult=4.0)
        dur_4x = (len(t_4x) - 1) * t_4x[0].tick_delay
        assert t_4x[0].tick_delay >= ANIM_MIN_INTERVAL
        assert len(t_4x) >= 8, f"{name} 4x số khung {len(t_4x)} < 8"
        assert dur_4x <= dur_1x / 2.0 + 0.1, f"{name} 4x thời gian {dur_4x}s không nhanh hơn đáng kể so với 1x ({dur_1x}s)"
        if name == "long":
            # Với lộ trình dài 15 đỉnh, thời gian 4x (1.12s) xấp xỉ 1/4 của 1x (4.0s)
            assert abs(dur_4x - (dur_1x / 4.0)) <= 0.25


def test_map_animation_skip_button_jumps_to_end(app):
    """AppTest: bấm nút anim_skip thì trạng thái chuyển thành 'Hoàn tất', không exception, nút bị disable."""
    app.sidebar.radio(key="main_nav").set_value("Điều phối chuyến").run()
    assert not app.exception

    _pick(app, "req_pickup", "N3")
    _pick(app, "req_dropoff", "N7")
    app.button(key="btn_submit").click().run()
    assert not app.exception

    app.button(key="btn_dispatch").click().run()
    assert not app.exception

    # Kiểm tra nút Đến cuối (anim_skip) xuất hiện
    skip_btns = [b for b in app.button if b.key == "anim_skip"]
    assert len(skip_btns) == 1
    assert not skip_btns[0].disabled

    # Bấm Đến cuối
    app.button(key="anim_skip").click().run()
    assert not app.exception

    # Kiểm tra trạng thái hoàn tất
    slider = [s for s in app.slider if s.key == "anim_step"][0]
    assert app.session_state["anim_step"] == slider.max
    all_text = " ".join([m.value for m in app.markdown])
    assert "Hoàn tất" in all_text

    # Sau khi đến cuối, nút Đến cuối bị vô hiệu hóa
    skip_btn = [b for b in app.button if b.key == "anim_skip"][0]
    assert skip_btn.disabled


def test_map_animation_speed_select_options_and_default(app):
    """AppTest: tùy chọn tốc độ anim_speed gồm 1x, 2x, 4x, mặc định 2x; đổi qua cả 3 giá trị không lỗi."""
    app.sidebar.radio(key="main_nav").set_value("Điều phối chuyến").run()
    assert not app.exception

    _pick(app, "req_pickup", "N3")
    _pick(app, "req_dropoff", "N7")
    app.button(key="btn_submit").click().run()
    app.button(key="btn_dispatch").click().run()
    assert not app.exception

    speed_boxes = [s for s in app.selectbox if s.key == "anim_speed"]
    assert len(speed_boxes) == 1
    box = speed_boxes[0]
    assert box.options == ["1x", "2x", "4x"]
    assert box.value == "2x"

    # Lần lượt chuyển qua cả 3 tốc độ không gây exception
    for speed_val in ["1x", "2x", "4x"]:
        app.selectbox(key="anim_speed").select(speed_val).run()
        assert not app.exception
        # Kiểm tra caption tổng thời gian phát hiển thị đúng
        captions = [c.value for c in app.caption if "Tổng thời gian phát ≈" in c.value]
        assert len(captions) >= 1


def test_map_animation_scrub_many_values_and_completed_status(app):
    """AppTest: ghép chuyến, đặt anim_step ở nhiều giá trị không có exception, tua đến tick cuối hiển thị Hoàn tất."""
    app.sidebar.radio(key="main_nav").set_value("Điều phối chuyến").run()
    assert not app.exception

    # Gửi yêu cầu đặt xe và ghép chuyến
    _pick(app, "req_pickup", "N3")
    _pick(app, "req_dropoff", "N7")
    app.button(key="btn_submit").click().run()
    assert not app.exception

    app.button(key="btn_dispatch").click().run()
    assert not app.exception

    sliders = [s for s in app.slider if s.key == "anim_step"]
    assert len(sliders) == 1
    slider = sliders[0]
    max_val = int(slider.max)
    assert max_val >= 4

    # Đặt anim_step ở nhiều giá trị: 0, 1, nửa chừng, và cuối cùng
    for test_step in [0, 1, max_val // 2, max_val]:
        app.slider(key="anim_step").set_value(test_step).run()
        assert not app.exception
        assert app.session_state["anim_step"] == test_step

    # Khi tua đến tick cuối cùng, trạng thái là Hoàn tất
    all_text = " ".join([m.value for m in app.markdown])
    assert "Hoàn tất" in all_text

    # anim_progress được cập nhật trong session_state
    assert "anim_progress" in app.session_state
    assert 0.0 <= float(app.session_state["anim_progress"]) <= 1.0


def test_map_animation_consecutive_dispatches_rebuild_cache(app):
    """AppTest: ghép 2 chuyến liên tiếp thì danh sách khung hình (timeline cache) được dựng lại (không dùng khung cũ)."""
    app.sidebar.radio(key="main_nav").set_value("Điều phối chuyến").run()
    assert not app.exception

    # Ghép chuyến 1: N3 -> N7
    _pick(app, "req_pickup", "N3")
    _pick(app, "req_dropoff", "N7")
    app.button(key="btn_submit").click().run()
    assert not app.exception

    app.button(key="btn_dispatch").click().run()
    assert not app.exception

    cache_key_1 = app.session_state.get("_anim_timeline_cache_key")
    assert cache_key_1 is not None

    # Ghép chuyến 2: N2 -> N5
    _pick(app, "req_pickup", "N2")
    _pick(app, "req_dropoff", "N5")
    app.button(key="btn_submit").click().run()
    assert not app.exception

    app.button(key="btn_dispatch").click().run()
    assert not app.exception

    cache_key_2 = app.session_state.get("_anim_timeline_cache_key")
    assert cache_key_2 is not None
    # Khóa cache của chuyến 2 phải khác chuyến 1 -> timeline được dựng lại
    assert cache_key_2 != cache_key_1


def test_dispatch_failure_renders_without_key_error_result(app):
    """Kiểm thử: khi ghép chuyến thất bại (ví dụ: không có tài xế rảnh),
    thẻ cảnh báo hiển thị nguyên nhân và gợi ý, không phát sinh KeyError: 'result'.
    """
    app.sidebar.radio(key="main_nav").set_value("Điều phối chuyến").run()
    assert not app.exception

    # Làm tất cả tài xế bận để tạo tình huống ghép chuyến thất bại
    d = _d(app)
    for drv in d.drivers.values():
        drv.status = "busy"

    # Tạo yêu cầu đặt xe
    _pick(app, "req_pickup", "N3")
    _pick(app, "req_dropoff", "N7")
    app.button(key="btn_submit").click().run()
    assert not app.exception

    # Bấm Ghép chuyến -> Thất bại do không còn tài xế rảnh
    app.button(key="btn_dispatch").click().run()
    assert not app.exception

    # Đảm bảo hiển thị đầy đủ thẻ nguyên nhân và gợi ý mà không có lỗi Exception
    all_markdown = " ".join(m.value for m in app.markdown)
    assert "Không thể ghép chuyến" in all_markdown
    assert "Không còn tài xế rảnh" in all_markdown


def test_map_positioned_at_bottom(app):
    """Kiểm thử vị trí bản đồ luôn nằm ở dưới cùng trong tab_data và tab_dispatch."""
    # 1. Tab Quản lý dữ liệu: "Bản đồ Mạng lưới Giao thông" nằm sau "Quản lý Đội ngũ Tài xế"
    app.sidebar.radio(key="main_nav").set_value("Quản lý dữ liệu").run()
    assert not app.exception
    subheaders_data = [s.value for s in app.subheader]
    assert "Quản lý Đội ngũ Tài xế" in subheaders_data
    assert "Bản đồ Mạng lưới Giao thông" in subheaders_data
    idx_drivers = subheaders_data.index("Quản lý Đội ngũ Tài xế")
    idx_data_map = subheaders_data.index("Bản đồ Mạng lưới Giao thông")
    assert idx_data_map > idx_drivers

    # 2. Tab Điều phối chuyến: "Bản đồ điều phối" nằm sau "Danh sách Chuyến xe"
    app.sidebar.radio(key="main_nav").set_value("Điều phối chuyến").run()
    assert not app.exception
    subheaders_dispatch = [s.value for s in app.subheader]
    idx_trips = next(i for i, s in enumerate(subheaders_dispatch) if s.startswith("Danh sách Chuyến xe"))
    idx_dispatch_map = subheaders_dispatch.index("Bản đồ điều phối")
    assert idx_dispatch_map > idx_trips


def test_benchmark_header_bold_xe_ranh_chip(app):
    """Kiểm tra chữ 'Xe rảnh' trong chips của tab_benchmark được in đậm bằng thẻ <strong>."""
    app.sidebar.radio(key="main_nav").set_value("Đối chuẩn thuật toán").run()
    assert not app.exception
    headers = [m.value for m in app.markdown if '<div class="page-header">' in m.value]
    assert len(headers) == 1
    assert "<strong>Xe rảnh</strong>:" in headers[0]


# =====================================================================
# 10. KIỂM THỬ XEM LẠI LỘ TRÌNH ĐỦ HAI CHẶNG TRONG LỊCH SỬ (PICKUP_PATH)
# =====================================================================


def test_ui_history_trip_renders_both_legs_after_completion(app):
    """UI AppTest (mock):
    - Ghép chuyến mới -> hoàn thành chuyến.
    - Chọn xem lại chuyến đó trong lịch sử: bản đồ dùng đủ 2 chặng:
      + Chặng đón: màu xanh lá #16a34a, nét solid.
      + Chặng chở: màu cam #ea580c, nét dashed.
    - Kiểm tra qua chuỗi DOT trong proto.spec của graphviz_chart.
    - F5/rerun không làm mất chặng xanh.
    """
    app.sidebar.radio(key="main_nav").set_value("Điều phối chuyến").run()
    assert not app.exception

    # Gửi yêu cầu đặt xe N3 -> N7
    _pick(app, "req_pickup", "N3")
    _pick(app, "req_dropoff", "N7")
    app.button(key="btn_submit").click().run()
    assert not app.exception

    # Ghép chuyến
    app.button(key="btn_dispatch").click().run()
    assert not app.exception
    trip = _d(app).trips_snapshot()[0]

    # Hoàn thành chuyến
    app.button(key=f"btn_complete_{trip.id}").click().run()
    assert not app.exception
    completed_trip = _d(app).trips_snapshot()[0]
    assert completed_trip.status == "completed"

    # Chọn chuyến trong selectbox lịch sử (nếu có selectbox)
    selectboxes = [s for s in app.selectbox if s.key == "anim_trip_select"]
    if selectboxes:
        opt = next(o for o in selectboxes[0].options if trip.id in o)
        selectboxes[0].select(opt).run()
        assert not app.exception

    # Kiểm tra chuỗi DOT được truyền vào st.graphviz_chart
    charts = app.get("graphviz_chart")
    assert len(charts) > 0
    dot_spec = charts[-1].proto.spec

    # Kiểm tra đủ 2 chặng trong DOT: chặng xanh lá (#16a34a) và chặng cam (#ea580c)
    assert "#16a34a" in dot_spec, "Lộ trình đón (xanh lá) phải xuất hiện trong DOT"
    assert "#ea580c" in dot_spec, "Lộ trình chở khách (cam) phải xuất hiện trong DOT"
    assert "solid" in dot_spec
    assert "dashed" in dot_spec

    # Chú giải dưới bản đồ có thông tin cả 2 chặng kèm ETA
    captions = [c.value for c in app.caption]
    assert any("Xanh lá: xe đến điểm đón" in c and "Cam nét đứt: chở khách đến điểm trả" in c for c in captions)

    # F5 / rerun lại ứng dụng: không làm mất chặng xanh
    app.run()
    assert not app.exception
    reloaded_charts = app.get("graphviz_chart")
    reloaded_dot = reloaded_charts[-1].proto.spec
    assert "#16a34a" in reloaded_dot
    assert "#ea580c" in reloaded_dot


def test_ui_seed_t1_history_shows_legacy_info_message(real_app, tmp_path):
    """UI AppTest (real backend):
    - Chọn chuyến seed T1 (COMPLETED, không có pickup_path).
    - Hiển thị st.info: 'Chuyến này được tạo trước khi hệ thống lưu lộ trình đón nên chỉ hiển thị chặng chở khách.'
    - Không phát sinh exception.
    - Bản đồ hiển thị chặng cam (chở khách), không có chặng xanh.
    """
    real_app.sidebar.radio(key="main_nav").set_value("Điều phối chuyến").run()
    assert not real_app.exception

    # Chọn chuyến seed T1
    selectboxes = [s for s in real_app.selectbox if s.key == "anim_trip_select"]
    assert len(selectboxes) > 0
    t1_opt = next(o for o in selectboxes[0].options if "T1" in o)
    selectboxes[0].select(t1_opt).run()
    assert not real_app.exception

    # Kiểm tra banner st.info giải thích dữ liệu cũ
    infos = [i.value for i in real_app.info]
    assert any("Chuyến này được tạo trước khi hệ thống lưu lộ trình đón nên chỉ hiển thị chặng chở khách." in i for i in infos)

    # Kiểm tra DOT: có chặng cam (#ea580c), không có chặng xanh đón (#16a34a)
    charts = real_app.get("graphviz_chart")
    assert len(charts) > 0
    dot_spec = charts[-1].proto.spec
    assert "#ea580c" in dot_spec
    assert "#16a34a" not in dot_spec


def test_ui_seed_t2_assigned_shows_both_legs(real_app, tmp_path):
    """UI AppTest (real backend):
    - Chuyến seed T2 (ASSIGNED) hiển thị đủ hai chặng nhờ suy ra từ vị trí tài xế.
    - Không hiện banner st.info dữ liệu cũ.
    """
    real_app.sidebar.radio(key="main_nav").set_value("Điều phối chuyến").run()
    assert not real_app.exception

    # Chọn chuyến seed T2
    selectboxes = [s for s in real_app.selectbox if s.key == "anim_trip_select"]
    assert len(selectboxes) > 0
    t2_opt = next(o for o in selectboxes[0].options if "T2" in o)
    selectboxes[0].select(t2_opt).run()
    assert not real_app.exception

    # Kiểm tra DOT có cả 2 chặng
    charts = real_app.get("graphviz_chart")
    assert len(charts) > 0
    dot_spec = charts[-1].proto.spec
    assert "#16a34a" in dot_spec
    assert "#ea580c" in dot_spec

    # Không hiện banner dữ liệu cũ
    infos = [i.value for i in real_app.info]
    assert not any("Chuyến này được tạo trước khi hệ thống lưu lộ trình đón" in i for i in infos)


def test_cancel_queued_request_flow(app):
    """Kiểm tra hủy yêu cầu trong hàng đợi (cancel_request) qua UI hoạt động đúng."""
    from ui.session import item_id
    assert item_id("R16 (N3 – Cầu Rồng → N7 – Bến xe)") == "R16"
    assert item_id("R16 (N3 → N7)") == "R16"
    assert item_id("N3 – Cầu Rồng") == "N3"

    # Tạo yêu cầu mới
    _pick(app, "req_pickup", "N3")
    _pick(app, "req_dropoff", "N7")
    app.button(key="btn_submit").click().run()
    assert not app.exception
    queue = _d(app).queue_snapshot()
    assert len(queue) == 1
    req = queue[0]

    # Chọn yêu cầu cần hủy trong selectbox
    sel = next(s for s in app.selectbox if s.key == "cancel_req_select")
    target_opt = next(o for o in sel.options if req.id in o)
    sel.select(target_opt).run()

    # Nhấn Hủy yêu cầu -> dialog xuất hiện -> nhấn Xác nhận hủy
    app.button(key="btn_cancel_request").click().run()
    app.button(key="btn_confirm_cancel_request").click().run()
    assert not app.exception

    # Kiểm tra hàng đợi và all_requests đã được xóa
    assert len(_d(app).queue_snapshot()) == 0
    assert req.id not in _d(app).all_requests

