import os
import pytest
from fastapi.testclient import TestClient

# Ensure the app uses a test configuration if needed
os.environ.setdefault("ANALYSIS_ENGINE", "python")

from app.main import app  # noqa: E402

@pytest.fixture(scope="session")
def client():
    return TestClient(app)
