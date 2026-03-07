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


# ---------------------------------------------------------------------------
# Refresh token rotation tests (PR #46)
# ---------------------------------------------------------------------------

def test_refresh_rotates_refresh_token():
    """Оновлення токена видає новий refresh токен (ротація)."""
    from webapp.api import app
    from webapp.routers.auth import create_token

    mock_user = MagicMock()
    mock_user.id = 10000000020
    mock_user.role = "user"
    mock_user.status = "active"

    refresh_token = create_token(10000000020, "rotateuser", "user", "refresh")

    with patch("webapp.routers.auth.orm_get_user_by_id", new_callable=AsyncMock, return_value=mock_user):
        client = TestClient(app)
        resp = client.post("/api/auth/refresh", json={"refresh_token": refresh_token})

    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "access_token" in data
    assert "refresh_token" in data
    # New refresh token must differ from the old one
    assert data["refresh_token"] != refresh_token


def test_refresh_rotated_token_is_different_jti():
    """Новий refresh токен має інший jti ніж старий."""
    import jwt as _jwt
    from webapp.api import app
    from webapp.routers.auth import create_token, SECRET_KEY, ALGORITHM

    mock_user = MagicMock()
    mock_user.id = 10000000021
    mock_user.role = "user"
    mock_user.status = "active"

    old_refresh = create_token(10000000021, "jtiuser", "user", "refresh")
    old_payload = _jwt.decode(old_refresh, SECRET_KEY, algorithms=[ALGORITHM])

    with patch("webapp.routers.auth.orm_get_user_by_id", new_callable=AsyncMock, return_value=mock_user):
        client = TestClient(app)
        resp = client.post("/api/auth/refresh", json={"refresh_token": old_refresh})

    assert resp.status_code == 200
    new_refresh = resp.json()["refresh_token"]
    new_payload = _jwt.decode(new_refresh, SECRET_KEY, algorithms=[ALGORITHM])

    assert new_payload["jti"] != old_payload["jti"]
    assert new_payload["user_id"] == old_payload["user_id"]


def test_rotated_refresh_token_rejected_with_redis():
    """Вже ротований refresh токен відхиляється при повторному використанні (з Redis)."""
    import jwt as _jwt
    from webapp.api import app
    from webapp.routers.auth import create_token, SECRET_KEY, ALGORITHM, _REVOKED_JTI_PREFIX

    mock_user = MagicMock()
    mock_user.id = 10000000022
    mock_user.role = "user"
    mock_user.status = "active"

    old_refresh = create_token(10000000022, "replayuser", "user", "refresh")
    old_payload = _jwt.decode(old_refresh, SECRET_KEY, algorithms=[ALGORITHM])
    old_jti = old_payload["jti"]

    # Stateful mock: tracks which jtis have been revoked via setex
    revoked_jtis: set = set()

    async def mock_setex(key, ttl, val):
        if key.startswith(_REVOKED_JTI_PREFIX):
            revoked_jtis.add(key[len(_REVOKED_JTI_PREFIX):])

    async def mock_exists(key):
        if key.startswith(_REVOKED_JTI_PREFIX):
            return 1 if key[len(_REVOKED_JTI_PREFIX):] in revoked_jtis else 0
        return 0

    mock_redis = MagicMock()
    mock_redis.incr = AsyncMock(return_value=1)
    mock_redis.expire = AsyncMock(return_value=True)
    mock_redis.setex = mock_setex
    mock_redis.exists = mock_exists

    original_redis = getattr(app.state, "redis", None)
    app.state.redis = mock_redis
    try:
        client = TestClient(app)
        # First use — succeeds and rotates (old jti is revoked in mock state)
        with patch("webapp.routers.auth.orm_get_user_by_id", new_callable=AsyncMock, return_value=mock_user):
            resp1 = client.post("/api/auth/refresh", json={"refresh_token": old_refresh})
        assert resp1.status_code == 200
        # Old jti should now be tracked as revoked
        assert old_jti in revoked_jtis

        # Second use of same old token — rejected because jti is now revoked
        with patch("webapp.routers.auth.orm_get_user_by_id", new_callable=AsyncMock, return_value=mock_user):
            resp2 = client.post("/api/auth/refresh", json={"refresh_token": old_refresh})
    finally:
        app.state.redis = original_redis

    assert resp2.status_code == 401
    assert "анульовано" in resp2.json()["detail"].lower() or "використано" in resp2.json()["detail"].lower()


