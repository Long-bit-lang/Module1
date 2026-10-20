"""Bộ kiểm thử cho module models — TV1.

Ma trận test T01–T28:
  - T01–T02  : BaseEntity (abstract, __eq__)
  - T03–T08  : Location
  - T09–T17  : Driver
  - T18–T23  : RideRequest
  - T24–T27  : Trip
  - T28      : Constants / __init__
"""
import pytest
from models import (
    BaseEntity,
    Location,
    Driver, FREE, BUSY,
    RideRequest, QUEUED,
    Trip, ASSIGNED, COMPLETED, CANCELLED,
)


# ---------------------------------------------------------------------------
# Helpers / Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def loc():
    return Location("N1", "Ngã tư A")


@pytest.fixture
def driver():
    return Driver("D1", "An", "N1")


@pytest.fixture
def request_():
    return RideRequest("R1", "N1", "N7")


@pytest.fixture
def trip():
    return Trip("T1", "R1", "D1", 7.0)


# ---------------------------------------------------------------------------
# T01–T02  BaseEntity
# ---------------------------------------------------------------------------

class TestBaseEntity:
    def test_T01_cannot_instantiate_directly(self):
        """T01: BaseEntity là abstract — không thể khởi tạo trực tiếp."""
        with pytest.raises(TypeError):
            BaseEntity("X1")  # type: ignore[abstract]

    def test_T02_eq_same_id(self):
        """T02: Hai entity cùng lớp, cùng id thì bằng nhau."""
        a = Location("N1", "A")
        b = Location("N1", "B")
        assert a == b

    def test_T02b_eq_different_class(self):
        """T02b: Khác lớp thì không bằng nhau dù cùng id."""
        loc = Location("D1", "Nơi nào đó")
        drv = Driver("D1", "An", "N1")
        assert loc != drv

    def test_T02c_repr_contains_class_and_id(self):
        """T02c: repr() chứa tên lớp và id."""
        d = Driver("D1", "An", "N1")
        r = repr(d)
        assert "Driver" in r
        assert "D1" in r


# ---------------------------------------------------------------------------
# T03–T08  Location
# ---------------------------------------------------------------------------

class TestLocation:
    def test_T03_valid_init(self, loc):
        """T03: Khởi tạo hợp lệ — id và name đúng."""
        assert loc.id == "N1"
        assert loc.name == "Ngã tư A"

    def test_T04_empty_id_raises(self):
        """T04: id rỗng → ValueError."""
        with pytest.raises(ValueError):
            Location("")

    def test_T05_default_name_is_empty(self):
        """T05: name mặc định là chuỗi rỗng."""
        loc = Location("N2")
        assert loc.name == ""

    def test_T06_to_dict(self, loc):
        """T06: to_dict() trả về đúng schema."""
        assert loc.to_dict() == {"id": "N1", "name": "Ngã tư A"}

    def test_T07_from_dict(self):
        """T07: from_dict() tạo đúng object."""
        data = {"id": "N2", "name": "Chợ B"}
        obj = Location.from_dict(data)
        assert obj.id == "N2"
        assert obj.name == "Chợ B"

    def test_T08_roundtrip(self, loc):
        """T08: to_dict → from_dict cho object bằng gốc."""
        assert Location.from_dict(loc.to_dict()) == loc


# ---------------------------------------------------------------------------
# T09–T17  Driver
# ---------------------------------------------------------------------------

class TestDriver:
    def test_T09_valid_init_default_free(self, driver):
        """T09: Status mặc định là FREE."""
        assert driver.status == FREE
        assert driver.id == "D1"
        assert driver.name == "An"
        assert driver.node == "N1"

    def test_T10_empty_id_raises(self):
        """T10: id rỗng → ValueError."""
        with pytest.raises(ValueError):
            Driver("", "An", "N1")

    def test_T11_empty_name_raises(self):
        """T11: name rỗng → ValueError."""
        with pytest.raises(ValueError):
            Driver("D1", "", "N1")

    def test_T12_empty_node_raises(self):
        """T12: node rỗng → ValueError."""
        with pytest.raises(ValueError):
            Driver("D1", "An", "")

    def test_T13_invalid_status_raises(self):
        """T13: status không hợp lệ → ValueError."""
        with pytest.raises(ValueError):
            Driver("D1", "An", "N1", status="idle")

    def test_T14_assign_free_to_busy(self, driver):
        """T14: assign() chuyển FREE → BUSY thành công."""
        driver.assign()
        assert driver.status == BUSY

    def test_T15_assign_when_busy_raises(self, driver):
        """T15: assign() khi đang BUSY → RuntimeError."""
        driver.assign()
        with pytest.raises(RuntimeError):
            driver.assign()

    def test_T16_release_busy_to_free(self, driver):
        """T16: release() chuyển BUSY → FREE."""
        driver.assign()
        driver.release()
        assert driver.status == FREE

    def test_T17_to_dict_and_from_dict_roundtrip(self, driver):
        """T17: to_dict → from_dict cho object bằng gốc."""
        d = driver.to_dict()
        assert d == {"id": "D1", "name": "An", "node": "N1", "status": "free"}
        restored = Driver.from_dict(d)
        assert restored == driver
        assert restored.name == driver.name
        assert restored.node == driver.node
        assert restored.status == driver.status


