"""Skill 基类定义"""
from dataclasses import dataclass, field
from typing import Callable, Dict, Any, List, Optional
from loyan.core.decorators.context import PluginContext


@dataclass
class Skill:
    """Skill 基础类"""
    name: str
    display_name: str
    description: str
    commands: List[str] = field(default_factory=list)
    permission: str = "all"
    chat_type: List[str] = field(default_factory=lambda: ["private", "group"])
    handler: Optional[Callable] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def check_permission(self, ctx: PluginContext) -> bool:
        """检查权限"""
        from loyan.core.pipeline.helpers import is_master, is_admin
        if self.permission == "all":
            return True
        if self.permission == "master":
            return is_master(ctx)
        if self.permission == "admin":
            return is_admin(ctx)
        return False
    
    async def execute(self, ctx: PluginContext) -> Optional[PluginContext]:
        """执行 Skill"""
        if not self.check_permission(ctx):
            return ctx
        if self.handler:
            await self.handler(ctx)
        return ctx
