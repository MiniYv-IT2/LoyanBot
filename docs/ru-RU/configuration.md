# Руководство по конфигурации

LoyanBot использует иерархическую систему конфигурации с JSON-файлами и переопределением через переменные окружения. Это руководство описывает все доступные параметры конфигурации фреймворка.

## 1. Обзор файла конфигурации

### Иерархия конфигурации

Конфигурация загружается из нескольких источников с следующим приоритетом (высший приоритет побеждает):

1. Переменные окружения (префикс `GRACY_`)
2. Файловая конфигурация (`storage/config.json`)
3. Значения по умолчанию Schema (встроенные во фреймворк)

### Файлы конфигурации

| Файл | Расположение | Назначение |
|------|-------------|------------|
| `config.json` | `storage/config.json` | Глобальная конфигурация фреймворка |
| `config.json` | `storage/instances/<имя>/config.json` | Конфигурация экземпляра |
| `config.json` | `storage/config/<имя_плагина>_config.json` | Конфигурация плагина |
| `plugin_conf.json` | `loyan/plugins/<имя>/plugin_conf.json` | Значения по умолчанию Schema плагина |
| `settings.schema_conf.json` | `loyan/core/config/settings.schema_conf.json` | Определения полей фреймворка |

## 2. Базовая конфигурация

### bot_version

| Свойство | Значение |
|----------|----------|
| Тип | `string` |
| По умолчанию | `"v1.9.25"` |
| Описание | Идентификатор версии фреймворка (автоматически обновляется при обновлении) |

```json
{
  "bot_version": "v1.9.25"
}
```

### log_level

| Свойство | Значение |
|----------|----------|
| Тип | `string` |
| По умолчанию | `"INFO"` |
| Варианты | `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` |
| Описание | Управляет подробностью вывода логов |

```json
{
  "log_level": "INFO"
}
```

### log_encoding

| Свойство | Значение |
|----------|----------|
| Тип | `string` |
| По умолчанию | `"utf-8"` |
| Описание | Кодировка, используемая для файлов логов |

```json
{
  "log_encoding": "utf-8"
}
```

### debug_mode

| Свойство | Значение |
|----------|----------|
| Тип | `bool` |
| По умолчанию | `false` |
| Описание | При включении логи выводятся в структурированном JSON-формате со стек-трейсами |

```json
{
  "debug_mode": false
}
```

### auto_replies

| Свойство | Значение |
|----------|----------|
| Тип | `dict` |
| По умолчанию | `{}` |
| Описание | Соответствие ключевых слов ответам для автоматических ответов. Сопоставляется на этапе `ResponseSender`, когда ни один плагин не совпадает с сообщением. |

```json
{
  "auto_replies": {
    "привет": "Привет! Я LoyanBot.",
    "спасибо": "Пожалуйста!"
  }
}
```

### auto_update

| Свойство | Значение |
|----------|----------|
| Тип | `bool` |
| По умолчанию | `true` |
| Описание | Включить ежедневное автоматическое обновление плагинов из магазина |

```json
{
  "auto_update": true
}
```

### update_check_interval_hours

| Свойство | Значение |
|----------|----------|
| Тип | `int` |
| По умолчанию | `24` |
| Описание | Интервал проверки обновлений фреймворка в часах |

```json
{
  "update_check_interval_hours": 24
}
```

### auto_update_core

| Свойство | Значение |
|----------|----------|
| Тип | `bool` |
| По умолчанию | `false` |
| Описание | Автоматическая проверка обновлений фреймворка (установка по-прежнему требует подтверждения) |

```json
{
  "auto_update_core": false
}
```

## 3. Конфигурация адаптеров

Адаптеры конфигурируются на уровне экземпляра в `storage/instances/<имя>/config.json`. Каждый экземпляр поддерживает один адаптер платформы.

### Адаптер OneBot / NapCat

Адаптер OneBot поддерживает режимы подключения HTTP и WebSocket.

#### HTTP режим

```json
{
  "platform": "onebot",
  "bot_name": "ОсновнойБот",
  "robot_id": "123456789",
  "master_id": "987654321",
  "enabled": true,
  "type": "http",
  "http_url": "http://127.0.0.1:3000",
  "callback_port": 3002
}
```

#### WebSocket прямой режим

```json
{
  "platform": "onebot",
  "bot_name": "WSБот",
  "robot_id": "123456789",
  "master_id": "987654321",
  "enabled": true,
  "type": "ws_forward",
  "host": "0.0.0.0",
  "port": 8080,
  "access_token": "your_token_here"
}
```

#### WebSocket обратный режим

```json
{
  "platform": "onebot",
  "bot_name": "ОбратныйWSБот",
  "robot_id": "123456789",
  "master_id": "987654321",
  "enabled": true,
  "type": "ws_reverse",
  "host": "127.0.0.1",
  "port": 8080,
  "access_token": "your_token_here"
}
```

