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
    Trip, ASSIGNED, COMPLETED,
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


# ---------------------------------------------------------------------------
# T28  Constants & __init__ exports
# ---------------------------------------------------------------------------

class TestConstants:
    def test_T28a_all_constants_importable(self):
        """T28a: Tất cả hằng số import được từ models."""
        # Import ở đầu file đã chứng minh; test này chạy được = pass
        assert True

    def test_T28b_constant_values_match_contract(self):
        """T28b: Giá trị hằng số đúng theo CONTRACT §1."""
        assert FREE == "free"
        assert BUSY == "busy"
        assert QUEUED == "queued"
        assert ASSIGNED == "assigned"
        assert COMPLETED == "completed"

    def test_T28c_no_core_import_in_models(self):
        """T28c: models không import từ core hay streamlit."""
        import models
        import models.base_entity
        import models.location
        import models.driver
        import models.ride_request
        import models.trip

        for mod in [
            models, models.base_entity, models.location,
            models.driver, models.ride_request, models.trip,
        ]:
            deps = vars(mod).keys()
            assert "streamlit" not in str(deps)
            # Kiểm tra không có tham chiếu tới core trong source
            import inspect, os
            try:
                src = inspect.getfile(mod)
                if os.path.isfile(src):
                    content = open(src, encoding="utf-8").read()
                    assert "from core" not in content
                    assert "import core" not in content
            except (TypeError, OSError):
                pass
