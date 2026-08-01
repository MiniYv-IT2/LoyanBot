"""业务事件类型与强类型 Payload schema

三层事件模型中的"业务事件"层：
    - EventType：71 个事件类型，按 10 个域组织（消息/群组/好友/平台/实例/插件/通知/系统/用户/AI）
    - 每个事件类型对应一个 Payload dataclass，承载事件语义字段（类型安全，IDE 补全）
    - BusinessEvent：业务事件载体（type + payload + 来源 + 拦截标志）
    - validate_payload()：按事件类型分发校验，构造对应 Payload

用法:
    from loyan.core.event import EventType, BusinessEvent, validate_payload

    ev = BusinessEvent(EventType.GROUP_MEMBER_JOINED,
                       validate_payload(EventType.GROUP_MEMBER_JOINED,
                                        {"group_id": "123", "user_id": "456"}))
"""

from __future__ import annotations

import dataclasses
import typing
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List


class EventType(str, Enum):
    """业务事件类型（71 个，10 域）"""

    # ── 消息域（2）──
    MESSAGE_RECEIVED = "message_received"      # 收到一条新消息
    MESSAGE_SENT = "message_sent"              # 发送了一条消息（成功或失败）

    # ── 群组域（12）──
    GROUP_MEMBER_JOINED = "group_member_joined"            # 成员入群
    GROUP_MEMBER_LEFT = "group_member_left"                # 成员退群
    GROUP_MEMBER_KICKED = "group_member_kicked"            # 成员被踢出群
    GROUP_ADMIN_CHANGED = "group_admin_changed"            # 群管理员变动
    GROUP_MUTED = "group_muted"                            # 全员禁言开启
    GROUP_UNMUTED = "group_unmuted"                        # 全员禁言解除
    GROUP_MEMBER_MUTED = "group_member_muted"              # 某成员被禁言
    GROUP_MEMBER_UNMUTED = "group_member_unmuted"          # 某成员禁言解除
    GROUP_RECALLED = "group_recalled"                      # 群消息被撤回
    GROUP_FILE_UPLOADED = "group_file_uploaded"            # 群文件上传
    GROUP_TITLE_CHANGED = "group_title_changed"            # 群名修改
    GROUP_ANNOUNCEMENT_CHANGED = "group_announcement_changed"  # 群公告变更

    # ── 好友域（4）──
    FRIEND_REQUEST = "friend_request"        # 收到好友申请（可 cancel 拒绝）
    FRIEND_ADDED = "friend_added"            # 新增好友
    FRIEND_DELETED = "friend_deleted"        # 好友被删除
    FRIEND_RECALLED = "friend_recalled"      # 好友申请被撤回

    # ── 平台域（5）──
    PLATFORM_CONNECTED = "platform_connected"      # 平台连接建立
    PLATFORM_DISCONNECTED = "platform_disconnected"  # 平台连接断开
    PLATFORM_RECONNECTING = "platform_reconnecting"  # 平台连接重连中
    PLATFORM_ERROR = "platform_error"              # 平台运行错误
    PLATFORM_BANNED = "platform_banned"            # 平台账号被封禁

    # ── 实例域（5）──
    INSTANCE_STARTED = "instance_started"              # 实例启动
    INSTANCE_STOPPED = "instance_stopped"              # 实例停止
    INSTANCE_RELOADED = "instance_reloaded"            # 实例配置重载
    INSTANCE_ERROR = "instance_error"                  # 实例运行错误
    INSTANCE_HEALTH_CHANGED = "instance_health_changed"  # 实例健康状态变化

    # ── 插件域（10）──
    PLUGIN_LOADED = "plugin_loaded"                        # 插件加载成功
    PLUGIN_UNLOADED = "plugin_unloaded"                    # 插件卸载
    PLUGIN_ENABLED = "plugin_enabled"                      # 插件被启用
    PLUGIN_DISABLED = "plugin_disabled"                    # 插件被禁用
    PLUGIN_ERROR = "plugin_error"                          # 插件运行错误
    PLUGIN_INSTALLED = "plugin_installed"                  # 插件安装
    PLUGIN_UNINSTALLED = "plugin_uninstalled"              # 插件卸载移除
    PLUGIN_UPDATED = "plugin_updated"                      # 插件更新
    PLUGIN_CONFIG_CHANGED = "plugin_config_changed"        # 插件配置变更
    PLUGIN_DEPENDENCY_INSTALLED = "plugin_dependency_installed"  # 插件依赖安装

    # ── 通知域（4）──
    SYSTEM_ANNOUNCEMENT = "system_announcement"            # 系统公告推送
    SYSTEM_MAINTENANCE = "system_maintenance"              # 系统维护计划
    SYSTEM_UPDATE_AVAILABLE = "system_update_available"    # 有新版本可用
    SYSTEM_ALERT = "system_alert"                          # 系统告警

    # ── 系统域（5）──
    SYSTEM_STARTUP = "system_startup"              # 框架启动完成
    SYSTEM_SHUTDOWN = "system_shutdown"            # 框架开始关闭
    SYSTEM_RESTARTING = "system_restarting"        # 框架重启中
    SYSTEM_CONFIG_CHANGED = "system_config_changed"  # 框架配置变更
    SYSTEM_ADMIN_CHANGED = "system_admin_changed"  # 管理员名单变动

    # ── 用户域（3）──
    USER_BLACKLISTED = "user_blacklisted"              # 用户被拉黑
    USER_UNBLACKLISTED = "user_unblacklisted"          # 用户被移出黑名单
    USER_PERMISSION_CHANGED = "user_permission_changed"  # 用户权限变更

    # ── AI 域（21）──
    AI_PROVIDER_LOADED = "ai_provider_loaded"        # AI 提供方加载
    AI_PROVIDER_ERROR = "ai_provider_error"          # AI 提供方出错
    AI_PROVIDER_REMOVED = "ai_provider_removed"      # AI 提供方移除
    AI_REQUEST_STARTED = "ai_request_started"        # AI 请求开始
    AI_REQUEST_COMPLETED = "ai_request_completed"    # AI 请求完成
    AI_REQUEST_FAILED = "ai_request_failed"          # AI 请求失败
    AI_REQUEST_TIMEOUT = "ai_request_timeout"        # AI 请求超时
    AI_SESSION_CREATED = "ai_session_created"        # AI 会话创建
    AI_SESSION_CLOSED = "ai_session_closed"          # AI 会话关闭
    AI_SESSION_RESET = "ai_session_reset"            # AI 会话重置
    AI_MEMORY_UPDATED = "ai_memory_updated"          # AI 记忆更新
    AI_MEMORY_FULL = "ai_memory_full"                # AI 记忆已满
    AI_CONTEXT_TRUNCATED = "ai_context_truncated"    # AI 上下文被截断
    AI_PERSONA_CHANGED = "ai_persona_changed"        # AI 人格切换
    AI_TOKEN_LOW = "ai_token_low"                    # AI Token 余量不足
    AI_MODEL_SWITCHED = "ai_model_switched"          # AI 模型切换
    AI_EMBEDDING_COMPLETED = "ai_embedding_completed"  # AI 向量化完成
    AI_TOOL_CALLED = "ai_tool_called"                # AI 调用工具
    AI_TOOL_ERROR = "ai_tool_error"                  # AI 工具调用出错
    AI_STREAM_STARTED = "ai_stream_started"          # AI 流式输出开始
    AI_STREAM_ENDED = "ai_stream_ended"              # AI 流式输出结束


