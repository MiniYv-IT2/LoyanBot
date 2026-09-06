# 插件开发

LoyanBot 拥有强大的插件系统，允许你扩展机器人的功能。本指南涵盖创建、配置和发布插件所需的一切知识。

## 1. 插件系统概述

### 架构

插件是 Python 包，框架在运行时发现、加载和管理它们。插件系统支持：

- 基于 TOML 的元数据声明
- 基于装饰器的命令注册
- 插件间的依赖管理
- 无需重启机器人的热重载
- 用于分发的插件商店
- 每个插件的配置和数据存储

### 插件发现

插件管理器扫描两个目录寻找插件：

1. **系统插件**：`loyan/plugins/`（内置，随框架分发）
2. **用户插件**：`storage/plugins/`（从商店安装或手动创建）

## 2. 插件目录结构

插件由以下文件组成：

```
MyPlugin/
  metadata.toml       # 插件元数据（必需）
  main.py             # 核心模块，包含处理器（必需）
  config.py           # 默认配置（可选）
  config.json         # 插件配置（自动生成）
  res/                # 静态资源（可选）
  core/               # 额外模块（可选）
    draw.py
  requirements.txt    # Python 依赖（可选）
```

### 最小插件

```
HelloWorld/
  metadata.toml
  main.py
```

### 标准插件

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

## 3. 插件元数据 (metadata.toml)

`metadata.toml` 文件声明插件的身份、命令和行为。

### 完整 metadata.toml 示例

```toml
[plugin]
name        = "天气查询"
version     = "1.0.0"
author      = "开发者"
description = "查询任意城市的天气信息"
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
# 无依赖
```

### 元数据字段

#### [plugin] 部分

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `name` | string | 是 | 显示名称，显示在帮助和商店中 |
| `version` | string | 语义版本号（如 `"1.0.0"`） |
| `author` | string | 否 | 插件作者名称 |
| `description` | string | 否 | 功能简短描述 |
| `category` | string | 否 | 商店分类 |
| `tags` | list | 否 | 用于搜索和过滤的标签 |
| `icon` | string | 否 | 图标文件名（相对于插件目录） |
| `priority` | int | 否 | 执行优先级（默认：50，越大越先执行） |

#### [handler] 部分

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `entry` | string | 是 | `main.py` 中主处理函数的名称 |

#### [trigger] 部分

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `commands` | list | 是 | 触发命令列表（如 `["/weather", "/天气"]`） |
| `chat_type` | list | 否 | 有效的聊天类型：`["private", "group"]`（默认：两者都支持） |
| `permission` | string | 否 | 所需权限：`"all"`、`"master"`、`"admin"`（默认：`"all"`） |
| `is_at_required` | bool | 否 | 群聊中是否需要 @机器人（默认：false） |

#### [dependencies] 部分

```toml
[dependencies]
[[deps]]
name = "Help_plugin"
min_version = "1.0.0"
max_version = "2.0.0"
```

## 4. 插件生命周期

### 加载流程

1. **扫描**：插件管理器扫描插件目录查找 `metadata.toml`
2. **验证**：检查元数据语法和必需字段
3. **依赖检查**：验证所有依赖是否满足
4. **加载模块**：导入 `main.py`（或 `<插件名>.py`）
5. **注册**：扫描装饰器标记的函数并注册命令
6. **配置**：从 `config.py` 和 `config.json` 初始化插件配置
7. **执行**：在首次匹配命令时调用入口处理函数

### 生命周期钩子

插件可以定义以下可选函数：

```python
# 机器人启动后调用（所有插件加载完成后）
def on_ready():
    pass

# 机器人关闭时调用
def on_shutdown():
    pass
```

### 热重载

框架使用 `watchfiles` 监控插件目录变更：

- 文件修改触发目标插件的定向重载
- 新增/删除插件目录触发全量重新扫描
- 运行时数据文件（图片、缓存）不触发重载
- 监听器在机器人达到 `READY` 阶段时自动启动

