import ast
import sys
from pathlib import Path

def test_runtime_modules_parse_as_python_37_source():
    for path in Path("src").rglob("*.py"):
        kwargs = {"feature_version": (3, 7)} if sys.version_info >= (3, 8) else {}
        ast.parse(path.read_text(), **kwargs)

def test_compatibility_metadata_mentions_python_37():
    text = Path("pyproject.toml").read_text()
    assert 'requires-python = ">=3.7"' in text
    assert "numpy==1.21.6" in text
    assert "timezonefinder==5.2.0" in text
