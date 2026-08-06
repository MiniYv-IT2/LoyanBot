"""IM 会话 ID 解析 — 统一 IM 对话会话标识

格式: chat_{platform}_{instance_id}_{chat_type}_{peer_id}[_{sub_id}]
    - platform: 适配器协议 (onebot / qq_official / telegram ...)
    - instance_id: 实例持久化标识 (Part A)
    - chat_type: private | group
    - peer_id: 对端 ID (私聊=发送者, 群聊=群号)
    - sub_id: 可选段, 群聊个人子记忆时追加; 默认 None = 群聊公共记忆

面板会话 (chat_panel_web_*) 与本模块完全隔离, 互不干扰。
"""

from typing import Optional


def resolve_im_session_id(
    platform: str,
    instance_id: str,
    chat_type: str,
    peer_id: str,
    sub_id: Optional[str] = None,
) -> str:
    """按统一格式生成 IM 会话 ID; 缺少 peer_id 时返回空串"""
    if not peer_id:
        return ""
    parts = ["chat", platform, instance_id, chat_type, str(peer_id)]
    if sub_id:
        parts.append(str(sub_id))
    return "_".join(parts)


def resolve_from_context(ctx) -> str:
    """从 PluginContext 提取 IM 会话 ID (群聊默认公共记忆)"""
    tag = ctx.adapter_tag
    platform = tag.platform if tag else ""
    instance_id = tag.instance_id if tag else ""
    peer_id = ctx.target_id if ctx.chat_type == "group" else ctx.sender_id
    return resolve_im_session_id(platform, instance_id, ctx.chat_type, peer_id)
