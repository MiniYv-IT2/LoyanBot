# API Key Authentication — Design & Constraints

**Date:** 2026-09-06  
**Owner:** LoyanBot Core Team  
**Status:** Implementation Ready

---

## 1. Overview

This document defines the API Key authentication system for external programmatic access, while preserving the existing JWT-based frontend panel authentication. All existing `/api/loyanui/*` routes remain protected by JWT. New `/api/v1/*` routes use API Key authentication.

---

## 2. Authentication Architecture

### 2.1 Route Groups

| Group | Prefix | Auth | Purpose |
|-------|--------|------|---------|
| Public (no auth) | Various | None | Login, version, schemas, health |
| JWT (panel frontend) | `/api/loyanui/*` | JWT cookie/header | All existing panel routes |
| API Key (external) | `/api/v1/*` | `X-API-Key` header | New external API |
| JWT (dev mgmt) | `/api/v1/dev/*` | JWT (admin only) | API Key CRUD |

### 2.2 Authorization Check Order

```
before_request → check path → decide auth type → verify → allow/deny
```

### 2.3 Response Format

| Status | Body |
|--------|------|
| 401 (no auth) | `{"error": "unauthorized"}` |
| 401 (bad key) | `{"error": "invalid_key"}` |
| 403 (no permission) | `{"error": "forbidden"}` |
| 404 (unknown route) | `{"error": "not_found"}` |

---

## 3. Complete Route Inventory

### 3.1 Public (No Authentication Required)

| Method | Path | Module | Description |
|--------|------|--------|-------------|
| GET | `/api/loyanui/auth/captcha` | `auth/__init__.py:28` | Get CAPTCHA |
| POST | `/api/loyanui/auth/login` | `auth/__init__.py:12` | Login, returns JWT |
| POST | `/api/loyanui/auth/verify` | `auth/__init__.py:33` | Verify JWT token |
| GET | `/api/loyanui/version` | `monitor/__init__.py:20` | Bot version |
| GET | `/api/loyanui/adapter/types` | `adapters/schema.py:7` | Adapter type list |
| GET | `/api/loyanui/adapter/schema/<type>` | `adapters/schema.py:11` | Adapter config schema |
| GET | `/api/loyanui/providers/types` | `providers/__init__.py:7` | Provider type list |
| GET | `/api/loyanui/providers/vendors` | `providers/__init__.py:12` | Provider vendor list |
| GET | `/api/loyanui/user-config/schema` | `settings/__init__.py:35` | User config schema |
| GET | `/api/loyanui/settings/schema` | `settings/__init__.py:7` | Settings schema |
| GET | `/api/loyanui/panel/schema` | `settings/__init__.py:72` | Panel config schema |
| GET | `/api/loyanui/update/check` | `update/__init__.py:5` | Check available updates |
| GET | `/api/loyanui/update/changelog` | `update/__init__.py:23` | Update changelog |
| GET | `/health` | `monitor/__init__.py:85` | Health check |
| GET | `/metrics` | `monitor/__init__.py:92` | Prometheus metrics |
| GET | `/api/v1/status` | `v1/status.py` (new) | v1 status/health |
| GET | `/api/loyanui/qqbot/qr-login/create` | `adapters/qr_login.py:9` | QQ QR login create |
| GET | `/api/loyanui/qqbot/qr-login/poll` | `adapters/qr_login.py:22` | QQ QR login poll |

### 3.2 JWT-Protected (Panel Frontend) — EXISTING, NO CHANGE

