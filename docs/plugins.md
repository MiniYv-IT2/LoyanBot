# Plugin Development

LoyanBot has a powerful plugin system that allows you to extend the bot's functionality. This guide covers everything you need to know about creating, configuring, and publishing plugins.

## 1. Plugin System Overview

### Architecture

Plugins are Python packages that the framework discovers, loads, and manages at runtime. The plugin system supports:

- TOML-based metadata declarations
- Decorator-based command registration
- Dependency management between plugins
- Hot-reload without bot restart
- Plugin store for distribution
- Per-plugin configuration and data storage

### Plugin Discovery

The plugin manager scans two directories for plugins:

1. **System plugins**: `loyan/plugins/` (built-in, shipped with the framework)
2. **User plugins**: `storage/plugins/` (installed from store or manually created)

## 2. Plugin Directory Structure

A plugin consists of the following files:

```
MyPlugin/
  metadata.toml       # Plugin metadata (required)
  main.py             # Core module with handlers (required)
  config.py           # Default configuration (optional)
  config.json         # Plugin configuration (auto-generated)
  res/                # Static resources (optional)
  core/               # Additional modules (optional)
    draw.py
  requirements.txt    # Python dependencies (optional)
```

### Minimal Plugin

```
HelloWorld/
  metadata.toml
  main.py
```

### Standard Plugin

```
WeatherPlugin/
  metadata.toml
  main.py
  config.py
  config.json
  res/
    icons/
  core/
    forecast.py
    utils.py
  requirements.txt
```

## 3. Plugin Metadata (metadata.toml)

The `metadata.toml` file declares the plugin's identity, commands, and behavior.

### Complete metadata.toml Example

```toml
[plugin]
name        = "Weather Query"
version     = "1.0.0"
author      = "Developer"
description = "Query weather information for any city"
category    = "utility"
tags        = ["weather", "utility"]
icon        = "weather.png"
priority    = 50

[handler]
entry       = "handle_weather"

[trigger]
commands       = ["/weather", "/天气"]
chat_type      = ["private", "group"]
permission     = "all"
is_at_required = false

[dependencies]
# No dependencies
```

### Metadata Fields

#### [plugin] Section

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Display name shown in help and store |
| `version` | string | Yes | Semantic version (e.g., `"1.0.0"`) |
| `author` | string | No | Plugin author name |
| `description` | string | No | Short description of functionality |
| `category` | string | No | Category for store organization |
| `tags` | list | No | Tags for search and filtering |
| `icon` | string | No | Icon filename (relative to plugin dir) |
| `priority` | int | No | Execution priority (default: 50, higher = first) |

#### [handler] Section

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `entry` | string | Yes | Name of the main handler function in `main.py` |

#### [trigger] Section

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `commands` | list | Yes | List of trigger commands (e.g., `["/weather", "/天气"]`) |
| `chat_type` | list | No | Valid chat types: `["private", "group"]` (default: both) |
| `permission` | string | No | Required permission: `"all"`, `"master"`, `"admin"` (default: `"all"`) |
| `is_at_required` | bool | No | Whether @mention is required in group chats (default: false) |

#### [dependencies] Section

```toml
[dependencies]
[[deps]]
name = "Help_plugin"
min_version = "1.0.0"
max_version = "2.0.0"
```

## 4. Plugin Lifecycle

### Loading Sequence

1. **Scan**: Plugin manager scans plugin directories for `metadata.toml`
2. **Validate**: Check metadata syntax and required fields
3. **Dependency Check**: Verify all dependencies are satisfied
4. **Load Module**: Import `main.py` (or `<plugin_name>.py`)
5. **Register**: Scan for decorated functions and register commands
6. **Configure**: Initialize plugin configuration from `config.py` and `config.json`
7. **Execute**: Call the entry handler on first matching command

### Lifecycle Hooks

Plugins can define these optional functions:

```python
# Called when the bot starts (after all plugins loaded)
def on_ready():
    pass

# Called when the bot is shutting down
def on_shutdown():
    pass
```

### Hot Reload

