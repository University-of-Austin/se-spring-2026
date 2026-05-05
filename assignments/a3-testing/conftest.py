"""Shared conftest for all A3 submissions.

Sits at `assignments/a3-testing/conftest.py` so every student's phase1 tests
pick it up automatically via pytest's conftest-walk-up behavior. Students do
not need their own phase1 conftest.

What this does:
  1. Checks that the running Python is 3.12, 3.13, or 3.14. The compiled
     modules are version-locked to CPython bytecode; anything else will fail
     at import with a cryptic "bad magic number" error, so fail here instead
     with a clear message.
  2. Adds the matching pyc bundle from `starter/assignment3/modules/pyXY/`
     to sys.path so `from lru_cache import LRUCache` (etc.) resolves.

Phase 2 tests use a SEPARATE conftest at each student's own phase2/ level
that shadows this one's sys.path entry with the student's fixed src/.
"""
import sys
from pathlib import Path

SUPPORTED = {(3, 12), (3, 13), (3, 14)}
major, minor = sys.version_info.major, sys.version_info.minor

if (major, minor) not in SUPPORTED:
    supported_str = ", ".join(f"{a}.{b}" for a, b in sorted(SUPPORTED))
    raise RuntimeError(
        f"A3 requires CPython {supported_str}. You are running {major}.{minor}. "
        f"Install a supported version via `pyenv install 3.12` or "
        f"`uv venv --python 3.12 .venv`."
    )

HERE = Path(__file__).resolve().parent                # assignments/a3-testing/
REPO_ROOT = HERE.parent.parent                        # <repo>
BUNDLE = REPO_ROOT / "starter" / "assignment3" / "modules" / f"py{major}{minor}"

if not BUNDLE.exists():
    raise RuntimeError(
        f"Expected compiled-module bundle at {BUNDLE}. "
        f"Is the class repo checkout complete?"
    )

if str(BUNDLE) not in sys.path:
    sys.path.insert(0, str(BUNDLE))
