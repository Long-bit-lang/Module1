# Kiểm thử benchmark A1/A2

## Môi trường và dữ liệu thử nghiệm

- Hệ điều hành: Windows 11 (10.0.26200)
- Python: 3.12.15, 64-bit
- CPU: Intel(R) Core(TM) i5-11400H 11th @ 2.70GHz
- Đồ thị: 200 đỉnh (`N000` đến `N199`), 600 cạnh có hướng, không có trọng số âm.
  Mỗi đỉnh `Ni` có cạnh đến `N(i+1 mod 200)`, `N(i+7 mod 200)` và `N(i+19 mod 200)`,
  với trọng số lần lượt là `1 + i % 5`, `3 + i % 7` và `2 + i % 11`.
- Tài xế: 25 tài xế, có mã từ `D00` đến `D24`, đặt tại `N((driver_index * 7) mod 200)`.
  Điểm đón: `N199`.
- Mỗi chiến lược được chạy 40 lần trên cùng đồ thị và tập tài xế. Thời gian báo cáo là
  trung vị của `MatchResult.runtime_ms`. `visited_count` và kết quả chọn tài xế được
  lấy từ một lần chạy đại diện.

## Kết quả

| Chiến lược | driver_id | ETA (phút) | visited_count | Thời gian trung vị (ms) |
|---|---:|---:|---:|---:|
| A1 - Dijkstra từng tài xế | D23 | 15.0 | 3.974 | 3.9163 |
| A2 - Dijkstra trên đồ thị đảo chiều | D23 | 15.0 | 27 | 0.3486 |

## Nhận xét

- Trong lần thử nghiệm này, cả hai chiến lược đều tìm được tài xế tối ưu `D23`
  với ETA 15.0 phút.
- Thời gian thực thi chỉ được đo trên một máy với cấu hình nêu trên. Kết quả có thể
  khác trên máy khác vì cấu hình phần cứng, tải hệ thống và môi trường chạy.
- Thời gian của A2 bao gồm cả thời gian tạo đồ thị đảo chiều, vì thao tác này diễn ra
  bên trong `find_driver()`.
- Đây là kết quả trên một dữ liệu thử nghiệm cụ thể, chưa đủ để khái quát hiệu năng
  cho mọi đồ thị. Cần thử nghiệm thêm với nhiều quy mô và cấu trúc đồ thị khác nhau.
