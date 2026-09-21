"""Bridge to the repository's existing calculator-assist module.

Do not duplicate the calculator logic here. The goal is to keep the original
validated implementation in scripts/calc_assist.py as the single source of truth.
"""

from pathlib import Path
import sys
from typing import Callable


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from scripts.calc_assist import fix_arithmetic as _fix_arithmetic
except Exception:  # pragma: no cover - fallback for isolated local tests
    _fix_arithmetic = None


def fix_arithmetic(text: str) -> tuple[str, list]:
    if _fix_arithmetic is None:
        return text, []
    return _fix_arithmetic(text)