def test_refresh_without_redis_still_works():
    """Оновлення токена без Redis повертає нові токени (graceful degradation)."""
    from webapp.api import app
    from webapp.routers.auth import create_token

    mock_user = MagicMock()
    mock_user.id = 10000000023
    mock_user.role = "user"
    mock_user.status = "active"

    refresh_token = create_token(10000000023, "noredisuser", "user", "refresh")

    # Ensure redis is None (simulating unavailable Redis)
    original_redis = getattr(app.state, "redis", None)
    app.state.redis = None
    try:
        with patch("webapp.routers.auth.orm_get_user_by_id", new_callable=AsyncMock, return_value=mock_user):
            client = TestClient(app)
            resp = client.post("/api/auth/refresh", json={"refresh_token": refresh_token})
    finally:
        app.state.redis = original_redis

    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "access_token" in data
    assert "refresh_token" in data


def test_refresh_revokes_old_jti_in_redis():
    """Після ротації старий jti refresh токена поміщається у Redis-чорний список."""
    import jwt as _jwt
    from webapp.api import app
    from webapp.routers.auth import create_token, SECRET_KEY, ALGORITHM, _REVOKED_JTI_PREFIX

    mock_user = MagicMock()
    mock_user.id = 10000000024
    mock_user.role = "user"
    mock_user.status = "active"

    old_refresh = create_token(10000000024, "revoketest", "user", "refresh")
    old_payload = _jwt.decode(old_refresh, SECRET_KEY, algorithms=[ALGORITHM])
    old_jti = old_payload["jti"]

    mock_redis = MagicMock()
    mock_redis.incr = AsyncMock(return_value=1)
    mock_redis.expire = AsyncMock(return_value=True)
    mock_redis.setex = AsyncMock()
    mock_redis.exists = AsyncMock(return_value=0)

    original_redis = getattr(app.state, "redis", None)
    app.state.redis = mock_redis
    try:
        with patch("webapp.routers.auth.orm_get_user_by_id", new_callable=AsyncMock, return_value=mock_user):
            client = TestClient(app)
            resp = client.post("/api/auth/refresh", json={"refresh_token": old_refresh})
    finally:
        app.state.redis = original_redis

    assert resp.status_code == 200
    # Verify the old refresh jti was blacklisted in Redis
    setex_calls = [call[0] for call in mock_redis.setex.call_args_list]
    revoked_keys = [args[0] for args in setex_calls]
    assert any(f"{_REVOKED_JTI_PREFIX}{old_jti}" == key for key in revoked_keys)


# ---------------------------------------------------------------------------
# Logout: refresh token revocation tests (PR #46)
# ---------------------------------------------------------------------------

def test_logout_with_refresh_token_revokes_both():
    """Logout із refresh токеном у тілі анулює обидва токени в Redis."""
    import jwt as _jwt
    from webapp.api import app
    from webapp.routers.auth import create_token, SECRET_KEY, ALGORITHM, _REVOKED_JTI_PREFIX

    access_token = create_token(10000000030, "logoutboth", "user", "access")
    refresh_token = create_token(10000000030, "logoutboth", "user", "refresh")

    access_payload = _jwt.decode(access_token, SECRET_KEY, algorithms=[ALGORITHM])
    refresh_payload = _jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])

    mock_redis = MagicMock()
    mock_redis.setex = AsyncMock()
    mock_redis.exists = AsyncMock(return_value=0)

    original_redis = getattr(app.state, "redis", None)
    app.state.redis = mock_redis
    try:
        client = TestClient(app)
        resp = client.post(
            "/api/auth/logout",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"refresh_token": refresh_token},
        )
    finally:
        app.state.redis = original_redis

    assert resp.status_code == 200
    assert resp.json()["success"] is True

    # Both access and refresh JTIs should be blacklisted
    setex_calls = [call[0] for call in mock_redis.setex.call_args_list]
    revoked_keys = {args[0] for args in setex_calls}
    assert f"{_REVOKED_JTI_PREFIX}{access_payload['jti']}" in revoked_keys
    assert f"{_REVOKED_JTI_PREFIX}{refresh_payload['jti']}" in revoked_keys


