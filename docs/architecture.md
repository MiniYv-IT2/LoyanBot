# Architecture

LoyanBot is designed with a layered, modular architecture that separates concerns and enables extensibility. This document describes the overall architecture, the message processing pipeline, the state machine, and the lifecycle management system.

## 1. Overall Architecture

### Layer Diagram

```
+-------------------------------------------------------------+
|                    Application Layer                         |
|  (bot.py, CLI, Web Panel)                                   |
+-------------------------------------------------------------+
|                    Core Layer                                |
|  (Pipeline, PluginManager, ConfigManager, SecurityManager)  |
+-------------------------------------------------------------+
|                    Adapter Layer                             |
|  (OneBot, Telegram, QQ Official, Satori)                    |
+-------------------------------------------------------------+
|                    Brain Layer                               |
|  (AI Providers, Chat Engine, Memory, Skills)                |
+-------------------------------------------------------------+
|                    Infrastructure Layer                      |
|  (EventBus, Lifecycle, Scheduler, Database)                 |
+-------------------------------------------------------------+
```

### Component Overview

| Component | Location | Responsibility |
|-----------|----------|----------------|
| `PluginManager` | `loyan/core/plugin_manager.py` | Plugin discovery, loading, registration, hot-reload |
| `ConfigManager` | `loyan/core/config_manager.py` | Configuration loading, validation, plugin config |
| `SecurityManager` | `loyan/core/security_manager.py` | RBAC, rate limiting, blacklist, audit logging |
| `AdapterPool` | `loyan/core/loyan_adapter/pool.py` | Multi-adapter instance management |
| `Pipeline` | `loyan/core/pipeline/pipeline.py` | Message processing pipeline (onion model) |
| `LifecycleManager` | `loyan/core/lifecycle/lifecycle_manager.py` | Phased startup/shutdown orchestration |
| `RuntimeRegistry` | `loyan/core/runtime/runtime.py` | Per-instance runtime state management |
| `MonitorManager` | `loyan/core/monitor.py` | System metrics and health monitoring |
| `EventBus` | `loyan/core/event.py` | Internal event pub/sub system |
| `ProviderManager` | `loyan/brain/provider/manager.py` | AI provider lifecycle and model management |

### Dependency Container

The framework uses a lightweight dependency injection container (`loyan/core/container.py`):

```python
container = Container()
container.register("adapter_pool", lambda _c: adapter_pool)
container.register("event_bus", lambda _c: event_bus)
container.register("config_manager", lambda _c: config_manager)
container.register("runtime_registry", lambda _c: RuntimeRegistry())
container.register("plugin_manager", lambda _c: plugin_manager)
```

Components are lazily constructed on first `get()` call and cached as singletons.

## 2. Message Pipeline

The message processing pipeline follows the **onion model** with five sequential stages. Each stage can short-circuit the pipeline by returning `None`.

### Pipeline Flow

```
Incoming Message (LoyanEvent)
        |
        v
+------------------+
|  SecurityFilter  |  Logging, monitoring, input validation
+------------------+
        |
        v
+------------------+
| BuiltinCommands  |  /shutdown, /restart, /about, /help
+------------------+
        |
        v
+------------------+
| CommandMatcher   |  TOML + decorator command matching
+------------------+
        |
        v
+------------------+
|  PluginHandler   |  Permission check, handler execution, timing
+------------------+
        |
        v
+------------------+
| ResponseSender   |  Auto-reply, fallback handler (LLM)
+------------------+
        |
        v
+------------------+
| StatsCollector   |  Usage statistics collection
+------------------+
```

### Stage Details

#### SecurityFilter

**File**: `loyan/core/pipeline/security_filter.py`

Responsibilities:
- Record message received in the monitor
- Log the incoming message with context (sender, chat type, content)
- Sanitize user IDs in logs for privacy

```python
class SecurityFilter(Stage):
    async def process(self, ctx: PluginContext) -> Optional[PluginContext]:
        # Record in monitor
        monitor_manager.record_message_received()
        # Log with styling pipeline
        self._log_via_styling(ctx)
        return ctx
```

