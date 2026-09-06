# Разработка плагинов

LoyanBot обладает мощной системой плагинов, позволяющей расширять функциональность бота. Это руководство описывает всё, что вам нужно знать о создании, настройке и публикации плагинов.

## 1. Обзор системы плагинов

### Архитектура

Плагины - это Python-пакеты, которые фреймворк обнаруживает, загружает и управляет ими во время выполнения. Система плагинов поддерживает:

- Объявление метаданных на основе TOML
- Регистрацию команд на основе декораторов
- Управление зависимостями между плагинами
- Горячую перезагрузку без перезапуска бота
- Магазин плагинов для распространения
- Индивидуальную конфигурацию и хранение данных для каждого плагина

### Обнаружение плагинов

Менеджер плагинов сканирует две директории для поиска плагинов:

1. **Системные плагины**: `loyan/plugins/` (встроенные, поставляемые с фреймворком)
2. **Пользовательские плагины**: `storage/plugins/` (установленные из магазина или созданные вручную)

## 2. Структура директории плагина

Плагин состоит из следующих файлов:

```
MyPlugin/
  metadata.toml       # Метаданные плагина (обязательно)
  main.py             # Основной модуль с обработчиками (обязательно)
  config.py           # Конфигурация по умолчанию (опционально)
  config.json         # Конфигурация плагина (генерируется автоматически)
  res/                # Статические ресурсы (опционально)
  core/               # Дополнительные модули (опционально)
    draw.py
  requirements.txt    # Зависимости Python (опционально)
```

### Минимальный плагин

```
HelloWorld/
  metadata.toml
  main.py
```

### Стандартный плагин

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

## 3. Метаданные плагина (metadata.toml)

Файл `metadata.toml` объявляет идентичность, команды и поведение плагина.

### Полный пример metadata.toml

```toml
[plugin]
name        = "Запрос погоды"
version     = "1.0.0"
author      = "Разработчик"
description = "Запрос информации о погоде для любого города"
category    = "utility"
tags        = ["weather", "utility"]
icon        = "weather.png"
priority    = 50

[handler]
entry       = "handle_weather"

[trigger]
commands       = ["/weather", "/погода"]
chat_type      = ["private", "group"]
permission     = "all"
is_at_required = false

[dependencies]
# Нет зависимостей
```

### Поля метаданных

#### Раздел [plugin]

| Поле | Тип | Обязательно | Описание |
|------|-----|-------------|----------|
| `name` | string | Да | Отображаемое имя в справке и магазине |
| `version` | string | Да | Семантический номер версии (например, `"1.0.0"`) |
| `author` | string | Нет | Имя автора плагина |
| `description` | string | Нет | Краткое описание функциональности |
| `category` | string | Нет | Категория для организации в магазине |
| `tags` | list | Нет | Теги для поиска и фильтрации |
| `icon` | string | Нет | Имя файла иконки (относительно директории плагина) |
| `priority` | int | Нет | Приоритет выполнения (по умолчанию: 50, чем выше - тем раньше) |

#### Раздел [handler]

| Поле | Тип | Обязательно | Описание |
|------|-----|-------------|----------|
| `entry` | string | Да | Имя основной функции-обработчика в `main.py` |

#### Раздел [trigger]

| Поле | Тип | Обязательно | Описание |
|------|-----|-------------|----------|
| `commands` | list | Да | Список команд-триггеров (например, `["/weather", "/погода"]`) |
| `chat_type` | list | Нет | Допустимые типы чата: `["private", "group"]` (по умолчанию: оба) |
| `permission` | string | Нет | Требуемое разрешение: `"all"`, `"master"`, `"admin"` (по умолчанию: `"all"`) |
| `is_at_required` | bool | Нет | Требуется ли упоминание @бота в групповых чатах (по умолчанию: false) |

#### Раздел [dependencies]

```toml
[dependencies]
[[deps]]
name = "Help_plugin"
min_version = "1.0.0"
max_version = "2.0.0"
```

## 4. Жизненный цикл плагина

### Последовательность загрузки

1. **Сканирование**: Менеджер плагинов сканирует директории плагинов для поиска `metadata.toml`
2. **Валидация**: Проверка синтаксиса метаданных и обязательных полей
3. **Проверка зависимостей**: Удовлетворение всех зависимостей
4. **Загрузка модуля**: Импорт `main.py` (или `<имя_плагина>.py`)
5. **Регистрация**: Сканирование функций с декораторами и регистрация команд
6. **Конфигурация**: Инициализация конфигурации плагина из `config.py` и `config.json`
7. **Выполнение**: Вызов входной функции-обработчика при первом совпадении команды

