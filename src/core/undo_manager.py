"""TV3 - Undo/Redo bằng hai ngăn xếp."""
from .structures import Stack


class UndoManager:
    def __init__(self):
        self.undo_stack = Stack()
        self.redo_stack = Stack()

    def record(self, action) -> None:
        """Ghi thao tác mới; phải xóa redo_stack."""
        raise NotImplementedError  # TODO(TV3)

    def undo(self):
        raise NotImplementedError  # TODO(TV3)

    def redo(self):
        raise NotImplementedError  # TODO(TV3)