#### BuiltinCommands

**File**: `loyan/core/pipeline/builtin_commands.py`

Responsibilities:
- Handle framework-level commands: `/shutdown`, `/restart`, `/startup`, `/about`
- Dispatch registered builtin commands (e.g., `/chat` from brain)
- Enforce master-only permissions for dangerous operations

Built-in commands:
| Command | Permission | Action |
|---------|-----------|--------|
| `/shutdown` | master | Graceful bot shutdown with systemd support |
| `/restart` | master | Process restart (cross-platform) |
| `/startup` | master | Start the bot service via systemd |
| `/about` | all | Display bot version, adapters, plugin count |

#### CommandMatcher

**File**: `loyan/core/pipeline/command_matcher.py`

Responsibilities:
- Match incoming messages against TOML-declared commands (parallel matching)
- Match against `@on_command` decorator-registered commands
- Match against `@on_regex` regex patterns
- Support command prefix replacement (e.g., `#` instead of `/`)
- Support command aliases
- Enforce chat type, permission, and @mention requirements
- Select highest-priority match when multiple plugins match

Matching algorithm:
1. **TOML matching** (parallel): Scan all plugins' `commands` lists simultaneously
2. **Decorator matching** (sequential): Scan `DECORATOR_COMMAND_REGISTRY`
3. **Regex matching**: Test `@on_regex` patterns
4. **Priority resolution**: Sort by plugin `priority` field (higher wins)

```python
class CommandMatcher(Stage):
    async def process(self, ctx: PluginContext) -> Optional[PluginContext]:
        # Parallel TOML matching
        tasks = [_check_plugin(p) for p in plugin_manager.registry]
        results = await asyncio.gather(*tasks)
        matches = [r for r in results if r is not None]

        if matches:
            matches.sort(key=lambda x: x["priority"], reverse=True)
            best = matches[0]
            ctx.command = best["matched_cmd"]
            ctx.plugin_name = best["plugin"]["name"]
            ctx.extra["handler_func"] = best["plugin"]["handler_func"]
            return ctx

        # Fallback to decorator matching
        for entry in DECORATOR_COMMAND_REGISTRY:
            # ... match commands and patterns
```

#### PluginHandler

**File**: `loyan/core/pipeline/plugin_handler.py`

Responsibilities:
- Execute the matched plugin handler function
- Support both new-style (`ctx: PluginContext`) and old-style (7-parameter) signatures
- Inject `ctx.send` and `ctx.reply` helper functions
- Time execution and log performance metrics
- Catch and log exceptions

```python
class PluginHandler(Stage):
    timeout: float = 300.0  # 5 minutes for LLM requests

    async def process(self, ctx: PluginContext) -> Optional[PluginContext]:
        handler_func = ctx.extra.get("handler_func")
        if not handler_func:
            return ctx

        start_time = time.time()
        inject_send_reply(ctx)

        try:
            sig = inspect.signature(handler_func)
            params = list(sig.parameters.keys())

            if len(params) == 1 and params[0] in ("ctx", "self"):
                await handler_func(ctx)
            else:
                # Old-style handler with 7 parameters
                await handler_func(
                    ctx.plugin_manager, send, data,
                    ctx.sender_id, ctx.chat_type, "all", logger
                )
        except Exception as e:
            logger.error(f"Plugin error: {e}", exc_info=True)

        return None
```

#### ResponseSender

**File**: `loyan/core/pipeline/response_sender.py`

Responsibilities:
- Match against `auto_replies` keyword dictionary
- Dispatch to `@on_fallback` handlers (e.g., LLM chat)
- Final catch-all for unmatched messages

