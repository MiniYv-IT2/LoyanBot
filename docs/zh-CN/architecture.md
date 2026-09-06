# 架构说明

LoyanBot 采用分层、模块化架构，分离关注点并支持扩展。本文档描述整体架构、消息处理流水线、状态机和生命周期管理系统。

## 1. 整体架构

### 层次图

```
+-------------------------------------------------------------+
|                    应用层                                      |
|  (bot.py, CLI, Web 面板)                                     |
+-------------------------------------------------------------+
|                    核心层                                      |
|  (Pipeline, PluginManager, ConfigManager, SecurityManager)  |
+-------------------------------------------------------------+
|                    适配器层                                    |
|  (OneBot, Telegram, QQ Official, Satori)                    |
+-------------------------------------------------------------+
|                    Brain 层                                   |
|  (AI 提供商, Chat 引擎, 记忆, 技能)                           |
+-------------------------------------------------------------+
|                    基础设施层                                  |
|  (EventBus, 生命周期, 调度器, 数据库)                          |
+-------------------------------------------------------------+
```

### 组件概览

| 组件 | 位置 | 职责 |
|------|------|------|
| `PluginManager` | `loyan/core/plugin_manager.py` | 插件发现、加载、注册、热重载 |
| `ConfigManager` | `loyan/core/config_manager.py` | 配置加载、验证、插件配置 |
| `SecurityManager` | `loyan/core/security_manager.py` | RBAC、速率限制、黑名单、审计日志 |
| `AdapterPool` | `loyan/core/loyan_adapter/pool.py` | 多适配器实例管理 |
| `Pipeline` | `loyan/core/pipeline/pipeline.py` | 消息处理流水线（洋葱模型） |
| `LifecycleManager` | `loyan/core/lifecycle/lifecycle_manager.py` | 分阶段启动/关闭编排 |
| `RuntimeRegistry` | `loyan/core/runtime/runtime.py` | 每实例运行时状态管理 |
| `MonitorManager` | `loyan/core/monitor.py` | 系统指标和健康监控 |
| `EventBus` | `loyan/core/event.py` | 内部事件发布/订阅系统 |
| `ProviderManager` | `loyan/brain/provider/manager.py` | AI 提供商生命周期和模型管理 |

### 依赖容器

框架使用轻量级依赖注入容器（`loyan/core/container.py`）：

```python
container = Container()
container.register("adapter_pool", lambda _c: adapter_pool)
container.register("event_bus", lambda _c: event_bus)
container.register("config_manager", lambda _c: config_manager)
container.register("runtime_registry", lambda _c: RuntimeRegistry())
container.register("plugin_manager", lambda _c: plugin_manager)
```

组件在首次 `get()` 调用时惰性构造并缓存为单例。

## 2. 消息流水线

消息处理流水线遵循**洋葱模型**，包含五个顺序阶段。每个阶段可通过返回 `None` 短路后续阶段。

### 流水线流程

```
入站消息 (LoyanEvent)
        |
        v
+------------------+
|  SecurityFilter  |  日志记录、监控、输入验证
+------------------+
        |
        v
+------------------+
| BuiltinCommands  |  /关机, /重启, /关于, /帮助
+------------------+
        |
        v
+------------------+
| CommandMatcher   |  TOML + 装饰器命令匹配
+------------------+
        |
        v
+------------------+
|  PluginHandler   |  权限校验、插件执行、计时
+------------------+
        |
        v
+------------------+
| ResponseSender   |  自动回复、兜底分发（LLM）
+------------------+
        |
        v
+------------------+
| StatsCollector   |  使用量统计收集
+------------------+
```

### 阶段详解

#### SecurityFilter

**文件**：`loyan/core/pipeline/security_filter.py`

职责：
- 在监控器中记录消息已接收
- 使用上下文记录入站消息（发送者、聊天类型、内容）
- 在日志中脱敏用户 ID 以保护隐私

```python
class SecurityFilter(Stage):
    async def process(self, ctx: PluginContext) -> Optional[PluginContext]:
        # 记录到监控器
        monitor_manager.record_message_received()
        # 使用样式管道记录日志
        self._log_via_styling(ctx)
        return ctx
```

#### BuiltinCommands

**文件**：`loyan/core/pipeline/builtin_commands.py`

职责：
- 处理框架级命令：`/关机`、`/重启`、`/开机`、`/关于`
- 分发注册的内置命令（如 brain 的 `/chat`）
- 对危险操作强制执行仅主人权限

内置命令：
| 命令 | 权限 | 操作 |
|------|------|------|
| `/关机` | master | 优雅关闭机器人，支持 systemd |
| `/重启` | master | 进程重启（跨平台） |
| `/开机` | master | 通过 systemd 启动机器人服务 |
| `/关于` | all | 显示机器人版本、适配器、插件数量 |

#### CommandMatcher

**文件**：`loyan/core/pipeline/command_matcher.py`

