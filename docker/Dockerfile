# ═══════════════════════════════════════════════════════════
# LoyanBot — Docker 构建（Ubuntu 26.04 Resolute Raccoon + Python 3.14）
# ═══════════════════════════════════════════════════════════

# ─── Stage 1: build ──────────────────────────────────────
FROM ubuntu:26.04 AS builder

LABEL stage="builder"

# 阿里源
RUN sed -i 's/archive.ubuntu.com/mirrors.aliyun.com/g' /etc/apt/sources.list.d/ubuntu.sources 2>/dev/null; \
    sed -i 's/ports.ubuntu.com/mirrors.aliyun.com/g' /etc/apt/sources.list.d/ubuntu.sources 2>/dev/null; \
    true

# Python 3.14 + 构建工具
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 验证 Python 版本 >= 3.11
RUN python3 --version

# pip 换阿里源
RUN pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/

WORKDIR /build

# 先拷依赖定义，利用 Docker 缓存
COPY pyproject.toml ./

# 安装依赖（不安装包本身，只装依赖）
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r pyproject.toml 2>/dev/null || \
    pip install --no-cache-dir typer quart hypercorn aiohttp requests websockets tomli openai Pillow numpy psutil py-cpuinfo mss aiosqlite cryptography litellm pycryptodome python-telegram-bot watchfiles

# ─── Stage 2: runtime ────────────────────────────────────
FROM ubuntu:26.04 AS runtime

LABEL org.opencontainers.image.title="LoyanBot"
LABEL org.opencontainers.image.description="跨平台 IM 轻量异步机器人框架"
LABEL org.opencontainers.image.url="https://github.com/MiniYv-IT2/LoyanBot"
LABEL org.opencontainers.image.source="https://github.com/MiniYv-IT2/LoyanBot"

# 阿里源 + 运行时最小系统
RUN sed -i 's/archive.ubuntu.com/mirrors.aliyun.com/g' /etc/apt/sources.list.d/ubuntu.sources 2>/dev/null; \
    sed -i 's/ports.ubuntu.com/mirrors.aliyun.com/g' /etc/apt/sources.list.d/ubuntu.sources 2>/dev/null; \
    apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    tini \
    && rm -rf /var/lib/apt/lists/*

# 从 builder 拷已安装的依赖
COPY --from=builder /usr/local/lib/python3.14/site-packages /usr/local/lib/python3.14/site-packages
COPY --from=builder /usr/bin/python3 /usr/bin/python3

# 项目源码（唯一来源）
WORKDIR /loyan
COPY --from=builder /build/loyan/ ./loyan/
COPY --from=builder /build/bot.py ./bot.py
COPY --from=builder /build/pyproject.toml ./
COPY docker/docker-entrypoint.sh /usr/local/bin/

RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# 持久化目录
VOLUME ["/loyan/storage", "/loyan/plugins_custom"]

# LoyanUI 面板端口
EXPOSE 5090

ENTRYPOINT ["tini", "--", "docker-entrypoint.sh"]
CMD ["loyan", "run"]
