# Архитектура

LoyanBot построен на слоистой, модульной архитектуре, разделяющей обязанности и обеспечивающей расширяемость. Этот документ описывает общую архитектуру, конвейер обработки сообщений, конечный автомат и систему управления жизненным циклом.

## 1. Общая архитектура

### Диаграмма слоев

```
+-------------------------------------------------------------+
|                    Слой приложений                            |
|  (bot.py, CLI, Веб-панель)                                  |
+-------------------------------------------------------------+
|                    Ядро                                       |
|  (Pipeline, PluginManager, ConfigManager, SecurityManager)  |
+-------------------------------------------------------------+
|                    Слой адаптеров                             |
|  (OneBot, Telegram, QQ Official, Satori)                    |
+-------------------------------------------------------------+
|                    Слой Brain                                |
|  (AI-поставщики, Chat-движок, Память, Навыки)               |
+-------------------------------------------------------------+
|                    Инфраструктурный слой                      |
|  (EventBus, Жизненный цикл, Планировщик, База данных)       |
+-------------------------------------------------------------+
```

### Обзор компонентов

| Компонент | Расположение | Ответственность |
|-----------|-------------|-----------------|
| `PluginManager` | `loyan/core/plugin_manager.py` | Обнаружение, загрузка, регистрация, горячая перезагрузка плагинов |
| `ConfigManager` | `loyan/core/config_manager.py` | Загрузка, валидация конфигурации, конфигурация плагинов |
| `SecurityManager` | `loyan/core/security_manager.py` | RBAC, ограничение частоты, черный список, аудит логирования |
| `AdapterPool` | `loyan/core/loyan_adapter/pool.py` | Управление экземплярами нескольких адаптеров |
| `Pipeline` | `loyan/core/pipeline/pipeline.py` | Конвейер обработки сообщений (модель луковицы) |
| `LifecycleManager` | `loyan/core/lifecycle/lifecycle_manager.py` | Фазированное управление запуском/остановкой |
| `RuntimeRegistry` | `loyan/core/runtime/runtime.py` | Управление состоянием выполнения каждого экземпляра |
| `MonitorManager` | `loyan/core/monitor.py` | Метрики системы и мониторинг здоровья |
| `EventBus` | `loyan/core/event.py` | Внутренняя система публикации/подписки на события |
| `ProviderManager` | `loyan/brain/provider/manager.py` | Управление жизненным циклом AI-поставщиков и моделями |

### Контейнер зависимостей

Фреймворк использует легковесный контейнер инъекции зависимостей (`loyan/core/container.py`):

```python
container = Container()
container.register("adapter_pool", lambda _c: adapter_pool)
container.register("event_bus", lambda _c: event_bus)
container.register("config_manager", lambda _c: config_manager)
container.register("runtime_registry", lambda _c: RuntimeRegistry())
container.register("plugin_manager", lambda _c: plugin_manager)
```

Компоненты создаются лениво при первом вызове `get()` и кэшируются как синглтоны.

## 2. Конвейер обработки сообщений

Конвейер обработки сообщений следует **модели луковицы** с пятью последовательными этапами. Каждый этап может прервать конвейер, вернув `None`.

### Поток конвейера

```
Входящее сообщение (LoyanEvent)
        |
        v
+------------------+
|  SecurityFilter  |  Логирование, мониторинг, валидация ввода
+------------------+
        |
        v
+------------------+
| BuiltinCommands  |  /shutdown, /restart, /about, /help
+------------------+
        |
        v
+------------------+
| CommandMatcher   |  Совпадение команд TOML + декораторов
+------------------+
        |
        v
+------------------+
|  PluginHandler   |  Проверка разрешений, выполнение, замер времени
+------------------+
        |
        v
+------------------+
| ResponseSender   |  Автоответ, обработчик fallback (LLM)
+------------------+
        |
        v
+------------------+
| StatsCollector   |  Сбор статистики использования
+------------------+
```

### Подробности этапов

#### SecurityFilter

**Файл**: `loyan/core/pipeline/security_filter.py`

Ответственность:
- Запись полученного сообщения в монитор
- Логирование входящего сообщения с контекстом (отправитель, тип чата, содержание)
- Маскировка ID пользователей в логах для защиты конфиденциальности

