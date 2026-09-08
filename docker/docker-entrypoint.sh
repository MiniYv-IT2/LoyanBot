#!/bin/bash
set -e

# ═══════════════════════════════════════════════════════════
# LoyanBot Docker Entrypoint
# ═══════════════════════════════════════════════════════════

# 挂载自定义插件：plugins_custom/ → loyan/plugins_custom/
if [ -d /loyan/plugins_custom ] && [ "$(ls -A /loyan/plugins_custom 2>/dev/null)" ]; then
    ln -sfn /loyan/plugins_custom /loyan/loyan/plugins_custom
fi

# 首次运行：storage/ 目录由 VOLUME 保证存在
# storage/config.json 由 loyan run 首次启动时自动创建
# 但实例需要用户主动创建

exec "$@"