# ═══════════════════════════ 消息域 Payload（2）═══════════════════════════


@dataclass
class MessageReceivedPayload:
    """收到一条新消息"""
    sender_id: str          # 发送者 ID
    target_id: str          # 目标 ID（私聊=对方，群聊=群号）
    chat_type: str          # "private" | "group"
    raw_text: str = ""      # 消息纯文本
    message_id: str = ""    # 平台消息 ID


@dataclass
class MessageSentPayload:
    """发送了一条消息"""
    target_id: str          # 目标 ID
    chat_type: str          # "private" | "group"
    success: bool = True    # 是否发送成功
    error: str = ""         # 失败时的错误信息


# ═══════════════════════════ 群组域 Payload（12）═══════════════════════════


@dataclass
class GroupMemberJoinedPayload:
    """成员入群"""
    group_id: str           # 群号
    user_id: str            # 入群成员
    operator_id: str = ""   # 操作者（主动拉人时非空）
    at: int = 0             # 入群时间戳（秒）


@dataclass
class GroupMemberLeftPayload:
    """成员退群"""
    group_id: str           # 群号
    user_id: str            # 退群成员


@dataclass
class GroupMemberKickedPayload:
    """成员被踢出群"""
    group_id: str           # 群号
    user_id: str            # 被踢成员
    operator_id: str = ""   # 执行踢人的管理员


