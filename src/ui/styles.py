"""TV5 - CSS tối giản cho hệ thống điều phối đặt xe."""

CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
}

/* Lộ trình đón khách — breadcrumb */
.route-path {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 0.4rem;
    background: #f8fafc;
    padding: 0.6rem 1rem;
    border-radius: 8px;
    border: 1px solid #e2e8f0;
    margin-top: 0.5rem;
    font-size: 0.88rem;
    color: #334155;
}
.route-node {
    background: #dbeafe;
    color: #1e40af;
    padding: 0.2rem 0.5rem;
    border-radius: 4px;
    font-weight: 600;
    font-size: 0.85rem;
}
</style>
"""
