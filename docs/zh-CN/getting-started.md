# 快速开始

LoyanBot 是一个轻量级、异步、多平台聊天机器人框架，基于 Python 3.11+ 构建。它支持 QQ（通过 NapCat/OneBot）、QQ 官方、Telegram 和 Satori 平台，并集成 OpenAI、Anthropic、Ollama 和 LiteLLM 等大语言模型提供商。

## 1. 环境要求

### Python 版本

- 需要 Python 3.11 或更高版本（支持 3.12 和 3.13）

### 系统依赖

- 操作系统：Linux、macOS 或 Windows
- `pip` 包管理器（Python 自带）
- Docker 部署：Docker Engine 20.10+ 和 Docker Compose v2

### 核心依赖

以下包会通过 pip 自动安装：

| 包名 | 用途 |
|------|------|
| quart | 异步 Web 框架，用于面板和 HTTP 回调 |
| hypercorn | Quart 的 ASGI 服务器 |
| aiohttp | 异步 HTTP 客户端/服务器 |
| websockets | OneBot WebSocket 模式的 WebSocket 支持 |
| openai | OpenAI API 客户端 |
| litellm | 通用大模型提供商网关 |
| Pillow | 图片生成（帮助卡片等） |
| psutil | 系统监控 |
| aiosqlite | 异步 SQLite 数据库访问 |
| watchfiles | 插件热重载文件监控 |
| python-telegram-bot | Telegram 适配器 |
| pycryptodome | 加密操作 |

### 可选依赖

- `playwright`（基于浏览器的搜索功能）
- `mss` 和 `py-cpuinfo`（高级系统监控）

## 2. 安装方式

### pip 安装（推荐）

```bash
# 从 PyPI 安装
pip install loyan

# 安装所有可选依赖
pip install loyan[all]
```

### 源码安装

```bash
# 克隆仓库
git clone https://github.com/MiniYv-IT2/LoyanBot.git
cd LoyanBot

# 开发模式安装
pip install -e .

# 安装所有可选依赖
pip install -e ".[all]"
```

### Docker 安装

```bash
# 克隆仓库
git clone https://github.com/MiniYv-IT2/LoyanBot.git
cd LoyanBot

# 使用 Docker Compose 构建并启动
docker compose -f docker/docker-compose.yml up -d

# 手动构建镜像
docker build -f docker/Dockerfile -t loyan:latest .
docker run -d -p 5090:5090 -v loyan_storage:/loyan/storage --name loyan loyan:latest
```

Docker 卷挂载：
- `/loyan/storage` - 持久化配置、实例、日志和插件数据
- `/loyan/plugins_custom` - 可选的自定义插件目录

面板端口为 **5090**。

## 3. 配置说明

### 配置文件位置

首次运行后，配置文件位于：

```
<项目根目录>/storage/config.json
```

### 基础配置结构

框架配置文件（`config.json`）包含全局设置：

```json
{
  "callback_port": 3002,
  "connection_mode": "http",
  "bot_version": "v1.9.25",
  "log_encoding": "utf-8",
  "log_level": "INFO",
  "debug_mode": false,
  "auto_replies": {
    "你好": "你好！我是 LoyanBot，有什么可以帮你？"
  },
  "store": {
    "sources": [
      {
        "name": "官方源",
        "store_url": "http://38.55.145.10:16385/store.json",
        "enabled": true
      }
    ]
  }
}
```

### 关键配置字段

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `log_level` | string | `"INFO"` | 日志级别：DEBUG、INFO、WARNING、ERROR、CRITICAL |
| `debug_mode` | bool | `false` | 启用调试模式（结构化日志） |
| `log_encoding` | string | `"utf-8"` | 日志文件编码 |
| `auto_replies` | dict | `{}` | 关键词自动回复映射 |
| `auto_update` | bool | `true` | 每日自动更新插件 |
| `auto_update_core` | bool | `false` | 自动检查框架更新 |

### 环境变量

配置值可通过环境变量覆盖：

| 环境变量 | 配置键 | 说明 |
|----------|--------|------|
| `GRACYBOT_HOME` | - | 项目根目录覆盖 |