@dataclass
class GroupAdminChangedPayload:
    """群管理员变动"""
    group_id: str           # 群号
    user_id: str            # 变动的成员
    is_admin: bool = False  # True=设为管理员，False=取消
    operator_id: str = ""   # 操作者


@dataclass
class GroupMutedPayload:
    """全员禁言开启"""
    group_id: str           # 群号
    operator_id: str = ""   # 操作者
    duration: int = 0       # 禁言时长（秒，0=永久）


@dataclass
class GroupUnmutedPayload:
    """全员禁言解除"""
    group_id: str           # 群号
    operator_id: str = ""   # 操作者


@dataclass
class GroupMemberMutedPayload:
    """某成员被禁言"""
    group_id: str           # 群号
    user_id: str            # 被禁言成员
    operator_id: str = ""   # 操作者
    duration: int = 0       # 禁言时长（秒，0=永久）


@dataclass
class GroupMemberUnmutedPayload:
    """某成员禁言解除"""
    group_id: str           # 群号
    user_id: str            # 被解禁成员
    operator_id: str = ""   # 操作者


@dataclass
class GroupRecalledPayload:
    """群消息被撤回"""
    group_id: str           # 群号
    operator_id: str = ""   # 撤回者（可能是成员或管理员）
    message_id: str = ""    # 被撤回消息 ID
    message: str = ""       # 被撤回消息内容摘要


@dataclass
class GroupFileUploadedPayload:
    """群文件上传"""
    group_id: str           # 群号
    user_id: str            # 上传者
    file_name: str = ""     # 文件名
    file_size: int = 0      # 文件大小（字节）


@dataclass
class GroupTitleChangedPayload:
    """群名修改"""
    group_id: str           # 群号
    operator_id: str = ""   # 操作者
    title: str = ""         # 新群名


@dataclass
class GroupAnnouncementChangedPayload:
    """群公告变更"""
    group_id: str           # 群号
    operator_id: str = ""   # 操作者
    content: str = ""       # 公告内容


# ═══════════════════════════ 好友域 Payload（4）═══════════════════════════


@dataclass
class FriendRequestPayload:
    """收到好友申请（订阅者可 cancel 拒绝）"""
    user_id: str            # 申请者 ID
    nickname: str = ""      # 申请者昵称
    message: str = ""       # 验证消息


@dataclass
class FriendAddedPayload:
    """新增好友"""
    user_id: str            # 新好友 ID


@dataclass
class FriendDeletedPayload:
    """好友被删除"""
    user_id: str            # 被删除的好友 ID


@dataclass
class FriendRecalledPayload:
    """好友申请被撤回"""
    user_id: str            # 撤回申请的用户 ID


# ═══════════════════════════ 平台域 Payload（5）═══════════════════════════


@dataclass
class PlatformConnectedPayload:
    """平台连接建立"""
    platform: str           # 平台名（onebot/qq_official/satori/telegram）
    tag: str = ""           # 实例 tag
    reason: str = ""        # 附加说明


@dataclass
class PlatformDisconnectedPayload:
    """平台连接断开"""
    platform: str           # 平台名
    tag: str = ""           # 实例 tag
    reason: str = ""        # 断开原因


@dataclass
class PlatformReconnectingPayload:
    """平台连接重连中"""
    platform: str           # 平台名
    tag: str = ""           # 实例 tag
    reason: str = ""        # 重连原因


