"""主从绑定管理器 — /master_set /unbind 及状态持久化

职责：
- 绑定/解绑主人 openid
- 状态读写配置文件（持久化）
- 同步运行时 master_id 及 SecurityManager 角色表
"""

import json
import logging
import os
from typing import Optional

_logger = logging.getLogger("Adapter.QQOfficial.bind")


def update_runtime_master_id(openid: str, runtime=None) -> None:
    """更新运行时 master_id，使框架权限校验和审计日志立即可见"""
    # 更新 Runtime 上的 master_id
    if runtime and hasattr(runtime, 'master_id'):
        runtime.master_id = openid
    # 同步更新 SecurityManager 的角色表
    try:
        from loyan.core.security_manager import security_manager, UserRole
        if openid:
            security_manager.user_roles[str(openid)] = UserRole.ADMIN
        else:
            keys_to_remove = [k for k, v in security_manager.user_roles.items() if v == UserRole.ADMIN]
            for k in keys_to_remove:
                security_manager.user_roles.pop(k, None)
    except Exception as e:
        _logger.error(f"更新权限角色失败: {e}", exc_info=True)


class MasterBinding:
    """主从绑定管理器

    用法:
        binding = MasterBinding(config_path="/path/to/config.json")
        binding.load_state()
        if binding.bind(sender_openid):
            ...
        if binding.unbind(sender_openid):
            ...
    """

    def __init__(self, config_path: str = "", runtime=None):
        self._master_openid: str = ""
        self._is_bound: bool = False
        self._config_path = config_path
        self._runtime = runtime

    # ── 属性 ──

    @property
    def master_openid(self) -> str:
        return self._master_openid

    @property
    def is_bound(self) -> bool:
        return self._is_bound

    # ── 状态持久化 ──

    def load_state(self) -> str:
        """从配置文件恢复绑定状态，返回已绑定的 openid（空字符串=未绑定）"""
        if not self._config_path or not os.path.exists(self._config_path):
            return ""
        try:
            with open(self._config_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            admins = cfg.get("admins_id", [])
            master_id = admins[0] if admins else cfg.get("master_id", "")
            if master_id and len(master_id) > 20:
                self._master_openid = master_id
                self._is_bound = True
                update_runtime_master_id(master_id, self._runtime)
                _logger.info(f"已恢复绑定: master_openid={master_id[:8]}****")
            else:
                _logger.info("未绑定主人，发送 /master_set 绑定")
            return self._master_openid
        except Exception as e:
            _logger.warning(f"读取绑定状态失败: {e}")
            return ""

    def save_state(self, master_openid: str) -> None:
        """持久化绑定状态到配置文件"""
        if not self._config_path or not os.path.exists(self._config_path):
            return
        try:
            with open(self._config_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            cfg["_master_openid"] = master_openid
            admins = cfg.get("admins_id", [])
            if master_openid not in admins:
                admins.append(master_openid)
            cfg["admins_id"] = admins
            with open(self._config_path, "w", encoding="utf-8") as f:
                json.dump(cfg, f, ensure_ascii=False, indent=2)
        except Exception as e:
            _logger.warning(f"保存绑定状态失败: {e}")

    # ── 绑定 / 解绑 ──

    def bind(self, openid: str) -> bool:
        """绑定主人，返回 True=成功"""
        if self._is_bound:
            return False
        self._master_openid = openid
        self._is_bound = True
        self.save_state(openid)
        update_runtime_master_id(openid, self._runtime)
        _logger.info(f"绑定成功: openid={openid[:8]}****")
        return True

    def unbind(self, openid: str) -> bool:
        """解绑主人（只有当前主人才能解绑），返回 True=成功"""
        if not self._is_bound:
            return False
        if openid != self._master_openid:
            return False
        old_openid = self._master_openid
        self._master_openid = ""
        self._is_bound = False
        self.save_state("")
        update_runtime_master_id("", self._runtime)
        _logger.info(f"解绑成功: old_openid={old_openid[:8]}****")
        return True