```python
class SecurityFilter(Stage):
    async def process(self, ctx: PluginContext) -> Optional[PluginContext]:
        # Запись в монитор
        monitor_manager.record_message_received()
        # Логирование через стилизованную конвейерную обработку
        self._log_via_styling(ctx)
        return ctx
```

#### BuiltinCommands

**Файл**: `loyan/core/pipeline/builtin_commands.py`

Ответственность:
- Обработка команд фреймворка: `/shutdown`, `/restart`, `/about`, `/help`
- Диспетчеризация зарегистрированных встроенных команд (например, `/chat` от brain)
- Принудительное выполнение разрешений только для владельца для опасных операций

Встроенные команды:
| Команда | Разрешение | Действие |
|---------|-----------|----------|
| `/shutdown` | master | Изящное выключение бота с поддержкой systemd |
| `/restart` | master | Перезапуск процесса (кроссплатформенный) |
| `/startup` | master | Запуск сервиса бота через systemd |
| `/about` | all | Отображение версии бота, адаптеров, количества плагинов |

#### CommandMatcher

**Файл**: `loyan/core/pipeline/command_matcher.py`

Ответственность:
- Сопоставление входящих сообщений с командами, объявленными в TOML (параллельное сопоставление)
- Сопоставление с командами, зарегистрированными через декораторы `@on_command`
- Сопоставление с регулярными выражениями `@on_regex`
- Поддержка замены префикса команды (например, `#` вместо `/`)
- Поддержка псевдонимов команд
- Принудительное выполнение требований типа чата, разрешений и упоминаний
- Выбор совпадения с наивысшим приоритетом при совпадении нескольких плагинов

Алгоритм сопоставления:
1. **TOML сопоставление** (параллельное): Одновременное сканирование списков `commands` всех плагинов
2. **Сопоставление декораторов** (последовательное): Сканирование `DECORATOR_COMMAND_REGISTRY`
3. **Сопоставление регулярных выражений**: Тестирование паттернов `@on_regex`
4. **Разрешение приоритета**: Сортировка по полю `priority` плагина (чем выше, тем лучше)

```python
class CommandMatcher(Stage):
    async def process(self, ctx: PluginContext) -> Optional[PluginContext]:
        # Параллельное TOML сопоставление
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

        # Fallback на сопоставление декораторов
        for entry in DECORATOR_COMMAND_REGISTRY:
            # ... сопоставление команд и паттернов
```

#### PluginHandler

**Файл**: `loyan/core/pipeline/plugin_handler.py`

Ответственность:
- Выполнение функции-обработчика совпавшего плагина
- Поддержка нового стиля (`ctx: PluginContext`) и старого стиля (7-параметровая) сигнатуры
- Внедрение вспомогательных функций `ctx.send` и `ctx.reply`
- Замер времени выполнения и логирование метрик производительности
- Перехват и логирование исключений

```python
class PluginHandler(Stage):
    timeout: float = 300.0  # Запросы LLM могут быть медленными, 5 минут

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
                # Старый стиль обработчика с 7 параметрами
                await handler_func(
                    ctx.plugin_manager, send, data,
                    ctx.sender_id, ctx.chat_type, "all", logger
                )
        except Exception as e:
            logger.error(f"Ошибка плагина: {e}", exc_info=True)

        return None
```

#### ResponseSender

**Файл**: `loyan/core/pipeline/response_sender.py`

Ответственность:
- Сопоставление со словарем ключевых слов `auto_replies`
- Диспетчеризация к обработчикам `@on_fallback` (например, LLM чат)
- Окончательный fallback для несовпавших сообщений

```python
class ResponseSender(Stage):
    async def process(self, ctx: PluginContext) -> Optional[PluginContext]:
        raw_msg = ctx.raw_text.strip()

        # Сопоставление автоответов
        auto_replies = config_manager.get("auto_replies", {})
        for keyword, reply in auto_replies.items():
            if keyword in raw_msg:
                await loyan_send_msg(ctx.target_id, LoyanText(text=reply))
                return None

        # Fallback обработчик (LLM и т.д.)
        for entry in FALLBACK_HANDLERS:
            if ctx.chat_type in entry.get("chat_type", []):
                await entry["handler_func"](ctx)
                return None

        return None
```

### Размыкатель цепи

Конвейер реализует паттерн размыкателя цепи для отказоустойчивости:

