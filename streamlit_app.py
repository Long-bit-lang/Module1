"""Entrypoint chuyển tiếp cho Streamlit Community Cloud."""
from __future__ import annotations

import sys
from pathlib import Path

# Thêm thư mục 'src' vào sys.path để import models, core, ui
_ROOT = Path(__file__).resolve().parent
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))
if str(_ROOT) not in sys.path:
    sys.path.append(str(_ROOT))

import runpy

runpy.run_path(str(_SRC / "app.py"), run_name="__main__")
