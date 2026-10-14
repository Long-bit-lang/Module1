"""TV1 - Chuyến đi được tạo sau khi điều phối."""
from .base_entity import BaseEntity


class Trip(BaseEntity):
    def __init__(self, id: str, request_id: str, driver_id: str,
                 eta: float, status: str = "assigned"):
        super().__init__(id)
        self.request_id = request_id
        self.driver_id = driver_id
        self.eta = eta
        self.status = status

    # TODO(TV1): to_dict / from_dict
