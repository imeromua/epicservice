# EpicService — Security Operations Runbook

This document is for operators and deployers. It covers production-critical environment
configuration, reverse-proxy setup, Redis requirements, and degradation behaviour.

---

## Required production environment variables

| Variable | Required | Notes |
|---|---|---|
| `BOT_TOKEN` | **yes** | Telegram Bot token from @BotFather. App refuses to start without it. |
| `DB_USER` | **yes** | PostgreSQL username. |
| `DB_PASSWORD` | **yes** | PostgreSQL password. |
| `DB_HOST` | **yes** | PostgreSQL host. |
| `DB_PORT` | **yes** | PostgreSQL port (1–65535). |
| `DB_NAME` | **yes** | PostgreSQL database name. |
| `JWT_SECRET_KEY` | **yes** | Secret for JWT signing. **Must be set to a strong random value in production.** App refuses to start with the default value when `APP_ENV=production`. |
| `APP_ENV` | **yes** | Set to `production`. Enables production-mode startup guardrails. |
| `ADMIN_IDS` | recommended | Comma-separated Telegram user IDs of administrators. Without it the admin panel is inaccessible. |
| `WEBAPP_URL` | recommended | Full HTTPS URL of the Mini App, e.g. `https://epicservice.example.com`. |
| `REDIS_ENABLED` | recommended | Set to `true` (default). Required for rate limiting, token revocation, and refresh-token rotation. |
| `REDIS_HOST` | recommended | Redis hostname (default: `localhost`). |
| `REDIS_PORT` | recommended | Redis port (default: `6379`). |
| `REDIS_PASSWORD` | optional | Redis AUTH password if required. |
| `TRUSTED_PROXIES` | recommended | Comma-separated proxy IPs or CIDR ranges (see below). |
| `SERVER_URL` | optional | Backend URL for the mobile/Android app. |
| `CORS_ORIGINS` | optional | Additional allowed CORS origins (comma-separated). |

---

## Reverse proxy / TRUSTED_PROXIES configuration

Rate limiting uses the real client IP. Without proxy awareness, all requests
appear to come from the proxy IP and share a single rate-limit bucket.

### How it works

`webapp/utils/client_ip.py` implements safe proxy-aware IP extraction:

1. If the connecting peer IP **is** in `TRUSTED_PROXIES`, the `X-Forwarded-For`
   header is parsed and the **left-most** entry (original client) is used.
2. If the connecting peer IP **is not** in `TRUSTED_PROXIES` (or `TRUSTED_PROXIES`
   is empty), `X-Forwarded-For` is **ignored** and the direct connecting IP is used.

This means spoofed `X-Forwarded-For` headers from untrusted clients are safely ignored.

### Configuration

```env
# Single proxy IP:
TRUSTED_PROXIES=10.0.0.1

# Multiple proxies or CIDR ranges:
TRUSTED_PROXIES=10.0.0.1,192.168.1.0/24,172.16.0.0/12
```

### Recommendations

- Set `TRUSTED_PROXIES` to the IP address(es) of your nginx / load balancer upstream.
- **Do not** set `TRUSTED_PROXIES=0.0.0.0/0` — this trusts every connecting IP and
  allows clients to spoof any IP address via the `X-Forwarded-For` header.
- For cloud load balancers (AWS ALB, GCP LB) use their documented IP ranges.
- If the app has no reverse proxy, leave `TRUSTED_PROXIES` unset (safe default).

### nginx example

```nginx
location / {
    proxy_pass http://localhost:8000;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header Host $host;
}
```

Then set `TRUSTED_PROXIES` to the nginx server IP.

---

## Redis requirements

Redis is used for:

