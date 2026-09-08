FROM ubuntu:26.04

LABEL org.opencontainers.image.title="LoyanBot"
LABEL org.opencontainers.image.description="跨平台 IM 轻量异步机器人框架"

RUN sed -i 's/archive.ubuntu.com/mirrors.aliyun.com/g' /etc/apt/sources.list.d/ubuntu.sources 2>/dev/null || true

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    build-essential \
    tini \
    fonts-dejavu-core \
    fonts-droid-fallback \
    fonts-liberation \
    fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m venv /venv
ENV PATH="/venv/bin:$PATH"

RUN pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/

WORKDIR /loyan
COPY loyan/ ./loyan/
COPY bot.py ./
COPY pyproject.toml ./
COPY docker/docker-entrypoint.sh /usr/local/bin/

RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir typer quart hypercorn aiohttp requests websockets \
    tomli openai Pillow numpy psutil py-cpuinfo mss aiosqlite cryptography \
    litellm pycryptodome python-telegram-bot watchfiles

VOLUME ["/loyan/storage", "/loyan/plugins_custom"]
EXPOSE 5090

ENTRYPOINT ["tini", "--", "docker-entrypoint.sh"]
CMD ["loyan", "run"]
