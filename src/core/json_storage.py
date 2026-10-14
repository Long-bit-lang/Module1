"""TV4 - Đọc/ghi JSON cho đồ thị, tài xế, yêu cầu, chuyến đi."""
from __future__ import annotations
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[2] / "data"


class StorageError(Exception):
    """Lỗi file thiếu / JSON hỏng / thiếu trường bắt buộc."""


class JsonStorage:
    def __init__(self, data_dir: Path = DATA_DIR):
        self.data_dir = data_dir

    def load_all(self) -> dict:
        raise NotImplementedError  # TODO(TV4)

    def save_all(self, state: dict) -> None:
        """Ghi file tạm rồi thay thế file đích."""
        raise NotImplementedError  # TODO(TV4)
