"""
Тести для автентифікації автономного додатку.
Перевіряє JWT-based login/password auth endpoints.
"""

from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient


# --- Тести реєстрації ---

def test_register_success():
    """Реєстрація нового користувача повертає токени та дані користувача."""
    from webapp.api import app

    mock_user = MagicMock()
    mock_user.id = 10000000001
    mock_user.login = "testuser"
    mock_user.first_name = "Тест"
    mock_user.role = "user"
    mock_user.status = "pending"

    with (
        patch("webapp.routers.auth.orm_get_user_by_login", new_callable=AsyncMock, return_value=None),
        patch("webapp.routers.auth.orm_get_user_by_id", new_callable=AsyncMock, return_value=None),
        patch("webapp.routers.auth.orm_create_standalone_user", new_callable=AsyncMock, return_value=mock_user),
    ):
        client = TestClient(app)
        resp = client.post("/api/auth/register", json={
            "login": "testuser",
            "password": "securepass123",
            "first_name": "Тест"
        })

    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["user"]["login"] == "testuser"
    assert data["user"]["first_name"] == "Тест"


def test_register_duplicate_login():
    """Реєстрація з існуючим логіном повертає 409."""
    from webapp.api import app

    existing_user = MagicMock()
    existing_user.login = "taken"

    with patch("webapp.routers.auth.orm_get_user_by_login", new_callable=AsyncMock, return_value=existing_user):
        client = TestClient(app)
        resp = client.post("/api/auth/register", json={
            "login": "taken",
            "password": "securepass123",
            "first_name": "Тест"
        })

    assert resp.status_code == 409
    assert "зайнятий" in resp.json()["detail"]


def test_register_short_password():
    """Реєстрація з коротким паролем повертає 422."""
    from webapp.api import app

    client = TestClient(app)
    resp = client.post("/api/auth/register", json={
        "login": "testuser",
        "password": "123",
        "first_name": "Тест"
    })

    assert resp.status_code == 422


def test_register_short_login():
    """Реєстрація з коротким логіном повертає 422."""
    from webapp.api import app

    client = TestClient(app)
    resp = client.post("/api/auth/register", json={
        "login": "ab",
        "password": "securepass123",
        "first_name": "Тест"
    })

    assert resp.status_code == 422


# --- Тести авторизації ---

def test_login_success():
    """Успішна авторизація повертає токени."""
    from webapp.api import app
    from webapp.routers.auth import hash_password

    pwd_hash = hash_password("mypassword")
    mock_user = MagicMock()
    mock_user.id = 10000000002
    mock_user.login = "worker1"
    mock_user.first_name = "Працівник"
    mock_user.password_hash = pwd_hash
    mock_user.role = "user"
    mock_user.status = "active"

    with patch("webapp.routers.auth.orm_get_user_by_login", new_callable=AsyncMock, return_value=mock_user):
        client = TestClient(app)
        resp = client.post("/api/auth/login", json={
            "login": "worker1",
            "password": "mypassword"
        })

    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["user"]["id"] == 10000000002


def test_login_wrong_password():
    """Невірний пароль повертає 401."""
    from webapp.api import app
    from webapp.routers.auth import hash_password

    mock_user = MagicMock()
    mock_user.id = 10000000002
    mock_user.login = "worker1"
    mock_user.password_hash = hash_password("correctpassword")

    with patch("webapp.routers.auth.orm_get_user_by_login", new_callable=AsyncMock, return_value=mock_user):
        client = TestClient(app)
        resp = client.post("/api/auth/login", json={
            "login": "worker1",
            "password": "wrongpassword"
        })

    assert resp.status_code == 401


def test_login_nonexistent_user():
    """Авторизація неіснуючого користувача повертає 401."""
    from webapp.api import app

    with patch("webapp.routers.auth.orm_get_user_by_login", new_callable=AsyncMock, return_value=None):
        client = TestClient(app)
        resp = client.post("/api/auth/login", json={
            "login": "nobody",
            "password": "anypassword"
        })

    assert resp.status_code == 401


# --- Тести токенів ---

def test_me_endpoint_with_valid_token():
    """Ендпоїнт /me повертає дані користувача з валідним токеном."""
    from webapp.api import app
    from webapp.routers.auth import create_token

    mock_user = MagicMock()
    mock_user.id = 10000000003
    mock_user.login = "admin1"
    mock_user.first_name = "Адмін"
    mock_user.username = "admin1"
    mock_user.role = "admin"
    mock_user.status = "active"

    token = create_token(10000000003, "admin1", "admin", "access")

    with patch("webapp.routers.auth.orm_get_user_by_id", new_callable=AsyncMock, return_value=mock_user):
        client = TestClient(app)
        resp = client.get("/api/auth/me", headers={
            "Authorization": f"Bearer {token}"
        })

    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["user"]["id"] == 10000000003
    assert data["user"]["role"] == "admin"


def test_me_endpoint_without_token():
    """Ендпоїнт /me без токена повертає 422."""
    from webapp.api import app

    client = TestClient(app)
    resp = client.get("/api/auth/me")

    assert resp.status_code == 422


def test_me_endpoint_with_invalid_token():
    """Ендпоїнт /me з невірним токеном повертає 401."""
    from webapp.api import app

    client = TestClient(app)
    resp = client.get("/api/auth/me", headers={
        "Authorization": "Bearer invalid.token.here"
    })

    assert resp.status_code == 401


def test_refresh_token():
    """Оновлення access токена за допомогою refresh токена."""
    from webapp.api import app
    from webapp.routers.auth import create_token

    mock_user = MagicMock()
    mock_user.id = 10000000004
    mock_user.role = "user"

    refresh_token = create_token(10000000004, "refreshuser", "user", "refresh")

    with patch("webapp.routers.auth.orm_get_user_by_id", new_callable=AsyncMock, return_value=mock_user):
        client = TestClient(app)
        resp = client.post("/api/auth/refresh", json={
            "refresh_token": refresh_token
        })

    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "access_token" in data


def test_refresh_with_access_token_fails():
    """Спроба оновити токен за допомогою access токена замість refresh повертає 401."""
    from webapp.api import app
    from webapp.routers.auth import create_token

    access_token = create_token(10000000004, "user1", "user", "access")

    client = TestClient(app)
    resp = client.post("/api/auth/refresh", json={
        "refresh_token": access_token
    })

    assert resp.status_code == 401
    assert "тип" in resp.json()["detail"].lower()


# --- Тести допоміжних функцій ---

def test_password_hashing():
    """Перевірка хешування та верифікації паролів."""
    from webapp.routers.auth import hash_password, verify_password

    password = "test_password_123"
    hashed = hash_password(password)

    assert hashed != password
    assert verify_password(password, hashed)
    assert not verify_password("wrong_password", hashed)


def test_token_creation_and_validation():
    """Перевірка створення та валідації JWT токенів."""
    from webapp.routers.auth import create_token, get_current_user

    token = create_token(12345, "testlogin", "user", "access")
    user_id = get_current_user(token)
    assert user_id == 12345


def test_standalone_page_returns_html():
    """Ендпоїнт /standalone повертає HTML сторінку."""
    from webapp.api import app

    client = TestClient(app)
    resp = client.get("/standalone")

    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert "EpicService" in resp.text