@dataclass
class PlatformErrorPayload:
    """平台运行错误"""
    platform: str           # 平台名
    tag: str = ""           # 实例 tag
    reason: str = ""        # 错误信息


@dataclass
class PlatformBannedPayload:
    """平台账号被封禁"""
    platform: str           # 平台名
    tag: str = ""           # 实例 tag
    reason: str = ""        # 封禁原因


# ═══════════════════════════ 实例域 Payload（5）═══════════════════════════


@dataclass
class InstanceStartedPayload:
    """实例启动"""
    name: str               # 实例名
    tag: str = ""           # 实例 tag


@dataclass
class InstanceStoppedPayload:
    """实例停止"""
    name: str               # 实例名
    tag: str = ""           # 实例 tag


@dataclass
class InstanceReloadedPayload:
    """实例配置重载"""
    name: str               # 实例名
    tag: str = ""           # 实例 tag


@dataclass
class InstanceErrorPayload:
    """实例运行错误"""
    name: str               # 实例名
    tag: str = ""           # 实例 tag
    error: str = ""         # 错误信息


@dataclass
class InstanceHealthChangedPayload:
    """实例健康状态变化"""
    name: str               # 实例名
    tag: str = ""           # 实例 tag
    healthy: bool = True    # 是否健康


# ═══════════════════════════ 插件域 Payload（10）═══════════════════════════


@dataclass
class PluginLoadedPayload:
    """插件加载成功"""
    name: str               # 插件名


@dataclass
class PluginUnloadedPayload:
    """插件卸载"""
    name: str               # 插件名


@dataclass
class PluginEnabledPayload:
    """插件被启用"""
    name: str               # 插件名


@dataclass
class PluginDisabledPayload:
    """插件被禁用"""
    name: str               # 插件名


@dataclass
class PluginErrorPayload:
    """插件运行错误"""
    name: str               # 插件名
    error: str = ""         # 错误信息


@dataclass
class PluginInstalledPayload:
    """插件安装"""
    name: str               # 插件名
    version: str = ""       # 安装版本


@dataclass
class PluginUninstalledPayload:
    """插件卸载移除"""
    name: str               # 插件名


@dataclass
class PluginUpdatedPayload:
    """插件更新"""
    name: str               # 插件名
    old_version: str = ""   # 旧版本
    new_version: str = ""   # 新版本


@dataclass
class PluginConfigChangedPayload:
    """插件配置变更"""
    name: str               # 插件名
    key: str = ""           # 变更的配置键
    old: Any = None         # 旧值
    new: Any = None         # 新值


@dataclass
class PluginDependencyInstalledPayload:
    """插件依赖安装"""
    name: str               # 插件名
    dependency: str = ""    # 依赖名


# ═══════════════════════════ 通知域 Payload（4）═══════════════════════════


@dataclass
class SystemAnnouncementPayload:
    """系统公告推送"""
    level: str = "info"     # 等级（info/warning/error）
    title: str = ""         # 公告标题
    content: str = ""       # 公告内容
    targets: List[str] = field(default_factory=list)  # 目标用户/群（空=全员）


@dataclass
class SystemMaintenancePayload:
    """系统维护计划"""
    start_at: str = ""      # 开始时间
    end_at: str = ""        # 结束时间
    reason: str = ""        # 维护原因


@dataclass
class SystemUpdateAvailablePayload:
    """有新版本可用"""
    current: str = ""       # 当前版本
    new: str = ""           # 新版本
    changelog: str = ""     # 更新说明


@dataclass
class SystemAlertPayload:
    """系统告警"""
    level: str = "info"     # 告警等级
    source: str = ""        # 告警来源
    message: str = ""       # 告警内容
    detail: str = ""        # 详细上下文


# ═══════════════════════════ 系统域 Payload（5）═══════════════════════════


@dataclass
class SystemStartupPayload:
    """框架启动完成"""
    version: str = ""       # 框架版本


@dataclass
class SystemShutdownPayload:
    """框架开始关闭"""
    reason: str = ""        # 关闭原因


@dataclass
class SystemRestartingPayload:
    """框架重启中"""
    reason: str = ""        # 重启原因


