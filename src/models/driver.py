"""TV1 - Tài xế và trạng thái."""
from .base_entity import BaseEntity

FREE = "free"
BUSY = "busy"


class Driver(BaseEntity):
    def __init__(self, id: str, name: str, node: str, status: str = FREE):
        super().__init__(id)
        self.name = name
        self.node = node
        self.status = status

    def assign(self) -> None:
        raise NotImplementedError  # TODO(TV1): free -> busy, báo lỗi nếu đang busy

    def release(self) -> None:
        raise NotImplementedError  # TODO(TV1): busy -> free

    # TODO(TV1): to_dict / from_dict