```python
class ResponseSender(Stage):
    async def process(self, ctx: PluginContext) -> Optional[PluginContext]:
        raw_msg = ctx.raw_text.strip()

        # Auto-reply matching
        auto_replies = config_manager.get("auto_replies", {})
        for keyword, reply in auto_replies.items():
            if keyword in raw_msg:
                await loyan_send_msg(ctx.target_id, LoyanText(text=reply))
                return None

        # Fallback handler (LLM, etc.)
        for entry in FALLBACK_HANDLERS:
            if ctx.chat_type in entry.get("chat_type", []):
                await entry["handler_func"](ctx)
                return None

        return None
```

### Circuit Breaker

The pipeline implements a circuit breaker pattern for fault tolerance:

- After 3 consecutive failures, a stage is "tripped" and skipped
- After 30 seconds (configurable), a half-open probe is attempted
- If the probe succeeds, the circuit closes; if it fails, recovery time doubles (max 300s)

### Pipeline Timeout

- Per-stage timeout: 60 seconds (configurable per stage)
- Global pipeline timeout: 120 seconds

## 3. State Machine

### Lifecycle Phases

The framework uses a strict state machine with the following phases:

```
CREATED (0)
    |
    v
CONFIG_LOADED (10)
    |
    v
DATABASE_READY (20)
    |
    v
PLUGINS_SCANNED (30)
    |
    v
PLUGINS_LOADED (40)
    |
    v
BRAIN_READY (50)
    |
    v
INSTANCES_READY (60)
    |
    v
ADAPTERS_READY (70)
    |
    v
RUNNING (80)
    |
    v
STOPPING (90)
    |
    v
STOPPED (100)
```

### Phase Descriptions

| Phase | Value | Description |
|-------|-------|-------------|
| `CREATED` | 0 | Initial object created, nothing initialized |
| `CONFIG_LOADED` | 10 | Configuration manager finished loading |
| `DATABASE_READY` | 20 | Database connection established |
| `PLUGINS_SCANNED` | 30 | Plugin directories scanned, metadata collected |
| `PLUGINS_LOADED` | 40 | All plugins loaded and registered |
| `BRAIN_READY` | 50 | Brain module initialized (providers, keystore, persona) |
| `INSTANCES_READY` | 60 | Bot instances created with pipelines |
| `ADAPTERS_READY` | 70 | Adapters connected to platforms |
| `RUNNING` | 80 | Fully operational, accepting messages |
| `STOPPING` | 90 | Shutdown in progress |
| `STOPPED` | 100 | Fully stopped, all resources released |

### Transition Rules

Phases can only transition forward during startup and backward during shutdown:

```python
_TRANSITION_TABLE = {
    Phase.CREATED: [Phase.CONFIG_LOADED],
    Phase.CONFIG_LOADED: [Phase.DATABASE_READY],
    Phase.DATABASE_READY: [Phase.PLUGINS_SCANNED],
    Phase.PLUGINS_SCANNED: [Phase.PLUGINS_LOADED],
    Phase.PLUGINS_LOADED: [Phase.BRAIN_READY],
    Phase.BRAIN_READY: [Phase.INSTANCES_READY],
    Phase.INSTANCES_READY: [Phase.ADAPTERS_READY],
    Phase.ADAPTERS_READY: [Phase.RUNNING],
    Phase.RUNNING: [Phase.STOPPING],
    Phase.STOPPING: [Phase.STOPPED],
    Phase.STOPPED: [Phase.CREATED],  # Allow restart
}
```

## 4. Lifecycle Management

### LifecycleManager

The `LifecycleManager` (`loyan/core/lifecycle/lifecycle_manager.py`) orchestrates the entire application lifecycle:

```python
class LifecycleManager:
    def __init__(self):
        self._state = StateMachine()
        self._hooks = HookRegistry()
        self._executor = HookExecutor(self._hooks)
        self._metrics = MetricsCollector()
        self._checker = CompositeChecker()
        self._reporter = HealthReporter(...)
```

### Lifecycle Events

Modules register hooks at specific lifecycle events:

