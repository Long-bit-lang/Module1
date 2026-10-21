"""TV5 - Thiết kế giao diện CSS tối ưu, trực quan và đạt chuẩn WCAG AA.

Palette màu chủ đạo:
- Màu chính: #2563EB (Royal Blue)
- Nền phụ / Card: #FFFFFF, #F8FAFC (Slate-50)
- Viền: #E2E8F0 (Slate-200), bo góc 8-12px
- Văn bản: #0F172A (Slate-900), phụ #475569 (Slate-600)
- Trạng thái:
  + Rảnh / Thành công: #059669 / #ECFDF5
  + Bận / Lỗi: #DC2626 / #FEF2F2
  + Chờ / Cảnh báo: #D97706 / #FFFBEB
  + Đang chạy: #2563EB / #EFF6FF
"""

CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    color: #0F172A;
}

/* ── 1. Thẻ KPI tổng quan (Header & Dashboard) ────────────────────────────── */
.kpi-card {
    display: flex;
    align-items: center;
    gap: 0.85rem;
    background: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 10px;
    padding: 0.75rem 1rem;
    box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04);
    transition: transform 150ms ease, box-shadow 150ms ease, border-color 150ms ease;
    margin-bottom: 0.35rem;
}
.kpi-card:hover {
    border-color: #CBD5E1;
    box-shadow: 0 3px 6px rgba(15, 23, 42, 0.08);
}
.kpi-icon-wrap {
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.35rem;
    width: 2.6rem;
    height: 2.6rem;
    border-radius: 8px;
    background: #F1F5F9;
    flex-shrink: 0;
}
.kpi-body {
    display: flex;
    flex-direction: column;
    min-width: 0;
}
.kpi-label {
    font-size: 0.78rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.03em;
    color: #475569;
    line-height: 1.2;
}
.kpi-value {
    font-size: 1.35rem;
    font-weight: 700;
    color: #0F172A;
    line-height: 1.3;
}
.kpi-subtext {
    font-size: 0.73rem;
    color: #64748B;
    margin-top: 0.1rem;
}

/* ── 2. Huy hiệu trạng thái (Status Badges) ────────────────────────────────── */
.badge-status {
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
    padding: 0.22rem 0.65rem;
    border-radius: 9999px;
    font-size: 0.8rem;
    font-weight: 600;
    line-height: 1.2;
    white-space: nowrap;
}
.badge-free {
    background: #ECFDF5;
    color: #047857;
    border: 1px solid #A7F3D0;
}
.badge-busy {
    background: #FEF2F2;
    color: #B91C1C;
    border: 1px solid #FECACA;
}
.badge-queued {
    background: #FFFBEB;
    color: #B45309;
    border: 1px solid #FDE68A;
}
.badge-assigned {
    background: #EFF6FF;
    color: #1D4ED8;
    border: 1px solid #BFDBFE;
}
.badge-completed {
    background: #F0FDF4;
    color: #15803D;
    border: 1px solid #BBF7D0;
}
.badge-default {
    background: #F1F5F9;
    color: #475569;
    border: 1px solid #CBD5E1;
}
.badge-cancelled {
    background: #FEF2F2;
    color: #991B1B;
    border: 1px solid #FECACA;
}

/* ── 3. Hộp thông báo rỗng (Empty State) ───────────────────────────────────── */
.empty-state-box {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
    padding: 1.6rem 1.2rem;
    background: #F8FAFC;
    border: 1.5px dashed #CBD5E1;
    border-radius: 10px;
    margin: 0.4rem 0;
}
.empty-icon {
    font-size: 2.2rem;
    margin-bottom: 0.4rem;
}
.empty-title {
    font-size: 0.98rem;
    font-weight: 600;
    color: #1E293B;
    margin-bottom: 0.2rem;
}
.empty-desc {
    font-size: 0.85rem;
    color: #64748B;
    max-width: 480px;
    line-height: 1.4;
}
.empty-hint {
    margin-top: 0.65rem;
    padding: 0.35rem 0.75rem;
    background: #EFF6FF;
    border-radius: 6px;
    font-size: 0.82rem;
    color: #1E40AF;
}

