"""Kiểm tra import cơ bản - chạy được ngay từ ngày 1."""


def test_imports():
    import models.base_entity, models.location, models.driver  # noqa: F401
    import models.ride_request, models.trip  # noqa: F401
    import core.road_graph, core.strategies, core.structures  # noqa: F401
    import core.dispatcher, core.json_storage  # noqa: F401