# ---------------------------------------------------------------------------
# T18–T23  RideRequest
# ---------------------------------------------------------------------------

class TestRideRequest:
    def test_T18_valid_init_default_queued(self, request_):
        """T18: Status mặc định là QUEUED."""
        assert request_.status == QUEUED
        assert request_.pickup_node == "N1"
        assert request_.dropoff_node == "N7"

    def test_T19_empty_id_raises(self):
        """T19: id rỗng → ValueError."""
        with pytest.raises(ValueError):
            RideRequest("", "N1", "N7")

    def test_T20_empty_pickup_raises(self):
        """T20: pickup_node rỗng → ValueError."""
        with pytest.raises(ValueError):
            RideRequest("R1", "", "N7")

    def test_T21_pickup_equals_dropoff_raises(self):
        """T21: pickup_node == dropoff_node → ValueError."""
        with pytest.raises(ValueError):
            RideRequest("R1", "N1", "N1")

    def test_T22_invalid_status_raises(self):
        """T22: status không hợp lệ → ValueError."""
        with pytest.raises(ValueError):
            RideRequest("R1", "N1", "N7", status="pending")

    def test_T23_to_dict_and_from_dict_roundtrip(self, request_):
        """T23: to_dict → from_dict cho object bằng gốc."""
        d = request_.to_dict()
        assert d == {
            "id": "R1",
            "pickup_node": "N1",
            "dropoff_node": "N7",
            "status": "queued",
        }
        restored = RideRequest.from_dict(d)
        assert restored == request_
        assert restored.pickup_node == request_.pickup_node
        assert restored.dropoff_node == request_.dropoff_node
        assert restored.status == request_.status

    def test_T23b_valid_status_cancelled(self):
        """T23b: RideRequest chấp nhận status CANCELLED và roundtrip to_dict/from_dict chuẩn xác."""
        req = RideRequest("R99", "N2", "N5", status=CANCELLED)
        assert req.status == CANCELLED
        d = req.to_dict()
        assert d["status"] == "cancelled"
        restored = RideRequest.from_dict(d)
        assert restored == req
        assert restored.status == CANCELLED


# ---------------------------------------------------------------------------
# T24–T27  Trip
# ---------------------------------------------------------------------------