| Feature | Redis key pattern | Notes |
|---|---|---|
| Rate limiting | `rl:<scope>:<identifier>` | INCR+EXPIRE per fixed window. |
| JWT access-token revocation (logout) | `revoked_jti:<jti>` | TTL = remaining token lifetime. |
| Refresh-token rotation / replay protection | `revoked_jti:<jti>` | Old refresh JTI blacklisted on rotation. |
| OTP storage and verification | managed by `utils/otp.py` | TTL = OTP expiry window. |
| Telegram bot FSM state | aiogram RedisStorage | Required for conversation state persistence. |

### What degrades when Redis is unavailable

| Feature | Degradation |
|---|---|
| Rate limiting | **Disabled** — all requests are allowed through (fail-open). |
| Token revocation | **Disabled** — revoked tokens remain valid until natural expiry. |
| Refresh-token rotation | **Disabled** — rotated tokens can be replayed until expiry. |
| OTP `/phone/request` | **Returns HTTP 503** — endpoint requires Redis. |
| Bot FSM | Uses in-process memory (state lost on restart). |

**Production recommendation:** always run Redis in production. Use Redis Sentinel or
cluster if high availability is required.

---

## APP_ENV=production requirement

Setting `APP_ENV=production`:

1. **Enforces** `JWT_SECRET_KEY` — refuses to start with the default insecure value.
2. **Emits warnings** at startup for other security-sensitive misconfiguration
   (missing `TRUSTED_PROXIES`, disabled Redis, default `WEBAPP_URL`, empty `ADMIN_IDS`).

Always set `APP_ENV=production` in production. It is safe to omit in development
and test environments (the insecure JWT default will warn but not block).

---

## Rate limiting configuration

Rate limits are configurable via environment variables:

| Variable | Default | Description |
|---|---|---|
| `RATE_OTP_REQ_IP_MAX` | `5` | Max OTP requests per IP in the window. |
| `RATE_OTP_REQ_IP_WINDOW` | `600` | OTP per-IP window in seconds (10 min). |
| `RATE_OTP_REQ_PHONE_MAX` | `3` | Max OTP requests per phone in the window. |
| `RATE_OTP_REQ_PHONE_WINDOW` | `600` | OTP per-phone window in seconds. |
| `RATE_LOGIN_IP_MAX` | `10` | Max login attempts per IP in the window. |
| `RATE_LOGIN_IP_WINDOW` | `900` | Login window in seconds (15 min). |
| `RATE_REFRESH_IP_MAX` | `30` | Max refresh requests per IP in the window. |
| `RATE_REFRESH_IP_WINDOW` | `900` | Refresh window in seconds (15 min). |

---

## Logout / refresh / token-rotation notes

- **Logout** (`POST /api/auth/logout`): revokes the access token JTI and optionally
  the refresh token JTI in Redis. Clients must delete both tokens locally; if Redis is
  down, tokens expire naturally.
- **Refresh** (`POST /api/auth/refresh`): rotates the refresh token — the old refresh
  JTI is blacklisted in Redis and a new access+refresh token pair is returned. Replaying
  an already-rotated refresh token is rejected when Redis is available.
- **Token lifetimes**: access tokens expire in 24 hours; refresh tokens expire in 30 days.
  Adjust `ACCESS_TOKEN_EXPIRE_HOURS` / `REFRESH_TOKEN_EXPIRE_DAYS` in `webapp/routers/auth.py`
  if needed.

---

## Remaining security debt (future PRs)

- **Content Security Policy (CSP):** A full CSP header is not set to preserve Telegram
  Mini App iframe embedding. A nonce-based CSP could be added per-page in future.
- **Database credential rotation:** No mechanism to rotate DB credentials without restart.
- **Redis TLS:** Redis connection is plaintext. For production, use a Redis instance with
  TLS and authenticate via `REDIS_PASSWORD`.
- **Audit logging:** Security events (login failures, rate-limit hits, token revocations)
  go to the application log. A dedicated audit log or SIEM integration is not present.
- **Bot token rotation:** `BOT_TOKEN` has no rotation support.
- **Health endpoint:** `/health` does not expose Redis/DB connectivity status; a
  detailed readiness probe could be added safely.