### Хуки жизненного цикла

Плагины могут определять следующие необязательные функции:

```python
# Вызывается после запуска бота (после загрузки всех плагинов)
def on_ready():
    pass

# Вызывается при выключении бота
def on_shutdown():
    pass
```

### Горячая перезагрузка

Фреймворк отслеживает изменения в директориях плагинов с помощью `watchfiles`:

- Изменение файла запускает целевую перезагрузку изменённого плагина
- Добавление/удаление директории плагина запускает полное повторное сканирование
- Файлы данных во время выполнения (изображения, кэш) не запускают перезагрузку
- Наблюдатель запускается автоматически при достижении фазы `READY`

Ручная перезагрузка плагина:

```bash
loyan plugin reload <имя_плагина>
```

## 5. API плагинов

### Декораторы

Пакет `graci` предоставляет декораторы для разработки плагинов:

#### @on_command

Объявляет функции-триггеры команд:

```python
from graci import on_command, plugin_handler, PluginContext

@on_command("/hello", "/привет")
@plugin_handler
async def handle_hello(ctx: PluginContext):
    await ctx.send("Привет!")
```

#### @on_regex

Триггерится при совпадении с регулярным выражением:

```python
from graci import on_regex, plugin_handler, PluginContext
import re

@on_regex(r"weather\s+(\w+)", flags=re.IGNORECASE)
@plugin_handler
async def handle_weather_regex(ctx: PluginContext):
    match = ctx.extra.get("_regex_match")
    city = match.group(1) if match else "unknown"
    await ctx.send(f"Погода в {city}")
```

#### @on_keyword

Триггерится при наличии определённых ключевых слов:

```python
from graci import on_keyword, plugin_handler, PluginContext

@on_keyword("привет", "hi", "hey")
@plugin_handler
async def handle_greeting(ctx: PluginContext):
    await ctx.send("Привет!")
```

#### @on_fallback

Обрабатывает сообщения, не совпавшие ни с одним другим плагином:

```python
from graci import on_fallback, plugin_handler, PluginContext

@on_fallback()
@plugin_handler
async def handle_unmatched(ctx: PluginContext):
    await ctx.send("Я не понимаю эту команду.")
```

#### @brain_tool

Объявляет инструмент, доступный для AI:

```python
from graci import brain_tool, PluginContext

@brain_tool(
    name="get_weather",
    description="Получить текущую погоду для города",
    params={"city": {"type": "string", "description": "Название города"}},
    permission="admin"
)
def get_weather(ctx: PluginContext, city: str = "") -> str:
    return f"Погода в {city}: Ясно, 25C"
```

#### @plugin_handler

Обязательная обёртка для всех функций-обработчиков. Обрабатывает:
- Проверку разрешений
- Ограничение частоты
- Принудительную перезарядку
- Замер времени и мониторинг
- Перехват исключений

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
@cooldown(seconds=86400)  # Раз в день
@plugin_handler
async def handle_daily(ctx: PluginContext):
    pass
```

### PluginContext

Класс данных `PluginContext` предоставляет всю информацию о текущем сообщении:

```python
@dataclass
class PluginContext:
    sender_id: str           # Пользователь, отправивший сообщение
    target_id: str           # Цель (отправитель для личных, ID группы для групповых)
    chat_type: str           # "private" или "group"
    nickname: str            # Отображаемое имя отправителя
    raw_text: str            # Исходный текст сообщения
    text: str                # Очищенный текст
    images: List[str]        # ID файлов изображений
    ats: List[str]           # ID упомянутых пользователей
    is_at_bot: bool          # Был ли упомянут бот
    command: str             # Совпавшая строка команды
    plugin_name: str         # Имя текущего плагина
    raw_data: dict           # Исходные данные платформы
    send: Callable           # Функция отправки сообщения
    reply: Callable          # Функция быстрого ответа
    logger: Callable         # Логгер плагина
    session: Any             # Объект сессии (если есть @with_session)
    runtime: Runtime         # Текущий экземпляр Runtime
```

### Отправка сообщений

```python
from graci import LoyanText, LoyanImage, LoyanAt