#### Поля экземпляра OneBot

| Поле | Тип | Обязательно | Описание |
|------|-----|-------------|----------|
| `platform` | string | Да | Должно быть `"onebot"` |
| `bot_name` | string | Да | Пользовательское имя для идентификации |
| `robot_id` | string | Да | QQ-номер бота |
| `master_id` | string | Да | QQ-номер владельца |
| `type` | string | Нет | `"http"` (по умолчанию), `"ws_forward"` или `"ws_reverse"` |
| `http_url` | string | Нет | URL HTTP API NapCat (по умолчанию: `http://127.0.0.1:3000`) |
| `callback_port` | int | Нет | Порт HTTP-коллбэка (по умолчанию: 3002) |
| `host` | string | Нет | Адрес привязки WebSocket (по умолчанию: `0.0.0.0`) |
| `port` | int | Нет | Порт WebSocket (по умолчанию: 8080) |
| `access_token` | string | Нет | Токен доступа WebSocket |
| `admins_id` | list | Нет | Дополнительные ID администраторов |

### Адаптер QQ Official

```json
{
  "platform": "qq_official",
  "bot_name": "QQOfficialБот",
  "robot_id": "bot_app_id",
  "master_id": "owner_user_id",
  "enabled": true,
  "app_id": "your_app_id",
  "app_secret": "your_app_secret",
  "is_sandbox": false
}
```

| Поле | Тип | Обязательно | Описание |
|------|-----|-------------|----------|
| `platform` | string | Да | Должно быть `"qq_official"` |
| `app_id` | string | Да | App ID QQ Open Platform |
| `app_secret` | string | Да | App Secret QQ Open Platform |
| `is_sandbox` | bool | Нет | Использовать песочницу (по умолчанию: false) |

### Адаптер Telegram

```json
{
  "platform": "telegram",
  "bot_name": "TelegramБот",
  "robot_id": "your_bot_token",
  "master_id": "owner_telegram_id",
  "enabled": true
}
```

| Поле | Тип | Обязательно | Описание |
|------|-----|-------------|----------|
| `platform` | string | Да | Должно быть `"telegram"` |
| `robot_id` | string | Да | Токен Telegram бота (формат: `123456:ABC-DEF...`) |
| `master_id` | string | Да | ID владельца в Telegram |

### Адаптер Satori

```json
{
  "platform": "satori",
  "bot_name": "SatoriБот",
  "robot_id": "",
  "master_id": "owner_id",
  "enabled": true,
  "satori_url": "http://127.0.0.1:6100",
  "satori_token": "your_token"
}
```

### Конфигурация нескольких экземпляров

Несколько экземпляров могут работать одновременно. Создайте отдельные директории в `storage/instances/`:

```
storage/instances/
  основной/config.json
  резервный/config.json
  telegram-bot/config.json
```

Первый зарегистрированный экземпляр становится адаптером по умолчанию для исходящих сообщений.

## 4. Конфигурация AI-моделей

AI-поставщики управляются через Менеджер поставщиков. Поставщики хранятся в базе данных и настраиваются через веб-панель или API.

### Поддерживаемые типы поставщиков

| Поставщик | Модуль | Описание |
|-----------|--------|----------|
| OpenAI | `openai` | GPT-4, GPT-3.5 и т.д. |
| Anthropic | `anthropic` | Модели Claude |
| Ollama | `ollama` | Локальный хостинг моделей |
| LiteLLM | `litellm` | Универсальный шлюз для 100+ поставщиков |
| iFlytek | `iflytek` | Китайский AI-поставщик |
| Persona | `persona` | Движок пользовательских персон |

### Добавление поставщика через API

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

### Поля поставщика

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | string | Уникальный идентификатор экземпляра поставщика |
| `type` | string | Тип поставщика (например, `openai`, `anthropic`, `ollama`) |
| `model` | string | Имя используемой модели |
| `api_key` | string | API-ключ для аутентификации |
| `api_base` | string | Базовый URL API (опционально, для пользовательских эндпоинтов) |
| `enabled` | bool | Активен ли этот поставщик |
| `extra` | dict | Дополнительная конфигурация特定于 поставщика |

### Поддержка поставщиков LiteLLM

LiteLLM поддерживает 100+ поставщиков LLM через единый интерфейс. Основные поставщики включают:

- `openai`, `anthropic`, `ollama`, `huggingface`, `azure`, `bedrock`, `vertex_ai`, `palm`, `cohere`, `replicate`, `together`, `groq`, `deepseek`, `mistral`, `nlp_cloud`, `aleph_alpha`, `baseten`, `triton`, `volcengine` и другие.

### Размыкатель цепи

Каждый экземпляр поставщика имеет автоматический размыкатель цепи. После последовательных неудач размыкатель открывается и временно пропускает поставщика. Размыкатель восстанавливается после настраиваемого тайм-аута.

