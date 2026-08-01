"""OneBot HTTP 回调路由 — 由 OneBotAdapter.register_routes() 注册到框架

NapCat 通过 HTTP POST 推送消息到 /callback 路由。
此模块封装了全部 OneBot HTTP 入站逻辑，框架 core 不感知。
"""

import asyncio
import time
import traceback
import logging
from loyan.core.webserv import request, jsonify

from loyan.core.loyan_adapter.message import LoyanText
from loyan.core.loyan_adapter.send import loyan_send_msg
from loyan.core.loyan_adapter.event import LoyanEvent
from loyan.core.utils import logger, logger_manager

_DEDUP_TTL = 1  # 去重窗口（秒）


def _get_event_bus():
    """获取 EventBus：优先从全局容器注入，回落到模块级单例。

    正常流程 get_container() 惰性构建的默认容器注册的是同一模块级
    event_bus，行为不变；测试用 set_container() 注入 Fake。
    """
    try:
        from loyan.core.container import get_container
        bus = get_container().get("event_bus")
        if bus is not None:
            return bus
    except Exception:
        pass
    from loyan.core.event import event_bus
    return event_bus

# self_id → OneBot HTTP parser 映射（由 register_routes 填充）
_http_parsers: dict[str, "LoyanOneBot"] = {}  # type: ignore[name-defined]

# 去重缓存
_event_dedup_cache: dict[tuple, float] = {}


def register_http_parser(self_id: str, parser) -> None:
    """注册一个 OneBot HTTP 解析器到路由"""
    if self_id:
        _http_parsers[self_id] = parser


def _get_parser_by_self_id(self_id: str):
    """根据 self_id 查找对应的 OneBot HTTP 解析器"""
    if self_id and self_id in _http_parsers:
        return _http_parsers[self_id]
    return None


def _create_callback_route(app):
    """创建 /callback 路由并注册到 app"""

    @app.route('/callback', methods=['POST'])
    async def callback():
        context = {
            'client_ip': request.remote_addr,
            'request_id': str(time.time())[-6:],
            'path': request.path
        }

        parser = None
        json_data = None

        try:
            # ── Content-Type 检查 ──
            if 'application/json' not in (request.content_type or ''):
                return jsonify({"retcode": 415, "msg": "仅支持application/json格式"}), 415

            # ── 解析 JSON ──
            try:
                json_data = await request.get_json()
                if json_data is None:
                    return jsonify({"retcode": 400, "msg": "无效的JSON格式"}), 400
            except Exception:
                return jsonify({"retcode": 400, "msg": "JSON解析错误"}), 400

            # ── 元事件静默处理 ──
            if json_data.get("post_type") == "meta_event":
                return jsonify({"retcode": 0})

            # ── 事件去重 ──
            dedup_key = (
                str(json_data.get("self_id", "")),
                str(json_data.get("user_id", "")),
                str(json_data.get("raw_message", "")),
                str(json_data.get("notice_type", "")),
                int(time.time() / _DEDUP_TTL),
            )
            now = time.time()
            stale = [k for k, v in list(_event_dedup_cache.items()) if now - v > _DEDUP_TTL * 2]
            for k in stale:
                _event_dedup_cache.pop(k, None)
            if dedup_key in _event_dedup_cache:
                return jsonify({"retcode": 0})
            _event_dedup_cache[dedup_key] = now

            # ── 查找适配器 ──
            self_id = str(json_data.get("self_id", ""))
            parser = _get_parser_by_self_id(self_id)
            http_event = parser.parse_http_request(json_data) if parser else None

            if http_event:
                # 标记事件来源
                if parser and hasattr(parser, '_source_tag') and parser._source_tag:
                    http_event.source = parser._source_tag

                # 过滤自身消息
                parser_robot_id = getattr(parser, '_robot_id', '') if parser else ''
                if http_event.sender_id and parser_robot_id and str(http_event.sender_id) == str(parser_robot_id):
                    return jsonify({"retcode": 0})

                # EventBus 发布
                try:
                    await _get_event_bus().publish(http_event)
                except Exception as e:
                    logger_manager.log_with_context(
                        logger, logging.WARNING, f"EventBus 发布失败: {e}", context
                    )
            else:
                # 非消息事件 → 业务事件转换并发布
                if parser:
                    biz = parser.parse_business_event(json_data)
                    if biz is not None:
                        bus = _get_event_bus()
                        publish = getattr(bus, "publish_business", None)
                        if publish is not None:
                            try:
                                await publish(biz)
                            except Exception as e:
                                logger_manager.log_with_context(
                                    logger, logging.WARNING, f"业务事件发布失败: {e}", context
                                )
                return jsonify({"retcode": 0})

            return jsonify({"retcode": 0})

        except Exception as e:
            logger_manager.log_with_context(logger, logging.CRITICAL,
                f"回调异常: {str(e)}", context,
                extra={"stack_trace": traceback.format_exc()})

            # 通知实例主人
            try:
                master_id = getattr(parser, '_instance_master_id', '') if parser else ''
                if not master_id and json_data:
                    master_id = str(json_data.get("user_id", ""))
                if master_id:
                    notify = f"🚨 机器人异常\n时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n错误: {str(e)}"
                    await loyan_send_msg(master_id, LoyanText(text=notify), chat_type="private")
            except Exception:
                pass

            return jsonify({"retcode": 500, "msg": "系统维护中，请稍后再试"}), 500

    return callback
