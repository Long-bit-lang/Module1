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
    # 1. Trang mặc định ban đầu: "Quản lý dữ liệu"
    assert app.session_state["main_nav"] == "Quản lý dữ liệu"
    headers = [m.value for m in app.markdown if '<div class="page-header">' in m.value]
    assert len(headers) == 1
    assert "Quản lý dữ liệu" in headers[0]
    assert "Điều phối chuyến" not in headers[0]
    assert "Đối chuẩn thuật toán" not in headers[0]

    # 2. Chuyển sang "Điều phối chuyến"
    app.sidebar.radio(key="main_nav").set_value("Điều phối chuyến").run()
    assert not app.exception
    headers = [m.value for m in app.markdown if '<div class="page-header">' in m.value]
    assert len(headers) == 1
    assert "Điều phối chuyến" in headers[0]
    assert "Quản lý dữ liệu" not in headers[0]
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
    """Kiểm thử: nhấn Phát (anim_play) chạy từng bước và tự động dừng khi đến bước cuối cùng."""
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

    # Cho chạy qua các tick cho đến khi hết bước
    max_ticks = 15
    ticks = 0
    while app.session_state.get("anim_playing", False) and ticks < max_ticks:
        app.run()
        assert not app.exception
        ticks += 1

    # Đã tự động dừng khi đến bước cuối cùng
    assert app.session_state["anim_playing"] is False


def test_map_animation_undo_hides_playback_controls(app):
    """Kiểm thử xử lý biên: sau khi Undo thì ẩn nút phát (anim_play) và thông báo 'chuyến đã hoàn tác'."""
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

    # Nhấn Hoàn tác (btn_undo)
    app.button(key="btn_undo").click().run()
    assert not app.exception

    # Nút phát anim_play phải bị ẩn sau khi hoàn tác
    assert not any(b.key == "anim_play" for b in app.button)

    # Có thông báo chuyến đã hoàn tác
    all_text = " ".join([m.value for m in app.info] + [m.value for m in app.warning] + [m.value for m in app.markdown])
    assert "chuyến" in all_text.lower() and "hoàn tác" in all_text.lower()


def test_build_animation_timeline_unit_contract():
    """Kiểm thử đơn vị cho hàm build_animation_timeline: tính toán thời gian ảo, độ trễ và nét vẽ."""
    from ui.components import build_animation_timeline

    edges = [("A", "B", 4.0), ("B", "C", 6.0), ("C", "D", 2.0)]
    def lbl(x): return f"Đỉnh {x}"

    # 1. Trường hợp bình thường: chặng đón (A->B), chặng chở (B->C->D)
    timeline = build_animation_timeline(["A", "B"], ["B", "C", "D"], edges, lbl, speed_mult=1.0)
    assert len(timeline) == 4  # A, B, C, D

    # Bước 0 (tại A): T+0, đón khách, các cạnh sắp tới đều nét đứt
    assert timeline[0].step_index == 0
    assert timeline[0].node == "A"
    assert timeline[0].elapsed_time == 0.0
    assert "0.3" <= str(timeline[0].step_delay) <= "1.2"
    assert 0.3 <= timeline[0].step_delay <= 1.2
    assert timeline[0].custom_edges[("A", "B")][1] == "dashed"  # sắp tới
    assert "Bước 1/4" in timeline[0].caption

    # Bước 1 (tại B): T+4, điểm đón, cạnh A->B đã đi nét liền
    assert timeline[1].step_index == 1
    assert timeline[1].node == "B"
    assert timeline[1].elapsed_time == 4.0
    assert timeline[1].custom_edges[("A", "B")][1] == "solid"
    assert timeline[1].custom_edges[("B", "C")][1] == "dashed"

    # Bước 3 (tại D): T+12 (4 + 6 + 2), tất cả cạnh đã đi nét liền
    assert timeline[3].step_index == 3
    assert timeline[3].node == "D"
    assert timeline[3].elapsed_time == 12.0
    assert timeline[3].custom_edges[("A", "B")][1] == "solid"
    assert timeline[3].custom_edges[("B", "C")][1] == "solid"
    assert timeline[3].custom_edges[("C", "D")][1] == "solid"

    # 2. Giới hạn độ trễ [0.3, 1.2] với các tốc độ khác nhau
    for spd in [0.5, 1.0, 2.0]:
        t = build_animation_timeline(["A", "B", "C"], None, edges, lbl, speed_mult=spd)
        for s in t:
            assert 0.3 <= s.step_delay <= 1.2

    # 3. Biên: 1 đỉnh
    t_single = build_animation_timeline(["A"], None, edges, lbl)
    assert len(t_single) == 1
    assert t_single[0].elapsed_time == 0.0

    # 4. Biên: rỗng
    t_empty = build_animation_timeline([], None, edges, lbl)
    assert len(t_empty) == 0


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