- После 3 последовательных неудач этап "отключается" и пропускается
- Через 30 секунд (настраивается) предпринимается полупробное открытие
- Если проба успешна, размыкатель закрывается; если нет, время восстановления удваивается (макс. 300 сек)

### Тайм-аут конвейера

- Тайм-аут этапа: 60 секунд (настраивается для каждого этапа)
- Глобальный тайм-аут конвейера: 120 секунд

## 3. Конечный автомат

### Фазы жизненного цикла

Фреймворк использует строгий конечный автомат со следующими фазами:

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

### Описание фаз

| Фаза | Значение | Описание |
|------|---------|----------|
| `CREATED` | 0 | Начальный объект создан, ничего не инициализировано |
| `CONFIG_LOADED` | 10 | Загрузка менеджера конфигурации завершена |
| `DATABASE_READY` | 20 | Подключение к базе данных установлено |
| `PLUGINS_SCANNED` | 30 | Директории плагинов просканированы, метаданные собраны |
| `PLUGINS_LOADED` | 40 | Все плагины загружены и зарегистрированы |
| `BRAIN_READY` | 50 | Модуль Brain инициализирован (поставщики, хранилище ключей, персона) |
| `INSTANCES_READY` | 60 | Экземпляры ботов созданы с Pipeline |
| `ADAPTERS_READY` | 70 | Адаптеры подключены к платформам |
| `RUNNING` | 80 | Полностью готов к приему сообщений |
| `STOPPING` | 90 | Выполняется выключение |
| `STOPPED` | 100 | Полностью остановлен, все ресурсы освобождены |

### Правила переходов

Фазы могут переходить только вперед при запуске и назад при выключении:

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
    Phase.STOPPED: [Phase.CREATED],  # Разрешить перезапуск
}
```

## 4. Управление жизненным циклом

### LifecycleManager

`LifecycleManager` (`loyan/core/lifecycle/lifecycle_manager.py`) управляет всем жизненным циклом приложения:

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

### События жизненного цикла

Модули регистрируют хуки на определенных событиях жизненного цикла:

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

### Регистрация хуков

```python
from loyan.core.lifecycle import lifecycle, LifecycleEvent

# Регистрация хука на определенном событии
lifecycle.register_hook(
    event=LifecycleEvent.READY,
    callback=my_ready_handler,
    name="my_handler",
    priority=50,
    timeout=30.0
)
```

### Выполнение хуков

Хуки выполняются в порядке приоритета (чем выше приоритет, тем раньше) с принудительным тайм-аутом:

```python
async def fire_event_async(self, event: LifecycleEvent) -> dict:
    return await self._executor.run_event(event)
```

### Последовательность запуска

Последовательность запуска в `main.py`:

```python
async def run_bot():
    # 1. Настройка логирования
    logger_manager.setup_logging(log_level=LOG_LEVEL, debug_mode=DEBUG_MODE)

    # 2. Построение и установка контейнера зависимостей
    container = build_container()
    container.build()
    set_container(container)

    # 3. Загрузка конфигурации
    config_manager.load()
    await lifecycle.fire_event_async(LifecycleEvent.AFTER_CONFIG_LOAD)

    # 4. Инициализация плагинов (сканирование метаданных + загрузка модулей)
    plugin_manager.init()
    await plugin_manager.async_load()
    await lifecycle.fire_event_async(LifecycleEvent.AFTER_PLUGINS_LOADED)

    # 5. Инициализация Brain (AI-поставщики)
    import loyan.brain
    await lifecycle.fire_event_async(LifecycleEvent.AFTER_BRAIN_READY)

    # 6. Инициализация экземпляров (создание Pipeline, адаптеров)
    await init_instances()
    await lifecycle.fire_event_async(LifecycleEvent.AFTER_INSTANCES_READY)

    # 7. Запуск адаптеров (подключение к платформам)
    # (Запускается хуком жизненного цикла на AFTER_INSTANCES_READY)
    await lifecycle.fire_event_async(LifecycleEvent.AFTER_ADAPTERS_START)

    # 8. Хуки on_ready плагинов
    plugin_manager.trigger_on_ready()
    await lifecycle.fire_event_async(LifecycleEvent.READY)
```

### Последовательность выключения

```python
async def _run_shutdown_sequence(self):
    await self._run_event(LifecycleEvent.BEFORE_SHUTDOWN)
    for phase in shutdown_range():
        self._state.transition(phase)
    await self._run_event(LifecycleEvent.AFTER_SHUTDOWN)
