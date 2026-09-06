# ═══════════════════════════════════════════════════════════
# LoyanBot — Docker 构建（Ubuntu 26.04 Resolute Raccoon + Python 3.14）
# ═══════════════════════════════════════════════════════════

FROM ubuntu:26.04

LABEL org.opencontainers.image.title="LoyanBot"
LABEL org.opencontainers.image.description="跨平台 IM 轻量异步机器人框架"
LABEL org.opencontainers.image.url="https://github.com/MiniYv-IT2/LoyanBot"
LABEL org.opencontainers.image.source="https://github.com/MiniYv-IT2/LoyanBot"

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
    tini \
    && rm -rf /var/lib/apt/lists/*

# 创建虚拟环境
RUN python3 -m venv /venv
ENV PATH="/venv/bin:$PATH"

# pip 换阿里源
RUN pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/

# 项目源码
WORKDIR /loyan
COPY loyan/ ./loyan/
COPY bot.py ./
COPY pyproject.toml ./
COPY docker/docker-entrypoint.sh /usr/local/bin/

# 安装依赖（只装依赖，不安装包本身）
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir typer quart hypercorn aiohttp requests websockets \
    tomli openai Pillow numpy psutil py-cpuinfo mss aiosqlite cryptography \
    litellm pycryptodome python-telegram-bot watchfiles

# 持久化目录
VOLUME ["/loyan/storage", "/loyan/plugins_custom"]

# LoyanUI 面板端口
EXPOSE 5090

ENTRYPOINT ["tini", "--", "docker-entrypoint.sh"]
CMD ["loyan", "run"]