/* ── 4. Chú giải bản đồ (Map Legend) ───────────────────────────────────────── */
.map-legend-container {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 0.6rem;
    background: #F8FAFC;
    border: 1px solid #E2E8F0;
    border-radius: 8px;
    padding: 0.5rem 0.85rem;
    margin-top: 0.4rem;
    font-size: 0.8rem;
}
.legend-title {
    font-weight: 700;
    color: #334155;
    margin-right: 0.25rem;
}
.legend-pills-wrap {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 0.5rem;
}
.legend-pill {
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
    color: #334155;
    background: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 6px;
    padding: 0.15rem 0.5rem;
    font-size: 0.78rem;
}
.legend-indicator {
    width: 0.55rem;
    height: 0.55rem;
    border-radius: 50%;
    display: inline-block;
}
.legend-dot-free {
    background: #10B981;
}
.legend-dot-busy {
    background: #EF4444;
}
.legend-dot-waiting {
    background: #F59E0B;
}
.legend-line-solid {
    width: 1rem;
    height: 3px;
    background: #16A34A;
    border-radius: 1px;
}
.legend-line-dashed {
    width: 1rem;
    height: 3px;
    background: repeating-linear-gradient(90deg, #EA580C, #EA580C 3px, transparent 3px, transparent 6px);
}

/* ── 4b. Huy hiệu Zoom & Khung cuộn bản đồ (Zoom Indicator & Canvas) ───────── */
.zoom-badge-indicator {
    display: flex;
    align-items: center;
    justify-content: center;
    height: 38px;
    background: #F1F5F9;
    border: 1px solid #CBD5E1;
    border-radius: 8px;
    font-size: 0.88rem;
    font-weight: 700;
    color: #1E293B;
    user-select: none;
}

/* Khung cuộn 2 chiều tổng quát cho container chứa đồ thị */
div[data-testid="stVerticalBlockBorderWrapper"]:has(.stGraphVizChart) {
    overflow: auto !important;
}

/* Khung Canvas bản đồ: Flexbox column cho phép căn giữa an toàn bằng margin: auto */
.st-key-map_data_canvas,
.st-key-map_dispatch_canvas,
div[class*="st-key-"][class*="_canvas"] {
    display: flex !important;
    flex-direction: column !important;
    overflow: auto !important;
}

/* Khung bọc phần tử biểu đồ: margin: auto giúp căn giữa khi zoom nhỏ, tự co về 0 khi zoom lớn */
.st-key-map_data_canvas .stElementContainer,
.st-key-map_dispatch_canvas .stElementContainer,
div[class*="st-key-"][class*="_canvas"] .stElementContainer {
    margin: auto !important;
    max-width: none !important;
}

/* Khung đồ thị Graphviz & SVG: căn giữa nội dung, không làm cắt mất mép trái khi cuộn */
.st-key-map_data_canvas .stGraphVizChart,
.st-key-map_dispatch_canvas .stGraphVizChart,
div[class*="st-key-"][class*="_canvas"] .stGraphVizChart {
    margin: auto !important;
    display: flex !important;
    flex-direction: column !important;
    align-items: center !important;
    overflow: visible !important;
}

.st-key-map_data_canvas .stGraphVizChart > svg,
.st-key-map_dispatch_canvas .stGraphVizChart > svg,
div[class*="st-key-"][class*="_canvas"] .stGraphVizChart > svg {
    margin: auto !important;
}

/* ── 5. Lộ trình di chuyển (Route Breadcrumbs) ─────────────────────────────── */

.route-path {
    display: flex;
    flex-direction: column;
    gap: 0.4rem;
    background: #F8FAFC;
    padding: 0.65rem 0.95rem;
    border-radius: 8px;
    border: 1px solid #E2E8F0;
    margin-top: 0.5rem;
    font-size: 0.85rem;
}
.route-title {
    color: #334155;
    font-size: 0.82rem;
}
.route-nodes-wrap {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 0.35rem;
}
.route-node {
    background: #EFF6FF;
    color: #1D4ED8;
    border: 1px solid #BFDBFE;
    padding: 0.18rem 0.55rem;
    border-radius: 6px;
    font-weight: 600;
    font-size: 0.82rem;
}
.route-arrow {
    color: #94A3B8;
    font-weight: bold;
    font-size: 0.78rem;
}

/* ── 6. Hộp Xem trước cuốc xe (Ride Preview Card) ─────────────────────────── */
.ride-preview-card {
    background: #F0FDF4;
    border: 1px solid #BBF7D0;
    border-radius: 8px;
    padding: 0.65rem 0.9rem;
    margin: 0.4rem 0 0.6rem 0;
    font-size: 0.84rem;
    color: #166534;
}
.ride-preview-card.warning-preview {
    background: #FEF2F2;
    border-color: #FECACA;
    color: #991B1B;
}

/* ── 7. Khối Bắt đầu nhanh (Quick Start) ──────────────────────────────────── */
.quick-start-box {
    background: #F8FAFC;
    border: 1px solid #E2E8F0;
    border-left: 4px solid #2563EB;
    border-radius: 8px;
    padding: 0.85rem 1.1rem;
    margin-bottom: 0.75rem;
}
.qs-step {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 1.35rem;
    height: 1.35rem;
    background: #2563EB;
    color: #FFFFFF;
    border-radius: 50%;
    font-size: 0.75rem;
    font-weight: 700;
    margin-right: 0.4rem;
}

/* ── 8. Chế độ Trình diễn (Demo Stepper) ──────────────────────────────────── */
.demo-stepper-container {
    background: #F8FAFC;
    border: 1.5px solid #2563EB;
    border-radius: 10px;
    padding: 0.85rem 1.1rem;
    margin-bottom: 0.85rem;
    box-shadow: 0 2px 4px rgba(37, 99, 235, 0.08);
}
.demo-stepper-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 0.5rem;
    font-weight: 700;
    color: #1E3A8A;
}

