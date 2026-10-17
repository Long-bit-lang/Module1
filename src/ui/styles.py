"""TV5 - CSS tối giản và tương thích dark/light theme cho hệ thống điều phối đặt xe."""

CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
}

/* Lộ trình đón khách — breadcrumb tương thích cả light & dark mode */
.route-path {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 0.4rem;
    background: rgba(128, 128, 128, 0.08);
    padding: 0.6rem 1rem;
    border-radius: 8px;
    border: 1px solid rgba(128, 128, 128, 0.2);
    margin-top: 0.5rem;
    font-size: 0.88rem;
    color: inherit;
}
.route-node {
    background: rgba(59, 130, 246, 0.15);
    color: #3b82f6;
    padding: 0.2rem 0.5rem;
    border-radius: 4px;
    font-weight: 600;
    font-size: 0.85rem;
}
</style>
"""