def test_logout_without_refresh_token_still_revokes_access():
    """Logout без refresh токена у тілі все одно анулює access токен."""
    import jwt as _jwt
    from webapp.api import app
    from webapp.routers.auth import create_token, SECRET_KEY, ALGORITHM, _REVOKED_JTI_PREFIX

    access_token = create_token(10000000031, "logoutaccess", "user", "access")
    access_payload = _jwt.decode(access_token, SECRET_KEY, algorithms=[ALGORITHM])

    mock_redis = MagicMock()
    mock_redis.setex = AsyncMock()
    mock_redis.exists = AsyncMock(return_value=0)

    original_redis = getattr(app.state, "redis", None)
    app.state.redis = mock_redis
    try:
        client = TestClient(app)
        resp = client.post(
            "/api/auth/logout",
            headers={"Authorization": f"Bearer {access_token}"},
        )
    finally:
        app.state.redis = original_redis

    assert resp.status_code == 200
    assert resp.json()["success"] is True

    setex_calls = [call[0] for call in mock_redis.setex.call_args_list]
    revoked_keys = {args[0] for args in setex_calls}
    assert f"{_REVOKED_JTI_PREFIX}{access_payload['jti']}" in revoked_keys
    # Only one revocation (no refresh token provided)
    assert len(revoked_keys) == 1


def test_logout_with_invalid_refresh_token_still_succeeds():
    """Logout із невалідним refresh токеном у тілі все одно повертає успіх."""
    from webapp.api import app
    from webapp.routers.auth import create_token

    access_token = create_token(10000000032, "logoutinvalidrt", "user", "access")

    client = TestClient(app)
    resp = client.post(
        "/api/auth/logout",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"refresh_token": "invalid.refresh.token"},
    )

    assert resp.status_code == 200
    assert resp.json()["success"] is True


def test_logout_does_not_revoke_other_users_refresh_token():
    """Logout не повинен анулювати refresh токен іншого користувача."""
    import jwt as _jwt
    from webapp.api import app
    from webapp.routers.auth import create_token, SECRET_KEY, ALGORITHM, _REVOKED_JTI_PREFIX

    # User A's access token, User B's refresh token
    user_a_access = create_token(10000000040, "usera", "user", "access")
    user_b_refresh = create_token(10000000041, "userb", "user", "refresh")
    user_b_payload = _jwt.decode(user_b_refresh, SECRET_KEY, algorithms=[ALGORITHM])

    mock_redis = MagicMock()
    mock_redis.setex = AsyncMock()
    mock_redis.exists = AsyncMock(return_value=0)

    original_redis = getattr(app.state, "redis", None)
    app.state.redis = mock_redis
    try:
        client = TestClient(app)
        resp = client.post(
            "/api/auth/logout",
            headers={"Authorization": f"Bearer {user_a_access}"},
            json={"refresh_token": user_b_refresh},
        )
    finally:
        app.state.redis = original_redis

    assert resp.status_code == 200
    # User B's refresh token jti must NOT be in the revocation list
    setex_calls = [call[0] for call in mock_redis.setex.call_args_list]
    revoked_keys = {args[0] for args in setex_calls}
    assert f"{_REVOKED_JTI_PREFIX}{user_b_payload['jti']}" not in revoked_keys