/* ── 9. Thẻ Tie-breaking Callout ───────────────────────────────────────────── */
.tiebreak-callout {
    background: #FFFBEB;
    border: 1px solid #FCD34D;
    border-left: 4px solid #F59E0B;
    border-radius: 6px;
    padding: 0.55rem 0.85rem;
    margin-top: 0.5rem;
    font-size: 0.83rem;
    color: #92400E;
}

/* ── 10. Menu điều hướng dọc Sidebar (main_nav) ─────────────────────────── */
.st-key-main_nav {
    margin-bottom: 0.5rem;
}
.st-key-main_nav div[role="radiogroup"] {
    gap: 0.35rem;
    display: flex;
    flex-direction: column;
}
.st-key-main_nav div[role="radiogroup"] label {
    display: flex !important;
    align-items: center !important;
    padding: 0.55rem 0.85rem !important;
    border-radius: 8px !important;
    font-weight: 500 !important;
    color: #334155 !important;
    cursor: pointer !important;
    transition: all 150ms ease !important;
    border: 1px solid transparent !important;
}
.st-key-main_nav div[role="radiogroup"] label:hover {
    background: #F1F5F9 !important;
    color: #1E293B !important;
}
/* Mục đang chọn tô nền #2563EB nhạt (#EFF6FF), bo góc 8px */
.st-key-main_nav div[role="radiogroup"] label:has(input:checked) {
    background: #EFF6FF !important;
    color: #1D4ED8 !important;
    border: 1px solid #BFDBFE !important;
    font-weight: 600 !important;
}
/* Ẩn chấm tròn radio mặc định để giống menu thanh lịch */
.st-key-main_nav div[role="radiogroup"] label div:first-child {
    display: none !important;
}

