# 配置指南

LoyanBot 使用分层配置系统，支持 JSON 文件和环境变量覆盖。本指南涵盖框架中所有可用的配置选项。

## 1. 配置文件概述

### 配置层级

配置从多个源加载，优先级如下（高优先级覆盖低优先级）：

1. 环境变量（前缀 `GRACY_`）
2. 文件配置（`storage/config.json`）
3. Schema 默认值（框架内置）

### 配置文件

| 文件 | 位置 | 用途 |
|------|------|------|
| `config.json` | `storage/config.json` | 全局框架配置 |
| `config.json` | `storage/instances/<名称>/config.json` | 实例级配置 |
| `config.json` | `storage/config/<插件名>_config.json` | 插件级配置 |
| `plugin_conf.json` | `loyan/plugins/<名称>/plugin_conf.json` | 插件 Schema 默认值 |
| `settings.schema_conf.json` | `loyan/core/config/settings.schema_conf.json` | 框架字段定义 |

## 2. 基础配置

### bot_version

| 属性 | 值 |
|------|-----|
| 类型 | `string` |
| 默认值 | `"v1.9.25"` |
| 说明 | 框架版本标识（升级时自动更新） |

```json
{
  "bot_version": "v1.9.25"
}
```

### log_level

| 属性 | 值 |
|------|-----|
| 类型 | `string` |
| 默认值 | `"INFO"` |
| 可选值 | `DEBUG`、`INFO`、`WARNING`、`ERROR`、`CRITICAL` |
| 说明 | 控制日志输出的详细程度 |

```json
{
  "log_level": "INFO"
}
```

### log_encoding

| 属性 | 值 |
|------|-----|
| 类型 | `string` |
| 默认值 | `"utf-8"` |
| 说明 | 日志文件使用的编码格式 |

```json
{
  "log_encoding": "utf-8"
}
```

### debug_mode

| 属性 | 值 |
|------|-----|
| 类型 | `bool` |
| 默认值 | `false` |
| 说明 | 启用后日志以结构化 JSON 格式输出，包含堆栈跟踪 |

```json
{
  "debug_mode": false
}
```

### auto_replies

| 属性 | 值 |
|------|-----|
| 类型 | `dict` |
| 默认值 | `{}` |
| 说明 | 关键词到回复的映射，当没有插件匹配消息时在 `ResponseSender` 阶段匹配 |

```json
{
  "auto_replies": {
    "你好": "你好！我是 LoyanBot。",
    "谢谢": "不客气！"
  }
}
```

### auto_update

| 属性 | 值 |
|------|-----|
| 类型 | `bool` |
| 默认值 | `true` |
| 说明 | 启用每日自动从商店更新插件 |

```json
{
  "auto_update": true
}
```

### update_check_interval_hours

| 属性 | 值 |
|------|-----|
| 类型 | `int` |
| 默认值 | `24` |
| 说明 | 框架更新检查间隔（小时） |

```json
{
  "update_check_interval_hours": 24
}
```

### auto_update_core

| 属性 | 值 |
|------|-----|
| 类型 | `bool` |
| 默认值 | `false` |
| 说明 | 自动检查框架更新（安装仍需确认） |

```json
{
  "auto_update_core": false
}
```

## 3. 适配器配置

适配器在实例级配置 `storage/instances/<名称>/config.json` 中配置。每个实例支持一个平台适配器。

### OneBot / NapCat 适配器

OneBot 适配器支持 HTTP 和 WebSocket 连接模式。

#### HTTP 模式

```json
{
  "platform": "onebot",
  "bot_name": "主号",
  "robot_id": "123456789",
  "master_id": "987654321",
  "enabled": true,
  "type": "http",
  "http_url": "http://127.0.0.1:3000",
  "callback_port": 3002
}
```

#### WebSocket 正向模式

```json
{
  "platform": "onebot",
  "bot_name": "WS机器人",
  "robot_id": "123456789",
  "master_id": "987654321",
  "enabled": true,
  "type": "ws_forward",
  "host": "0.0.0.0",
  "port": 8080,
  "access_token": "your_token_here"
}
```

#### WebSocket 反向模式

```json
{
  "platform": "onebot",
  "bot_name": "反向WS机器人",
  "robot_id": "123456789",
  "master_id": "987654321",
  "enabled": true,
  "type": "ws_reverse",
  "host": "127.0.0.1",
  "port": 8080,
  "access_token": "your_token_here"
}
```