手动重载插件：

```bash
loyan plugin reload <插件名>
```

## 5. 插件 API

### 装饰器

`graci` 包提供插件开发用的装饰器：

#### @on_command

声明命令触发函数：

```python
from graci import on_command, plugin_handler, PluginContext

@on_command("/hello", "/你好")
@plugin_handler
async def handle_hello(ctx: PluginContext):
    await ctx.send("你好！")
```

#### @on_regex

正则表达式匹配触发：

```python
from graci import on_regex, plugin_handler, PluginContext
import re

@on_regex(r"weather\s+(\w+)", flags=re.IGNORECASE)
@plugin_handler
async def handle_weather_regex(ctx: PluginContext):
    match = ctx.extra.get("_regex_match")
    city = match.group(1) if match else "unknown"
    await ctx.send(f"{city} 的天气")
```

#### @on_keyword

包含特定关键词时触发：

```python
from graci import on_keyword, plugin_handler, PluginContext

@on_keyword("你好", "hi", "hey")
@plugin_handler
async def handle_greeting(ctx: PluginContext):
    await ctx.send("你好！")
```

#### @on_fallback

处理未被其他插件匹配的消息：

```python
from graci import on_fallback, plugin_handler, PluginContext

@on_fallback()
@plugin_handler
async def handle_unmatched(ctx: PluginContext):
    await ctx.send("我不理解这个命令。")
```

#### @brain_tool

声明 AI 可调用的工具：

```python
from graci import brain_tool, PluginContext

@brain_tool(
    name="get_weather",
    description="获取城市的当前天气",
    params={"city": {"type": "string", "description": "城市名称"}},
    permission="admin"
)
def get_weather(ctx: PluginContext, city: str = "") -> str:
    return f"{city} 的天气：晴，25度"
```

#### @plugin_handler

所有处理函数必需的包装器。处理：
- 权限检查
- 速率限制
- 冷却时间执行
- 执行计时和监控
- 异常捕获

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
@cooldown(seconds=86400)  # 每天一次
@plugin_handler
async def handle_daily(ctx: PluginContext):
    pass
```

### PluginContext

`PluginContext` 数据类提供当前消息的所有信息：

```python
@dataclass
class PluginContext:
    sender_id: str           # 发送消息的用户
    target_id: str           # 目标（私聊=发送者，群聊=群组 ID）
    chat_type: str           # "private" 或 "group"
    nickname: str            # 发送者显示名称
    raw_text: str            # 原始消息文本
    text: str                # 净化后的文本
    images: List[str]        # 图片文件 ID
    ats: List[str]           # 被 @的用户 ID
    is_at_bot: bool          # 是否 @了机器人
    command: str             # 匹配到的命令字符串
    plugin_name: str         # 当前插件名称
    raw_data: dict           # 平台特定的原始数据
    send: Callable           # 发送消息函数
    reply: Callable          # 快速回复函数
    logger: Callable         # 插件日志器
    session: Any             # 会话对象（如果有 @with_session）
    runtime: Runtime         # 当前 Runtime 实例
```

### 发送消息

```python
from graci import LoyanText, LoyanImage, LoyanAt

# 发送文本
await ctx.send(LoyanText(text="你好！"))

# 从文件发送图片
await ctx.send(LoyanImage(file_path="/path/to/image.png"))

# 从 URL 发送图片
await ctx.send(LoyanImage(url="https://example.com/image.png"))

# 发送 @提及
await ctx.send(LoyanAt(target_id="123456"))

# 回复消息
await ctx.reply("这是回复！")