/* ── 11. Panel thao tác bên phải (Action Panel) ─────────────────────────── */
.st-key-action_panel {
    position: fixed !important;
    right: 0 !important;
    top: 3.5rem !important;
    width: 360px !important;
    height: calc(100vh - 3.5rem) !important;
    overflow-y: auto !important;
    background: #FFFFFF !important;
    border-left: 1px solid #E2E8F0 !important;
    box-shadow: -4px 0 20px rgba(15, 23, 42, 0.08) !important;
    z-index: 990 !important;
    padding: 1rem 0.85rem !important;
    transition: transform 200ms ease-in-out !important;
}

/* Nút bật/tắt panel nổi ở góc trên bên phải */
.st-key-btn_toggle_panel {
    position: fixed !important;
    z-index: 99999 !important;
}

.panel-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding-bottom: 0.5rem;
    margin-bottom: 0.75rem;
    border-bottom: 1.5px solid #E2E8F0;
    padding-right: 130px;
}
.panel-header-title {
    font-size: 0.88rem;
    font-weight: 700;
    letter-spacing: 0.04em;
    color: #1E3A8A;
}

/* ── 12. Trung tâm Thông báo & Banner nổi bật (Notification Center) ──────── */
.st-key-notification_center {
    margin-bottom: 0.85rem;
}
.notif-banner {
    display: flex;
    align-items: center;
    border-radius: 8px;
    padding: 0.85rem 1.15rem;
    margin-bottom: 0.4rem;
    box-shadow: 0 1px 3px rgba(15, 23, 42, 0.05);
    border: 1px solid #E2E8F0;
    transition: all 180ms ease;
}
.notif-banner-body {
    display: flex;
    align-items: center;
    gap: 0.85rem;
    width: 100%;
}
.notif-banner-icon {
    font-size: 1.4rem;
    line-height: 1;
    flex-shrink: 0;
}
.notif-banner-content {
    display: flex;
    align-items: baseline;
    flex-wrap: wrap;
    gap: 0.5rem;
    min-width: 0;
}
.notif-banner-text {
    font-size: 1.05rem;
    font-weight: 600;
    line-height: 1.4;
}
.notif-banner-time {
    font-size: 0.78rem;
    opacity: 0.75;
    font-weight: 500;
}

/* Các phân loại banner với viền trái 6px đặc trưng (B2) */
.notif-banner-success {
    background: #ECFDF5;
    border-left: 6px solid #059669;
    border-color: #A7F3D0 #A7F3D0 #A7F3D0 #059669;
    color: #065F46;
    animation: notifFadeOut 0.4s ease-out 8s forwards;
}
.notif-banner-error {
    background: #FEF2F2;
    border-left: 6px solid #DC2626;
    border-color: #FECACA #FECACA #FECACA #DC2626;
    color: #991B1B;
}
.notif-banner-warning {
    background: #FFFBEB;
    border-left: 6px solid #D97706;
    border-color: #FDE68A #FDE68A #FDE68A #D97706;
    color: #92400E;
}
.notif-banner-info {
    background: #EFF6FF;
    border-left: 6px solid #2563EB;
    border-color: #BFDBFE #BFDBFE #BFDBFE #2563EB;
    color: #1E40AF;
    animation: notifFadeOut 0.4s ease-out 8s forwards;
}

/* Tự động ẩn sau ~8s mượt mà (B2) */
@keyframes notifFadeOut {
    0% { opacity: 1; max-height: 200px; }
    100% { opacity: 0; max-height: 0; margin-bottom: 0; padding-top: 0; padding-bottom: 0; display: none; overflow: hidden; }
}

/* Nút đóng thông báo nhỏ gọn */
div[class*="st-key-btn_close_notif_"] button {
    background: transparent !important;
    border: none !important;
    color: #64748B !important;
    font-size: 1.1rem !important;
    padding: 0.2rem 0.5rem !important;
    box-shadow: none !important;
}
div[class*="st-key-btn_close_notif_"] button:hover {
    color: #0F172A !important;
    background: #E2E8F0 !important;
}

