# Tài liệu Mô hình Dữ liệu — Module 1 (Nhi)

> **Phạm vi**: `src/models/` — 5 lớp model độc lập, không import từ `core` hay `streamlit`.
> **Nhánh Git**: `feat/models`

---

## Tổng quan kiến trúc

```
BaseEntity (ABC)
├── Location
├── Driver
├── RideRequest
└── Trip
```

Mọi entity kế thừa `BaseEntity`, đảm bảo có `id` ổn định và khả năng chuyển đổi JSON hai chiều (`to_dict` / `from_dict`).

---

## 1. `BaseEntity` — Lớp nền tảng trừu tượng

**File**: `src/models/base_entity.py`

### Thuộc tính

| Tên | Kiểu | Bắt buộc | Mô tả |
|-----|------|----------|-------|
| `id` | `str` | ✅ | Mã định danh duy nhất, không rỗng, không thay đổi sau khi tạo |

### Phương thức

| Phương thức | Chữ ký | Mô tả |
|-------------|---------|-------|
| `to_dict()` | `() -> dict[str, Any]` | **Abstract** — chuyển entity thành dict để ghi JSON |
| `from_dict()` | `(cls, data: dict) -> BaseEntity` | **Abstract classmethod** — khôi phục entity từ dict |
| `__eq__()` | `(other: object) -> bool` | So sánh bằng nhau theo `id` và kiểu lớp |
| `__repr__()` | `() -> str` | Chuỗi debug dạng `ClassName(id='...')` |

### Ràng buộc

- **Không thể khởi tạo trực tiếp** (`abc.ABC`) — Python ném `TypeError` ngay khi thử
- `id` rỗng (`""`) hoặc chỉ có khoảng trắng → `ValueError`
- Lớp con **bắt buộc** override cả `to_dict()` và `from_dict()`, nếu không Python từ chối khởi tạo

---

## 2. `Location` — Địa danh đỉnh đồ thị

**File**: `src/models/location.py`

### Mục đích thiết kế

Lưu tên hiển thị trực quan cho đỉnh đồ thị. Tách riêng khỏi `RoadGraph` để thuật toán Dijkstra chỉ làm việc với chuỗi `id` thuần túy, không phụ thuộc thông tin giao diện.

### Thuộc tính

| Tên | Kiểu | Mặc định | Mô tả |
|-----|------|----------|-------|
| `id` | `str` | — | Mã đỉnh (ví dụ: `"N1"`), khớp với node id trong `RoadGraph` |
| `name` | `str` | `""` | Tên địa danh hiển thị (ví dụ: `"Ngã tư A"`) |

### Schema `to_dict()`

```python
{"id": "N1", "name": "Ngã tư A"}
```

Khớp phần tử trong mảng `nodes` của `graph.json`.

### Ràng buộc

- `id` không được rỗng → `ValueError`
- `name` **có thể rỗng** (đỉnh chưa đặt tên địa danh)
- Không có ràng buộc trạng thái (Location là dữ liệu tĩnh)

---

## 3. `Driver` — Tài xế

**File**: `src/models/driver.py`

### Hằng số trạng thái

| Hằng số | Giá trị | Ý nghĩa |
|---------|---------|---------|
| `FREE` | `"free"` | Tài xế đang rảnh, có thể nhận chuyến mới |
| `BUSY` | `"busy"` | Tài xế đang bận, không nhận chuyến mới |

### Thuộc tính

| Tên | Kiểu | Mặc định | Mô tả |
|-----|------|----------|-------|
| `id` | `str` | — | Mã tài xế (ví dụ: `"D1"`) |
| `name` | `str` | — | Tên hiển thị |
| `node` | `str` | — | Mã đỉnh vị trí hiện tại trên đồ thị |
| `status` | `str` | `FREE` | Trạng thái — chỉ nhận `FREE` hoặc `BUSY` |

### Phương thức nghiệp vụ

| Phương thức | Chữ ký | Mô tả |
|-------------|---------|-------|
| `assign()` | `() -> None` | Chuyển `FREE` → `BUSY`. Ném `RuntimeError` nếu đang `BUSY` |
| `release()` | `() -> None` | Chuyển `BUSY` → `FREE` |

### Sơ đồ chuyển trạng thái

```
     assign()
FREE ─────────► BUSY
FREE ◄───────── BUSY
     release()
```

### Schema `to_dict()`

```python
{"id": "D1", "name": "An", "node": "N1", "status": "free"}
```

Khớp phần tử trong mảng `drivers` của `drivers.json`.

### Ràng buộc

| Trường | Ràng buộc | Lỗi ném ra |
|--------|-----------|------------|
| `id` | Không rỗng | `ValueError` |
| `name` | Không rỗng | `ValueError` |
| `node` | Không rỗng | `ValueError` |
| `status` khi khởi tạo | Phải là `FREE` hoặc `BUSY` | `ValueError` |
| `assign()` khi `BUSY` | Không được gọi | `RuntimeError` |

