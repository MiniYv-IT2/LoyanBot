# Getting Started

LoyanBot is a lightweight, asynchronous, multi-platform chatbot framework built on Python 3.11+. It connects to QQ (via NapCat/OneBot), QQ Official, Telegram, and Satori platforms, and integrates with LLM providers including OpenAI, Anthropic, Ollama, and LiteLLM.

## 1. Requirements

### Python Version

- Python 3.11 or higher is required (3.12 and 3.13 are also supported).

### System Dependencies

- Operating system: Linux, macOS, or Windows
- `pip` package manager (comes with Python)
- For Docker deployment: Docker Engine 20.10+ and Docker Compose v2

### Core Dependencies

The following packages are installed automatically via pip:

| Package | Purpose |
|---------|---------|
| quart | Async web framework for the panel and HTTP callbacks |
| hypercorn | ASGI server for Quart |
| aiohttp | Async HTTP client/server |
| websockets | WebSocket support for OneBot WS mode |
| openai | OpenAI API client |
| litellm | Universal LLM provider gateway |
| Pillow | Image generation (help cards, etc.) |
| psutil | System monitoring |
| aiosqlite | Async SQLite database access |
| watchfiles | Plugin hot-reload file watching |
| python-telegram-bot | Telegram adapter |
| pycryptodome | Cryptographic operations |

### Optional Dependencies

- `playwright` (for browser-based search features)
- `mss` and `py-cpuinfo` (for advanced system monitoring)

## 2. Installation

### pip Install (Recommended)

```bash
# Install from PyPI
pip install loyan

# Or install with all optional dependencies
pip install loyan[all]
```

### Source Install

```bash
# Clone the repository
git clone https://github.com/MiniYv-IT2/LoyanBot.git
cd LoyanBot

# Install in development mode
pip install -e .

# Or install with all optional dependencies
pip install -e ".[all]"
```

### Docker Install

```bash
# Clone the repository
git clone https://github.com/MiniYv-IT2/LoyanBot.git
cd LoyanBot

# Build and start with Docker Compose
docker compose -f docker/docker-compose.yml up -d

# Or build the image manually
docker build -f docker/Dockerfile -t loyan:latest .
docker run -d -p 5090:5090 -v loyan_storage:/loyan/storage --name loyan loyan:latest
```

Docker volumes:
- `/loyan/storage` - Persistent configuration, instances, logs, and plugin data
- `/loyan/plugins_custom` - Optional custom plugin directory

The panel is exposed on port **5090**.

## 3. Configuration

### Configuration File Location

After first run, the configuration file is located at:

```
<project_root>/storage/config.json
```

### Basic Configuration Structure

The framework configuration file (`config.json`) contains global settings:

```json
{
  "callback_port": 3002,
  "connection_mode": "http",
  "bot_version": "v1.9.25",
  "log_encoding": "utf-8",
  "log_level": "INFO",
  "debug_mode": false,
  "auto_replies": {
    "hello": "Hello! I am LoyanBot, how can I help you?"
  },
  "store": {
    "sources": [
      {
        "name": "Official",
        "store_url": "http://38.55.145.10:16385/store.json",
        "enabled": true
      }
    ]
  }
}
```

### Key Configuration Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `log_level` | string | `"INFO"` | Log level: DEBUG, INFO, WARNING, ERROR, CRITICAL |
| `debug_mode` | bool | `false` | Enable debug mode (structured logging) |
| `log_encoding` | string | `"utf-8"` | Log file encoding |
| `auto_replies` | dict | `{}` | Keyword auto-reply mapping |
| `auto_update` | bool | `true` | Auto-update plugins daily |
| `auto_update_core` | bool | `false` | Auto-check for framework updates |

### Environment Variables

Configuration values can be overridden via environment variables:

| Environment Variable | Config Key | Description |
|---------------------|------------|-------------|
| `GRACYBOT_HOME` | - | Project root directory override |

## 4. Instance Configuration

LoyanBot supports multiple bot instances. Each instance has its own configuration under:

```
storage/instances/<instance_name>/config.json
```

### Instance Configuration Example

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

### Instance Configuration Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `platform` | string | Yes | Platform type: `onebot`, `qq_official`, `telegram`, `satori` |
| `bot_name` | string | Yes | Custom name for logging and identification |
| `robot_id` | string | Yes | Bot account ID (QQ number, Telegram bot token, etc.) |
| `master_id` | string | Yes | Owner user ID for admin commands |
| `enabled` | bool | No | Whether this instance is enabled (default: true) |
| `type` | string | No | Connection type for OneBot: `http`, `ws_forward`, `ws_reverse` |
| `http_url` | string | No | HTTP API endpoint URL |
| `callback_port` | int | No | Port for receiving HTTP callbacks |
| `admins_id` | list | No | Additional admin user IDs |

### Creating an Instance

Use the CLI to create a new bot instance:

```bash
loyan instance add <instance_name>
```

This creates the directory `storage/instances/<instance_name>/` with a default `config.json`.

## 5. Starting the Bot

### CLI Command

```bash
loyan run
```

### Direct Python Execution

```bash
python bot.py
```

### Docker

```bash
docker compose -f docker/docker-compose.yml up -d
```

### Startup Sequence

The bot follows a phased startup sequence:

1. **Configuration Load** - Reads `config.json` and instance configs
2. **Database Ready** - Initializes database connections
3. **Plugins Scanned** - Scans plugin directories and reads metadata
4. **Plugins Loaded** - Loads plugin modules and registers commands
5. **Brain Ready** - Initializes AI providers and keystore
6. **Instances Ready** - Creates bot instances with pipelines
7. **Adapters Ready** - Connects to messaging platforms
8. **Running** - Fully operational, accepting messages

### Startup Output

When the bot starts successfully, you will see:

```
====== LoyanBot v{version} ======
```

And the master user will receive a welcome message in private chat:

```
LoyanBot v{version} started successfully!
Loaded {N} plugins
```

## 6. Verifying Installation

### Check Bot Status

After starting, send the `/about` command to the bot in private chat. It will respond with:

```
LoyanBot v{version}
- Author: MiniYv
- Platform: Cross-platform IM lightweight async framework
- Adapters: onebot/MainBot (HTTP)
- Python: 3.11.x
- Plugins: N registered
```

### Check Plugin Commands

Send `/help` to the bot. It will generate a help image showing all registered plugin commands.

### Check Logs

Logs are stored in:

```
storage/logs/loyan.log        # All logs (DEBUG and above)
storage/logs/loyan_error.log  # Error logs only
```

### Check Web Panel

If `http_port` is configured, the web panel is accessible at:

```
http://localhost:5090
```

## 7. Common Issues

### "Config file not found"

The bot auto-creates a default configuration on first run. If this message appears, check that the `storage/` directory is writable.

### "No adapters started"

Ensure at least one instance configuration exists under `storage/instances/` with `enabled: true` and a valid platform type.

### "Plugin X missing metadata.toml"

Every plugin directory must contain a `metadata.toml` file. Check the plugin directory structure.

### Connection refused to HTTP callback

If using HTTP mode, ensure NapCat or the OneBot implementation is running and the `callback_port` in the instance config matches the NapCat callback configuration.

### Docker: "Permission denied"

The Docker container runs as root by default. If mounting volumes from a host directory, ensure proper permissions:

```bash
chmod -R 777 storage/
```

### Plugin hot-reload not working

Ensure `watchfiles` is installed:

```bash
pip install watchfiles
```

### Logs are too verbose

Set `log_level` to `WARNING` in `config.json`:

```json
{
  "log_level": "WARNING"
}
```
