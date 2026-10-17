# 🚕 Hệ thống Quản lý và Điều phối Đặt xe Thông minh trên Đồ thị Giao thông

> **Dự án Module 1** — Mô phỏng và giải quyết bài toán điều phối đặt xe tự động, tối ưu hóa thời gian đón khách (ETA) trên mạng lưới giao thông có hướng sử dụng giải thuật tìm đường ngắn nhất, hàng đợi FIFO, cơ chế hoàn tác Undo/Redo và lưu trữ JSON nguyên tử (Atomic).

[![Python](https://img.shields.io/badge/Python-3.12%2B-blue.svg)](https://www.python.org/)
[![Framework](https://img.shields.io/badge/Streamlit-1.63%2B-FF4B4B.svg)](https://streamlit.io/)
[![Package Manager](https://img.shields.io/badge/uv-Astral-purple.svg)](https://docs.astral.sh/uv/)
[![Tests](https://img.shields.io/badge/pytest-118%20passed-brightgreen.svg)](https://pytest.org/)

---

## 📖 Mục lục
- [1. Giới thiệu bài toán](#1-giới-thiệu-bài-toán)
- [2. Kiến trúc hệ thống & Phân công nhiệm vụ](#2-kiến-trúc-hệ-thống--phân-công-nhiệm-vụ)
- [3. Tính năng nổi bật](#3-tính-năng-nổi-bật)
- [4. Phân tích thuật toán: A1 vs A2](#4-phân-tích-thuật-toán-a1-vs-a2)
- [5. Cài đặt & Khởi chạy](#5-cài-đặt--khởi-chạy)
- [6. Hướng dẫn kiểm thử (Testing)](#6-hướng-dẫn-kiểm-thử-testing)
- [7. Kịch bản chạy mẫu (Demo Walkthrough)](#7-kịch-bản-chạy-mẫu-demo-walkthrough)
- [8. Quy chuẩn mã nguồn & Git Workflow](#8-quy-chuẩn-mã-nguồn--git-workflow)

---

## 1. Giới thiệu bài toán

Trong hệ thống vận tải hành khách đô thị thông minh, việc tìm kiếm và ghép nối tài xế rảnh tới khách hàng cần đạt 2 mục tiêu song hành:
1. **Khách hàng**: Thời gian đón (ETA - Estimated Time of Arrival) phải là ngắn nhất có thể.
2. **Hệ thống**: Tính công bằng (FIFO - khách đặt trước được xử lý trước) và thuật toán có hiệu năng thực thi cao trên đồ thị mạng lưới đường xá có hướng và trọng số thời gian di chuyển (phút).

Dự án hiện thực hóa trọn vẹn luồng nghiệp vụ trên đồ thị giao thông thực tế (thành phố Đà Nẵng: Cầu Rồng, Chợ Hàn, Bến xe Trung tâm, Ga Đà Nẵng, Sân bay Quốc tế, v.v.), tích hợp giao diện tương tác trực quan thời gian thực.

---

## 2. Kiến trúc hệ thống & Phân công nhiệm vụ

Hệ thống được thiết kế theo kiến trúc phân tầng (Layered Architecture) với tính tách biệt rõ ràng giữa các module nghiệp vụ, tuân theo bản hợp đồng giao tiếp chuẩn [CONTRACT.md](docs/CONTRACT.md):

```
Module1/
├── src/
│   ├── models/            # [TV1] Các thực thể nghiệp vụ dữ liệu
│   ├── core/
│   │   ├── road_graph.py  # [TV2] Đồ thị giao thông có hướng trọng số
│   │   ├── strategies.py  # [TV2] Chiến lược ghép cuốc A1 & A2 (Dijkstra)
│   │   ├── structures.py  # [TV3] Cấu trúc dữ liệu: RequestQueue (FIFO) & Stack
│   │   ├── undo_manager.py# [TV3] Quản lý lịch sử Undo / Redo
│   │   ├── dispatcher.py  # [TV3] Bộ điều phối nghiệp vụ tập trung
│   │   └── json_storage.py# [TV4] Lưu trữ đọc/ghi JSON nguyên tử (Atomic)
│   ├── ui/                # [TV5] Giao diện người dùng Streamlit
│   │   ├── session.py     # Quản lý Session State & Cầu nối Backend
│   │   ├── tab_data.py    # Tab 1: Quản lý dữ liệu mạng lưới & Tài xế
│   │   ├── tab_dispatch.py# Tab 2: Điều phối cuốc xe & Undo/Redo
│   │   ├── tab_benchmark.py# Tab 3: Đối chuẩn hiệu năng giải thuật
│   │   ├── graph_view.py  # Bản đồ Graphviz với lộ trình trực quan
│   │   ├── constants.py   # Hằng số trạng thái dùng chung
│   │   ├── ports.py       # Protocol giao tiếp chuẩn UI-Backend
│   │   ├── mock.py        # Backend giả lập dự phòng
│   │   └── styles.py      # Tùy biến giao diện CSS Inter
│   └── app.py             # [TV5] Entrypoint ứng dụng Streamlit
├── data/
│   ├── seed/              # Dữ liệu gốc chuẩn (graph, drivers, requests, trips)
│   └── runtime/           # Dữ liệu runtime tự động lưu trữ nguyên tử
├── docs/                  # Tài liệu phân tích, hợp đồng giao tiếp & benchmark
└── tests/                 # Bộ kịch bản kiểm thử tự động (Unit, Contract, UI AppTest, Integration)
```

### Bảng phân công thành viên
| Thành viên | Phụ trách | Phạm vi triển khai |
|---|---|---|
| **TV1** | Data Models | `BaseEntity`, `Location`, `Driver`, `RideRequest`, `Trip`, enum trạng thái. |
| **TV2** | Graph & Algorithms | `RoadGraph`, Giải thuật Dijkstra Forward (A1) & Reverse (A2), ma trận trọng số. |
| **TV3** | Dispatcher & History | Hàng đợi yêu cầu `RequestQueue`, ngăn xếp `UndoManager`, bộ điều phối `Dispatcher`. |
| **TV4** | Storage Engine | `JsonStorage`, Atomic Write qua file tạm `.tmp`, thẩm định schema dữ liệu. |
| **TV5** (Lead) | UI & Integration | Streamlit UI Dashboard, tích hợp hệ thống, `CONTRACT.md`, CI/CD và tài liệu. |

---

## 3. Tính năng nổi bật

### 🗺️ Mạng lưới giao thông trực quan (Graphviz)
- Đồ thị hiển thị trực quan các đỉnh giao thông và cung đường một chiều có trọng số di chuyển.
- Tự động đánh dấu trạng thái tài xế trên từng nút giao thông (viền xanh lá: tài xế sẵn sàng; viền đỏ: tài xế đang bận; viền cam: điểm đón đang chờ).
- Bảng tra cứu cung đường và danh sách tài xế theo thời gian thực.

### ⚡ Trung tâm điều phối thông minh
- Khởi tạo cuốc xe mới với điểm đón và điểm trả khách rõ ràng, tự động xác thực tính liên thông của tuyến đường.
- Hàng đợi FIFO đảm bảo yêu cầu đến trước luôn được xử lý trước.
- Thuật toán tự động tìm tài xế rảnh có thời gian tiếp cận khách hàng ngắn nhất (ETA nhỏ nhất), trả về lộ trình chi tiết từng nút.
- Hỗ trợ ghép từng yêu cầu hoặc "Ghép tất cả" toàn bộ hàng đợi khả thi.

### ↩️ Lịch sử thao tác hoàn tác / làm lại (Undo / Redo)
- Áp dụng cấu trúc dữ liệu **2 Ngăn xếp (Dual-Stack)**: `undo_stack` và `redo_stack`.
- Thao tác Undo đưa cuốc xe vừa gán về lại đầu hàng đợi FIFO và khôi phục tài xế về trạng thái rảnh (`free`).
- Redo cho phép khôi phục lại ngay lần điều phối vừa hoàn tác.
- Tự động làm mới ngăn xếp khi có thao tác làm biến đổi trạng thái (như hoàn thành chuyến xe).

### 💾 Lưu trữ dữ liệu an toàn (Atomic JSON Storage)
- Quá trình ghi dữ liệu áp dụng cơ chế **Atomic Replacement**: ghi vào file tạm `.tmp` sau đó dùng thao tác `os.replace` để tránh mất mát hoặc hỏng file JSON khi chương trình bị dừng đột ngột.
- Tự động tách biệt thư mục gốc `data/seed/` và thư mục hoạt động `data/runtime/`.

---

## 4. Phân tích thuật toán: A1 vs A2

Hệ thống triển khai 2 chiến lược điều phối dựa trên giải thuật Dijkstra trên đồ thị có hướng $G = (V, E)$:

| Tiêu chí | Chiến lược A1 (Forward Dijkstra) | Chiến lược A2 (Reverse Dijkstra) |
|---|---|---|
| **Cơ chế hoạt động** | Với mỗi tài xế rảnh $d_i$, chạy Dijkstra từ vị trí của $d_i$ đến điểm đón $P$. | Đảo chiều tất cả cung của $G$ thành $G^R$, chỉ chạy **một lượt duy nhất** Dijkstra từ điểm đón $P$. |
| **Số lần chạy Dijkstra** | $k$ lần (với $k$ là số tài xế đang rảnh). | **1 lần duy nhất**. |
| **Độ phức tạp thời gian** | $O(k \cdot (E + V \log V))$ | $O(E + V \log V)$ |
| **Hiệu năng thực nghiệm** | Phù hợp khi số tài xế rảnh rất ít ($k \le 2$). | Tối ưu vượt trội khi mạng lưới có nhiều tài xế rảnh ($k \gg 1$), giảm đáng kể số đỉnh duyệt và runtime. |
| **Tính đúng đắn** | Tìm đường đi ngắn nhất $d_i \to P$. | Đường đi ngắn nhất trên đồ thị đảo chiều $P \to d_i$ tương đương với $d_i \to P$ trên đồ thị gốc. |

*Lưu ý: Cả hai thuật toán luôn đảm bảo tìm ra cùng một tài xế tối ưu và cùng thời gian ETA.*

---

## 5. Cài đặt & Khởi chạy

### Yêu cầu tiên quyết
- Python 3.12 trở lên.
- Quản lý gói: [uv](https://docs.astral.sh/uv/) (khuyên dùng) hoặc `pip` / `virtualenv`.

### 1. Cài đặt thư viện
```bash
# Đồng bộ môi trường bằng uv
uv sync
```

### 2. Khởi chạy giao diện Streamlit
```bash
# Chạy ứng dụng với backend thật (JsonStorage + Dispatcher)
uv run streamlit run src/app.py
```

### 3. Tùy chọn chế độ Backend qua biến môi trường
Hệ thống hỗ trợ chạy song song chế độ kiểm thử hoặc thực tế:
- **Bắt buộc dùng backend thật**:
  ```bash
  RIDE_DISPATCH_BACKEND=real uv run streamlit run src/app.py
  ```
- **Chạy bằng backend giả lập (mock)**:
  ```bash
  RIDE_DISPATCH_BACKEND=mock uv run streamlit run src/app.py
  ```
*(Trên Windows PowerShell: sử dụng `$env:RIDE_DISPATCH_BACKEND="real"` trước khi chạy).*

Truy cập ứng dụng tại: **`http://localhost:8501`**

---

## 6. Hướng dẫn kiểm thử (Testing)

Dự án xây dựng bộ kiểm thử tự động toàn diện bao gồm:
- **Unit Tests**: Kiểm tra tính độc lập của Models, Graph, Hàng đợi FIFO, UndoManager, JsonStorage.
- **Contract Tests**: Đảm bảo tất cả thành phần tuân thủ chuẩn giao tiếp [CONTRACT.md](docs/CONTRACT.md).
- **UI AppTest**: Giả lập tương tác người dùng trên giao diện Streamlit thực thụ (đặt xe, bấm điều phối, bấm undo/redo, hoàn thành chuyến).
- **Integration Tests**: Kiểm thử luồng tích hợp đầu-cuối từ lưu trữ đĩa, nạp dữ liệu đến điều phối và hoàn tác.

Chạy toàn bộ test suite bằng câu lệnh:
```bash
uv run pytest -v
```

Kết quả kiểm thử chuẩn:
```text
============================= 118 passed in 4.62s ==============================
```

---

## 7. Kịch bản chạy mẫu (Demo Walkthrough)

Để quan sát đầy đủ các chức năng nghiệp vụ, thực hiện theo 5 bước sau trên giao diện:

1. **Kiểm tra dữ liệu mạng lưới (Tab "Quản lý dữ liệu")**:
   - Quan sát bản đồ đồ thị và vị trí các tài xế rảnh (đỉnh viền xanh).
   - Điền form để thêm một tài xế mới tại một đỉnh bất kỳ (ví dụ: `N2 - Bến xe Trung tâm`).
2. **Tạo yêu cầu đặt xe (Tab "Điều phối chuyến")**:
   - Chọn điểm đón (`N3 - Cầu Rồng`) và điểm trả (`N6 - Chợ Hàn`).
   - Nhấn **Gửi yêu cầu**. Yêu cầu xuất hiện ngay trong danh sách Hàng đợi FIFO.
3. **Thực hiện điều phối**:
   - Chọn thuật toán **A2 (Dijkstra đảo chiều)**.
   - Nhấn **Ghép chuyến** (hoặc **Ghép tất cả**). Hệ thống tự động chọn tài xế rảnh gần nhất, hiển thị thẻ kết quả với ETA, số đỉnh duyệt và chuỗi breadcrumb lộ trình.
4. **Kiểm tra tính năng Hoàn tác (Undo / Redo)**:
   - Nhấn **Undo**: Chuyến xe vừa gán bị hủy, tài xế quay về trạng thái rảnh, yêu cầu quay lại vị trí số 1 trong hàng đợi FIFO.
   - Nhấn **Redo**: Phục hồi lại chuyến xe vừa hoàn tác.
5. **Hoàn thành chuyến & Đối chuẩn thuật toán**:
   - Nhấn nút **Hoàn thành** tại danh sách chuyến xe. Tài xế di chuyển về điểm trả và chuyển sang trạng thái rảnh.
   - Chuyển sang Tab **"Đối chuẩn thuật toán"**: Nhấn **Chạy đối chuẩn** để so sánh trực quan thời gian chạy và số đỉnh duyệt giữa A1 và A2 qua biểu đồ cột; hoặc mở mục **Thử nghiệm mở rộng quy mô** để quan sát ưu thế vượt trội của A2 khi số tài xế tăng lên 100.

---

## 8. Quy chuẩn mã nguồn & Git Workflow

- **Branching Model**: Mỗi thành viên làm việc trên nhánh tính năng riêng:
  - `feat/models`
  - `feat/algorithms`
  - `feat/dispatcher`
  - `feat/storage`
  - `feat/ui`
- **Quy tắc Commit Message**:
  - `feat:` Bổ sung tính năng mới
  - `fix:` Sửa lỗi
  - `test:` Bổ sung hoặc chỉnh sửa kịch bản kiểm thử
  - `docs:` Cập nhật tài liệu
  - `refactor:` Tái cấu trúc mã nguồn mà không đổi hành vi
- **Quản lý Codeowner**: Mọi thay đổi vào nhánh `main` phải thông qua Pull Request và có sự xét duyệt theo phân quyền thư mục tại `.github/CODEOWNERS`.
