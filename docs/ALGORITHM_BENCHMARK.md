# Kiểm thử benchmark A1/A2

## Môi trường và dữ liệu thử nghiệm

- Hệ điều hành: Linux 7.0.0-38-generic (#38-Ubuntu SMP PREEMPT_DYNAMIC)
- Python: 3.12.15, 64-bit
- CPU: x86_64
- Đồ thị: 200 đỉnh (`N000` đến `N199`), 600 cạnh có hướng, không có trọng số âm.
  Mỗi đỉnh `Ni` có cạnh đến `N(i+1 mod 200)`, `N(i+7 mod 200)` và `N(i+19 mod 200)`,
  với trọng số lần lượt là `1 + i % 5`, `3 + i % 7` và `2 + i % 11`.
- Tài xế: 25 tài xế, có mã từ `D00` đến `D24`, đặt tại `N((driver_index * 7) mod 200)`.
  Điểm đón: `N199`.
- Mỗi chiến lược được chạy 40 lần lặp trên cùng đồ thị và tập tài xế.
  - A1: chạy Dijkstra lặp từ từng tài xế đến điểm đón.
  - A2: sử dụng cơ chế cache đồ thị đảo (`_reversed_cache`) của `RoadGraph`. Lần chạy đầu tiên (cold) bao gồm chi phí tạo đồ thị đảo; các lần chạy sau (warm) tái sử dụng đồ thị đảo đã được lưu trong cache.
  - Để phản ánh trung thực hiệu năng, bảng kết quả báo cáo cả lần chạy đầu (cold) và trung vị các lần chạy lặp tiếp theo (warm).

## Kết quả

| Chiến lược | driver_id | ETA (phút) | visited_count | Lần đầu (cold, ms) | Trung vị warm (ms) |
|---|---:|---:|---:|---:|---:|
| A1 - Dijkstra từng tài xế | D23 | 15.0 | 3974 | 4.7172 | 3.9280 |
| A2 - Dijkstra đảo chiều | D23 | 15.0 | 27 | 1.3993 | 0.0300 |

## Nhận xét

- Trong thử nghiệm này, cả hai chiến lược đều tìm được tài xế tối ưu `D23` với ETA 15.0 phút.
- **Về số đỉnh duyệt:** A2 chỉ duyệt **27 đỉnh** so với **3974 đỉnh** của A1 (giảm ~147 lần).
- **Về thời gian thực thi (cold vs warm):**
  - **Lần chạy đầu (cold):** Thời gian của A2 (~1.40 ms) bao gồm cả thời gian khởi tạo đồ thị đảo chiều bên trong `find_driver()`. Kể cả khi tính cả chi phí đảo đồ thị, A2 vẫn nhanh hơn A1 (~4.72 ms) gấp hơn 3.3 lần.
  - **Các lần chạy sau (warm):** Do `RoadGraph` có cơ chế cache (`_reversed_cache`), A2 tái sử dụng đồ thị đảo đã nạp sẵn nên thời gian thực thi chỉ còn **~0.030 ms**, nhanh hơn A1 hơn 130 lần.
- Thời gian thực thi được đo trên máy thử nghiệm. Kết quả cụ thể có thể khác nhau tùy cấu hình phần cứng, tải hệ thống và môi trường chạy.
- Đây là kết quả trên một dữ liệu thử nghiệm cụ thể, cần kết hợp khảo sát thêm với nhiều quy mô và cấu trúc đồ thị khác nhau (như mô phỏng mở rộng trong Tab Benchmark).