@dataclass
class SystemConfigChangedPayload:
    """框架配置变更"""
    key: str                # 变更的配置键
    old: Any = None         # 旧值
    new: Any = None         # 新值


@dataclass
class SystemAdminChangedPayload:
    """管理员名单变动"""
    operator: str = ""      # 操作者
    action: str = ""        # add/remove
    target: str = ""        # 目标用户 ID
    role: str = ""          # 涉及的角色


# ═══════════════════════════ 用户域 Payload（3）═══════════════════════════


@dataclass
class UserBlacklistedPayload:
    """用户被拉黑"""
    user: str               # 被拉黑用户 ID
    operator: str = ""      # 操作者


@dataclass
class UserUnblacklistedPayload:
    """用户被移出黑名单"""
    user: str               # 被移出用户 ID
    operator: str = ""      # 操作者


@dataclass
class UserPermissionChangedPayload:
    """用户权限变更"""
    user: str               # 变更用户 ID
    operator: str = ""      # 操作者
    old_role: str = ""      # 旧角色
    new_role: str = ""      # 新角色


# ═══════════════════════════ AI 域 Payload（21）═══════════════════════════


@dataclass
class AiProviderLoadedPayload:
    """AI 提供方加载"""
    provider: str = ""      # 提供方名


@dataclass
class AiProviderErrorPayload:
    """AI 提供方出错"""
    provider: str = ""      # 提供方名
    error: str = ""         # 错误信息


@dataclass
class AiProviderRemovedPayload:
    """AI 提供方移除"""
    provider: str = ""      # 提供方名


@dataclass
class AiRequestStartedPayload:
    """AI 请求开始"""
    request_id: str = ""    # 请求 ID
    provider: str = ""      # 提供方名
    model: str = ""         # 模型名


@dataclass
class AiRequestCompletedPayload:
    """AI 请求完成"""
    request_id: str = ""    # 请求 ID
    provider: str = ""      # 提供方名
    model: str = ""         # 模型名
    duration_ms: int = 0    # 耗时（毫秒）


@dataclass
class AiRequestFailedPayload:
    """AI 请求失败"""
    request_id: str = ""    # 请求 ID
    provider: str = ""      # 提供方名
    error: str = ""         # 错误信息


@dataclass
class AiRequestTimeoutPayload:
    """AI 请求超时"""
    request_id: str = ""    # 请求 ID
    provider: str = ""      # 提供方名
    timeout: float = 0.0    # 超时阈值（秒）


@dataclass
class AiSessionCreatedPayload:
    """AI 会话创建"""
    session_id: str = ""    # 会话 ID


@dataclass
class AiSessionClosedPayload:
    """AI 会话关闭"""
    session_id: str = ""    # 会话 ID


@dataclass
class AiSessionResetPayload:
    """AI 会话重置"""
    session_id: str = ""    # 会话 ID


@dataclass
class AiMemoryUpdatedPayload:
    """AI 记忆更新"""
    session_id: str = ""    # 会话 ID
    entries: int = 0        # 更新条目数


@dataclass
class AiMemoryFullPayload:
    """AI 记忆已满"""
    session_id: str = ""    # 会话 ID
    total: int = 0          # 记忆总量


@dataclass
class AiContextTruncatedPayload:
    """AI 上下文被截断"""
    session_id: str = ""    # 会话 ID
    removed_chars: int = 0  # 截断字符数


@dataclass
class AiPersonaChangedPayload:
    """AI 人格切换"""
    persona: str = ""       # 新人格名


@dataclass
class AiTokenLowPayload:
    """AI Token 余量不足"""
    provider: str = ""      # 提供方名
    remaining: int = 0      # 剩余 Token
    threshold: int = 0      # 告警阈值


@dataclass
class AiModelSwitchedPayload:
    """AI 模型切换"""
    provider: str = ""      # 提供方名
    model: str = ""         # 新模型名


@dataclass
class AiEmbeddingCompletedPayload:
    """AI 向量化完成"""
    count: int = 0          # 向量化条目数
    duration_ms: int = 0    # 耗时（毫秒）


