"""Stage: CommandMatcher — TOML + @on_command / @on_regex 命令匹配"""

import asyncio
import logging
import re
from typing import Optional

from loyan.core.pipeline import Stage
from loyan.core.decorators.context import PluginContext
from loyan.core.pipeline.helpers import is_master

_logger = logging.getLogger("Core.Pipeline")


class CommandMatcher(Stage):
    """命令匹配器

    职责:
        - 遍历 PLUGIN_REGISTRY 匹配 TOML commands
        - 遍历 DECORATOR_COMMAND_REGISTRY 匹配 @on_command
        - 匹配结果写入 ctx.matched_command / ctx.matched_plugin
    """

    async def process(self, ctx: PluginContext) -> Optional[PluginContext]:
        raw_msg = ctx.raw_text.strip()
        if not raw_msg:
            return ctx

        # ── 路径 A: TOML 命令匹配（并行过滤 + 优先级选胜者） ──
        from loyan.core.plugin_manager import plugin_manager

        prefix, aliases = self._cmd_config(ctx)

        async def _check_plugin(plugin: dict) -> Optional[dict]:
            matched = self._match_any(
                plugin.get("commands", []), raw_msg,
                prefix=prefix, aliases=aliases, plugin_name=plugin.get("name", ""),
            )
            if not matched:
                return None
            matched_cmd, hit = matched
            if ctx.chat_type not in plugin.get("chat_type", ["private", "group"]):
                return None
            if plugin.get("permission") == "master":
                if not is_master(ctx, plugin):
                    return None
            if ctx.chat_type == "group" and plugin.get("is_at_required", False) and not ctx.is_at_bot:
                return None
            return {"plugin": plugin, "matched_cmd": matched_cmd, "hit": hit, "priority": plugin.get("priority", 50)}

        tasks = [_check_plugin(p) for p in plugin_manager.registry]
        results = await asyncio.gather(*tasks)
        matches = [r for r in results if r is not None]
        if matches:
            matches.sort(key=lambda x: x["priority"], reverse=True)
            best = matches[0]
            plugin = best["plugin"]
            ctx.command = best["matched_cmd"]
            self._normalize_command(ctx, ctx.command, best["hit"])
            ctx.plugin_name = plugin["name"]
            ctx.extra["priority"] = best["priority"]
            ctx.extra["handler_func"] = plugin.get("command_handlers", {}).get(ctx.command) or plugin.get("handler_func")
            ctx.extra["_match_source"] = "toml"
            _logger.debug(f"[CommandMatcher] TOML 并行匹配: {plugin['name']} → {best['matched_cmd']} (priority={best['priority']})")
            return ctx

        # ── 路径 B: @on_command / @on_regex 装饰器匹配 ──
        from loyan.core.decorators.registration import DECORATOR_COMMAND_REGISTRY

        for entry in DECORATOR_COMMAND_REGISTRY:
            commands = entry.get("commands", [])
            matched = self._match_any(
                commands, raw_msg,
                prefix=prefix, aliases=aliases, plugin_name=entry.get("plugin_name", ""),
            )
            if matched:
                matched_cmd, hit = matched
                e_ct = entry.get("chat_type", ["private", "group"])
                if ctx.chat_type not in e_ct:
                    continue
                ctx.command = matched_cmd
                self._normalize_command(ctx, ctx.command, hit)
                ctx.plugin_name = entry.get("plugin_name", "decorator")
                ctx.extra["handler_func"] = entry["handler_func"]
                ctx.extra["_match_source"] = "decorator"
                _logger.debug(f"[CommandMatcher] 装饰器匹配: {ctx.plugin_name} → {matched_cmd}")
                return ctx

            patterns = entry.get("patterns", [])
            for pattern_str, compiled in patterns:
                m = compiled.search(raw_msg)
                if m:
                    e_ct = entry.get("chat_type", ["private", "group"])
                    if ctx.chat_type not in e_ct:
                        continue
                    ctx.command = f"regex:{pattern_str}"
                    ctx.plugin_name = entry.get("plugin_name", "decorator")
                    ctx.extra["handler_func"] = entry["handler_func"]
                    ctx.extra["_match_source"] = "decorator"
                    ctx.extra["_regex_match"] = m
                    _logger.debug(f"[CommandMatcher] 正则匹配: {ctx.plugin_name} → {pattern_str}")
                    return ctx

        ctx.extra["_match_source"] = "none"
        return ctx

    def _match_any(self, commands: list, raw_msg: str, prefix: str = "",
                   aliases: dict | None = None, plugin_name: str = "") -> Optional[tuple]:
        """匹配命令列表，返回 (原命令, 实际命中形态)

        候选生成：原命令 + 前缀替换版（/ 开头命令）+ 插件别名映射。
        命中候选时返回原命令（handler 表按原命令索引）与命中形态
        （供调用方把 raw_text 归一化为原命令形态，保证插件
        raw_text.replace(ctx.command) 参数提取始终成立）。
        """
        matched = []
        for cmd in commands:
            variants = []
            if cmd.startswith("/"):
                if prefix and prefix != "/":
                    variants.append(prefix + cmd[1:])
                else:
                    variants.append(cmd)
            else:
                variants.append(cmd)
            if aliases and plugin_name:
                variants.extend(aliases.get(plugin_name, {}).get(cmd, []) or [])
            for v in variants:
                if v == "//":
                    if re.search(r'(?:^|\s)//', raw_msg):
                        matched.append((cmd, v))
                        break
                elif raw_msg == v or raw_msg.startswith(v + " ") or raw_msg.startswith(v + "\n"):
                    matched.append((cmd, v))
                    break
        if not matched:
            return None
        return max(matched, key=lambda t: len(t[0]))

    @staticmethod
    def _normalize_command(ctx, matched_cmd: str, hit: str) -> None:
        """把 ctx.raw_text 中命中的命令形态还原为注册名（canonical 归一化）

        前缀替换（#跑图 → /跑图）或别名命中时，插件按
        raw_text.replace(ctx.command) 提取参数，必须保证
        ctx.command 出现在 raw_text 中。
        """
        if hit and hit != matched_cmd:
            ctx.raw_text = ctx.raw_text.replace(hit, matched_cmd, 1)

    def _cmd_config(self, ctx) -> tuple:
        """当前实例的指令前缀与别名映射（带缓存）"""
        try:
            from loyan.core.config.user_config import get_effective_cached
            instance = getattr(getattr(ctx, "runtime", None), "instance_name", "") or ""
            eff = get_effective_cached(instance)
            return eff.get("command_prefix", "/"), eff.get("command_aliases", {}) or {}
        except Exception:
            return "/", {}