# 发送多个段
await ctx.send(
    LoyanText(text="结果如下："),
    LoyanImage(file_path="result.png")
)
```

### 消息类型

| 类型 | 字段 | 说明 |
|------|------|------|
| `LoyanText` | `text: str` | 纯文本消息 |
| `LoyanImage` | `file_path`、`url`、`file_data` | 图片（文件、URL 或字节） |
| `LoyanAt` | `target_id: str` | @提及用户 |
| `LoyanReply` | `message_id: str` | 回复某条消息 |
| `LoyanVoice` | `file_path: str` | 语音消息 |
| `LoyanFile` | `file_path`、`url` | 文件附件 |
| `LoyanVideo` | `file_path`、`url`、`file_data` | 视频消息 |
| `LoyanForward` | `forward_id`、`title` | 转发消息 |

### 路径工具

`LoyanPaths` 类为插件数据提供标准化路径：

```python
from graci import LoyanPaths

paths = LoyanPaths("MyPlugin")

# 数据目录 (storage/data/plugins/MyPlugin/)
data_dir = paths.data()

# 资源目录 (插件的 res/ 文件夹)
res_dir = paths.res()

# 数据库文件路径
db_path = paths.db()

# 临时目录
tmp_dir = paths.temp()
```

### 配置访问

```python
from graci import config_manager

# 获取插件配置
config = config_manager.get_plugin("MyPlugin")

# 获取特定键
api_key = config_manager.get_plugin("MyPlugin", key="api_key", default="")

# 更新插件配置
config_manager.update_plugin("MyPlugin", {"api_key": "new_key"})
```

### 日志

```python
from graci import get_logger

logger = get_logger("MyPlugin")
logger.info("插件已启动")
logger.warning("使用了已弃用的功能")
logger.error("操作失败", exc_info=True)
```

## 6. 插件配置

### 默认配置 (config.py)

```python
# MyPlugin/config.py
DEFAULT_CONFIG = {
    "api_key": "",
    "max_results": 10,
    "timeout": 30,
    "language": "zh"
}
```

### 配置优先级

配置按以下顺序合并（后者覆盖前者）：

1. `config.py` 中的 `DEFAULT_CONFIG`
2. `storage/config.json`（全局用户配置）
3. `storage/config/<插件名>/config.json`（全局插件配置）
4. `storage/instances/<实例>/plugins/<插件名>/config.json`（实例级配置）

### Schema 验证 (plugin_conf.json)

```json
{
  "api_key": {
    "type": "str",
    "default": "",
    "description": "服务的 API 密钥",
    "required": true
  },
  "max_results": {
    "type": "int",
    "default": 10,
    "description": "最大返回结果数",
    "options": [5, 10, 20, 50]
  }
}
```

## 7. 依赖管理

### 声明依赖

在 `metadata.toml` 中：

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

### 循环依赖检测

插件管理器使用 DFS 遍历自动检测循环依赖。如果检测到循环，会记录错误并加载受影响的插件。

### 版本比较

插件版本按数字比较：
- `"1.0.0"` vs `"1.0.1"` -> `"1.0.0"` 较低
- `"2.0"` vs `"1.9.9"` -> `"2.0"` 较高

## 8. 热重载

### 自动热重载

插件监听器监控插件目录并自动重载更改的插件：

```python
# 监听器在 READY 生命周期阶段自动启动
# 使用 watchfiles 进行高效的文件系统监控
# 变更通过 300ms 防抖
```

### 触发重载的变更

| 变更类型 | 操作 |
|----------|------|
| 修改 `.py` 文件 | 目标插件定向重载 |
| 新增插件目录 | 全量重新扫描所有插件 |
| 删除插件目录 | 全量重新扫描所有插件 |
| 修改 `metadata.toml` | 全量重新扫描所有插件 |
| 修改运行时数据 | 无操作（图片、缓存等） |

### 手动重载

```bash
# 通过 CLI 重载
loyan plugin reload <插件名>

# 或通过 API
POST /api/plugins/<插件名>/reload
```

## 9. 完整示例

### Hello World 插件

**metadata.toml**：
```toml
[plugin]
name        = "Hello World"
version     = "1.0.0"
author      = "开发者"
description = "一个简单的 Hello World 插件"

