"""pytest configuration."""
import sys
from pathlib import Path

# Add backend to Python path for imports
sys.path.insert(0, str(Path(__file__).parent / "backend"))
