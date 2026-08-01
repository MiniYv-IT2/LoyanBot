import json
import logging
from typing import Optional, Dict, Any

# 从 core 包导入配置模块
from loyan.core.config import AUTO_REPLIES, LOG_LEVEL, DEBUG_MODE

# 导入配置管理器
from loyan.core.config_manager import config_manager

# 复用 logger_manager 模块的全局实例（单一实例，避免双实例日志配置不一致）
from loyan.core.logger_manager import logger_manager

logger = logger_manager.get_logger('Loyan')

# 可选：日志脱敏过滤器（core.security 不存在时跳过）
try:
    from loyan.core.security import SanitizeLogFilter
    _sanitize_filter = SanitizeLogFilter()
    logger_manager.get_logger('').addFilter(_sanitize_filter)
    for _name in ['LoyanBot', 'Loyan', 'LoyanBot-Plugin', 'Loyan.Send', 'LoyanPipeline', 'LoyanEvent']:
        logger_manager.get_logger(_name).addFilter(_sanitize_filter)
except ImportError:
    pass