职责：
- 将入站消息与 TOML 声明的命令匹配（并行匹配）
- 与 `@on_command` 装饰器注册的命令匹配
- 与 `@on_regex` 正则模式匹配
- 支持命令前缀替换（如用 `#` 代替 `/`）
- 支持命令别名
- 强制执行聊天类型、权限和 @提及要求
- 当多个插件匹配时选择最高优先级的匹配

匹配算法：
1. **TOML 匹配**（并行）：同时扫描所有插件的 `commands` 列表
2. **装饰器匹配**（顺序）：扫描 `DECORATOR_COMMAND_REGISTRY`
3. **正则匹配**：测试 `@on_regex` 模式
4. **优先级解析**：按插件 `priority` 字段排序（越大越优先）

```python
class CommandMatcher(Stage):
    async def process(self, ctx: PluginContext) -> Optional[PluginContext]:
        # 并行 TOML 匹配
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

        # 回退到装饰器匹配
        for entry in DECORATOR_COMMAND_REGISTRY:
            # ... 匹配命令和模式
```

#### PluginHandler

**文件**：`loyan/core/pipeline/plugin_handler.py`

职责：
- 执行匹配的插件处理函数
- 支持新风格（`ctx: PluginContext`）和旧风格（7 参数）签名
- 注入 `ctx.send` 和 `ctx.reply` 辅助函数
- 计时执行并记录性能指标
- 捕获和记录异常

```python
class PluginHandler(Stage):
    timeout: float = 300.0  # LLM 请求可能较慢，给 5 分钟

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
                # 旧风格处理器，7 个参数
                await handler_func(
                    ctx.plugin_manager, send, data,
                    ctx.sender_id, ctx.chat_type, "all", logger
                )
        except Exception as e:
            logger.error(f"插件错误：{e}", exc_info=True)

        return None
```

#### ResponseSender

**文件**：`loyan/core/pipeline/response_sender.py`

职责：
- 与 `auto_replies` 关键词字典匹配
- 分发到 `@on_fallback` 处理器（如 LLM 聊天）
- 未匹配消息的最终兜底

```python
class ResponseSender(Stage):
    async def process(self, ctx: PluginContext) -> Optional[PluginContext]:
        raw_msg = ctx.raw_text.strip()

        # 自动回复匹配
        auto_replies = config_manager.get("auto_replies", {})
        for keyword, reply in auto_replies.items():
            if keyword in raw_msg:
                await loyan_send_msg(ctx.target_id, LoyanText(text=reply))
                return None

        # 兜底处理器（LLM 等）
        for entry in FALLBACK_HANDLERS:
            if ctx.chat_type in entry.get("chat_type", []):
                await entry["handler_func"](ctx)
                return None

        return None
```

### 熔断器

流水线实现熔断器模式以实现容错：

- 连续 3 次失败后，阶段被"跳过"并跳过执行
- 30 秒后（可配置）尝试半开探针
- 如果探针成功，熔断器关闭；如果失败，恢复时间加倍（最大 300 秒）

### 流水线超时

- 每阶段超时：60 秒（每个阶段可配置）
- 全局流水线超时：120 秒

## 3. 状态机

### 生命周期阶段

框架使用严格的状态机，包含以下阶段：

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

### 阶段描述

| 阶段 | 值 | 描述 |
|------|-----|------|
| `CREATED` | 0 | 初始对象已创建，未初始化任何内容 |
| `CONFIG_LOADED` | 10 | 配置管理器加载完成 |
| `DATABASE_READY` | 20 | 数据库连接已建立 |
| `PLUGINS_SCANNED` | 30 | 插件目录已扫描，元数据已收集 |
| `PLUGINS_LOADED` | 40 | 所有插件已加载并注册 |
| `BRAIN_READY` | 50 | Brain 模块已初始化（提供商、密钥库、人设） |
| `INSTANCES_READY` | 60 | 机器人实例已创建，包含 Pipeline |
| `ADAPTERS_READY` | 70 | 适配器已连接到平台 |
| `RUNNING` | 80 | 完全可用，接受消息 |
| `STOPPING` | 90 | 关闭进行中 |
| `STOPPED` | 100 | 完全停止，所有资源已释放 |

### 转换规则

阶段只能在启动期间向前转换，在关闭期间向后转换：

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
    Phase.STOPPED: [Phase.CREATED],  # 允许重启
}
```

## 4. 生命周期管理

### LifecycleManager

`LifecycleManager`（`loyan/core/lifecycle/lifecycle_manager.py`）编排整个应用生命周期：

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

### 生命周期事件

模块在特定生命周期事件注册钩子：

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

### 钩子注册

```python
from loyan.core.lifecycle import lifecycle, LifecycleEvent

# 在特定事件注册钩子
lifecycle.register_hook(
    event=LifecycleEvent.READY,
    callback=my_ready_handler,
    name="my_handler",
    priority=50,
    timeout=30.0
)
```

### 钩子执行

钩子按优先级顺序执行（优先级越高越先执行），并强制超时：

```python
async def fire_event_async(self, event: LifecycleEvent) -> dict:
    return await self._executor.run_event(event)
