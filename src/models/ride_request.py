"""TV1 - Yêu cầu đặt xe."""
from .base_entity import BaseEntity


class RideRequest(BaseEntity):
    def __init__(self, id: str, pickup_node: str, dropoff_node: str):
        super().__init__(id)
        self.pickup_node = pickup_node
        self.dropoff_node = dropoff_node

    # TODO(TV1): to_dict / from_dict