## 4. 实例配置

LoyanBot 支持多机器人实例。每个实例的配置位于：

```
storage/instances/<实例名称>/config.json
```

### 实例配置示例

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

### 实例配置字段

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `platform` | string | 是 | 平台类型：`onebot`、`qq_official`、`telegram`、`satori` |
| `bot_name` | string | 是 | 自定义名称，用于日志和识别 |
| `robot_id` | string | 是 | 机器人账号 ID（QQ 号、Telegram bot token 等） |
| `master_id` | string | 是 | 主人用户 ID，用于管理员命令 |
| `enabled` | bool | 否 | 是否启用此实例（默认：true） |
| `type` | string | 否 | OneBot 连接类型：`http`、`ws_forward`、`ws_reverse` |
| `http_url` | string | 否 | HTTP API 端点 URL |
| `callback_port` | int | 否 | 接收 HTTP 回调的端口 |
| `admins_id` | list | 否 | 额外的管理员用户 ID |

### 创建实例

使用 CLI 创建新的机器人实例：

```bash
loyan instance add <实例名称>
```

这会创建 `storage/instances/<实例名称>/` 目录和默认 `config.json`。

## 5. 启动运行

### CLI 命令

```bash
loyan run
```

### 直接 Python 执行

```bash
python bot.py
```

### Docker

```bash
docker compose -f docker/docker-compose.yml up -d
```

### 启动流程

机器人遵循分阶段启动流程：

1. **配置加载** - 读取 `config.json` 和实例配置
2. **数据库就绪** - 初始化数据库连接
3. **插件扫描** - 扫描插件目录并读取元数据
4. **插件加载** - 加载插件模块并注册命令
5. **Brain 就绪** - 初始化 AI 提供商和密钥库
6. **实例就绪** - 创建机器人实例和 Pipeline
7. **适配器就绪** - 连接到消息平台
8. **运行中** - 完全可用，接受消息

### 启动输出

机器人成功启动后，会看到：

```
====== LoyanBot v{版本} ======
```

主人会在私聊中收到欢迎消息：

```
LoyanBot v{版本} 启动成功！
已加载 {N} 个插件
```

## 6. 验证安装

### 检查机器人状态

启动后，在私聊中发送 `/关于` 命令。机器人会响应：

```
LoyanBot v{版本}
- 作者: 小禹
- 定位: 跨平台 IM 轻量异步框架
- 适配器: onebot/主号 (HTTP)
- Python: 3.11.x
- 插件: N 个已注册
```

### 检查插件命令

向机器人发送 `/help`。它会生成一张帮助图片，显示所有已注册的插件命令。

### 检查日志

日志存储在：

```
storage/logs/loyan.log        # 所有日志（DEBUG 及以上）
storage/logs/loyan_error.log  # 仅错误日志
```

### 检查 Web 面板

如果配置了 `http_port`，Web 面板可通过以下地址访问：

```
http://localhost:5090
```

## 7. 常见问题

### "配置文件未找到"

机器人会在首次运行时自动创建默认配置。如果出现此消息，请检查 `storage/` 目录是否可写。

### "无适配器启动"

确保 `storage/instances/` 下至少存在一个实例配置，且 `enabled: true` 并设置了有效的平台类型。

### "插件 X 缺少 metadata.toml"

每个插件目录必须包含 `metadata.toml` 文件。检查插件目录结构。

### HTTP 回调连接被拒绝

如果使用 HTTP 模式，请确保 NapCat 或 OneBot 实现正在运行，且实例配置中的 `callback_port` 与 NapCat 回调配置匹配。

### Docker: "权限被拒绝"

Docker 容器默认以 root 运行。如果从主机目录挂载卷，请确保正确权限：

```bash
chmod -R 777 storage/
```

### 插件热重载不工作

确保已安装 `watchfiles`：

```bash
pip install watchfiles
```

### 日志太详细

在 `config.json` 中将 `log_level` 设置为 `WARNING`：

```json
{
  "log_level": "WARNING"
}
```
