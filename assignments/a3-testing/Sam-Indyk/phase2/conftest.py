"""Phase 2 conftest - redirect imports to local src/ instead of starter .pyc."""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "src"))
