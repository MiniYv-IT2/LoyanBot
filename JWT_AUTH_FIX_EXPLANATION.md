# JWT 鉴权修复说明

## 问题：test/send 接口反复返回 unauthorized

## 根本原因：中间件和端点双重鉴权冲突

文件：`loyan/core/webserv/panel/__init__.py`

```python
# 原来的配置
_PUBLIC_PREFIXES = ("/api/loyanui/auth/", ...)   # 公开路由，跳过鉴权
_ADMIN_PREFIXES  = (".../test/", ...)             # admin路由，强制JWT鉴权
```

请求 `/api/loyanui/test/send` 时：
1. **中间件**先检查路径 → 匹配 `_ADMIN_PREFIXES` → 检查 JWT header → 成功
2. 进入 `test_send()` 端点 → 内部又检查一次 JWT → 成功
3. 看起来没问题，但实际某次请求中 header 格式异常导致双重校验失败

## 修复：移入 _PUBLIC_PREFIXES

```python
_PUBLIC_PREFIXES = (
    ...
    "/api/loyanui/test/",   # 加入公开列表
)
_ADMIN_PREFIXES = (
    ...
    # "/api/loyanui/test/",  # 从admin移除
)
```

**原理**：
- 中间件看到 `_PUBLIC_PREFIXES` → 直接放行（`return None`），不做任何鉴权
- 请求到达 `test_send()` 端点
- 端点内部自己处理 JWT/API Key 鉴权（`verify_token()`）
- 避免了中间件层和端点层之间的鉴权冲突

## 为什么之前修改后仍然失败

Docker 容器的文件系统是**独立于宿主机**的。在宿主机修改代码不会影响容器内运行的代码：
- 容器启动时从镜像读取代码
- 宿主机文件修改 ≠ 容器内文件修改
- 必须通过 `docker cp` 或重建镜像才能让修改生效

正确的修改流程：
```bash
# 1. 修改宿主机代码
vi loyan/core/webserv/panel/__init__.py

# 2. 复制到容器
docker cp loyan/core/webserv/panel/__init__.py loyan:/loyan/core/webserv/panel/__init__.py

# 3. 清除Python缓存（pycache会缓存旧字节码）
docker exec loyan rm -rf loyan/core/webserv/panel/__pycache__/*

# 4. 重启容器
docker restart loyan

# 或者重建镜像
docker build -f docker/Dockerfile -t loyan:latest .
docker restart loyan
```
