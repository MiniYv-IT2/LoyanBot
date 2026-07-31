import json
import logging
import os
from typing import Optional

_logger = logging.getLogger("Adapter.Telegram.bind")


class AdminBinding:
    def __init__(self, config_path: str = ""):
        self._admin_ids: list = []
        self._owner_id: str = ""
        self._config_path = config_path
        self._whitelist: set = set()
        self._blacklist: set = set()

    @property
    def admin_ids(self) -> list:
        return self._admin_ids

    @property
    def owner_id(self) -> str:
        return self._owner_id

    def load(self) -> list:
        if not self._config_path or not os.path.exists(self._config_path):
            return []
        try:
            with open(self._config_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            self._owner_id = str(cfg.get("master_id", cfg.get("owner_id", "")))
            self._admin_ids = cfg.get("admins_id", [])
            self._whitelist = set(str(x) for x in cfg.get("whitelist", []))
            self._blacklist = set(str(x) for x in cfg.get("blacklist", []))
            return self._admin_ids
        except Exception:
            return []

    def save(self) -> None:
        if not self._config_path:
            return
        try:
            cfg = {}
            if os.path.exists(self._config_path):
                with open(self._config_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
            cfg["admins_id"] = self._admin_ids
            cfg["owner_id"] = self._owner_id
            cfg["whitelist"] = list(self._whitelist)
            cfg["blacklist"] = list(self._blacklist)
            with open(self._config_path, "w", encoding="utf-8") as f:
                json.dump(cfg, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def is_owner(self, user_id: str) -> bool:
        return self._owner_id == user_id

    def is_admin(self, user_id: str) -> bool:
        return user_id in self._admin_ids or self.is_owner(user_id)

    def add_admin(self, user_id: str) -> bool:
        if user_id in self._admin_ids:
            return False
        self._admin_ids.append(user_id)
        self.save()
        return True

    def remove_admin(self, user_id: str) -> bool:
        if user_id not in self._admin_ids:
            return False
        self._admin_ids.remove(user_id)
        self.save()
        return True

    def set_owner(self, user_id: str) -> None:
        self._owner_id = user_id
        if user_id and user_id not in self._admin_ids:
            self._admin_ids.insert(0, user_id)
        self.save()

    def is_blocked(self, user_id: str) -> bool:
        return user_id in self._blacklist

    def block_user(self, user_id: str) -> bool:
        if user_id in self._blacklist:
            return False
        self._blacklist.add(user_id)
        if user_id in self._whitelist:
            self._whitelist.discard(user_id)
        self.save()
        return True

    def unblock_user(self, user_id: str) -> bool:
        if user_id not in self._blacklist:
            return False
        self._blacklist.discard(user_id)
        self.save()
        return True