/* Nhật ký thao tác (B3) */
.notif-log-item {
    display: flex;
    align-items: baseline;
    gap: 0.6rem;
    padding: 0.35rem 0.6rem;
    border-bottom: 1px dashed #E2E8F0;
    font-size: 0.85rem;
    color: #334155;
}
.notif-log-time {
    font-family: monospace;
    font-size: 0.8rem;
    color: #64748B;
    flex-shrink: 0;
}

/* Lớp ẩn cho accessibility & test compatibility */
.sr-only-notif {
    display: none !important;
}

/* ── 13. Thẻ Kết quả Điều phối Nổi bật (Hạng mục C) ─────────────────────── */
.st-key-dispatch_result_card {
    background: #EFF6FF !important;
    border: 1px solid #BFDBFE !important;
    border-left: 6px solid #2563EB !important;
    border-radius: 10px !important;
    padding: 1rem 1.25rem !important;
    margin-bottom: 0.85rem !important;
    box-shadow: 0 2px 8px rgba(37, 99, 235, 0.08) !important;
}
.dispatch-result-header {
    display: flex;
    align-items: center;
    gap: 0.65rem;
    flex-wrap: wrap;
    margin-bottom: 0.5rem;
}
.dispatch-result-title {
    font-size: 1.25rem;
    font-weight: 700;
    color: #1E3A8A;
    letter-spacing: -0.01em;
}
.dispatch-result-strategy {
    font-size: 0.86rem;
    color: #475569;
    font-weight: 500;
}

/* Thẻ Cảnh báo khi ghép thất bại (C3) */
.st-key-dispatch_failure_card {
    background: #FFFBEB !important;
    border: 1px solid #FDE68A !important;
    border-left: 6px solid #D97706 !important;
    border-radius: 10px !important;
    padding: 1rem 1.25rem !important;
    margin-bottom: 0.85rem !important;
    box-shadow: 0 2px 6px rgba(217, 119, 6, 0.08) !important;
}
.dispatch-failed-title {
    font-size: 1.15rem;
    font-weight: 700;
    color: #92400E;
}
.dispatch-failed-card {
    margin-top: 0.4rem;
}

/* Nút ẩn kết quả */
div[class*="st-key-btn_hide_last_result"] button {
    background: #FFFFFF !important;
    border: 1px solid #CBD5E1 !important;
    color: #475569 !important;
    font-size: 0.82rem !important;
    padding: 0.25rem 0.65rem !important;
}
div[class*="st-key-btn_hide_last_result"] button:hover {
    background: #F1F5F9 !important;
    color: #0F172A !important;
}

/* Tinh chỉnh nút bấm và form ──────────────────────────────────────────────── */
div[data-testid="stButton"] button {
    border-radius: 8px;
    font-weight: 600;
    transition: all 150ms ease;
}

/* ── 9. Bộ lọc dữ liệu & Phân trang (Hạng mục D) ───────────────────────────── */
.table-filter-bar {
    background: #F8FAFC;
    border: 1px solid #E2E8F0;
    border-radius: 8px;
    padding: 0.75rem;
    margin-bottom: 0.5rem;
}
.filter-counter-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    font-size: 0.85rem;
    font-weight: 500;
    color: #475569;
    background: #F1F5F9;
    padding: 0.2rem 0.6rem;
    border-radius: 6px;
    margin-bottom: 0.4rem;
}
/* ── 10. Tiêu đề trang & Chip thông số (Page header) ──────────────────────── */
.page-header {
    background: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-left: 5px solid #2563EB;
    border-radius: 10px;
    padding: 0.9rem 1.25rem;
    margin-bottom: 1.15rem;
    box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04);
}
.page-header-top {
    display: flex;
    align-items: center;
    gap: 0.5rem;
}
.page-header h1.page-header-title {
    margin: 0 !important;
    padding: 0 !important;
    font-size: 1.45rem !important;
    font-weight: 700 !important;
    color: #0F172A !important;
    line-height: 1.25 !important;
    display: flex !important;
    align-items: center !important;
    gap: 0.5rem !important;
    border: none !important;
}
.page-header-icon {
    font-size: 1.5rem;
    line-height: 1;
}
.page-header-text {
    font-size: 1.45rem;
    font-weight: 700;
    color: #0F172A;
}
.page-header-subtitle {
    font-size: 0.88rem;
    color: #64748B;
    margin-top: 0.3rem;
    margin-bottom: 0.65rem;
    line-height: 1.4;
}
.header-chips-wrap {
    display: flex;
    flex-wrap: wrap;
    gap: 0.45rem;
    align-items: center;
    margin-top: 0.4rem;
}
.header-chip {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    background: #F8FAFC;
    border: 1px solid #E2E8F0;
    border-radius: 8px;
    padding: 0.25rem 0.65rem;
    font-size: 0.82rem;
    color: #334155;
    box-shadow: 0 1px 2px rgba(15, 23, 42, 0.03);
    transition: background 150ms ease, border-color 150ms ease;
}
.header-chip:hover {
    background: #EFF6FF;
    border-color: #BFDBFE;
}
.header-chip-label {
    font-weight: 500;
    color: #64748B;
}
.header-chip-label strong,
.header-chip-label b {
    font-weight: 700;
    color: #0F172A;
}
.header-chip-val {
    font-weight: 700;
    color: #2563EB;
}