```

### Мониторинг здоровья

Система жизненного цикла включает мониторинг здоровья:

```python
# Получение отчета о здоровье
report = lifecycle.health_report()
# {
#   "status": "healthy",
#   "phase": "RUNNING",
#   "uptime": 259200,
#   "components": { ... }
# }

# Регистрация пользовательских проверок здоровья
lifecycle.register_check("my_service", check_my_service)

# Периодические проверки здоровья
await lifecycle.start_periodic_health_check(interval=60.0)
```

## 5. Архитектура выполнения

### Экземпляр Runtime

Каждый аккаунт бota представлен классом данных `Runtime`:

```python
@dataclass
class Runtime:
    instance_name: str           # "основной"
    robot_id: str                # QQ-номер бота
    master_id: str               # QQ-номер владельца
    adapter_tag: IdentityTag     # Связанный тег адаптера
    pipeline: Pipeline           # Независимый экземпляр Pipeline
    logger: logging.Logger       # Независимый файловый логгер
    plugin_manager: PluginManager  # Синглтон общего менеджера плагинов
    adapter_pool: AdapterPool    # Синглтон общего пула адаптеров
```

### RuntimeRegistry

Глобальный реестр управляет всеми экземплярами Runtime:

```python
class RuntimeRegistry:
    _runtimes: Dict[str, Runtime]      # ключ = identity_key
    _by_robot_id: Dict[str, Runtime]   # ключ = robot_id

    @classmethod
    def register(cls, runtime: Runtime): ...
    @classmethod
    def get_by_tag(cls, tag: IdentityTag): ...
    @classmethod
    def get_by_robot_id(cls, robot_id: str): ...
```

### RuntimeContext

Использует `contextvars` Python для передачи текущего Runtime через цепочку обработки сообщений:

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

Это гарантирует, что каждая асинхронная задача видит правильный Runtime для своего сообщения, даже при конкурентной обработке.

## 6. Архитектура адаптеров

### Иерархия адаптеров

```
LoyanAdapter (ABC)
  +-- OneBotAdapter
  +-- TelegramAdapter
  +-- QQOfficialAdapter
  ++-- SatoriAdapter
```

### AdapterPool

Управляет несколькими экземплярами адаптеров с потокобезопасными операциями:

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

Идентифицирует каждый экземпляр адаптера:

```python
@dataclass
class IdentityTag:
    platform: str       # "onebot", "telegram" и т.д.
    bot_name: str       # "ОсновнойБот"
    instance_id: str    # Уникальный идентификатор экземпляра

    @property
    def identity_key(self) -> str:
        return f"{self.platform}/{self.bot_name}/{self.instance_id}"
```

## 7. Система событий

### EventBus

Внутренняя шина событий обеспечивает публикацию/подписку на сообщения:

```python
class EventBus:
    async def publish(self, event: LoyanEvent): ...
    async def subscribe(self, event_type, handler, priority: int = 50): ...
    async def publish_business(self, event: BusinessEvent): ...
```

### Бизнес-события

Модули общаются через типизированные бизнес-события:

```python
class EventType(str, Enum):
    PLUGIN_LOADED = "PLUGIN_LOADED"
    PLUGIN_UNLOADED = "PLUGIN_UNLOADED"
    INSTANCE_STARTED = "INSTANCE_STARTED"
    INSTANCE_STOPPED = "INSTANCE_STOPPED"
    # ...
```

## 8. Поток данных

### Входящий поток сообщений

```
Платформа (QQ/Telegram)
    |
    v
Адаптер (OneBot/Telegram)
    |
    v
LoyanEvent (нормализованное)
    |
    v
EventBus.publish()
    |
    v
SecurityManager (проверка черного списка, аудит)
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
Функция-обработчик плагина
    |
    v
ctx.send(LoyanText(...))
    |
    v
AdapterPool.send()
    |
    v
Адаптер.send()
    |
    v
Платформа (QQ/Telegram)
```

### Исходящий поток сообщений

```
Плагин вызывает ctx.send()
    |
    v
RuntimeContext.get().adapter_tag
    |
    v
AdapterPool.get(tag)
    |
    v
Адаптер.send(target, segments, chat_type)
    |
    v
Вызов API特定于 платформы
    |
    v
Платформа доставляет сообщение
```