```python
class LifecycleEvent(str, Enum):
    BEFORE_INIT = "before_init"
    AFTER_CONFIG_LOAD = "after_config_load"
    AFTER_DATABASE_READY = "after_database_ready"
    AFTER_PLUGINS_SCANNED = "after_plugins_scanned"
    AFTER_PLUGINS_LOADED = "after_plugins_loaded"
    AFTER_BRAIN_READY = "after_brain_ready"
    AFTER_INSTANCES_READY = "after_instances_ready"
    BEFORE_ADAPTERS_START = "before_adapters_start"
    AFTER_ADAPTERS_START = "after_adapters_start"
    READY = "ready"
    BEFORE_SHUTDOWN = "before_shutdown"
    AFTER_SHUTDOWN = "after_shutdown"
    ON_ERROR = "on_error"
    ON_RESTART = "on_restart"
```

### Hook Registration

```python
from loyan.core.lifecycle import lifecycle, LifecycleEvent

# Register a hook at a specific event
lifecycle.register_hook(
    event=LifecycleEvent.READY,
    callback=my_ready_handler,
    name="my_handler",
    priority=50,
    timeout=30.0
)
```

### Hook Execution

Hooks are executed in priority order (higher priority first) with timeout enforcement:

```python
async def fire_event_async(self, event: LifecycleEvent) -> dict:
    return await self._executor.run_event(event)
```

### Startup Sequence

The startup sequence in `main.py`:

```python
async def run_bot():
    # 1. Setup logging
    logger_manager.setup_logging(log_level=LOG_LEVEL, debug_mode=DEBUG_MODE)

    # 2. Build and set dependency container
    container = build_container()
    container.build()
    set_container(container)

    # 3. Load configuration
    config_manager.load()
    await lifecycle.fire_event_async(LifecycleEvent.AFTER_CONFIG_LOAD)

    # 4. Initialize plugins (scan metadata + load modules)
    plugin_manager.init()
    await plugin_manager.async_load()
    await lifecycle.fire_event_async(LifecycleEvent.AFTER_PLUGINS_LOADED)

    # 5. Initialize brain (AI providers)
    import loyan.brain
    await lifecycle.fire_event_async(LifecycleEvent.AFTER_BRAIN_READY)

    # 6. Initialize instances (create pipelines, adapters)
    await init_instances()
    await lifecycle.fire_event_async(LifecycleEvent.AFTER_INSTANCES_READY)

    # 7. Start adapters (connect to platforms)
    # (Triggered by lifecycle hook on AFTER_INSTANCES_READY)
    await lifecycle.fire_event_async(LifecycleEvent.AFTER_ADAPTERS_START)

    # 8. Plugin on_ready hooks
    plugin_manager.trigger_on_ready()
    await lifecycle.fire_event_async(LifecycleEvent.READY)
```

### Shutdown Sequence

```python
async def _run_shutdown_sequence(self):
    await self._run_event(LifecycleEvent.BEFORE_SHUTDOWN)
    for phase in shutdown_range():
        self._state.transition(phase)
    await self._run_event(LifecycleEvent.AFTER_SHUTDOWN)
```

### Health Monitoring

The lifecycle system includes health monitoring:

```python
# Get health report
report = lifecycle.health_report()
# {
#   "status": "healthy",
#   "phase": "RUNNING",
#   "uptime": 259200,
#   "components": { ... }
# }

# Register custom health checks
lifecycle.register_check("my_service", check_my_service)

# Periodic health checks
await lifecycle.start_periodic_health_check(interval=60.0)
```

## 5. Runtime Architecture

### Runtime Instance

Each bot account is represented by a `Runtime` dataclass:

```python
@dataclass
class Runtime:
    instance_name: str           # "main-bot"
    robot_id: str                # Bot QQ number
    master_id: str               # Owner QQ number
    adapter_tag: IdentityTag     # Associated adapter tag
    pipeline: Pipeline           # Independent pipeline instance
    logger: logging.Logger       # Independent file logger
    plugin_manager: PluginManager  # Shared plugin manager singleton
    adapter_pool: AdapterPool    # Shared adapter pool singleton
```

