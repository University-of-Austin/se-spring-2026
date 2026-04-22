import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    # Will be wired up in Task 2 once main.py exists.
    # For now, returns a placeholder that skips dependent tests.
    pytest.skip("main.py not yet implemented")