/* ── 11. Thương hiệu thanh bên (Sidebar Brand) ────────────────────────────── */
.sidebar-brand-box {
    padding: 0.2rem 0 0.5rem 0;
    margin-bottom: 0.2rem;
}
.sidebar-brand-title {
    font-size: 1.05rem;
    font-weight: 700;
    color: #1E293B;
    line-height: 1.35;
}
.sidebar-brand-sub {
    font-size: 0.75rem;
    color: #64748B;
    margin-top: 0.15rem;
}
/* ── 12. Phát lại lộ trình (Route Animation / Timelapse) ─────────────────── */
.anim-box-card {
    background: #F8FAFC;
    border: 1px solid #E2E8F0;
    border-radius: 10px;
    padding: 0.85rem 1rem;
    margin-bottom: 0.75rem;
}
.anim-step-badge {
    display: inline-flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 0.45rem;
    background: #FFFFFF;
    border: 1px solid #CBD5E1;
    border-radius: 8px;
    padding: 0.35rem 0.85rem;
    font-size: 0.86rem;
    color: #1E293B;
    box-shadow: 0 1px 3px rgba(15, 23, 42, 0.05);
    margin-bottom: 0.5rem;
}
.anim-step-count {
    color: #2563EB;
    font-weight: 700;
}
.anim-step-node {
    color: #0F172A;
    font-weight: 600;
}
.anim-step-time {
    color: #047857;
    font-weight: 600;
}
.anim-sep {
    color: #94A3B8;
    font-size: 0.8rem;
}

/* Badge trạng thái animation (Đang phát, Tạm dừng, Hoàn tất) - Nhóm Animation */
.anim-status-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    padding: 0.25rem 0.65rem;
    border-radius: 6px;
    font-size: 0.82rem;
    font-weight: 600;
    line-height: 1.2;
    transition: all 150ms ease;
}
.anim-status-playing {
    background: #EFF6FF;
    color: #1D4ED8;
    border: 1px solid #BFDBFE;
}
.anim-status-paused {
    background: #FFFBEB;
    color: #B45309;
    border: 1px solid #FDE68A;
}
.anim-status-completed {
    background: #ECFDF5;
    color: #047857;
    border: 1px solid #A7F3D0;
}

/* Chấm nhấp nháy cho trạng thái Đang phát (chu kỳ 1.0s <= 1.2s) */
@keyframes animPulseDot {
    0% {
        opacity: 1;
        transform: scale(1);
    }
    50% {
        opacity: 0.25;
        transform: scale(0.85);
    }
    100% {
        opacity: 1;
        transform: scale(1);
    }
}
.anim-pulse-dot {
    display: inline-block;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background-color: #2563EB;
    animation: animPulseDot 1.0s infinite ease-in-out;
}
</style>
"""