The framework watches plugin directories for changes using `watchfiles`:

- File modifications trigger targeted reload of the changed plugin
- New/deleted plugin directories trigger a full rescan
- Runtime data files (images, cache) do not trigger reload
- The watcher starts automatically when the bot reaches the `READY` phase

To manually reload a plugin:

```bash
loyan plugin reload <plugin_name>
```

## 5. Plugin API

### Decorators

The `graci` package provides decorators for plugin development:

#### @on_command

Declares command trigger functions:

```python
from graci import on_command, plugin_handler, PluginContext

@on_command("/hello", "/你好")
@plugin_handler
async def handle_hello(ctx: PluginContext):
    await ctx.send("Hello!")
```

#### @on_regex

Triggers on regex pattern matches:

```python
from graci import on_regex, plugin_handler, PluginContext
import re

@on_regex(r"weather\s+(\w+)", flags=re.IGNORECASE)
@plugin_handler
async def handle_weather_regex(ctx: PluginContext):
    match = ctx.extra.get("_regex_match")
    city = match.group(1) if match else "unknown"
    await ctx.send(f"Weather for {city}")
```

#### @on_keyword

Triggers when specific keywords are present:

```python
from graci import on_keyword, plugin_handler, PluginContext

@on_keyword("hello", "hi", "hey")
@plugin_handler
async def handle_greeting(ctx: PluginContext):
    await ctx.send("Hello there!")
```

#### @on_fallback

Handles messages not matched by any other plugin:

```python
from graci import on_fallback, plugin_handler, PluginContext

@on_fallback()
@plugin_handler
async def handle_unmatched(ctx: PluginContext):
    await ctx.send("I don't understand that command.")
```

#### @brain_tool

Declares an AI-callable tool:

```python
from graci import brain_tool, PluginContext

@brain_tool(
    name="get_weather",
    description="Get current weather for a city",
    params={"city": {"type": "string", "description": "City name"}},
    permission="admin"
)
def get_weather(ctx: PluginContext, city: str = "") -> str:
    return f"Weather in {city}: Sunny, 25C"
```

#### @plugin_handler

Required wrapper for all handler functions. Handles:
- Permission checking
- Rate limiting
- Cooldown enforcement
- Execution timing and monitoring
- Exception catching

#### @rate_limit

```python
from graci import on_command, plugin_handler, rate_limit

@on_command("/gpt")
@rate_limit(max_calls=5, period=60)
@plugin_handler
async def handle_gpt(ctx: PluginContext):
    pass
```

#### @cooldown

```python
from graci import on_command, plugin_handler, cooldown

@on_command("/daily")
@cooldown(seconds=86400)  # Once per day
@plugin_handler
async def handle_daily(ctx: PluginContext):
    pass
```

### PluginContext

The `PluginContext` dataclass provides all information about the current message:

```python
@dataclass
class PluginContext:
    sender_id: str           # User who sent the message
    target_id: str           # Target (sender for private, group ID for group)
    chat_type: str           # "private" or "group"
    nickname: str            # Sender's display name
    raw_text: str            # Original message text
    text: str                # Sanitized text
    images: List[str]        # Image file IDs
    ats: List[str]           # Mentioned user IDs
    is_at_bot: bool          # Whether bot was @mentioned
    command: str             # Matched command string
    plugin_name: str         # Current plugin name
    raw_data: dict           # Platform-specific raw data
    send: Callable           # Send message function
    reply: Callable          # Quick reply function
    logger: Callable         # Plugin logger
    session: Any             # Session object (if @with_session)
    runtime: Runtime         # Current Runtime instance
```

### Sending Messages

```python
from graci import LoyanText, LoyanImage, LoyanAt

# Send text
await ctx.send(LoyanText(text="Hello!"))

# Send image from file
await ctx.send(LoyanImage(file_path="/path/to/image.png"))

# Send image from URL
await ctx.send(LoyanImage(url="https://example.com/image.png"))

# Send @mention
await ctx.send(LoyanAt(target_id="123456"))

# Reply to the message
await ctx.reply("This is a reply!")

# Send multiple segments
await ctx.send(
    LoyanText(text="Here is the result:"),
    LoyanImage(file_path="result.png")
)
```