@dataclass
class AiToolCalledPayload:
    """AI 调用工具"""
    tool: str = ""          # 工具名
    request_id: str = ""    # 关联请求 ID


@dataclass
class AiToolErrorPayload:
    """AI 工具调用出错"""
    tool: str = ""          # 工具名
    request_id: str = ""    # 关联请求 ID
    error: str = ""         # 错误信息


@dataclass
class AiStreamStartedPayload:
    """AI 流式输出开始"""
    request_id: str = ""    # 请求 ID
    provider: str = ""      # 提供方名


@dataclass
class AiStreamEndedPayload:
    """AI 流式输出结束"""
    request_id: str = ""    # 请求 ID
    provider: str = ""      # 提供方名
    duration_ms: int = 0    # 耗时（毫秒）


# ═══════════════════════════ BusinessEvent ═══════════════════════════


@dataclass
class BusinessEvent:
    """业务事件（全广播，按 type 路由到订阅者）

    与消息事件 LoyanEvent 不同：不精准路由到某 Runtime，
    而是广播给所有 biz:{type} 与 biz:* 订阅者。
    订阅者可在处理时调用 cancel() 拦截（如拒绝好友申请），
    后续订阅者将不再被调度。
    """

    type: EventType                    # 事件类型（71 个枚举之一）
    payload: Any                       # 对应事件类型的 Payload（类型安全）
    source: str = ""                   # 来源（"onebot"/"instance_manager"/"brain"）
    adapter_tag: str = ""              # 具体实例 tag（多实例区分）
    timestamp: float = 0.0             # 平台事件时间（秒，0 则发布时自动填充）
    cancelled: bool = False            # 订阅者是否已拦截

    def cancel(self) -> None:
        """拦截此事件，阻止后续订阅者收到"""
        self.cancelled = True


# ═══════════════════════════ validate_payload ═══════════════════════════

