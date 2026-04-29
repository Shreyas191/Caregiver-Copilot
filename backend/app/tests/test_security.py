import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routes import me

app = FastAPI()
app.include_router(me.router)
client = TestClient(app)


def test_get_me_missing_auth_header():
    """Missing authorization header returns 401 or 403."""
    response = client.get("/me")
    assert response.status_code in [401, 403]
    assert response.json() == {"detail": "Not authenticated"}


@pytest.fixture
def mock_verify_clerk_token(monkeypatch):
    """Mocks verify_clerk_token to return a valid payload for a test token."""

    def _mock_verify(token: str):
        if token == "valid-token":
            return {"sub": "user_12345"}
        raise Exception("Invalid token mock triggered")

    monkeypatch.setattr("app.core.security.verify_clerk_token", _mock_verify)


def test_get_me_valid_token(mock_verify_clerk_token):
    """Valid token returns 200 OK and the user ID."""
    response = client.get(
        "/me",
        headers={"Authorization": "Bearer valid-token"},
    )
    assert response.status_code == 200
    assert response.json() == {"clerk_user_id": "user_12345"}


def test_get_me_invalid_token(monkeypatch):
    """Invalid token returns 401 Unauthorized."""
    # We mock verify_clerk_token to raise the HTTPException an invalid token would
    from fastapi import HTTPException

    def _mock_verify_fail(token: str):
        raise HTTPException(status_code=401, detail="Invalid token header.")

    monkeypatch.setattr("app.core.security.verify_clerk_token", _mock_verify_fail)

    response = client.get(
        "/me",
        headers={"Authorization": "Bearer invalid-token"},
    )
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid token header."}
