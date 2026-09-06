# Configuration Guide

LoyanBot uses a layered configuration system with JSON files and environment variable overrides. This guide covers all configuration options available in the framework.

## 1. Configuration File Overview

### Configuration Hierarchy

Configuration is loaded from multiple sources with the following priority (highest wins):

1. Environment variables (prefix `GRACY_`)
2. File-based configuration (`storage/config.json`)
3. Schema defaults (built into the framework)

### Configuration Files

| File | Location | Purpose |
|------|----------|---------|
| `config.json` | `storage/config.json` | Global framework configuration |
| `config.json` | `storage/instances/<name>/config.json` | Per-instance configuration |
| `config.json` | `storage/config/<plugin>_config.json` | Per-plugin configuration |
| `plugin_conf.json` | `loyan/plugins/<name>/plugin_conf.json` | Plugin schema defaults |
| `settings.schema_conf.json` | `loyan/core/config/settings.schema_conf.json` | Framework field definitions |

## 2. Basic Configuration

### bot_version

| Property | Value |
|----------|-------|
| Type | `string` |
| Default | `"v1.9.25"` |
| Description | Framework version identifier (auto-updated on upgrade) |

```json
{
  "bot_version": "v1.9.25"
}
```

### log_level

| Property | Value |
|----------|-------|
| Type | `string` |
| Default | `"INFO"` |
| Options | `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` |
| Description | Controls the verbosity of log output |

```json
{
  "log_level": "INFO"
}
```

### log_encoding

| Property | Value |
|----------|-------|
| Type | `string` |
| Default | `"utf-8"` |
| Description | Encoding used for log files |

```json
{
  "log_encoding": "utf-8"
}
```

### debug_mode

| Property | Value |
|----------|-------|
| Type | `bool` |
| Default | `false` |
| Description | When enabled, logs are output in structured JSON format with stack traces |

```json
{
  "debug_mode": false
}
```

### auto_replies

| Property | Value |
|----------|-------|
| Type | `dict` |
| Default | `{}` |
| Description | Keyword-to-response mapping for automatic replies. Matched in `ResponseSender` stage when no plugin matches the message. |

```json
{
  "auto_replies": {
    "hello": "Hello! I am LoyanBot.",
    "thanks": "You're welcome!"
  }
}
```

### auto_update

| Property | Value |
|----------|-------|
| Type | `bool` |
| Default | `true` |
| Description | Enable daily automatic plugin updates from the store |

```json
{
  "auto_update": true
}
```

### update_check_interval_hours

| Property | Value |
|----------|-------|
| Type | `int` |
| Default | `24` |
| Description | Interval in hours between framework update checks |

```json
{
  "update_check_interval_hours": 24
}
```

### auto_update_core

| Property | Value |
|----------|-------|
| Type | `bool` |
| Default | `false` |
| Description | Auto-check for framework updates (installation still requires confirmation) |

```json
{
  "auto_update_core": false
}
```

## 3. Adapter Configuration

Adapters are configured per-instance in `storage/instances/<name>/config.json`. Each instance supports one platform adapter.

### OneBot / NapCat Adapter

The OneBot adapter supports HTTP and WebSocket connection modes.

#### HTTP Mode

```json
{
  "platform": "onebot",
  "bot_name": "MainBot",
  "robot_id": "123456789",
  "master_id": "987654321",
  "enabled": true,
  "type": "http",
  "http_url": "http://127.0.0.1:3000",
  "callback_port": 3002
}
```

#### WebSocket Forward Mode

```json
{
  "platform": "onebot",
  "bot_name": "WSBot",
  "robot_id": "123456789",
  "master_id": "987654321",
  "enabled": true,
  "type": "ws_forward",
  "host": "0.0.0.0",
  "port": 8080,
  "access_token": "your_token_here"
}
```

#### WebSocket Reverse Mode

```json
{
  "platform": "onebot",
  "bot_name": "ReverseBot",
  "robot_id": "123456789",
  "master_id": "987654321",
  "enabled": true,
  "type": "ws_reverse",
  "host": "127.0.0.1",
  "port": 8080,
  "access_token": "your_token_here"
}
```

