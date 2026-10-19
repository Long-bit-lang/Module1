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

/* Tinh chỉnh nút bấm và form ──────────────────────────────────────────────── */
div[data-testid="stButton"] button {
    border-radius: 8px;
    font-weight: 600;
    transition: all 150ms ease;
}
</style>
"""