### Message Types

| Type | Fields | Description |
|------|--------|-------------|
| `LoyanText` | `text: str` | Plain text message |
| `LoyanImage` | `file_path`, `url`, `file_data` | Image (file, URL, or bytes) |
| `LoyanAt` | `target_id: str` | @mention a user |
| `LoyanReply` | `message_id: str` | Reply to a message |
| `LoyanVoice` | `file_path: str` | Voice message |
| `LoyanFile` | `file_path`, `url` | File attachment |
| `LoyanVideo` | `file_path`, `url`, `file_data` | Video message |
| `LoyanForward` | `forward_id`, `title` | Forwarded message |

### Path Utilities

The `LoyanPaths` class provides standardized paths for plugin data:

```python
from graci import LoyanPaths

paths = LorentzPaths("MyPlugin")

# Data directory (storage/data/plugins/MyPlugin/)
data_dir = paths.data()

# Resource directory (plugin's res/ folder)
res_dir = paths.res()

# Database file path
db_path = paths.db()

# Temporary directory
tmp_dir = paths.temp()
```

### Configuration Access

```python
from graci import config_manager

# Get plugin config
config = config_manager.get_plugin("MyPlugin")

# Get specific key
api_key = config_manager.get_plugin("MyPlugin", key="api_key", default="")

# Update plugin config
config_manager.update_plugin("MyPlugin", {"api_key": "new_key"})
```

### Logging

```python
from graci import get_logger

logger = get_logger("MyPlugin")
logger.info("Plugin started")
logger.warning("Deprecated feature used")
logger.error("Operation failed", exc_info=True)
```

## 6. Plugin Configuration

### Default Configuration (config.py)

```python
# MyPlugin/config.py
DEFAULT_CONFIG = {
    "api_key": "",
    "max_results": 10,
    "timeout": 30,
    "language": "en"
}
```

### Configuration Priority

Configuration is merged in this order (later wins):

1. `DEFAULT_CONFIG` from `config.py`
2. `storage/config.json` (global user config)
3. `storage/config/<plugin_name>/config.json` (bot-level config)
4. `storage/instances/<instance>/plugins/<plugin_name>/config.json` (instance-level config)

### Schema Validation (plugin_conf.json)

```json
{
  "api_key": {
    "type": "str",
    "default": "",
    "description": "API key for the service",
    "required": true
  },
  "max_results": {
    "type": "int",
    "default": 10,
    "description": "Maximum results to return",
    "options": [5, 10, 20, 50]
  }
}
```

## 7. Dependency Management

### Declaring Dependencies

In `metadata.toml`:

```toml
[dependencies]
[[deps]]
name = "Help_plugin"
min_version = "1.0.0"

[[deps]]
name = "CoreUtils"
min_version = "0.5.0"
max_version = "2.0.0"
```

### Circular Dependency Detection

The plugin manager automatically detects circular dependencies using DFS traversal. If a cycle is detected, an error is logged and the affected plugins are not loaded.

### Version Comparison

Plugin versions are compared numerically:
- `"1.0.0"` vs `"1.0.1"` -> `"1.0.0"` is lower
- `"2.0"` vs `"1.9.9"` -> `"2.0"` is higher

## 8. Hot Reload

### Automatic Hot Reload

The plugin watcher monitors plugin directories and automatically reloads changed plugins:

```python
# The watcher is started automatically in the READY lifecycle phase
# It uses watchfiles for efficient filesystem monitoring
# Changes are debounced by 300ms
```

### What Triggers Reload

| Change Type | Action |
|-------------|--------|
| Modified `.py` file | Targeted reload of the changed plugin |
| New plugin directory | Full rescan of all plugins |
| Deleted plugin directory | Full rescan of all plugins |
| Modified `metadata.toml` | Full rescan of all plugins |
| Modified runtime data | No action (images, cache, etc.) |

### Manual Reload

