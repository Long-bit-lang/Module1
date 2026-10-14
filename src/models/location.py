"""TV1 - Vị trí (đỉnh) trên đồ thị giao thông."""
from .base_entity import BaseEntity


class Location(BaseEntity):
    def __init__(self, id: str, name: str = ""):
        super().__init__(id)
        self.name = name

    # TODO(TV1): to_dict / from_dict
