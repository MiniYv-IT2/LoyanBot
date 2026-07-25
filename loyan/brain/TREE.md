# brain 树状图

```
loyan/brain/
├── __init__.py              # 入口 + 生命周期
├── chat/
│   ├── __init__.py
│   └── engine.py            # 对话引擎
├── commands/
│   ├── __init__.py
│   └── chat.py              # /chat 命令
├── provider/
│   ├── base.py              # BaseProvider + BaseOpenAIProvider
│   ├── errors.py            # 异常体系
│   ├── keystore.py          # 密钥存储（SQLite + 加密）
│   ├── manager.py           # 注册、加载、模型管理
│   ├── paths.py             # 路径工具
│   ├── types/
│   │   ├── openai.py        # OpenAI 兼容（含视觉）
│   │   ├── anthropic.py     # Claude
│   │   ├── ollama.py        # 本地
│   │   └── iflytek.py       # 星火
│   ├── router/
│   │   ├── chain.py         # 故障切换
│   │   └── circuit.py       # 熔断器
│   ├── monitor/
│   │   ├── stats.py         # 调用统计（SQLite）
│   │   └── cost.py          # 费用计算（LiteLLM）
│   └── schemas/
│       ├── openai.schema_conf.json
│       ├── anthropic.schema_conf.json
│       ├── ollama.schema_conf.json
│       └── iflytek.schema_conf.json
├── memory/   ⬜ 空
├── mcp/      ⬜ 空
├── skill/    ⬜ 空
├── tts/      ⬜ 空
└── test/
    └── test_provider_openai.py
```

## 日志不可见方案

让终端日志「隐身」有几个方法：

**1. 级别过滤** — 默认只显示 WARNING 以上，INFO 全关：

```python
logging.getLogger("Brain").setLevel(logging.WARNING)
```

效果：安静得像没有日志，出问题才打印。

**2. 按模块开关** — brain 内部模块各自控制：

```python
logging.getLogger("Brain.provider.openai").setLevel(logging.WARNING)
logging.getLogger("Brain.chat").setLevel(logging.INFO)
```

**3. 压缩格式** — 去掉时间戳和模块名：

```
# 默认
2026-07-25 08:59:04 - [Brain] - INFO - [provider.openai] - 客户端已初始化

# 压缩后
客户端已初始化
```

**4. 归档 + 轮转** — 日志全写文件不看，终端干净：

```
storage/logs/
  brain.log        ← 全部日志写这里，不送终端
  brain_error.log  ← 只记 ERROR
```

要哪种？我可以改 `logger_manager.py` 或 brain 初始化时的日志配置。