```bash
# Reload via CLI
loyan plugin reload <plugin_name>

# Or via API
POST /api/plugins/<plugin_name>/reload
```

## 9. Complete Example

### Hello World Plugin

**metadata.toml**:
```toml
[plugin]
name        = "Hello World"
version     = "1.0.0"
author      = "Developer"
description = "A simple hello world plugin"

[handler]
entry       = "handle_hello"

[trigger]
commands    = ["/hello"]
chat_type   = ["private", "group"]
permission  = "all"
```

**main.py**:
```python
from graci import on_command, plugin_handler, PluginContext, LoyanText

@on_command("/hello")
@plugin_handler
async def handle_hello(ctx: PluginContext):
    """Respond with a greeting."""
    await ctx.send(LoyanText(text=f"Hello {ctx.nickname}!"))
```

### Weather Plugin with Config

**metadata.toml**:
```toml
[plugin]
name        = "Weather"
version     = "1.0.0"
author      = "Developer"
description = "Query weather information"

[handler]
entry       = "handle_weather"

[trigger]
commands    = ["/weather", "/天气"]
chat_type   = ["private", "group"]
permission  = "all"
```

**config.py**:
```python
DEFAULT_CONFIG = {
    "api_key": "",
    "default_city": "Beijing",
    "units": "metric"
}
```

**main.py**:
```python
from graci import on_command, plugin_handler, PluginContext, get_logger, config_manager

logger = get_logger("Weather")
config = config_manager.register_plugin_config("Weather")

@on_command("/weather")
@plugin_handler
async def handle_weather(ctx: PluginContext):
    """Query weather for a city."""
    # Extract city from message
    text = ctx.raw_text
    city = text.replace("/weather", "").strip() or config.get("default_city", "Beijing")

    if not config.get("api_key"):
        await ctx.reply("Weather API key not configured.")
        return

    # Query weather (simplified)
    try:
        weather_data = await query_weather(city, config["api_key"])
        await ctx.reply(f"Weather in {city}: {weather_data}")
    except Exception as e:
        logger.error(f"Weather query failed: {e}")
        await ctx.reply("Failed to query weather.")
```

## 10. Debugging

### Enable Debug Logging

Set `log_level` to `DEBUG` in `config.json`:

```json
{
  "log_level": "DEBUG"
}
```

### Plugin Debug Mode

Check plugin loading status in logs:

```
[INFO] Plugin manager initialized!
[INFO]   1. Hello World | Version: 1.0.0 | Priority: 50 | Commands: /hello
```

### Common Issues

1. **Plugin not loading**: Check that `metadata.toml` exists and has valid syntax
2. **Command not matching**: Verify command strings match exactly (case-sensitive)
3. **Import errors**: Ensure all imports are from `graci` or standard library
4. **Config not found**: Call `config_manager.register_plugin_config()` in `main.py`

### Testing Plugins

```python
# Use the test framework
from loyan.core.decorators.registration import clear_registry
from loyan.core.plugin_manager import PluginManager

# Create a test instance
pm = PluginManager(config_manager=mock_config, logger=mock_logger)
```

## 11. Publishing to the Plugin Store

### Store Requirements

To publish a plugin to the official store:

1. Plugin must have a valid `metadata.toml`
2. Plugin must be hosted in a public Git repository
3. Repository must have a `main` branch (or specified branch)
4. Plugin must not contain malicious code

### Store Configuration

Configure store sources in `config.json`:

```json
{
  "store": {
    "sources": [
      {
        "name": "Official",
        "store_url": "http://38.55.145.10:16385/store.json",
        "enabled": true
      }
    ],
    "git_mirrors": ["https://ghproxy.com/"]
  }
}
```

### Submitting a Plugin

Contact the LoyanBot development team with:

1. Git repository URL
2. Plugin description
3. Author information
4. License (GPL-3.0 compatible)

### Installation from Store

```bash
# List available plugins
loyan plugin list

# Install a plugin
loyan plugin install <plugin_name>

# Update a plugin
loyan plugin update <plugin_name>

# Uninstall a plugin
loyan plugin uninstall <plugin_name>
```