| Method | Path | Module |
|--------|------|--------|
| GET | `/api/loyanui/stats` | `monitor/__init__.py:25` |
| GET | `/api/loyanui/plugins` | `plugins/__init__.py:33` |
| POST | `/api/loyanui/plugins/<name>/enable` | `plugins/__init__.py:43` |
| POST | `/api/loyanui/plugins/<name>/disable` | `plugins/__init__.py:47` |
| POST | `/api/loyanui/plugins/<name>/reload` | `plugins/__init__.py:51` |
| POST | `/api/loyanui/plugins/<name>/remove` | `plugins/__init__.py:55` |
| POST | `/api/loyanui/plugins/<name>/reinstall` | `plugins/__init__.py:66` |
| GET | `/api/loyanui/providers` | `providers/__init__.py:17` |
| POST | `/api/loyanui/providers` | `providers/__init__.py:23` |
| PUT | `/api/loyanui/providers/<inst_id>` | `providers/__init__.py:35` |
| DELETE | `/api/loyanui/providers/<inst_id>` | `providers/__init__.py:47` |
| GET | `/api/loyanui/providers/<inst_id>/models` | `providers/__init__.py:66` |
| GET | `/api/loyanui/providers/usage` | `providers/__init__.py:75` |
| POST | `/api/loyanui/providers/test` | `providers/__init__.py:82` |
| GET | `/api/loyanui/settings` | `settings/__init__.py:15` |
| PUT | `/api/loyanui/settings` | `settings/__init__.py:21` |
| GET | `/api/loyanui/user-config` | `settings/__init__.py:43` |
| PUT | `/api/loyanui/user-config` | `settings/__init__.py:55` |
| GET | `/api/loyanui/panel` | `settings/__init__.py:80` |
| PUT | `/api/loyanui/panel` | `settings/__init__.py:85` |
| GET | `/api/loyanui/instances` | `adapters/__init__.py:44` |
| POST | `/api/loyanui/instances` | `adapters/__init__.py:76` |
| PATCH | `/api/loyanui/instances/<name>` | `adapters/__init__.py:91` |
| POST | `/api/loyanui/instances/<name>/reload` | `adapters/__init__.py:114` |
| POST | `/api/loyanui/instances/<name>/rename` | `adapters/__init__.py:118` |
| DELETE | `/api/loyanui/instances/<name>` | `adapters/__init__.py:126` |
| GET | `/api/loyanui/chat/sessions` | `chat/__init__.py:73` |
| POST | `/api/loyanui/chat/sessions` | `chat/__init__.py:80` |
| DELETE | `/api/loyanui/chat/sessions/<sid>` | `chat/__init__.py:91` |
| GET | `/api/loyanui/chat/sessions/<sid>/messages` | `chat/__init__.py:99` |
| GET | `/api/loyanui/chat/personas` | `chat/__init__.py:109` |
| POST | `/api/loyanui/chat/stream` | `chat/__init__.py:115` |
| POST | `/api/loyanui/chat/tasks` | `chat/__init__.py:124` |
| GET | `/api/loyanui/chat/tasks` | `chat/__init__.py:150` |
| GET | `/api/loyanui/chat/tasks/<task_id>` | `chat/__init__.py:155` |
| GET | `/api/loyanui/chat/tasks/<task_id>/events` | `chat/__init__.py:163` |
| POST | `/api/loyanui/chat/tasks/<task_id>/cancel` | `chat/__init__.py:195` |
| POST | `/api/loyanui/store/plugins` | `store/__init__.py:50` |
| POST | `/api/loyanui/store/plugins/<id>/update` | `store/__init__.py:56` |
| POST | `/api/loyanui/store/plugins/<id>/like` | `store/__init__.py:62` |
| GET | `/api/loyanui/store/config` | `store/__init__.py:68` |
| PUT | `/api/loyanui/store/config` | `store/__init__.py:72` |
| POST | `/api/loyanui/update/apply` | `update/__init__.py:14` |
| POST | `/api/loyanui/test/send` | `test/__init__.py:12` |

### 3.3 API Key-Protected (External API) — NEW `/api/v1/`

| Method | Path | File | Description |
|--------|------|------|-------------|
| GET | `/api/v1/plugins` | `v1/plugins.py` | Plugin list (read-only) |
| GET | `/api/v1/providers` | `v1/providers.py` | Provider instance list |
| GET | `/api/v1/providers/<inst_id>/models` | `v1/providers.py` | Model list for instance |
| POST | `/api/v1/chat/send` | `v1/chat.py` | Send message, get response |

### 3.4 JWT-Protected (Dev/API Key Management) — NEW `/api/v1/dev/`

| Method | Path | File | Description |
|--------|------|------|-------------|
| GET | `/api/v1/dev/apikeys` | `v1/dev.py` | List all API keys |
| POST | `/api/v1/dev/apikeys` | `v1/dev.py` | Create new API key |
| DELETE | `/api/v1/dev/apikeys/<key_id>` | `v1/dev.py` | Delete API key |

---

## 4. API Key Schema

Storage file: `storage/api_keys.json`

```json
{
  "keys": [
    {
      "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "key": "32_char_hex_string",
      "name": "production-bot",
      "permissions": ["read", "write"],
      "created_at": 1725600000,
      "last_used": 1725700000
    }
  ]
}
```

