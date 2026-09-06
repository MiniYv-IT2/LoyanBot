# API Reference

LoyanBot provides a RESTful API for managing instances, plugins, providers, and monitoring. The API is served by the Quart web server on the configured panel port (default: 5090).

## 1. Authentication

The API uses token-based authentication. Tokens are generated during the login process via the web panel.

### Token Format

```
Authorization: Bearer <token>
```

### Token Generation

Tokens are generated using the `SecurityManager.generate_token()` method:

```python
from loyan.core.security_manager import security_manager

token = security_manager.generate_token(user_id="admin")
```

### Token Verification

```python
is_valid = security_manager.verify_token(token)
```

Tokens expire after 24 hours.

## 2. Instance Management

### List Instances

```
GET /api/instances
```

**Response**:
```json
{
  "success": true,
  "data": [
    {
      "name": "main-bot",
      "platform": "onebot",
      "bot_name": "MainBot",
      "robot_id": "123456789",
      "status": "running",
      "conn_type": "HTTP"
    }
  ]
}
```

### Get Instance Details

```
GET /api/instances/<name>
```

**Response**:
```json
{
  "success": true,
  "data": {
    "name": "main-bot",
    "platform": "onebot",
    "bot_name": "MainBot",
    "robot_id": "123456789",
    "master_id": "987654321",
    "status": "running",
    "config": { ... }
  }
}
```

### Create Instance

```
POST /api/instances
```

**Request Body**:
```json
{
  "name": "new-bot",
  "platform": "onebot",
  "bot_name": "NewBot",
  "robot_id": "111222333",
  "master_id": "999888777",
  "type": "http",
  "http_url": "http://127.0.0.1:3000",
  "callback_port": 3002
}
```

**Response**:
```json
{
  "success": true,
  "message": "Instance created",
  "data": {
    "name": "new-bot"
  }
}
```

### Update Instance

```
PUT /api/instances/<name>
```

**Request Body**:
```json
{
  "bot_name": "UpdatedBot",
  "master_id": "999888777"
}
```

### Delete Instance

```
DELETE /api/instances/<name>
```

**Response**:
```json
{
  "success": true,
  "message": "Instance deleted"
}
```

### Reload Instance

```
POST /api/instances/<name>/reload
```

**Response**:
```json
{
  "success": true,
  "message": "Instance reloaded"
}
```

### Start Instance

```
POST /api/instances/<name>/start
```

### Stop Instance

```
POST /api/instances/<name>/stop
```

### Rename Instance

```
POST /api/instances/<name>/rename
```

**Request Body**:
```json
{
  "new_name": "renamed-bot"
}
```

## 3. Message Management

### Send Message

```
POST /api/messages/send
```

**Request Body**:
```json
{
  "target_id": "123456789",
  "chat_type": "private",
  "content": "Hello from API!",
  "tag": "onebot/MainBot"
}
```

**Response**:
```json
{
  "success": true,
  "message_id": "msg_abc123"
}
```

### Get Message History

```
GET /api/messages?limit=50&offset=0
```

**Query Parameters**:
- `limit` - Maximum messages to return (default: 50)
- `offset` - Pagination offset (default: 0)

## 4. Provider Management

### List Provider Types

```
GET /api/providers/types
```

**Response**:
```json
{
  "success": true,
  "data": ["openai", "anthropic", "ollama", "litellm", "iflytek", "persona"]
}
```

### List Providers

```
GET /api/providers
```

**Response**:
```json
{
  "success": true,
  "data": [
    {
      "id": "my_openai",
      "type": "openai",
      "model": "gpt-4",
      "enabled": true,
      "has_key": true
    }
  ]
}
```

### Add Provider

```
POST /api/providers
```

**Request Body**:
```json
{
  "id": "my_openai",
  "type": "openai",
  "model": "gpt-4",
  "api_key": "sk-...",
  "api_base": "https://api.openai.com/v1",
  "enabled": true
}
```

### Update Provider

```
PUT /api/providers/<instance_id>
```

**Request Body**:
```json
{
  "model": "gpt-4-turbo",
  "enabled": true
}
```

### Delete Provider

```
DELETE /api/providers/<instance_id>
```

### List Models

```
GET /api/providers/<instance_id>/models
```

**Response**:
```json
{
  "success": true,
  "data": ["gpt-4", "gpt-4-turbo", "gpt-3.5-turbo"]
}
```

### Enable/Disable Model

```
POST /api/providers/<instance_id>/models/<model>/enable
POST /api/providers/<instance_id>/models/<model>/disable
```

### Add Custom Model

```
POST /api/providers/<instance_id>/models/custom
```

**Request Body**:
```json
{
  "model": "custom-model-name"
}
```

### Get Usage Summary

```
GET /api/providers/usage?hours=24
```

**Response**:
```json
{
  "success": true,
  "data": {
    "total_requests": 1234,
    "total_tokens": 567890,
    "total_cost": 12.34,
    "by_provider": {
      "my_openai": {
        "requests": 1000,
        "tokens": 450000,
        "cost": 10.00
      }
    }
  }
}
```

