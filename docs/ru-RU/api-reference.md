# Справочник API

LoyanBot предоставляет RESTful API для управления экземплярами, плагинами, поставщиками и мониторингом. API обслуживается веб-сервером Quart на настроенном порту панели (по умолчанию: 5090).

## 1. Аутентификация

API использует аутентификацию на основе токенов. Токены генерируются в процессе входа через веб-панель.

### Формат токена

```
Authorization: Bearer <токен>
```

### Генерация токена

Токены генерируются методом `SecurityManager.generate_token()`:

```python
from loyan.core.security_manager import security_manager

token = security_manager.generate_token(user_id="admin")
```

### Проверка токена

```python
is_valid = security_manager.verify_token(token)
```

Токены истекают через 24 часа.

## 2. Управление экземплярами

### Список экземпляров

```
GET /api/instances
```

**Ответ**:
```json
{
  "success": true,
  "data": [
    {
      "name": "основной",
      "platform": "onebot",
      "bot_name": "ОсновнойБот",
      "robot_id": "123456789",
      "status": "running",
      "conn_type": "HTTP"
    }
  ]
}
```

### Получение деталей экземпляра

```
GET /api/instances/<имя>
```

**Ответ**:
```json
{
  "success": true,
  "data": {
    "name": "основной",
    "platform": "onebot",
    "bot_name": "ОсновнойБот",
    "robot_id": "123456789",
    "master_id": "987654321",
    "status": "running",
    "config": { ... }
  }
}
```

### Создание экземпляра

```
POST /api/instances
```

**Тело запроса**:
```json
{
  "name": "новый-бот",
  "platform": "onebot",
  "bot_name": "НовыйБот",
  "robot_id": "111222333",
  "master_id": "999888777",
  "type": "http",
  "http_url": "http://127.0.0.1:3000",
  "callback_port": 3002
}
```

**Ответ**:
```json
{
  "success": true,
  "message": "Экземпляр создан",
  "data": {
    "name": "новый-бот"
  }
}
```

### Обновление экземпляра

```
PUT /api/instances/<имя>
```

**Тело запроса**:
```json
{
  "bot_name": "ОбновленныйБот",
  "master_id": "999888777"
}
```

### Удаление экземпляра

```
DELETE /api/instances/<имя>
```

**Ответ**:
```json
{
  "success": true,
  "message": "Экземпляр удален"
}
```

### Перезагрузка экземпляра

```
POST /api/instances/<имя>/reload
```

**Ответ**:
```json
{
  "success": true,
  "message": "Экземпляр перезагружен"
}
```

### Запуск экземпляра

```
POST /api/instances/<имя>/start
```

### Остановка экземпляра

```
POST /api/instances/<имя>/stop
```

### Переименование экземпляра

```
POST /api/instances/<имя>/rename
```

**Тело запроса**:
```json
{
  "new_name": "новое-имя"
}
```

## 3. Управление сообщениями

### Отправка сообщения

```
POST /api/messages/send
```

**Тело запроса**:
```json
{
  "target_id": "123456789",
  "chat_type": "private",
  "content": "Сообщение от API!",
  "tag": "onebot/ОсновнойБот"
}
```

**Ответ**:
```json
{
  "success": true,
  "message_id": "msg_abc123"
}
```

### Получение истории сообщений

```
GET /api/messages?limit=50&offset=0
```

**Параметры запроса**:
- `limit` - Максимальное количество сообщений (по умолчанию: 50)
- `offset` - Смещение пагинации (по умолчанию: 0)

## 4. Управление поставщиками

### Список типов поставщиков

```
GET /api/providers/types
```

**Ответ**:
```json
{
  "success": true,
  "data": ["openai", "anthropic", "ollama", "litellm", "iflytek", "persona"]
}
```

### Список поставщиков

```
GET /api/providers
```

**Ответ**:
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

### Добавление поставщика

```
POST /api/providers
```

**Тело запроса**:
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

### Обновление поставщика

```
PUT /api/providers/<id_экземпляра>
```

**Тело запроса**:
```json
{
  "model": "gpt-4-turbo",
  "enabled": true
}
```

### Удаление поставщика

```
DELETE /api/providers/<id_экземпляра>
```

### Список моделей

```
GET /api/providers/<id_экземпляра>/models
```

**Ответ**:
```json
{
  "success": true,
  "data": ["gpt-4", "gpt-4-turbo", "gpt-3.5-turbo"]
}
```

### Включение/отключение модели