class TestTrip:
    def test_T24_valid_init_default_assigned(self, trip):
        """T24: Status mặc định là ASSIGNED."""
        assert trip.status == ASSIGNED
        assert trip.eta == 7.0

    def test_T25_negative_eta_raises(self):
        """T25: eta âm → ValueError."""
        with pytest.raises(ValueError):
            Trip("T1", "R1", "D1", eta=-1.0)

    def test_T26_invalid_status_raises(self):
        """T26: status không hợp lệ → ValueError."""
        with pytest.raises(ValueError):
            Trip("T1", "R1", "D1", 5.0, status="ongoing")

    def test_T26b_valid_status_cancelled(self):
        """T26b: Trip chấp nhận status CANCELLED và roundtrip to_dict/from_dict chuẩn xác."""
        t = Trip("T99", "R99", "D1", 5.5, status=CANCELLED)
        assert t.status == CANCELLED
        d = t.to_dict()
        assert d["status"] == "cancelled"
        restored = Trip.from_dict(d)
        assert restored == t
        assert restored.status == CANCELLED

    def test_T27_to_dict_and_from_dict_roundtrip(self, trip):
        """T27: to_dict → from_dict cho object bằng gốc."""
        d = trip.to_dict()
        assert d == {
            "id": "T1",
            "request_id": "R1",
            "driver_id": "D1",
            "eta": 7.0,
            "status": "assigned",
        }
        restored = Trip.from_dict(d)
        assert restored == trip
        assert restored.eta == trip.eta
        assert restored.status == trip.status


    def test_T27b_invalid_eta_nan_inf_bool_raises(self):
        """T27b: eta là NaN, inf hoặc boolean → ValueError."""
        for invalid_eta in (float("nan"), float("inf"), float("-inf"), True, False):
            with pytest.raises(ValueError):
                Trip("T1", "R1", "D1", eta=invalid_eta)

    def test_T27c_base_entity_hashable_in_set_and_dict(self, trip):
        """T27c: BaseEntity có __hash__ hợp lệ, dùng được trong set/dict."""
        t2 = Trip("T1", "R1", "D1", 7.0)
        s = {trip, t2}
        assert len(s) == 1
        d = {trip: "active"}
        assert d[t2] == "active"

    def test_T27d_trip_pickup_path_optional_and_validation(self):
        """T27d: Trip hỗ trợ pickup_path tùy chọn, mặc định [], từ chối dữ liệu không hợp lệ."""
        # 1. Mặc định là []
        t1 = Trip("T1", "R1", "D1", 5.0)
        assert t1.pickup_path == []
        t2 = Trip("T2", "R1", "D1", 5.0, pickup_path=None)
        assert t2.pickup_path == []

        # 2. Khởi tạo hợp lệ với list chuỗi
        t3 = Trip("T3", "R1", "D1", 5.0, pickup_path=["N1", "N2", "N3"])
        assert t3.pickup_path == ["N1", "N2", "N3"]

        # 3. to_dict không có khóa khi pickup_path rỗng
        assert "pickup_path" not in t1.to_dict()
        assert "pickup_path" not in t2.to_dict()

        # 4. Từ chối kiểu dữ liệu không phải list
        for invalid_type in ("N1", 123, ("N1", "N2"), {"N1": "N2"}, True):
            with pytest.raises(ValueError):
                Trip("T_err", "R1", "D1", 5.0, pickup_path=invalid_type)

        # 5. Từ chối phần tử trong list không phải chuỗi hoặc rỗng
        for invalid_item in (["N1", ""], ["N1", "   "], ["N1", 123], [None]):
            with pytest.raises(ValueError):
                Trip("T_err", "R1", "D1", 5.0, pickup_path=invalid_item)

    def test_T27e_trip_pickup_path_roundtrip_to_dict_from_dict(self):
        """T27e: Roundtrip to_dict và from_dict khi có pickup_path bảo toàn trọn vẹn dữ liệu."""
        path = ["N3", "N4", "N7"]
        t = Trip("T10", "R5", "D2", 8.5, pickup_path=path)
        d = t.to_dict()
        assert d["pickup_path"] == path

        restored = Trip.from_dict(d)
        assert restored == t
        assert restored.pickup_path == path
        assert restored.eta == 8.5
        assert restored.driver_id == "D2"



# ---------------------------------------------------------------------------
# T28  Constants & __init__ exports
# ---------------------------------------------------------------------------

class TestConstants:
    def test_T28a_all_constants_importable(self):
        """T28a: Tất cả hằng số và class thực thể được export đầy đủ từ models."""
        import models
        required_constants = ["FREE", "BUSY", "QUEUED", "ASSIGNED", "COMPLETED", "CANCELLED"]
        required_classes = ["BaseEntity", "Location", "Driver", "RideRequest", "Trip"]
        for name in required_constants + required_classes:
            assert hasattr(models, name), f"models thiếu export: {name}"
            val = getattr(models, name)
            assert val is not None, f"models.{name} có giá trị None"
        if hasattr(models, "__all__"):
            assert set(required_constants + required_classes) <= set(models.__all__)

    def test_T28b_constant_values_match_contract(self):
        """T28b: Giá trị hằng số đúng theo CONTRACT §1."""
        assert FREE == "free"
        assert BUSY == "busy"
        assert QUEUED == "queued"
        assert ASSIGNED == "assigned"
        assert COMPLETED == "completed"
        assert CANCELLED == "cancelled"

    def test_T28c_no_core_import_in_models(self):
        """T28c: models không import từ core hay streamlit."""
        import inspect
        import os
        from pathlib import Path
        import models
        import models.base_entity
        import models.location
        import models.driver
        import models.ride_request
        import models.trip

        modules = [
            models, models.base_entity, models.location,
            models.driver, models.ride_request, models.trip,
        ]
        for mod in modules:
            src = inspect.getfile(mod)
            assert os.path.isfile(src), f"Không tìm thấy file nguồn của {mod}"
            content = Path(src).read_text(encoding="utf-8")
            assert "from core" not in content, f"{mod} chứa 'from core'"
            assert "import core" not in content, f"{mod} chứa 'import core'"
            assert "import streamlit" not in content, f"{mod} chứa 'import streamlit'"
            assert "from streamlit" not in content, f"{mod} chứa 'from streamlit'"