> **Lưu ý**: Cập nhật `driver.node` sau khi hoàn thành chuyến là trách nhiệm của `Dispatcher.complete_trip()` (TV3), không phải `release()`.

---

## 4. `RideRequest` — Yêu cầu đặt xe

**File**: `src/models/ride_request.py`

### Hằng số trạng thái

| Hằng số | Giá trị | Ý nghĩa |
|---------|---------|---------|
| `QUEUED` | `"queued"` | Yêu cầu đang chờ trong hàng đợi FIFO |
| `ASSIGNED` | `"assigned"` | Yêu cầu đã được gán tài xế |

### Thuộc tính

| Tên | Kiểu | Mặc định | Mô tả |
|-----|------|----------|-------|
| `id` | `str` | — | Mã yêu cầu (ví dụ: `"R1"`) |
| `pickup_node` | `str` | — | Mã đỉnh điểm đón hành khách |
| `dropoff_node` | `str` | — | Mã đỉnh điểm trả hành khách |
| `status` | `str` | `QUEUED` | Trạng thái — chỉ nhận `QUEUED` hoặc `ASSIGNED` |

### Sơ đồ chuyển trạng thái

```
QUEUED ──► ASSIGNED
     (do Dispatcher)
```

### Schema `to_dict()`

```python
{"id": "R1", "pickup_node": "N3", "dropoff_node": "N7", "status": "queued"}
```

Khớp phần tử trong mảng `requests` của `requests.json`.

### Ràng buộc

| Trường | Ràng buộc | Lỗi ném ra |
|--------|-----------|------------|
| `id` | Không rỗng | `ValueError` |
| `pickup_node` | Không rỗng | `ValueError` |
| `dropoff_node` | Không rỗng | `ValueError` |
| `pickup_node` vs `dropoff_node` | Phải khác nhau | `ValueError` |
| `status` khi khởi tạo | Phải là `QUEUED` hoặc `ASSIGNED` | `ValueError` |

---

## 5. `Trip` — Chuyến đi

**File**: `src/models/trip.py`

### Hằng số trạng thái

| Hằng số | Giá trị | Ý nghĩa |
|---------|---------|---------|
| `ASSIGNED` | `"assigned"` | Chuyến đã gán tài xế, đang thực hiện |
| `COMPLETED` | `"completed"` | Chuyến đã hoàn thành |

### Thuộc tính

| Tên | Kiểu | Mặc định | Mô tả |
|-----|------|----------|-------|
| `id` | `str` | — | Mã chuyến đi (ví dụ: `"T1"`) |
| `request_id` | `str` | — | Mã yêu cầu đặt xe tương ứng |
| `driver_id` | `str` | — | Mã tài xế được gán |
| `eta` | `float` | — | Thời gian dự kiến đón (phút, phải ≥ 0) |
| `status` | `str` | `ASSIGNED` | Trạng thái — chỉ nhận `ASSIGNED` hoặc `COMPLETED` |

### Sơ đồ chuyển trạng thái

```
ASSIGNED ──► COMPLETED
     (do Dispatcher.complete_trip())
```

### Schema `to_dict()`

```python
{"id": "T1", "request_id": "R1", "driver_id": "D1", "eta": 7.0, "status": "assigned"}
```

Khớp phần tử trong mảng `trips` của `trips.json`.

### Ràng buộc

| Trường | Ràng buộc | Lỗi ném ra |
|--------|-----------|------------|
| `id` | Không rỗng | `ValueError` |
| `request_id` | Không rỗng | `ValueError` |
| `driver_id` | Không rỗng | `ValueError` |
| `eta` | Phải ≥ 0 | `ValueError` |
| `status` khi khởi tạo | Phải là `ASSIGNED` hoặc `COMPLETED` | `ValueError` |

---

## 6. Hằng số trạng thái — Bảng tổng hợp

Export từ `src/models/__init__.py`, dùng chung toàn dự án:

```python
from models import FREE, BUSY, QUEUED, ASSIGNED, COMPLETED
```

| Hằng số | Giá trị | Thuộc lớp |
|---------|---------|-----------|
| `FREE` | `"free"` | `Driver` |
| `BUSY` | `"busy"` | `Driver` |
| `QUEUED` | `"queued"` | `RideRequest` |
| `ASSIGNED` | `"assigned"` | `RideRequest`, `Trip` |
| `COMPLETED` | `"completed"` | `Trip` |

> ⚠️ **Quy tắc bắt buộc**: Tuyệt đối không hardcode chuỗi trạng thái (`"free"`, `"busy"`, ...) ở bất kỳ module nào trong dự án. Luôn import và dùng hằng số từ `models`.

---

## 7. Quy tắc `to_dict` / `from_dict`

Mỗi lớp đảm bảo tính **đối xứng hoàn hảo**:

```python
obj == Model.from_dict(obj.to_dict())  # luôn đúng
```

Điều này cho phép `JsonStorage` (TV4) đọc/ghi mà không mất dữ liệu, không cần biết chi tiết cài đặt bên trong từng lớp.
