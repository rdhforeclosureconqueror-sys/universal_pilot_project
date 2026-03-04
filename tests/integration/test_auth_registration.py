from uuid import uuid4

from auth.auth_handler import verify_password
from app.models.users import User, UserRole


def test_register_creates_bcrypt_hashed_user(client, db_session):
    email = f"reg-{uuid4().hex[:8]}@example.com"
    r = client.post("/auth/register", json={"email": email, "password": "secret123"})
    assert r.status_code == 200

    user = db_session.query(User).filter(User.email == email).first()
    assert user is not None
    assert user.role == UserRole.user
    assert len(user.hashed_password) == 60
    assert verify_password("secret123", user.hashed_password) is True


def test_create_admin_and_login(client, db_session):
    email = f"admin-{uuid4().hex[:8]}@example.com"
    r = client.post("/auth/create-admin", json={"email": email, "password": "secret123"})
    assert r.status_code == 200

    token_resp = client.post(
        "/auth/token",
        data={"username": email, "password": "secret123"},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert token_resp.status_code == 200
    token = token_resp.json()["access_token"]
    assert token


def test_login_bad_password_returns_401(client, db_session):
    email = f"badpw-{uuid4().hex[:8]}@example.com"
    client.post("/auth/register", json={"email": email, "password": "secret123"})

    token_resp = client.post(
        "/auth/token",
        data={"username": email, "password": "wrong"},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert token_resp.status_code == 401