# 事件类型 → Payload 类 分发表（覆盖全部 71 个事件类型）
_PAYLOAD_MAP: Dict[EventType, type] = {
    # 消息域（2）
    EventType.MESSAGE_RECEIVED: MessageReceivedPayload,
    EventType.MESSAGE_SENT: MessageSentPayload,
    # 群组域（12）
    EventType.GROUP_MEMBER_JOINED: GroupMemberJoinedPayload,
    EventType.GROUP_MEMBER_LEFT: GroupMemberLeftPayload,
    EventType.GROUP_MEMBER_KICKED: GroupMemberKickedPayload,
    EventType.GROUP_ADMIN_CHANGED: GroupAdminChangedPayload,
    EventType.GROUP_MUTED: GroupMutedPayload,
    EventType.GROUP_UNMUTED: GroupUnmutedPayload,
    EventType.GROUP_MEMBER_MUTED: GroupMemberMutedPayload,
    EventType.GROUP_MEMBER_UNMUTED: GroupMemberUnmutedPayload,
    EventType.GROUP_RECALLED: GroupRecalledPayload,
    EventType.GROUP_FILE_UPLOADED: GroupFileUploadedPayload,
    EventType.GROUP_TITLE_CHANGED: GroupTitleChangedPayload,
    EventType.GROUP_ANNOUNCEMENT_CHANGED: GroupAnnouncementChangedPayload,
    # 好友域（4）
    EventType.FRIEND_REQUEST: FriendRequestPayload,
    EventType.FRIEND_ADDED: FriendAddedPayload,
    EventType.FRIEND_DELETED: FriendDeletedPayload,
    EventType.FRIEND_RECALLED: FriendRecalledPayload,
    # 平台域（5）
    EventType.PLATFORM_CONNECTED: PlatformConnectedPayload,
    EventType.PLATFORM_DISCONNECTED: PlatformDisconnectedPayload,
    EventType.PLATFORM_RECONNECTING: PlatformReconnectingPayload,
    EventType.PLATFORM_ERROR: PlatformErrorPayload,
    EventType.PLATFORM_BANNED: PlatformBannedPayload,
    # 实例域（5）
    EventType.INSTANCE_STARTED: InstanceStartedPayload,
    EventType.INSTANCE_STOPPED: InstanceStoppedPayload,
    EventType.INSTANCE_RELOADED: InstanceReloadedPayload,
    EventType.INSTANCE_ERROR: InstanceErrorPayload,
    EventType.INSTANCE_HEALTH_CHANGED: InstanceHealthChangedPayload,
    # 插件域（10）
    EventType.PLUGIN_LOADED: PluginLoadedPayload,
    EventType.PLUGIN_UNLOADED: PluginUnloadedPayload,
    EventType.PLUGIN_ENABLED: PluginEnabledPayload,
    EventType.PLUGIN_DISABLED: PluginDisabledPayload,
    EventType.PLUGIN_ERROR: PluginErrorPayload,
    EventType.PLUGIN_INSTALLED: PluginInstalledPayload,
    EventType.PLUGIN_UNINSTALLED: PluginUninstalledPayload,
    EventType.PLUGIN_UPDATED: PluginUpdatedPayload,
    EventType.PLUGIN_CONFIG_CHANGED: PluginConfigChangedPayload,
    EventType.PLUGIN_DEPENDENCY_INSTALLED: PluginDependencyInstalledPayload,
    # 通知域（4）
    EventType.SYSTEM_ANNOUNCEMENT: SystemAnnouncementPayload,
    EventType.SYSTEM_MAINTENANCE: SystemMaintenancePayload,
    EventType.SYSTEM_UPDATE_AVAILABLE: SystemUpdateAvailablePayload,
    EventType.SYSTEM_ALERT: SystemAlertPayload,
    # 系统域（5）
    EventType.SYSTEM_STARTUP: SystemStartupPayload,
    EventType.SYSTEM_SHUTDOWN: SystemShutdownPayload,
    EventType.SYSTEM_RESTARTING: SystemRestartingPayload,
    EventType.SYSTEM_CONFIG_CHANGED: SystemConfigChangedPayload,
    EventType.SYSTEM_ADMIN_CHANGED: SystemAdminChangedPayload,
    # 用户域（3）
    EventType.USER_BLACKLISTED: UserBlacklistedPayload,
    EventType.USER_UNBLACKLISTED: UserUnblacklistedPayload,
    EventType.USER_PERMISSION_CHANGED: UserPermissionChangedPayload,
    # AI 域（21）
    EventType.AI_PROVIDER_LOADED: AiProviderLoadedPayload,
    EventType.AI_PROVIDER_ERROR: AiProviderErrorPayload,
    EventType.AI_PROVIDER_REMOVED: AiProviderRemovedPayload,
    EventType.AI_REQUEST_STARTED: AiRequestStartedPayload,
    EventType.AI_REQUEST_COMPLETED: AiRequestCompletedPayload,
    EventType.AI_REQUEST_FAILED: AiRequestFailedPayload,
    EventType.AI_REQUEST_TIMEOUT: AiRequestTimeoutPayload,
    EventType.AI_SESSION_CREATED: AiSessionCreatedPayload,
    EventType.AI_SESSION_CLOSED: AiSessionClosedPayload,
    EventType.AI_SESSION_RESET: AiSessionResetPayload,
    EventType.AI_MEMORY_UPDATED: AiMemoryUpdatedPayload,
    EventType.AI_MEMORY_FULL: AiMemoryFullPayload,
    EventType.AI_CONTEXT_TRUNCATED: AiContextTruncatedPayload,
    EventType.AI_PERSONA_CHANGED: AiPersonaChangedPayload,
    EventType.AI_TOKEN_LOW: AiTokenLowPayload,
    EventType.AI_MODEL_SWITCHED: AiModelSwitchedPayload,
    EventType.AI_EMBEDDING_COMPLETED: AiEmbeddingCompletedPayload,
    EventType.AI_TOOL_CALLED: AiToolCalledPayload,
    EventType.AI_TOOL_ERROR: AiToolErrorPayload,
    EventType.AI_STREAM_STARTED: AiStreamStartedPayload,
    EventType.AI_STREAM_ENDED: AiStreamEndedPayload,
}

_MISSING = object()