#### OneBot Instance Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `platform` | string | Yes | Must be `"onebot"` |
| `bot_name` | string | Yes | Custom name for identification |
| `robot_id` | string | Yes | Bot QQ number |
| `master_id` | string | Yes | Owner QQ number |
| `type` | string | No | `"http"` (default), `"ws_forward"`, or `"ws_reverse"` |
| `http_url` | string | No | NapCat HTTP API URL (default: `http://127.0.0.1:3000`) |
| `callback_port` | int | No | HTTP callback port (default: 3002) |
| `host` | string | No | WebSocket bind address (default: `0.0.0.0`) |
| `port` | int | No | WebSocket port (default: 8080) |
| `access_token` | string | No | WebSocket access token |
| `admins_id` | list | No | Additional admin user IDs |

### QQ Official Adapter

```json
{
  "platform": "qq_official",
  "bot_name": "QQOfficialBot",
  "robot_id": "bot_app_id",
  "master_id": "owner_user_id",
  "enabled": true,
  "app_id": "your_app_id",
  "app_secret": "your_app_secret",
  "is_sandbox": false
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `platform` | string | Yes | Must be `"qq_official"` |
| `app_id` | string | Yes | QQ Open Platform App ID |
| `app_secret` | string | Yes | QQ Open Platform App Secret |
| `is_sandbox` | bool | No | Use sandbox environment (default: false) |

### Telegram Adapter

```json
{
  "platform": "telegram",
  "bot_name": "TelegramBot",
  "robot_id": "your_bot_token",
  "master_id": "owner_telegram_id",
  "enabled": true
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `platform` | string | Yes | Must be `"telegram"` |
| `robot_id` | string | Yes | Telegram bot token (format: `123456:ABC-DEF...`) |
| `master_id` | string | Yes | Owner Telegram user ID |

### Satori Adapter

```json
{
  "platform": "satori",
  "bot_name": "SatoriBot",
  "robot_id": "",
  "master_id": "owner_id",
  "enabled": true,
  "satori_url": "http://127.0.0.1:6100",
  "satori_token": "your_token"
}
```

### Multi-Instance Configuration

Multiple instances can run simultaneously. Create separate directories under `storage/instances/`:

```
storage/instances/
  main-bot/config.json
  backup-bot/config.json
  telegram-bot/config.json
```

The first registered instance becomes the default adapter for outgoing messages.

## 4. AI Model Configuration

AI providers are managed through the Provider Manager. Providers are stored in the database and configured via the web panel or API.

### Supported Provider Types

| Provider | Module | Description |
|----------|--------|-------------|
| OpenAI | `openai` | GPT-4, GPT-3.5, etc. |
| Anthropic | `anthropic` | Claude models |
| Ollama | `ollama` | Local model hosting |
| LiteLLM | `litellm` | Universal gateway to 100+ providers |
| iFlytek | `iflytek` | Chinese AI provider |
| Persona | `persona` | Custom persona engine |

### Adding a Provider via API

```python
import httpx

async def add_provider():
    async with httpx.AsyncClient() as client:
        await client.post("http://localhost:5090/api/providers", json={
            "type": "openai",
            "id": "my_openai",
            "model": "gpt-4",
            "api_key": "sk-...",
            "api_base": "https://api.openai.com/v1",
            "enabled": True
        })
```

### Provider Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique identifier for the provider instance |
| `type` | string | Provider type (e.g., `openai`, `anthropic`, `ollama`) |
| `model` | string | Model name to use |
| `api_key` | string | API key for authentication |
| `api_base` | string | API base URL (optional, for custom endpoints) |
| `enabled` | bool | Whether this provider is active |
| `extra` | dict | Additional provider-specific configuration |

### LiteLLM Vendor Support

LiteLLM supports 100+ LLM providers through a unified interface. Common vendors include:

- `openai`, `anthropic`, `ollama`, `huggingface`, `azure`, `bedrock`, `vertex_ai`, `palm`, `cohere`, `replicate`, `together`, `groq`, `deepseek`, `mistral`, `nlp_cloud`, `aleph_alpha`, `baseten`, `triton`, `volcengine`, and more.

### Circuit Breaker

Each provider instance has an automatic circuit breaker. After consecutive failures, the circuit opens and the provider is temporarily skipped. The circuit recovers after a configurable timeout.

## 5. Security Configuration

### RBAC Permission System

LoyanBot implements a role-based access control system with three roles:

| Role | Permissions | Description |
|------|-------------|-------------|
| `guest` | `basic_query` | Regular users |
| `self` | `basic_query`, `use_plugins` | The bot itself |
| `master` | `basic_query`, `use_plugins`, `manage_plugins`, `system_admin` | Bot owner/admin |

### Permission Levels in Plugins

Plugins can declare required permission levels in their metadata:

```toml
[trigger]
permission = "master"    # Only master can use
# permission = "admin"   # Master and admins
# permission = "all"     # Everyone (default)
```

### Rate Limiting

The framework provides built-in rate limiting:

- Maximum 60 requests per minute per user
- Maximum 1000 requests per hour per user
- Block duration: 300 seconds on violation

Rate limits can be applied per-command via the `@rate_limit` decorator:

```python
from graci import on_command, plugin_handler, rate_limit

@on_command("/gpt")
@rate_limit(max_calls=5, period=60)  # 5 calls per 60 seconds
@plugin_handler
async def handle_gpt(ctx):
    pass
```

### Cooldown

Per-command cooldown via the `@cooldown` decorator:

```python
from graci import on_command, plugin_handler, cooldown

@on_command("/query")
@cooldown(seconds=10)  # 10 second cooldown between uses
@plugin_handler
async def handle_query(ctx):
    pass
```

### Blacklist

The `SecurityManager` supports user blacklisting:

```python
from loyan.core.security_manager import security_manager

# Add to blacklist (duration in seconds, 0 = permanent)
security_manager.add_to_blacklist(user_id="12345", reason="spam", duration=3600)

# Remove from blacklist
security_manager.remove_from_blacklist(user_id="12345")

# Check if blocked
is_blocked = security_manager.is_blocked(user_id="12345")
```

### Input Validation

- Maximum command length: 500 characters
- Maximum input content: 1000 characters (configurable)
- SQL injection pattern detection
- Dangerous command pattern blocking (e.g., `rm -rf`, `shutdown`)
- Sensitive character filtering (semicolons, pipes, etc.)

### Audit Logging

All security events are logged with the following information:

- User ID (sanitized in logs)
- Action performed
- Resource accessed
- Success/failure status
- Timestamp

## 6. Logging Configuration

### Log Files

| File | Level | Retention | Description |
|------|-------|-----------|-------------|
| `storage/logs/loyan.log` | DEBUG+ | 7 days | All framework logs |
| `storage/logs/loyan_error.log` | ERROR+ | 14 days | Error-only logs |

### Log Format

Console logs use a structured format:

```
2024-01-15 10:30:45 - [Category] [Module] [Attributes] - Level - Message
```

File logs include additional context:

```json
{
  "timestamp": "2024-01-15T10:30:45Z",
  "level": "INFO",
  "logger": "Core.Pipeline",
  "message": "received message",
  "context": {
    "sender_id": "****7890",
    "chat_type": "private"
  }
}
```

### Privacy Protection

All user IDs and sensitive information are automatically masked in logs:

- User IDs: `****` + last 4 digits
- API keys: First 6 characters + `****`
- Passwords: Always `******`

### Custom Log Levels

Plugins can use the framework logger:

```python
from graci import get_logger

logger = get_logger("MyPlugin")
logger.info("Plugin started")
logger.error("Something went wrong", exc_info=True)
```

## 7. Database Configuration

LoyanBot uses SQLite via `aiosqlite` for async database access.

### Database Files

```
storage/data/{plugin_name}.db
```

Each plugin gets its own database file by default.

### Plugin Database Access

Plugins use the `LoyanPaths` utility for database file paths:

```python
from graci import LoyanPaths

paths = LoyanPaths("MyPlugin")
db_path = paths.db()  # -> storage/data/plugins/MyPlugin/MyPlugin.db
```

### Provider Database

Provider instances are stored in:

```
storage/data/providers.db
```

This includes provider configuration, API keys (encrypted), and usage statistics.