## 5. Plugin Management

### List Plugins

```
GET /api/plugins
```

**Response**:
```json
{
  "success": true,
  "data": [
    {
      "name": "Help_plugin",
      "display_name": "Help Plugin",
      "version": "1.1.3",
      "author": "LoyanBot Team",
      "description": "View all commands",
      "enabled": true,
      "commands": ["/help", "/帮助", "/菜单"],
      "source": "system"
    }
  ]
}
```

### Get Plugin Details

```
GET /api/plugins/<name>
```

### Enable Plugin

```
POST /api/plugins/<name>/enable
```

### Disable Plugin

```
POST /api/plugins/<name>/disable
```

### Reload Plugin

```
POST /api/plugins/<name>/reload
```

### Remove Plugin

```
DELETE /api/plugins/<name>
```

**Note**: System plugins cannot be removed.

### Install Plugin from Store

```
POST /api/plugins/store/install
```

**Request Body**:
```json
{
  "plugin_id": "WeatherPlugin"
}
```

### Update Plugin from Store

```
POST /api/plugins/store/update
```

**Request Body**:
```json
{
  "plugin_id": "WeatherPlugin"
}
```

### List Store Plugins

```
GET /api/plugins/store?force=false
```

**Response**:
```json
{
  "success": true,
  "data": [
    {
      "id": "WeatherPlugin",
      "name": "Weather Query",
      "version": "1.0.0",
      "author": "Developer",
      "description": "Query weather",
      "installed": false,
      "update_available": false,
      "likes": 42,
      "downloads": 1234
    }
  ]
}
```

## 6. Monitoring Endpoints

### Health Check

```
GET /api/health
```

**Response**:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:45Z",
  "service": "LoyanBot",
  "version": "v1.9.25",
  "uptime": "3天 5小时 30分钟",
  "checks": {
    "cpu_healthy": true,
    "memory_healthy": true,
    "error_rate_healthy": true
  }
}
```

### System Status

```
GET /api/status
```

**Response**:
```json
{
  "status": "healthy",
  "uptime_seconds": 259200,
  "uptime_formatted": "3天 0小时 0分钟 0秒",
  "system": {
    "cpu_usage_percent": 15.2,
    "memory": {
      "usage_percent": 45.6,
      "used_mb": 1024.5,
      "total_mb": 4096.0
    }
  },
  "message_stats": {
    "total_received": 12345,
    "total_processed": 12300,
    "total_errors": 45,
    "error_rate_percent": 0.37,
    "avg_response_time_ms": 234.56
  }
}
```

### Performance Metrics

```
GET /api/metrics
```

**Response**:
```json
{
  "cpu_history": [...],
  "memory_history": [...],
  "message_stats": {
    "minute_history": [...],
    "response_times": [...]
  },
  "plugin_stats": {
    "Help_plugin": {
      "total_executions": 500,
      "successful_executions": 495,
      "avg_execution_time": 0.123
    }
  }
}
```

### Lifecycle Status

```
GET /api/lifecycle
```

**Response**:
```json
{
  "instance": "default",
  "phase": "RUNNING",
  "phase_value": 80,
  "running": true,
  "uptime": 259200.0,
  "hooks": 15,
  "tasks": 3,
  "restart_count": 0
}
```

### Lifecycle Timeline

```
GET /api/lifecycle/timeline
```

**Response**:
```json
[
  {
    "phase": "CONFIG_LOADED",
    "duration": 0.0234,
    "success": true
  },
  {
    "phase": "PLUGINS_LOADED",
    "duration": 0.4567,
    "success": true
  }
]
```

## 7. Configuration API

### Get Global Config

```
GET /api/config
```

### Update Global Config

```
PUT /api/config
```

**Request Body**:
```json
{
  "log_level": "DEBUG",
  "debug_mode": true
}
```

### Get Plugin Config

```
GET /api/config/plugin/<plugin_name>
```

### Update Plugin Config

```
PUT /api/config/plugin/<plugin_name>
```

**Request Body**:
```json
{
  "api_key": "new_key",
  "max_results": 20
}
```

## 8. Error Responses

All API endpoints return errors in a consistent format:

```json
{
  "success": false,
  "error": "error_code",
  "message": "Human-readable error message"
}
```

### Common Error Codes

| Code | Description |
|------|-------------|
| `not_found` | Resource not found |
| `already_exists` | Resource already exists |
| `validation_error` | Invalid request body |
| `unauthorized` | Missing or invalid authentication |
| `forbidden` | Insufficient permissions |
| `internal_error` | Server-side error |

## 9. Rate Limiting

API requests are rate-limited:

- 60 requests per minute per IP
- 1000 requests per hour per IP

Exceeding these limits returns HTTP 429:

```json
{
  "success": false,
  "error": "rate_limited",
  "message": "Too many requests"
}
```