def validate_payload(event_type: EventType, data: dict) -> Any:
    """按事件类型分发校验，构造对应 Payload

    - 缺必填字段（无默认值的字段未提供）抛 ValueError
    - 字段类型与注解不符抛 ValueError
    - 未知事件类型抛 ValueError

    Args:
        event_type: 事件类型（EventType 枚举）
        data: 原始事件字段 dict

    Returns:
        对应事件类型的 Payload dataclass 实例
    """
    cls = _PAYLOAD_MAP.get(event_type)
    if cls is None:
        raise ValueError(f"unknown event type: {event_type}")
    hints = typing.get_type_hints(cls)
    kwargs: Dict[str, Any] = {}
    for f in dataclasses.fields(cls):
        value = data.get(f.name, _MISSING)
        if value is _MISSING:
            # 无默认值的字段必须提供，否则视为缺必填
            if f.default is dataclasses.MISSING and f.default_factory is dataclasses.MISSING:
                raise ValueError(
                    f"missing required field '{f.name}' for event '{event_type.value}'"
                )
            continue
        expected = hints.get(f.name, Any)
        if expected is not Any and not isinstance(value, expected):
            raise ValueError(
                f"field '{f.name}' of event '{event_type.value}' expects "
                f"{getattr(expected, '__name__', expected)}, got {type(value).__name__}"
            )
        kwargs[f.name] = value
    return cls(**kwargs)


__all__ = [
    "EventType",
    "BusinessEvent",
    "MessageReceivedPayload",
    "MessageSentPayload",
    "GroupMemberJoinedPayload",
    "GroupMemberLeftPayload",
    "GroupMemberKickedPayload",
    "GroupAdminChangedPayload",
    "GroupMutedPayload",
    "GroupUnmutedPayload",
    "GroupMemberMutedPayload",
    "GroupMemberUnmutedPayload",
    "GroupRecalledPayload",
    "GroupFileUploadedPayload",
    "GroupTitleChangedPayload",
    "GroupAnnouncementChangedPayload",
    "FriendRequestPayload",
    "FriendAddedPayload",
    "FriendDeletedPayload",
    "FriendRecalledPayload",
    "PlatformConnectedPayload",
    "PlatformDisconnectedPayload",
    "PlatformReconnectingPayload",
    "PlatformErrorPayload",
    "PlatformBannedPayload",
    "InstanceStartedPayload",
    "InstanceStoppedPayload",
    "InstanceReloadedPayload",
    "InstanceErrorPayload",
    "InstanceHealthChangedPayload",
    "PluginLoadedPayload",
    "PluginUnloadedPayload",
    "PluginEnabledPayload",
    "PluginDisabledPayload",
    "PluginErrorPayload",
    "PluginInstalledPayload",
    "PluginUninstalledPayload",
    "PluginUpdatedPayload",
    "PluginConfigChangedPayload",
    "PluginDependencyInstalledPayload",
    "SystemAnnouncementPayload",
    "SystemMaintenancePayload",
    "SystemUpdateAvailablePayload",
    "SystemAlertPayload",
    "SystemStartupPayload",
    "SystemShutdownPayload",
    "SystemRestartingPayload",
    "SystemConfigChangedPayload",
    "SystemAdminChangedPayload",
    "UserBlacklistedPayload",
    "UserUnblacklistedPayload",
    "UserPermissionChangedPayload",
    "AiProviderLoadedPayload",
    "AiProviderErrorPayload",
    "AiProviderRemovedPayload",
    "AiRequestStartedPayload",
    "AiRequestCompletedPayload",
    "AiRequestFailedPayload",
    "AiRequestTimeoutPayload",
    "AiSessionCreatedPayload",
    "AiSessionClosedPayload",
    "AiSessionResetPayload",
    "AiMemoryUpdatedPayload",
    "AiMemoryFullPayload",
    "AiContextTruncatedPayload",
    "AiPersonaChangedPayload",
    "AiTokenLowPayload",
    "AiModelSwitchedPayload",
    "AiEmbeddingCompletedPayload",
    "AiToolCalledPayload",
    "AiToolErrorPayload",
    "AiStreamStartedPayload",
    "AiStreamEndedPayload",
    "validate_payload",
]