# Отправка текста
await ctx.send(LoyanText(text="Привет!"))

# Отправка изображения из файла
await ctx.send(LoyanImage(file_path="/path/to/image.png"))

# Отправка изображения по URL
await ctx.send(LoyanImage(url="https://example.com/image.png"))

# Отправка @упоминания
await ctx.send(LoyanAt(target_id="123456"))

# Ответ на сообщение
await ctx.reply("Это ответ!")

# Отправка нескольких сегментов
await ctx.send(
    LoyanText(text="Результат:"),
    LoyanImage(file_path="result.png")
)
```

### Типы сообщений

| Тип | Поля | Описание |
|-----|------|----------|
| `LoyanText` | `text: str` | Текстовое сообщение |
| `LoyanImage` | `file_path`, `url`, `file_data` | Изображение (файл, URL или байты) |
| `LoyanAt` | `target_id: str` | @упоминание пользователя |
| `LoyanReply` | `message_id: str` | Ответ на сообщение |
| `LoyanVoice` | `file_path: str` | Голосовое сообщение |
| `LoyanFile` | `file_path`, `url` | Файл-вложение |
| `LoyanVideo` | `file_path`, `url`, `file_data` | Видеосообщение |
| `LoyanForward` | `forward_id`, `title` | Пересланное сообщение |

### Утилиты путей

Класс `LoyanPaths` предоставляет стандартизированные пути для данных плагина:

```python
from graci import LoyanPaths

paths = LoyanPaths("MyPlugin")

# Директория данных (storage/data/plugins/MyPlugin/)
data_dir = paths.data()

# Директория ресурсов (папка res/ плагина)
res_dir = paths.res()

# Путь к файлу базы данных
db_path = paths.db()

# Временная директория
tmp_dir = paths.temp()
```

### Доступ к конфигурации

```python
from graci import config_manager

# Получить конфигурацию плагина
config = config_manager.get_plugin("MyPlugin")

# Получить конкретный ключ
api_key = config_manager.get_plugin("MyPlugin", key="api_key", default="")

# Обновить конфигурацию плагина
config_manager.update_plugin("MyPlugin", {"api_key": "new_key"})
```

### Логирование

```python
from graci import get_logger

logger = get_logger("MyPlugin")
logger.info("Плагин запущен")
logger.warning("Используется устаревшая функция")
logger.error("Операция не удалась", exc_info=True)
```

## 6. Конфигурация плагина

### Конфигурация по умолчанию (config.py)

```python
# MyPlugin/config.py
DEFAULT_CONFIG = {
    "api_key": "",
    "max_results": 10,
    "timeout": 30,
    "language": "ru"
}
```

### Приоритет конфигурации

Конфигурация объединяется в следующем порядке (побеждает последний):

1. `DEFAULT_CONFIG` из `config.py`
2. `storage/config.json` (глобальная пользовательская конфигурация)
3. `storage/config/<имя_плагина>/config.json` (глобальная конфигурация плагина)
4. `storage/instances/<экземпляр>/plugins/<имя_плагина>/config.json` (конфигурация экземпляра)

### Валидация Schema (plugin_conf.json)

```json
{
  "api_key": {
    "type": "str",
    "default": "",
    "description": "API-ключ для сервиса",
    "required": true
  },
  "max_results": {
    "type": "int",
    "default": 10,
    "description": "Максимальное количество результатов",
    "options": [5, 10, 20, 50]
  }
}
```

## 7. Управление зависимостями

### Объявление зависимостей

В `metadata.toml`:

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

### Обнаружение циклических зависимостей

Менеджер плагинов автоматически обнаруживает циклические зависимости с помощью обхода в глубину (DFS). Если обнаружен цикл, записывается ошибка и затронутые плагины не загружаются.

### Сравнение версий

Версии плагинов сравниваются числовым образом:
- `"1.0.0"` vs `"1.0.1"` -> `"1.0.0"` меньше
- `"2.0"` vs `"1.9.9"` -> `"2.0"` больше

## 8. Горячая перезагрузка

### Автоматическая горячая перезагрузка

Наблюдатель плагинов отслеживает директории плагинов и автоматически перезагружает изменённые плагины:

```python
# Наблюдатель запускается автоматически на фазе жизненного цикла READY
# Использует watchfiles для эффективного мониторинга файловой системы
# Изменения подавляются в течение 300мс
```

### Что запускает перезагрузку

| Тип изменения | Действие |
|---------------|----------|
| Изменение файла `.py` | Целевая перезагрузка изменённого плагина |
| Новая директория плагина | Полное повторное сканирование всех плагинов |
| Удалённая директория плагина | Полное повторное сканирование всех плагинов |
| Изменение `metadata.toml` | Полное повторное сканирование всех плагинов |
| Изменение данных во время выполнения | Нет действия (изображения, кэш и т.д.) |

### Ручная перезагрузка

```bash
# Через CLI
loyan plugin reload <имя_плагина>

