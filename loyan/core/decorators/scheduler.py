"""定时任务装饰器 — @on_interval / @on_cron / @on_delayed

用法:
    from loyan.core.decorators.scheduler import on_interval, on_cron
    
    @on_interval(120)
    async def send_status():
        await loyan_send_msg(...)
"""
import asyncio
import functools
import logging
from typing import Callable, Optional

from loyan.core.scheduler import scheduler

_logger = logging.getLogger("Core.Decorators")


def on_interval(seconds: float, name: Optional[str] = None):
    """
    定时任务装饰器 — 每隔 N 秒执行一次
    
    用法:
        @on_interval(120)
        async def send_status():
            await loyan_send_msg(...)
    """
    def decorator(func: Callable) -> Callable:
        task_name = name or f"{func.__module__}.{func.__name__}"
        
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            return await func(*args, **kwargs)
        
        # 注册到 scheduler
        try:
            scheduler.add_interval(task_name, wrapper, seconds)
            _logger.info(f"注册定时任务: {task_name} ({seconds}s)")
        except Exception as e:
            _logger.warning(f"注册定时任务失败 {task_name}: {e}")
        
        return wrapper
    
    return decorator


def on_cron(cron_spec: str, name: Optional[str] = None):
    """
    Cron 定时任务装饰器
    
    用法:
        @on_cron("0 * * * *")  # 每小时整点
        async def hourly_task():
            await loyan_send_msg(...)
    """
    def decorator(func: Callable) -> Callable:
        task_name = name or f"{func.__module__}.{func.__name__}"
        
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            return await func(*args, **kwargs)
        
        try:
            scheduler.add_cron(task_name, wrapper, cron_spec)
            _logger.info(f"注册 cron 任务: {task_name} ({cron_spec})")
        except Exception as e:
            _logger.warning(f"注册 cron 任务失败 {task_name}: {e}")
        
        return wrapper
    
    return decorator


def on_delayed(seconds: float, name: Optional[str] = None):
    """
    延迟执行装饰器（只执行一次）
    
    用法:
        @on_delayed(60)
        async def delayed_task():
            await loyan_send_msg(...)
    """
    def decorator(func: Callable) -> Callable:
        task_name = name or f"{func.__module__}.{func.__name__}"
        
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            return await func(*args, **kwargs)
        
        try:
            scheduler.add_delayed(task_name, wrapper, seconds)
            _logger.info(f"注册延迟任务: {task_name} ({seconds}s)")
        except Exception as e:
            _logger.warning(f"注册延迟任务失败 {task_name}: {e}")
        
        return wrapper
    
    return decorator
