# API 参考

LoyanBot 提供 RESTful API 用于管理实例、插件、提供商和监控。API 由 Quart Web 服务器提供，运行在配置的面板端口（默认：5090）。

## 1. 认证方式

API 使用基于令牌的认证。令牌通过 Web 面板的登录流程生成。

### 令牌格式

```
Authorization: Bearer <token>
```

### 令牌生成

令牌使用 `SecurityManager.generate_token()` 方法生成：

```python
from loyan.core.security_manager import security_manager

token = security_manager.generate_token(user_id="admin")
```

### 令牌验证

```python
is_valid = security_manager.verify_token(token)
```

令牌在 24 小时后过期。

## 2. 实例管理

### 列出实例

```
GET /api/instances
```

**响应**：
```json
{
  "success": true,
  "data": [
    {
      "name": "主号",
      "platform": "onebot",
      "bot_name": "主号",
      "robot_id": "123456789",
      "status": "running",
      "conn_type": "HTTP"
    }
  ]
}
```

### 获取实例详情

```
GET /api/instances/<名称>
```

**响应**：
```json
{
  "success": true,
  "data": {
    "name": "主号",
    "platform": "onebot",
    "bot_name": "主号",
    "robot_id": "123456789",
    "master_id": "987654321",
    "status": "running",
    "config": { ... }
  }
}
```

### 创建实例

```
POST /api/instances
```

**请求体**：
```json
{
  "name": "新机器人",
  "platform": "onebot",
  "bot_name": "新机器人",
  "robot_id": "111222333",
  "master_id": "999888777",
  "type": "http",
  "http_url": "http://127.0.0.1:3000",
  "callback_port": 3002
}
```

**响应**：
```json
{
  "success": true,
  "message": "实例已创建",
  "data": {
    "name": "新机器人"
  }
}
```

### 更新实例

```
PUT /api/instances/<名称>
```

**请求体**：
```json
{
  "bot_name": "更新后的名称",
  "master_id": "999888777"
}
```

### 删除实例

```
DELETE /api/instances/<名称>
```

**响应**：
```json
{
  "success": true,
  "message": "实例已删除"
}
```

### 重载实例

```
POST /api/instances/<名称>/reload
```

**响应**：
```json
{
  "success": true,
  "message": "实例已重载"
}
```

### 启动实例

```
POST /api/instances/<名称>/start
```

### 停止实例

```
POST /api/instances/<名称>/stop
```

### 重命名实例

```
POST /api/instances/<名称>/rename
```

**请求体**：
```json
{
  "new_name": "新名称"
}
```

## 3. 消息管理

### 发送消息

```
POST /api/messages/send
```

**请求体**：
```json
{
  "target_id": "123456789",
  "chat_type": "private",
  "content": "来自 API 的消息！",
  "tag": "onebot/主号"
}
```

**响应**：
```json
{
  "success": true,
  "message_id": "msg_abc123"
}
```

### 获取消息历史

```
GET /api/messages?limit=50&offset=0
```

**查询参数**：
- `limit` - 最大返回消息数（默认：50）
- `offset` - 分页偏移量（默认：0）

## 4. 提供商管理

### 列出提供商类型

```
GET /api/providers/types
```

**响应**：
```json
{
  "success": true,
  "data": ["openai", "anthropic", "ollama", "litellm", "iflytek", "persona"]
}
```

### 列出提供商

```
GET /api/providers
```

**响应**：
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

### 添加提供商

```
POST /api/providers
```

**请求体**：
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

### 更新提供商

```
PUT /api/providers/<实例ID>
```

**请求体**：
```json
{
  "model": "gpt-4-turbo",
  "enabled": true
}
```

### 删除提供商

```
DELETE /api/providers/<实例ID>
```

### 列出模型

```
GET /api/providers/<实例ID>/models
```

**响应**：
```json
{
  "success": true,
  "data": ["gpt-4", "gpt-4-turbo", "gpt-3.5-turbo"]
}
```

### 启用/禁用模型

```
POST /api/providers/<实例ID>/models/<模型>/enable
POST /api/providers/<实例ID>/models/<模型>/disable
```

### 添加自定义模型

```
POST /api/providers/<实例ID>/models/custom
```

**请求体**：
```json
{
  "model": "自定义模型名称"
}
```

### 获取使用量摘要

```
GET /api/providers/usage?hours=24
```

**响应**：
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

## 5. 插件管理

### 列出插件

```
GET /api/plugins
```

**响应**：
```json
{
  "success": true,
  "data": [
    {
      "name": "Help_plugin",
      "display_name": "帮助插件",
      "version": "1.1.3",
      "author": "LoyanBot开发团队",
      "description": "查看所有命令",
      "enabled": true,
      "commands": ["/help", "/帮助", "/菜单"],
      "source": "system"
    }
  ]
}
```

### 获取插件详情

```
GET /api/plugins/<名称>
```

### 启用插件

```
POST /api/plugins/<名称>/enable
```

### 禁用插件

```
POST /api/plugins/<名称>/disable
```

### 重载插件

```
POST /api/plugins/<名称>/reload
```

### 删除插件

```
DELETE /api/plugins/<名称>
```

**注意**：系统插件不能删除。

### 从商店安装插件

```
POST /api/plugins/store/install
```

**请求体**：
```json
{
  "plugin_id": "WeatherPlugin"
}
```

### 从商店更新插件

```
POST /api/plugins/store/update
```

**请求体**：
```json
{
  "plugin_id": "WeatherPlugin"
}
```

### 列出商店插件

```
GET /api/plugins/store?force=false
```

**响应**：
```json
{
  "success": true,
  "data": [
    {
      "id": "WeatherPlugin",
      "name": "天气查询",
      "version": "1.0.0",
      "author": "开发者",
      "description": "查询天气",
      "installed": false,
      "update_available": false,
      "likes": 42,
      "downloads": 1234
    }
  ]
}
```

## 6. 监控接口

### 健康检查

```
GET /api/health
```

**响应**：
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

### 系统状态

```
GET /api/status
```

**响应**：
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

### 性能指标

```
GET /api/metrics
```

**响应**：
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

### 生命周期状态

```
GET /api/lifecycle
```

**响应**：
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

### 生命周期时间线

```
GET /api/lifecycle/timeline
```

**响应**：
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

## 7. 配置 API

### 获取全局配置

```
GET /api/config
```

### 更新全局配置

```
PUT /api/config
```

**请求体**：
```json
{
  "log_level": "DEBUG",
  "debug_mode": true
}
```

### 获取插件配置

```
GET /api/config/plugin/<插件名>
```

### 更新插件配置

```
PUT /api/config/plugin/<插件名>
```

**请求体**：
```json
{
  "api_key": "new_key",
  "max_results": 20
}
```

## 8. 错误响应

所有 API 端点以一致的格式返回错误：

```json
{
  "success": false,
  "error": "error_code",
  "message": "人类可读的错误消息"
}
```

### 常见错误码

| 错误码 | 说明 |
|--------|------|
| `not_found` | 资源未找到 |
| `already_exists` | 资源已存在 |
| `validation_error` | 无效的请求体 |
| `unauthorized` | 缺少或无效的认证 |
| `forbidden` | 权限不足 |
| `internal_error` | 服务器端错误 |

## 9. 速率限制

API 请求受速率限制：

- 每 IP 每分钟 60 次请求
- 每 IP 每小时 1000 次请求

超过限制返回 HTTP 429：

```json
{
  "success": false,
  "error": "rate_limited",
  "message": "请求过于频繁"
}
```
