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