| Field | Type | Description |
|-------|------|-------------|
| id | string (UUID v4) | Unique identifier |
| key | string (64 hex chars) | The actual secret. Returned ONCE at creation, never stored in plain text after |
| name | string | Human-readable label |
| permissions | array | `["read"]` or `["read", "write"]` |
| created_at | int (unix ts) | Creation time |
| last_used | int (unix ts) | Last access time, 0 if never used |

---

## 5. Permission Model

| Permission | Allowed Operations |
|------------|-------------------|
| `read` | GET endpoints |
| `write` | POST/PUT/PATCH/DELETE endpoints |

If a key has only `read`, any write endpoint returns 403.

---

## 6. Implementation Plan

### 6.1 New Files to Create

| File | Lines (est.) | Purpose |
|------|-------------|---------|
| `loyan/core/webserv/auth/api_key.py` | ~100 | Key CRUD, storage, verification |
| `loyan/core/webserv/panel/api/v1/__init__.py` | ~10 | Register v1 sub-routers |
| `loyan/core/webserv/panel/api/v1/status.py` | ~20 | Health/status endpoint |
| `loyan/core/webserv/panel/api/v1/plugins.py` | ~30 | Plugin list endpoint |
| `loyan/core/webserv/panel/api/v1/providers.py` | ~40 | Provider+models endpoints |
| `loyan/core/webserv/panel/api/v1/chat.py` | ~60 | Chat send endpoint |
| `loyan/core/webserv/panel/api/v1/dev.py` | ~80 | API key management (JWT only) |

### 6.2 Existing Files to Modify

| File | Change |
|------|--------|
| `loyan/core/webserv/panel/auth/__init__.py` | Add `verify_api_key()` function |
| `loyan/core/webserv/panel/__init__.py` | Add `@app.before_request` middleware |
| `loyan/core/webserv/panel/api/__init__.py` | Import and register `v1` module |
| `loyan/core/webserv/panel/api/test/__init__.py` | Mark deprecated in docstring |

### 6.3 New Data File

| File | Action |
|------|--------|
| `storage/api_keys.json` | Create with default empty `{"keys": []}` |

---

## 7. Code Quality Constraints

| Rule | Limit |
|------|-------|
| Comments / total lines | <= 8% |
| Log statements / code lines | <= 10% |
| Log language | English only |
| Comment language | Chinese only (match existing codebase style) |
| No modifying unrelated code | Strictly enforce |
| No duplicate implementations | Reuse existing functions |

---

## 8. v1/chat/send Specification

**Request:**
```json
POST /api/v1/chat/send
Header: X-API-Key: <key>
Body: {
  "message": "hello",
  "instance_id": "",       // optional: provider instance to use
  "persona": "",           // optional: persona name
  "session_id": ""         // optional: reuse conversation
}
```

**Response (SSE stream):**
```
data: {"type":"text","content":"he"}
data: {"type":"text","content":"llo"}
data: {"type":"done","usage":{},"elapsed":1.2}
```

**Implementation:** Reuses `ChatEngine.chat_stream()` from `loyan.brain.chat.engine` directly. No new brain logic.

---

## 9. Migration of test/send

The existing `/api/loyanui/test/send` endpoint will:
1. Keep its current functionality unchanged (for backward compatibility with internal scripts)
2. Add a deprecation notice in the docstring
3. NOT be removed (internal scripts depend on it)

---

## 10. Testing Checklist

After implementation, verify:

- [ ] `GET /api/v1/status` without key → 401
- [ ] `GET /api/v1/status` with valid key → 200
- [ ] `POST /api/v1/chat/send` with valid key → streaming response
- [ ] `GET /api/v1/plugins` with valid read-only key → 200
- [ ] `POST /api/v1/chat/send` with read-only key → 403
- [ ] `GET /api/v1/dev/apikeys` with JWT → 200
- [ ] `POST /api/v1/dev/apikeys` with JWT → creates key, returns key value ONCE
- [ ] `DELETE /api/v1/dev/apikeys/<id>` with JWT → removes key
- [ ] All existing `/api/loyanui/*` routes still work with JWT
- [ ] Public routes (`/api/loyanui/auth/*`, `/api/loyanui/version`, etc.) work without auth
- [ ] `/api/loyanui/test/send` still works as before

---

## 11. What NOT to Touch

| Area | Reason |
|------|--------|
| Frontend static files | Out of scope |
| `loyan/brain/*` core logic | Must remain unchanged |
| Plugin system | Must remain unchanged |
| `loyan/core/event*` | Must remain unchanged |
| `loyan/core/config*` | Must remain unchanged |
| Dockerfile / docker-compose | Build separately after changes |