```

### 启动流程

`main.py` 中的启动流程：

```python
async def run_bot():
    # 1. 设置日志
    logger_manager.setup_logging(log_level=LOG_LEVEL, debug_mode=DEBUG_MODE)

    # 2. 构建并设置依赖容器
    container = build_container()
    container.build()
    set_container(container)

    # 3. 加载配置
    config_manager.load()
    await lifecycle.fire_event_async(LifecycleEvent.AFTER_CONFIG_LOAD)

    # 4. 初始化插件（扫描元数据 + 加载模块）
    plugin_manager.init()
    await plugin_manager.async_load()
    await lifecycle.fire_event_async(LifecycleEvent.AFTER_PLUGINS_LOADED)

    # 5. 初始化 Brain（AI 提供商）
    import loyan.brain
    await lifecycle.fire_event_async(LifecycleEvent.AFTER_BRAIN_READY)

    # 6. 初始化实例（创建 Pipeline、适配器）
    await init_instances()
    await lifecycle.fire_event_async(LifecycleEvent.AFTER_INSTANCES_READY)

    # 7. 启动适配器（连接到平台）
    # （由 AFTER_INSTANCES_READY 上的生命周期钩子触发）
    await lifecycle.fire_event_async(LifecycleEvent.AFTER_ADAPTERS_START)

    # 8. 插件 on_ready 钩子
    plugin_manager.trigger_on_ready()
    await lifecycle.fire_event_async(LifecycleEvent.READY)
```

### 关闭流程

```python
async def _run_shutdown_sequence(self):
    await self._run_event(LifecycleEvent.BEFORE_SHUTDOWN)
    for phase in shutdown_range():
        self._state.transition(phase)
    await self._run_event(LifecycleEvent.AFTER_SHUTDOWN)
```

### 健康监控

生命周期系统包含健康监控：

```python
# 获取健康报告
report = lifecycle.health_report()
# {
#   "status": "healthy",
#   "phase": "RUNNING",
#   "uptime": 259200,
#   "components": { ... }
# }

# 注册自定义健康检查
lifecycle.register_check("my_service", check_my_service)

# 定期健康检查
await lifecycle.start_periodic_health_check(interval=60.0)
```

## 5. 运行时架构

### Runtime 实例

每个机器人账号由一个 `Runtime` 数据类表示：

```python
@dataclass
class Runtime:
    instance_name: str           # "主号"
    robot_id: str                # 机器人 QQ 号
    master_id: str               # 主人 QQ 号
    adapter_tag: IdentityTag     # 关联的适配器标签
    pipeline: Pipeline           # 独立的 Pipeline 实例
    logger: logging.Logger       # 独立的文件日志器
    plugin_manager: PluginManager  # 共享的插件管理器单例
    adapter_pool: AdapterPool    # 共享的适配器池单例
```

### RuntimeRegistry

全局注册表管理所有 Runtime 实例：

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

使用 Python 的 `contextvars` 在消息处理链中传递当前 Runtime：

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

这确保每个异步任务在其消息处理中看到正确的 Runtime，即使在并发处理中也是如此。

## 6. 适配器架构

### 适配器层次

```
LoyanAdapter (ABC)
  +-- OneBotAdapter
  +-- TelegramAdapter
  +-- QQOfficialAdapter
  +-- SatoriAdapter
```

### AdapterPool

管理多个适配器实例，提供线程安全操作：

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

标识每个适配器实例：

```python
@dataclass
class IdentityTag:
    platform: str       # "onebot"、"telegram" 等
    bot_name: str       # "主号"
    instance_id: str    # 唯一实例标识符

    @property
    def identity_key(self) -> str:
        return f"{self.platform}/{self.bot_name}/{self.instance_id}"
```

## 7. 事件系统

### EventBus

内部事件总线提供发布/订阅消息传递：

```python
class EventBus:
    async def publish(self, event: LoyanEvent): ...
    async def subscribe(self, event_type, handler, priority: int = 50): ...
    async def publish_business(self, event: BusinessEvent): ...
```

### 业务事件

模块通过类型化的业务事件进行通信：

```python
class EventType(str, Enum):
    PLUGIN_LOADED = "PLUGIN_LOADED"
    PLUGIN_UNLOADED = "PLUGIN_UNLOADED"
    INSTANCE_STARTED = "INSTANCE_STARTED"
    INSTANCE_STOPPED = "INSTANCE_STOPPED"
    # ...
```

## 8. 数据流

### 入站消息流

```
平台 (QQ/Telegram)
    |
    v
适配器 (OneBot/Telegram)
    |
    v
LoyanEvent (标准化)
    |
    v
EventBus.publish()
    |
    v
SecurityManager (黑名单检查、审计)
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
插件处理函数
    |
    v
ctx.send(LoyanText(...))
    |
    v
AdapterPool.send()
    |
    v
适配器.send()
    |
    v
平台 (QQ/Telegram)
```

### 出站消息流

```
插件调用 ctx.send()
    |
    v
RuntimeContext.get().adapter_tag
    |
    v
AdapterPool.get(tag)
    |
    v
适配器.send(target, segments, chat_type)
    |
    v
平台特定 API 调用
    |
    v
平台投递消息
```