# Или через API
POST /api/plugins/<имя_плагина>/reload
```

## 9. Полный пример

### Плагин Hello World

**metadata.toml**:
```toml
[plugin]
name        = "Hello World"
version     = "1.0.0"
author      = "Разработчик"
description = "Простой плагин Hello World"

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
    """Ответить приветствием."""
    await ctx.send(LoyanText(text=f"Привет {ctx.nickname}!"))
```

### Плагин погоды с конфигурацией

**metadata.toml**:
```toml
[plugin]
name        = "Погода"
version     = "1.0.0"
author      = "Разработчик"
description = "Запрос информации о погоде"

[handler]
entry       = "handle_weather"

[trigger]
commands    = ["/weather", "/погода"]
chat_type   = ["private", "group"]
permission  = "all"
```

**config.py**:
```python
DEFAULT_CONFIG = {
    "api_key": "",
    "default_city": "Москва",
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
    """Запросить погоду для города."""
    # Извлечь город из сообщения
    text = ctx.raw_text
    city = text.replace("/weather", "").strip() or config.get("default_city", "Москва")

    if not config.get("api_key"):
        await ctx.reply("API-ключ погоды не настроен.")
        return

    # Запрос погоды (упрощённый)
    try:
        weather_data = await query_weather(city, config["api_key"])
        await ctx.reply(f"Погода в {city}: {weather_data}")
    except Exception as e:
        logger.error(f"Запрос погоды не удался: {e}")
        await ctx.reply("Не удалось запросить погоду.")
```

## 10. Методы отладки

### Включение отладочного логирования

Установите `log_level` в `DEBUG` в `config.json`:

```json
{
  "log_level": "DEBUG"
}
```

### Режим отладки плагина

Проверьте статус загрузки плагина в логах:

```
[INFO] Менеджер плагинов инициализирован!
[INFO]   1. Hello World | Версия: 1.0.0 | Приоритет: 50 | Команды: /hello
```

### Частые проблемы

1. **Плагин не загружается**: Проверьте наличие `metadata.toml` и правильность синтаксиса
2. **Команда не совпадает**: Убедитесь, что строки команд совпадают точно (с учётом регистра)
3. **Ошибки импорта**: Убедитесь, что все импорты из `graci` или стандартной библиотеки
4. **Конфигурация не найдена**: Вызовите `config_manager.register_plugin_config()` в `main.py`

### Тестирование плагинов

```python
# Используйте тестовый фреймворк
from loyan.core.decorators.registration import clear_registry
from loyan.core.plugin_manager import PluginManager

# Создайте тестовый экземпляр
pm = PluginManager(config_manager=mock_config, logger=mock_logger)
```

## 11. Публикация в магазине плагинов

### Требования магазина

Для публикации плагина в официальном магазине:

1. Плагин должен иметь действительный `metadata.toml`
2. Плагин должен быть размещён в публичном Git-репозитории
3. Репозиторий должен иметь ветку `main` (или указанную ветку)
4. Плагин не должен содержать вредоносный код

### Конфигурация магазина

Настройте источники магазина в `config.json`:

```json
{
  "store": {
    "sources": [
      {
        "name": "Официальный",
        "store_url": "http://38.55.145.10:16385/store.json",
        "enabled": true
      }
    ],
    "git_mirrors": ["https://ghproxy.com/"]
  }
}
```

### Отправка плагина

Свяжитесь с командой разработки LoyanBot и предоставьте:

1. URL Git-репозитория
2. Описание плагина
3. Информацию об авторе
4. Лицензию (совместимую с GPL-3.0)

### Установка из магазина

```bash
# Список доступных плагинов
loyan plugin list

# Установка плагина
loyan plugin install <имя_плагина>

# Обновление плагина
loyan plugin update <имя_плагина>

# Удаление плагина
loyan plugin uninstall <имя_плагина>
```
