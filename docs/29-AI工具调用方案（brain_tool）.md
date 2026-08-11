# 29-AI工具调用方案（brain_tool）

> 状态：实施中（2026-08-11）
> 方案定案：v5，经多轮评审收敛

## 一、目标

插件通过 `@brain_tool` 装饰器注册"AI 函数工具"，大模型在自然语言对话中自动选择并调用插件工具执行指令，无需显式命令。私聊未匹配消息自动触发（带工具），群聊需 @ 或 /chat。

## 二、架构

```
插件层:  @brain_tool(name, description, params, permission="admin")
             ↓ 插件加载时 plugin_manager 扫描 _loyan_ai_tool 标记
注册层:  AI_TOOL_REGISTRY(与 DECORATOR_COMMAND_REGISTRY 并列)
             ↓ 生成 OpenAI tools schema
执行层:  LoyanAgent.chat_with_tools(最多 5 轮)
             ↓ 权限校验 → 执行插件函数 → 结果回填
触发层:  @on_fallback 私聊兜底(仅 private)
```

## 三、API 设计

### 插件侧（graci 导出）

| API | 签名 | 说明 |
|---|---|---|
| `brain_tool` | `(name, description="", params=None, permission="admin")` | 装饰器，注册 AI 工具（对齐 on_command，不加前缀） |
| `list_brain_tools` | `()` | 查所有已注册工具（面板/插件重名检测） |
| `call_brain_tool` | `(name, args, ctx)` | 手动调用工具（插件间互调/调试） |

### 内部（不导出）

| 部件 | 命名 |
|---|---|
| 注册表 | `AI_TOOL_REGISTRY`（registration.py，与 DECORATOR_COMMAND_REGISTRY 并列） |
| 扫描标记 | `_loyan_ai_tool` |
| 注册函数 | `_register_ai_tool_function()` |
| 执行类 | `LoyanAgent`（loyan/brain/tools/agent.py） |
| 执行方法 | `LoyanAgent.chat_with_tools()` / `.chat_stream_with_tools()` |
| 面板事件 | `{"type":"tool_call", name, args}` / `{"type":"tool_result", name, result}` |

## 四、权限

- 新插件写 `permission="admin"`；旧写法 `"master"` 自动归一化为 `"admin"`
- 底层走现有 `is_admin()` / `check_permission_decorator()`，零新增权限代码
- 命令权限（require_master/require_admin）维持现状不动

## 五、文件改动清单

| # | 文件 | 动作 | 内容 |
|---|---|---|---|
| 1 | `loyan/core/decorators/registration.py` | 改 | `AI_TOOL_REGISTRY` + `BrainToolDecorator` + `brain_tool()` + `_register_ai_tool_function()` + 重名检测 |
| 2 | `loyan/core/plugin_manager.py` | 改 | 加载循环加 `_loyan_ai_tool` 扫描分支 |
| 3 | `loyan/brain/tools/agent.py` | 新 | `LoyanAgent`：chat_with_tools / chat_stream_with_tools（5 轮、权限归一化、错误回填、工具事件） |
| 4 | `loyan/brain/chat/engine.py` | 改 | 委托 chat_with_tools |
| 5 | `loyan/brain/commands/chat.py` | 改 | 新增 @on_fallback 私聊兜底（仅 private） |
| 6 | `loyan/graci/_plugin/__init__.py` | 改 | 导出 brain_tool/list_brain_tools/call_brain_tool |
| 7 | `loyan/graci/_ai/__init__.py` | 改 | 导出 LoyanAgent/chat_with_tools |
| 8 | `loyan/core/decorators/__init__.py` | 改 | 导出 brain_tool |
| 9 | `loyan/core/test/unit/brain/test_tools.py` | 新 | 注册/调用/循环/权限/兜底测试 |

## 六、行为约定

| 项 | 决定 |
|---|---|
| 私聊未匹配消息 | 自动触发 AI 对话（带工具） |
| 群聊未匹配消息 | 不触发（需 @ 或 /chat） |
| 工具开关 | 不设置，默认全开 |
| 权限 | 工具级 admin（master 归一化）；对话级兜底限 use_plugins |
| 轮次上限 | 5 轮防死循环 |
| 工具失败 | 错误文本回填模型，不中断对话 |
| 工具结果 | 只进当轮 messages，不入 DB 历史 |
| 重名 | 注册时检测，重复名 logger.warning |
| /chat | 保留（显式入口） |

## 七、插件使用示例

```python
from graci import brain_tool, PluginContext

@brain_tool(name="get_weather", description="查询天气",
            params={"city": {"type": "string", "required": True, "description": "城市名"}},
            permission="admin")
async def get_weather(ctx: PluginContext, city: str) -> str:
    return "晴, 25°C"
```

自然语言效果：
```
私聊: "北京明天天气怎么样?"
  → 未匹配命令 → 兜底 → LoyanAgent
  → 模型选 get_weather → 执行 → 结果回填 → "北京明天晴, 25°C"
```

## 八、实施顺序（每步验证）

1. registration.py：装饰器 + 注册中心 → 单测（标记/注册/重名）
2. plugin_manager 扫描 → 单测（加载自动注册）
3. LoyanAgent 循环 → 单测（FakeProvider 模拟 5 轮/权限/失败回填）
4. 私聊兜底 → 集成测试（未匹配消息触发）
5. graci 导出 → 导入测试
6. 全量测试 + 重启看日志

## 九、验证方式

- 单测：注册/调用/循环/权限归一化/失败回填/重名
- 集成：私聊未匹配 → LoyanAgent → fake 工具执行
- 真实：重启后私聊发自然语言指令验证工具执行

## 十、命名约定

- 类：`LoyanAgent`（框架公共类，Loyan 前缀）
- 装饰器：`brain_tool`（对齐 on_command 短名体系）
- API：`list_brain_tools` / `call_brain_tool`（brain_ 前缀区分 AI 工具）
- 注册表：`AI_TOOL_REGISTRY`（常量全大写）