def test_refresh_no_store_cache_control():
    """Відповідь /refresh містить Cache-Control: no-store для обох токенів."""
    from webapp.api import app
    from webapp.routers.auth import create_token

    mock_user = MagicMock()
    mock_user.id = 10000000033
    mock_user.role = "user"
    mock_user.status = "active"

    refresh_token = create_token(10000000033, "cachetest", "user", "refresh")

    with patch("webapp.routers.auth.orm_get_user_by_id", new_callable=AsyncMock, return_value=mock_user):
        client = TestClient(app)
        resp = client.post("/api/auth/refresh", json={"refresh_token": refresh_token})

    assert resp.status_code == 200
    assert resp.headers.get("cache-control") == "no-store"


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


# --- Тести CORS для мобільного додатку ---

def test_cors_allows_capacitor_https_localhost():
    """CORS дозволяє запити з https://localhost (Capacitor 6 Android)."""
    from webapp.api import app

    client = TestClient(app)
    resp = client.options(
        "/api/auth/login",
        headers={
            "Origin": "https://localhost",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )

    assert resp.status_code == 200
    assert resp.headers["access-control-allow-origin"] == "https://localhost"


def test_cors_allows_capacitor_scheme():
    """CORS дозволяє запити з capacitor://localhost."""
    from webapp.api import app

    client = TestClient(app)
    resp = client.options(
        "/api/auth/login",
        headers={
            "Origin": "capacitor://localhost",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )

    assert resp.status_code == 200
    assert resp.headers["access-control-allow-origin"] == "capacitor://localhost"


# ---------------------------------------------------------------------------
# Security hardening tests (PR #43)
# ---------------------------------------------------------------------------

# --- Blocked user enforcement ---

def test_blocked_user_cannot_login():
    """Заблокований користувач не може увійти — повертає 403."""
    from webapp.api import app
    from webapp.routers.auth import hash_password

    pwd_hash = hash_password("mypassword")
    mock_user = MagicMock()
    mock_user.id = 10000000010
    mock_user.login = "blocked_user"
    mock_user.first_name = "Blocked"
    mock_user.password_hash = pwd_hash
    mock_user.role = "user"
    mock_user.status = "blocked"

    with patch("webapp.routers.auth.orm_get_user_by_login", new_callable=AsyncMock, return_value=mock_user):
        client = TestClient(app)
        resp = client.post("/api/auth/login", json={
            "login": "blocked_user",
            "password": "mypassword"
        })

    assert resp.status_code == 403
    assert "заблоковано" in resp.json()["detail"].lower()


def test_blocked_user_cannot_refresh():
    """Заблокований користувач не може оновити токен — повертає 403."""
    from webapp.api import app
    from webapp.routers.auth import create_token

    mock_user = MagicMock()
    mock_user.id = 10000000011
    mock_user.role = "user"
    mock_user.status = "blocked"

    refresh_token = create_token(10000000011, "blocked_user", "user", "refresh")

    with patch("webapp.routers.auth.orm_get_user_by_id", new_callable=AsyncMock, return_value=mock_user):
        client = TestClient(app)
        resp = client.post("/api/auth/refresh", json={"refresh_token": refresh_token})

    assert resp.status_code == 403
    assert "заблоковано" in resp.json()["detail"].lower()


def test_active_user_can_login():
    """Активний користувач може увійти нормально."""
    from webapp.api import app
    from webapp.routers.auth import hash_password

    pwd_hash = hash_password("goodpass")
    mock_user = MagicMock()
    mock_user.id = 10000000012
    mock_user.login = "active_user"
    mock_user.first_name = "Active"
    mock_user.password_hash = pwd_hash
    mock_user.role = "user"
    mock_user.status = "active"

    with patch("webapp.routers.auth.orm_get_user_by_login", new_callable=AsyncMock, return_value=mock_user):
        client = TestClient(app)
        resp = client.post("/api/auth/login", json={"login": "active_user", "password": "goodpass"})

    assert resp.status_code == 200
    assert resp.json()["success"] is True


# --- Logout endpoint ---

def test_logout_returns_success_without_redis():
    """Logout повертає успіх навіть без Redis (клієнтський logout)."""
    from webapp.api import app
    from webapp.routers.auth import create_token

    token = create_token(10000000013, "logoutuser", "user", "access")

    client = TestClient(app)
    resp = client.post("/api/auth/logout", headers={"Authorization": f"Bearer {token}"})

    assert resp.status_code == 200
    assert resp.json()["success"] is True


def test_logout_with_invalid_token_returns_success():
    """Logout з невалідним токеном повертає успіх (токен вже недійсний)."""
    from webapp.api import app

    client = TestClient(app)
    resp = client.post("/api/auth/logout", headers={"Authorization": "Bearer invalid.token.value"})

    assert resp.status_code == 200
    assert resp.json()["success"] is True


def test_logout_without_token_returns_422():
    """Logout без токена повертає 422 (відсутній обов'язковий заголовок)."""
    from webapp.api import app

    client = TestClient(app)
    resp = client.post("/api/auth/logout")

    assert resp.status_code == 422


def test_logout_with_redis_blacklists_token():
    """Logout з Redis додає jti до чорного списку."""
    from webapp.api import app
    from webapp.routers.auth import create_token, SECRET_KEY, ALGORITHM, _REVOKED_JTI_PREFIX
    import jwt as _jwt

    token = create_token(10000000014, "logoutuser2", "user", "access")
    payload = _jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    jti = payload["jti"]

    mock_redis = MagicMock()
    mock_redis.setex = AsyncMock()
    mock_redis.exists = AsyncMock(return_value=0)

    original_redis = getattr(app.state, "redis", None)
    app.state.redis = mock_redis
    try:
        client = TestClient(app)
        resp = client.post("/api/auth/logout", headers={"Authorization": f"Bearer {token}"})
    finally:
        app.state.redis = original_redis

    assert resp.status_code == 200
    # Verify setex was called to blacklist the jti
    mock_redis.setex.assert_awaited_once()
    call_args = mock_redis.setex.call_args[0]
    assert call_args[0] == f"{_REVOKED_JTI_PREFIX}{jti}"


# --- OTP security: code must not be in response or logs ---

def test_otp_not_in_response_when_bot_unavailable():
    """OTP-код не повинен потрапляти у відповідь API."""
    from webapp.api import app

    mock_redis = MagicMock()
    mock_redis.setex = AsyncMock()
    mock_redis.delete = AsyncMock()

    original_redis = getattr(app.state, "redis", None)
    app.state.redis = mock_redis
    try:
        with patch("webapp.routers.auth.orm_get_user_by_phone", new_callable=AsyncMock, return_value=None):
            client = TestClient(app)
            resp = client.post("/api/auth/phone/request", json={"phone": "+380991234567"})
    finally:
        app.state.redis = original_redis

    assert resp.status_code == 200
    resp_text = resp.text
    # The OTP is a 6-digit numeric code; make sure no 6-digit number leaked in response
    # (response should not contain any field with an OTP value)
    data = resp.json()
    assert "otp" not in data
    assert "code" not in data
    # Insecure fallback message must not be present
    assert "з логів" not in resp_text
    assert "from logs" not in resp_text.lower()


def test_otp_not_logged(caplog):
    """OTP-код не повинен логуватися при невдалій доставці через бот."""
    import logging
    from webapp.api import app

    mock_redis = MagicMock()
    mock_redis.setex = AsyncMock()
    mock_redis.delete = AsyncMock()

    mock_user = MagicMock()
    mock_user.id = 10000000015

    mock_bot = MagicMock()
    mock_bot.send_message = AsyncMock(side_effect=Exception("Bot error"))

    original_redis = getattr(app.state, "redis", None)
    original_bot = getattr(app.state, "bot", None)
    app.state.redis = mock_redis
    app.state.bot = mock_bot
    try:
        with (
            patch("webapp.routers.auth.orm_get_user_by_phone", new_callable=AsyncMock, return_value=mock_user),
            caplog.at_level(logging.DEBUG, logger="webapp.routers.auth"),
        ):
            client = TestClient(app)
            resp = client.post("/api/auth/phone/request", json={"phone": "+380991234567"})
    finally:
        app.state.redis = original_redis
        app.state.bot = original_bot

    assert resp.status_code == 200
    # Ensure the actual OTP value was not written to any log record
    for record in caplog.records:
        msg = record.getMessage()
        # OTP is a 6-digit code; we can't know the exact value but we can check
        # that the insecure "OTP для <phone>: <code>" pattern is gone
        assert ": " not in msg or "+380991234567" not in msg or not any(
            part.isdigit() and len(part) == 6 for part in msg.split()
        ), f"Potential OTP leak in log: {msg}"


# --- JWT jti field is present in tokens ---

def test_token_contains_jti():
    """JWT токени повинні містити поле jti."""
    import jwt as _jwt
    from webapp.routers.auth import create_token, SECRET_KEY, ALGORITHM

    access_token = create_token(12345, "testuser", "user", "access")
    refresh_token = create_token(12345, "testuser", "user", "refresh")

    access_payload = _jwt.decode(access_token, SECRET_KEY, algorithms=[ALGORITHM])
    refresh_payload = _jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])

    assert "jti" in access_payload
    assert "jti" in refresh_payload
    assert len(access_payload["jti"]) == 36   # UUID4 format
    assert len(refresh_payload["jti"]) == 36
    # Each token has a unique jti
    assert access_payload["jti"] != refresh_payload["jti"]