### RuntimeRegistry

The global registry manages all Runtime instances:

```python
class RuntimeRegistry:
    _runtimes: Dict[str, Runtime]      # key = identity_key
    _by_robot_id: Dict[str, Runtime]   # key = robot_id

    @classmethod
    def register(cls, runtime: Runtime): ...
    @classmethod
    def get_by_tag(cls, tag: IdentityTag): ...
    @classmethod
    def get_by_robot_id(cls, robot_id: str): ...
```

### RuntimeContext

Uses Python's `contextvars` to pass the current Runtime through the message processing chain:

```python
_current_runtime: ContextVar[Runtime] = ContextVar("_current_runtime")

class RuntimeContext:
    @staticmethod
    def set(runtime: Runtime) -> Token: ...
    @staticmethod
    def get() -> Runtime: ...
    @staticmethod
    def reset(token: Token) -> None: ...
```

This ensures that each async task sees the correct Runtime for its message, even in concurrent processing.

## 6. Adapter Architecture

### Adapter Hierarchy

```
LoyanAdapter (ABC)
  +-- OneBotAdapter
  +-- TelegramAdapter
  +-- QQOfficialAdapter
  +-- SatoriAdapter
```

### AdapterPool

Manages multiple adapter instances with thread-safe operations:

```python
class AdapterPool:
    def register(self, adapter: LoyanAdapter, tag: IdentityTag, default: bool = False): ...
    def unregister(self, tag: IdentityTag) -> bool: ...
    def get(self, tag: IdentityTag) -> Optional[LoyanAdapter]: ...
    def get_default(self) -> Optional[LoyanAdapter]: ...
    async def send(self, target, segments, chat_type, tag=None) -> bool: ...
    async def broadcast(self, target, segments, chat_type) -> Dict[str, bool]: ...
    async def start_all(self, on_event) -> None: ...
    async def stop_all(self) -> None: ...
```

### IdentityTag

Identifies each adapter instance:

```python
@dataclass
class IdentityTag:
    platform: str       # "onebot", "telegram", etc.
    bot_name: str       # "MainBot"
    instance_id: str    # Unique instance identifier

    @property
    def identity_key(self) -> str:
        return f"{self.platform}/{self.bot_name}/{self.instance_id}"
```

## 7. Event System

### EventBus

The internal event bus provides publish/subscribe messaging:

```python
class EventBus:
    async def publish(self, event: LoyanEvent): ...
    async def subscribe(self, event_type, handler, priority: int = 50): ...
    async def publish_business(self, event: BusinessEvent): ...
```

### Business Events

Modules communicate through typed business events:

```python
class EventType(str, Enum):
    PLUGIN_LOADED = "PLUGIN_LOADED"
    PLUGIN_UNLOADED = "PLUGIN_UNLOADED"
    INSTANCE_STARTED = "INSTANCE_STARTED"
    INSTANCE_STOPPED = "INSTANCE_STOPPED"
    # ...
```

## 8. Data Flow

### Inbound Message Flow

```
Platform (QQ/Telegram)
    |
    v
Adapter (OneBot/Telegram)
    |
    v
LoyanEvent (normalized)
    |
    v
EventBus.publish()
    |
    v
SecurityManager (blacklist check, audit)
    |
    v
Pipeline.process()
    |-- SecurityFilter
    |-- BuiltinCommands
    |-- CommandMatcher
    |-- PluginHandler
    |-- ResponseSender
    |-- StatsCollector
    |
    v
Plugin Handler Function
    |
    v
ctx.send(LoyanText(...))
    |
    v
AdapterPool.send()
    |
    v
Adapter.send()
    |
    v
Platform (QQ/Telegram)
```

### Outbound Message Flow

```
Plugin calls ctx.send()
    |
    v
RuntimeContext.get().adapter_tag
    |
    v
AdapterPool.get(tag)
    |
    v
Adapter.send(target, segments, chat_type)
    |
    v
Platform-specific API call
    |
    v
Platform delivers message
```