## 5. Конфигурация безопасности

### Система контроля доступа на основе ролей (RBAC)

LoyanBot реализует систему контроля доступа на основе ролей с тремя ролями:

| Роль | Разрешения | Описание |
|------|-----------|----------|
| `guest` | `basic_query` | Обычные пользователи |
| `self` | `basic_query`, `use_plugins` | Сам бот |
| `master` | `basic_query`, `use_plugins`, `manage_plugins`, `system_admin` | Владелец/администратор бота |

### Уровни разрешений в плагинах

Плагины могут объявлять требуемые уровни разрешений в своих метаданных:

```toml
[trigger]
permission = "master"    # Только для владельца
# permission = "admin"   # Для владельца и администраторов
# permission = "all"     # Для всех (по умолчанию)
```

### Ограничение частоты

Фреймворк предоставляет встроенное ограничение частоты:

- Максимум 60 запросов в минуту на пользователя
- Максимум 1000 запросов в час на пользователя
- Блокировка на 300 секунд при нарушении

Ограничения частоты можно применять к отдельным командам через декоратор `@rate_limit`:

```python
from graci import on_command, plugin_handler, rate_limit

@on_command("/gpt")
@rate_limit(max_calls=5, period=60)  # 5 вызовов в 60 секунд
@plugin_handler
async def handle_gpt(ctx):
    pass
```

### Перезарядка

Перекомандная перезарядка через декоратор `@cooldown`:

```python
from graci import on_command, plugin_handler, cooldown

@on_command("/query")
@cooldown(seconds=10)  # 10 секунд перезарядки
@plugin_handler
async def handle_query(ctx):
    pass
```

### Черный список

`SecurityManager` поддерживает черный список пользователей:

```python
from loyan.core.security_manager import security_manager

# Добавить в черный список (duration в секундах, 0 = навсегда)
security_manager.add_to_blacklist(user_id="12345", reason="spam", duration=3600)

# Удалить из черного списка
security_manager.remove_from_blacklist(user_id="12345")

# Проверить, заблокирован ли
is_blocked = security_manager.is_blocked(user_id="12345")
```

### Валидация ввода

- Максимальная длина команды: 500 символов
- Максимальный ввод: 1000 символов (настраивается)
- Обнаружение паттернов SQL-инъекций
- Блокировка паттернов опасных команд (например, `rm -rf`, `shutdown`)
- Фильтрация чувствительных символов (точки с запятой, операторы и т.д.)

### Аудит логирования

Все события безопасности логируются со следующей информацией:

- ID пользователя (маскируется в логах)
- Выполняемое действие
- Доступный ресурс
- Статус успеха/неудачи
- Временная метка

## 6. Конфигурация логирования

### Файлы логов

| Файл | Уровень | Срок хранения | Описание |
|------|---------|---------------|----------|
| `storage/logs/loyan.log` | DEBUG+ | 7 дней | Все логи фреймворка |
| `storage/logs/loyan_error.log` | ERROR+ | 14 дней | Только логи ошибок |

### Формат логов

Консольные логи используют структурированный формат:

```
2024-01-15 10:30:45 - [Категория] [Модуль] [Атрибуты] - Уровень - Сообщение
```

Файловые логи включают дополнительный контекст:

```json
{
  "timestamp": "2024-01-15T10:30:45Z",
  "level": "INFO",
  "logger": "Core.Pipeline",
  "message": "получено сообщение",
  "context": {
    "sender_id": "****7890",
    "chat_type": "private"
  }
}
```

### Защита конфиденциальности

Все ID пользователей и чувствительная информация автоматически маскируются в логах:

- ID пользователей: `****` + последние 4 цифры
- API-ключи: первые 6 символов + `****`
- Пароли: всегда `******`

### Пользовательские уровни логирования

Плагины могут использовать логгер фреймворка:

```python
from graci import get_logger

logger = get_logger("MyPlugin")
logger.info("Плагин запущен")
logger.error("Произошла ошибка", exc_info=True)
```

## 7. Конфигурация базы данных

LoyanBot использует SQLite через `aiosqlite` для асинхронного доступа к базе данных.

### Файлы базы данных

```
storage/data/{имя_плагина}.db
```

Каждый плагин по умолчанию получает собственный файл базы данных.

### Доступ к базе данных плагина

Плагины используют утилиту `LoyanPaths` для путей к файлам базы данных:

```python
from graci import LoyanPaths

paths = LoyanPaths("MyPlugin")
db_path = paths.db()  # -> storage/data/plugins/MyPlugin/MyPlugin.db
```

### База данных поставщиков

Экземпляры поставщиков хранятся по адресу:

```
storage/data/providers.db
```

Включает конфигурацию поставщиков, API-ключи (зашифрованные) и статистику использования.