# --- Production secret check ---

def test_production_rejects_default_jwt_secret():
    """В production-середовищі запуск з JWT_SECRET_KEY за замовчуванням повинен завершуватися помилкою."""
    import importlib
    import sys
    import os

    # Save original env state
    original_app_env = os.environ.get("APP_ENV")
    original_jwt_key = os.environ.get("JWT_SECRET_KEY")

    try:
        os.environ["APP_ENV"] = "production"
        # Remove JWT_SECRET_KEY so it falls back to the insecure default
        os.environ.pop("JWT_SECRET_KEY", None)

        # Force re-import of config module
        config_mod = sys.modules.pop("config", None)
        try:
            import pytest
            with pytest.raises(ValueError, match="JWT_SECRET_KEY"):
                import config  # noqa: F401
        finally:
            # Restore original module
            sys.modules.pop("config", None)
            if config_mod is not None:
                sys.modules["config"] = config_mod
    finally:
        # Restore original env vars
        if original_app_env is None:
            os.environ.pop("APP_ENV", None)
        else:
            os.environ["APP_ENV"] = original_app_env

        if original_jwt_key is None:
            os.environ.pop("JWT_SECRET_KEY", None)
        else:
            os.environ["JWT_SECRET_KEY"] = original_jwt_key


def test_development_allows_default_jwt_secret():
    """В development-середовищі дефолтний JWT secret допускається (лише з попередженням)."""
    import sys
    import os

    original_app_env = os.environ.get("APP_ENV")
    original_jwt_key = os.environ.get("JWT_SECRET_KEY")

    try:
        os.environ["APP_ENV"] = "development"
        os.environ.pop("JWT_SECRET_KEY", None)

        config_mod = sys.modules.pop("config", None)
        try:
            import config as _cfg  # noqa: F401  - should NOT raise
            assert _cfg.APP_ENV == "development"
        finally:
            sys.modules.pop("config", None)
            if config_mod is not None:
                sys.modules["config"] = config_mod
    finally:
        if original_app_env is None:
            os.environ.pop("APP_ENV", None)
        else:
            os.environ["APP_ENV"] = original_app_env

        if original_jwt_key is None:
            os.environ.pop("JWT_SECRET_KEY", None)
        else:
            os.environ["JWT_SECRET_KEY"] = original_jwt_key