```
POST /api/providers/<id_экземпляра>/models/<модель>/enable
POST /api/providers/<id_экземпляра>/models/<модель>/disable
```

### Добавление пользовательской модели

```
POST /api/providers/<id_экземпляра>/models/custom
```

**Тело запроса**:
```json
{
  "model": "имя_пользовательской_модели"
}
```

### Получение сводки использования

```
GET /api/providers/usage?hours=24
```

**Ответ**:
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

## 5. Управление плагинами

### Список плагинов

```
GET /api/plugins
```

**Ответ**:
```json
{
  "success": true,
  "data": [
    {
      "name": "Help_plugin",
      "display_name": "Плагин помощи",
      "version": "1.1.3",
      "author": "Команда LoyanBot",
      "description": "Просмотр всех команд",
      "enabled": true,
      "commands": ["/help", "/помощь", "/меню"],
      "source": "system"
    }
  ]
}
```

### Получение деталей плагина

```
GET /api/plugins/<имя>
```

### Включение плагина

```
POST /api/plugins/<имя>/enable
```

### Отключение плагина

```
POST /api/plugins/<имя>/disable
```

### Перезагрузка плагина

```
POST /api/plugins/<имя>/reload
```

### Удаление плагина

```
DELETE /api/plugins/<имя>
```

**Примечание**: Системные плагины нельзя удалить.

### Установка плагина из магазина

```
POST /api/plugins/store/install
```

**Тело запроса**:
```json
{
  "plugin_id": "WeatherPlugin"
}
```

### Обновление плагина из магазина

```
POST /api/plugins/store/update
```

**Тело запроса**:
```json
{
  "plugin_id": "WeatherPlugin"
}
```

### Список плагинов магазина

```
GET /api/plugins/store?force=false
```

**Ответ**:
```json
{
  "success": true,
  "data": [
    {
      "id": "WeatherPlugin",
      "name": "Запрос погоды",
      "version": "1.0.0",
      "author": "Разработчик",
      "description": "Запрос погоды",
      "installed": false,
      "update_available": false,
      "likes": 42,
      "downloads": 1234
    }
  ]
}
```

## 6. Эндпоинты мониторинга

### Проверка здоровья

```
GET /api/health
```

**Ответ**:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:45Z",
  "service": "LoyanBot",
  "version": "v1.9.25",
  "uptime": "3 дня 5 часов 30 минут",
  "checks": {
    "cpu_healthy": true,
    "memory_healthy": true,
    "error_rate_healthy": true
  }
}
```

### Статус системы

```
GET /api/status
```

**Ответ**:
```json
{
  "status": "healthy",
  "uptime_seconds": 259200,
  "uptime_formatted": "3 дня 0 часов 0 минут 0 секунд",
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

### Метрики производительности

```
GET /api/metrics
```

**Ответ**:
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

### Статус жизненного цикла

```
GET /api/lifecycle
```

**Ответ**:
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

### Таймлайн жизненного цикла

```
GET /api/lifecycle/timeline
```

**Ответ**:
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

## 7. API конфигурации

### Получение глобальной конфигурации

```
GET /api/config
```

### Обновление глобальной конфигурации

```
PUT /api/config
```

**Тело запроса**:
```json
{
  "log_level": "DEBUG",
  "debug_mode": true
}
```

### Получение конфигурации плагина

```
GET /api/config/plugin/<имя_плагина>
```

### Обновление конфигурации плагина

```
PUT /api/config/plugin/<имя_плагина>
```

**Тело запроса**:
```json
{
  "api_key": "new_key",
  "max_results": 20
}
```

## 8. Ответы об ошибках

Все эндпоинты API возвращают ошибки в единообразном формате:

```json
{
  "success": false,
  "error": "код_ошибки",
  "message": "Читаемое описание ошибки"
}
```

### Частые коды ошибок

| Код | Описание |
|-----|----------|
| `not_found` | Ресурс не найден |
| `already_exists` | Ресурс уже существует |
| `validation_error` | Неверное тело запроса |
| `unauthorized` | Отсутствует или неверная аутентификация |
| `forbidden` | Недостаточно разрешений |
| `internal_error` | Ошибка на стороне сервера |

## 9. Ограничение частоты

Запросы API ограничены по частоте:

- 60 запросов в минуту на IP
- 1000 запросов в час на IP

При превышении этих лимитов возвращается HTTP 429:

```json
{
  "success": false,
  "error": "rate_limited",
  "message": "Слишком много запросов"
}
```
