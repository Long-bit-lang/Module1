# Hệ thống Quản lý và Điều phối Đặt xe Thông minh trên Đồ thị Giao thông

Python · Streamlit · JSON · Git · uv

## Cài đặt
```bash
uv sync
```

## Chạy ứng dụng
```bash
uv run streamlit run src/app.py
```

## Chạy kiểm thử
```bash
uv run pytest
```

## Cấu trúc
| Thư mục | Phụ trách | Nội dung |
|---|---|---|
| `src/models/` | TV1 | BaseEntity, Location, Driver, RideRequest, Trip |
| `src/core/road_graph.py`, `strategies.py` | TV2 | RoadGraph, Dijkstra A1/A2 |
| `src/core/dispatcher.py`, `structures.py`, `undo_manager.py` | TV3 | Điều phối, hàng đợi FIFO, Undo/Redo |
| `src/core/json_storage.py`, `data/` | TV4 | Đọc/ghi JSON, dữ liệu mẫu |
| `src/app.py`, `docs/`, README | TV5 | Giao diện, tích hợp, tài liệu |

Hợp đồng giữa các module: xem `docs/CONTRACT.md`.

## Quy trình Git
Mỗi người một nhánh (`feat/models`, `feat/algorithms`, `feat/dispatcher`, `feat/storage`, `feat/ui`),
không commit trực tiếp lên `main`, mọi thay đổi qua Pull Request có ít nhất 1 người review.