[handler]
entry       = "handle_hello"

[trigger]
commands    = ["/hello"]
chat_type   = ["private", "group"]
permission  = "all"
```

**main.py**：
```python
from graci import on_command, plugin_handler, PluginContext, LoyanText

@on_command("/hello")
@plugin_handler
async def handle_hello(ctx: PluginContext):
    """回复问候语。"""
    await ctx.send(LoyanText(text=f"你好 {ctx.nickname}！"))
```

### 带配置的天气插件

**metadata.toml**：
```toml
[plugin]
name        = "天气"
version     = "1.0.0"
author      = "开发者"
description = "查询天气信息"

[handler]
entry       = "handle_weather"

[trigger]
commands    = ["/weather", "/天气"]
chat_type   = ["private", "group"]
permission  = "all"
```

**config.py**：
```python
DEFAULT_CONFIG = {
    "api_key": "",
    "default_city": "北京",
    "units": "metric"
}
```

**main.py**：
```python
from graci import on_command, plugin_handler, PluginContext, get_logger, config_manager

logger = get_logger("Weather")
config = config_manager.register_plugin_config("Weather")

@on_command("/weather")
@plugin_handler
async def handle_weather(ctx: PluginContext):
    """查询城市的天气。"""
    # 从消息中提取城市
    text = ctx.raw_text
    city = text.replace("/weather", "").strip() or config.get("default_city", "北京")

    if not config.get("api_key"):
        await ctx.reply("天气 API 密钥未配置。")
        return

    # 查询天气（简化）
    try:
        weather_data = await query_weather(city, config["api_key"])
        await ctx.reply(f"{city} 的天气：{weather_data}")
    except Exception as e:
        logger.error(f"天气查询失败：{e}")
        await ctx.reply("天气查询失败。")
```

## 10. 调试方法

### 启用调试日志

在 `config.json` 中将 `log_level` 设置为 `DEBUG`：

```json
{
  "log_level": "DEBUG"
}
```

### 插件调试模式

在日志中检查插件加载状态：

```
[INFO] 插件管理器初始化完成！
[INFO]   1. Hello World | 版本：1.0.0 | 优先级：50 | 指令：/hello
```

### 常见问题

1. **插件未加载**：检查 `metadata.toml` 是否存在且语法有效
2. **命令未匹配**：验证命令字符串完全匹配（区分大小写）
3. **导入错误**：确保所有导入来自 `graci` 或标准库
4. **配置未找到**：在 `main.py` 中调用 `config_manager.register_plugin_config()`

### 测试插件

```python
# 使用测试框架
from loyan.core.decorators.registration import clear_registry
from loyan.core.plugin_manager import PluginManager

# 创建测试实例
pm = PluginManager(config_manager=mock_config, logger=mock_logger)
```

## 11. 发布到插件商店

### 商店要求

要将插件发布到官方商店：

1. 插件必须有有效的 `metadata.toml`
2. 插件必须托管在公共 Git 仓库中
3. 仓库必须有 `main` 分支（或指定分支）
4. 插件不得包含恶意代码

### 商店配置

在 `config.json` 中配置商店源：

```json
{
  "store": {
    "sources": [
      {
        "name": "官方源",
        "store_url": "http://38.55.145.10:16385/store.json",
        "enabled": true
      }
    ],
    "git_mirrors": ["https://ghproxy.com/"]
  }
}
```

### 提交插件

联系 LoyanBot 开发团队并提供：

1. Git 仓库 URL
2. 插件描述
3. 作者信息
4. 许可证（GPL-3.0 兼容）

### 从商店安装

```bash
# 列出可用插件
loyan plugin list

# 安装插件
loyan plugin install <插件名>

# 更新插件
loyan plugin update <插件名>

# 卸载插件
loyan plugin uninstall <插件名>
```