#### OneBot 实例字段

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `platform` | string | 是 | 必须为 `"onebot"` |
| `bot_name` | string | 是 | 自定义名称，用于识别 |
| `robot_id` | string | 是 | 机器人 QQ 号 |
| `master_id` | string | 是 | 主人 QQ 号 |
| `type` | string | 否 | `"http"`（默认）、`"ws_forward"` 或 `"ws_reverse"` |
| `http_url` | string | 否 | NapCat HTTP API URL（默认：`http://127.0.0.1:3000`） |
| `callback_port` | int | 否 | HTTP 回调端口（默认：3002） |
| `host` | string | 否 | WebSocket 绑定地址（默认：`0.0.0.0`） |
| `port` | int | 否 | WebSocket 端口（默认：8080） |
| `access_token` | string | 否 | WebSocket 访问令牌 |
| `admins_id` | list | 否 | 额外的管理员用户 ID |

### QQ 官方适配器

```json
{
  "platform": "qq_official",
  "bot_name": "QQ官方机器人",
  "robot_id": "bot_app_id",
  "master_id": "owner_user_id",
  "enabled": true,
  "app_id": "your_app_id",
  "app_secret": "your_app_secret",
  "is_sandbox": false
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `platform` | string | 是 | 必须为 `"qq_official"` |
| `app_id` | string | 是 | QQ 开放平台 App ID |
| `app_secret` | string | 是 | QQ 开放平台 App Secret |
| `is_sandbox` | bool | 否 | 使用沙箱环境（默认：false） |

### Telegram 适配器

```json
{
  "platform": "telegram",
  "bot_name": "Telegram机器人",
  "robot_id": "your_bot_token",
  "master_id": "owner_telegram_id",
  "enabled": true
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `platform` | string | 是 | 必须为 `"telegram"` |
| `robot_id` | string | 是 | Telegram bot token（格式：`123456:ABC-DEF...`） |
| `master_id` | string | 是 | 主人 Telegram 用户 ID |

### Satori 适配器

```json
{
  "platform": "satori",
  "bot_name": "Satori机器人",
  "robot_id": "",
  "master_id": "owner_id",
  "enabled": true,
  "satori_url": "http://127.0.0.1:6100",
  "satori_token": "your_token"
}
```

### 多实例配置

多个实例可以同时运行。在 `storage/instances/` 下创建独立目录：

```
storage/instances/
  主号/config.json
  备用号/config.json
  telegram-bot/config.json
```

第一个注册的实例成为默认适配器，用于发送消息。

## 4. AI 模型配置

AI 提供商通过提供商管理器管理。提供商存储在数据库中，可通过 Web 面板或 API 配置。

### 支持的提供商类型

| 提供商 | 模块 | 说明 |
|--------|------|------|
| OpenAI | `openai` | GPT-4、GPT-3.5 等 |
| Anthropic | `anthropic` | Claude 模型 |
| Ollama | `ollama` | 本地模型托管 |
| LiteLLM | `litellm` | 100+ 提供商的通用网关 |
| iFlytek | `iflytek` | 讯飞 AI 提供商 |
| Persona | `persona` | 自定义人设引擎 |

### 通过 API 添加提供商

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

### 提供商字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | string | 提供商实例的唯一标识符 |
| `type` | string | 提供商类型（如 `openai`、`anthropic`、`ollama`） |
| `model` | string | 要使用的模型名称 |
| `api_key` | string | 用于认证的 API 密钥 |
| `api_base` | string | API 基础 URL（可选，用于自定义端点） |
| `enabled` | bool | 此提供商是否激活 |
| `extra` | dict | 额外的提供商特定配置 |

### LiteLLM 供应商支持

LiteLLM 通过统一接口支持 100+ LLM 提供商。常见供应商包括：

- `openai`、`anthropic`、`ollama`、`huggingface`、`azure`、`bedrock`、`vertex_ai`、`palm`、`cohere`、`replicate`、`together`、`groq`、`deepseek`、`mistral`、`nlp_cloud`、`aleph_alpha`、`baseten`、`triton`、`volcengine` 等。

### 熔断器

每个提供商实例都有自动熔断器。连续失败后，熔断器打开并临时跳过该提供商。熔断器在可配置的超时后恢复。

## 5. 安全配置

### RBAC 权限系统

LoyanBot 实现了基于角色的访问控制系统，包含三个角色：

| 角色 | 权限 | 说明 |
|------|------|------|
| `guest` | `basic_query` | 普通用户 |
| `self` | `basic_query`、`use_plugins` | 机器人自身 |
| `master` | `basic_query`、`use_plugins`、`manage_plugins`、`system_admin` | 机器人主人/管理员 |

### 插件中的权限级别

插件可在元数据中声明所需的权限级别：

```toml
[trigger]
permission = "master"    # 仅主人可用
# permission = "admin"   # 主人和管理员
# permission = "all"     # 所有人（默认）
```

### 速率限制

框架提供内置速率限制：

- 每用户每分钟最多 60 次请求
- 每用户每小时最多 1000 次请求
- 违规后阻止 300 秒

可通过 `@rate_limit` 装饰器按命令设置速率限制：

```python
from graci import on_command, plugin_handler, rate_limit

@on_command("/gpt")
@rate_limit(max_calls=5, period=60)  # 60 秒内最多 5 次
@plugin_handler
async def handle_gpt(ctx):
    pass
```

### 冷却时间

通过 `@cooldown` 装饰器设置命令冷却时间：

```python
from graci import on_command, plugin_handler, cooldown

@on_command("/query")
@cooldown(seconds=10)  # 10 秒冷却
@plugin_handler
async def handle_query(ctx):
    pass
```

### 黑名单

`SecurityManager` 支持用户黑名单：

```python
from loyan.core.security_manager import security_manager

# 添加到黑名单（duration 为秒，0 = 永久）
security_manager.add_to_blacklist(user_id="12345", reason="spam", duration=3600)

# 从黑名单移除
security_manager.remove_from_blacklist(user_id="12345")

# 检查是否被阻止
is_blocked = security_manager.is_blocked(user_id="12345")
```

### 输入验证

- 最大命令长度：500 字符
- 最大输入内容：1000 字符（可配置）
- SQL 注入模式检测
- 危险命令模式阻止（如 `rm -rf`、`shutdown`）
- 敏感字符过滤（分号、管道符等）

### 审计日志

所有安全事件都会记录以下信息：

- 用户 ID（日志中脱敏）
- 执行的操作
- 访问的资源
- 成功/失败状态
- 时间戳

## 6. 日志配置

### 日志文件

| 文件 | 级别 | 保留时间 | 说明 |
|------|------|----------|------|
| `storage/logs/loyan.log` | DEBUG+ | 7 天 | 所有框架日志 |
| `storage/logs/loyan_error.log` | ERROR+ | 14 天 | 仅错误日志 |

### 日志格式

控制台日志使用结构化格式：

```
2024-01-15 10:30:45 - [分类] [模块] [属性] - 级别 - 消息
```

文件日志包含额外上下文：

```json
{
  "timestamp": "2024-01-15T10:30:45Z",
  "level": "INFO",
  "logger": "Core.Pipeline",
  "message": "收到消息",
  "context": {
    "sender_id": "****7890",
    "chat_type": "private"
  }
}
```

### 隐私保护

所有用户 ID 和敏感信息在日志中自动脱敏：

- 用户 ID：`****` + 后 4 位
- API 密钥：前 6 个字符 + `****`
- 密码：始终为 `******`

### 自定义日志级别

插件可使用框架日志器：

```python
from graci import get_logger

logger = get_logger("MyPlugin")
logger.info("插件已启动")
logger.error("发生错误", exc_info=True)
```

## 7. 数据库配置

LoyanBot 使用 SQLite 通过 `aiosqlite` 进行异步数据库访问。

### 数据库文件

```
storage/data/{插件名}.db
```

每个插件默认获得独立的数据库文件。

### 插件数据库访问

插件使用 `LoyanPaths` 工具获取数据库文件路径：

```python
from graci import LoyanPaths

paths = LoyanPaths("MyPlugin")
db_path = paths.db()  # -> storage/data/plugins/MyPlugin/MyPlugin.db
```

### 提供商数据库

提供商实例存储在：

```
storage/data/providers.db
```

包括提供商配置、API 密钥（加密）和使用统计。
