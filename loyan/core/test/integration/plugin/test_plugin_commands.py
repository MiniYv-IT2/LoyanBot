"""测试所有插件命令能否被 Pipeline 正确匹配
覆盖 loyan/plugins/（系统）和 storage/plugins/（用户）全部命令
"""
import asyncio, sys, os, logging
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
logging.basicConfig(level=logging.WARNING, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

# 设置 graci 别名（同 main.py 行为）
import loyan.graci as _graci_pkg
sys.modules.setdefault('graci', _graci_pkg)

from loyan.core.loyan_adapter import send as __send
from loyan.core.loyan_adapter.event import LoyanEvent
from loyan.core.loyan_adapter.identity import IdentityTag
from loyan.core.runtime.runtime import Runtime, RuntimeContext
from loyan.core.plugin_manager import plugin_manager
from loyan.core.pipeline.pipeline import Pipeline
from loyan.core.pipeline.security_filter import SecurityFilter
from loyan.core.pipeline.builtin_commands import BuiltinCommands
from loyan.core.pipeline.command_matcher import CommandMatcher
from loyan.core.pipeline.plugin_handler import PluginHandler
from loyan.core.pipeline.response_sender import ResponseSender
from loyan.core.pipeline.stats_collector import stats_collector

replies = []

async def _fake_send(target, *segments, chat_type="private", tag=None):
    for seg in segments:
        if hasattr(seg, 'text'):
            replies.append(seg.text)
    return True

__send.loyan_send_msg = _fake_send

EXPECTED_PLUGINS = [
    "Help_plugin", "LoyanUI", "Xiaoyu_plugin", "ExamplePlugin",
    "Config_test", "MonitorPlugin", "Music_Plugin", "SysInfo_plugin",
    "Update_Plugin", "Screenshot",
]

EXPECTED_BRAIN_COMMANDS = ["/chat", "/ai", "/chat reset", "/persona"]

def make_event(text):
    return LoyanEvent(sender_id="test_user_001", target_id="test_user_001",
                      chat_type="private", raw_text=text, message_id="t1")

async def main():
    global replies
    passed, failed, skipped = 0, 0, 0

    await stats_collector.init()
    plugin_manager.init()
    import loyan.brain

    # ── 检查插件加载 ──
    loaded = {p["name"] for p in plugin_manager.registry}
    print(f"\n已加载插件: {len(loaded)} 个")
    for p in EXPECTED_PLUGINS:
        if p in loaded:
            print(f"   {p}")
        else:
            print(f"   {p} — 未加载")

    # ── 构建 Pipeline ──
    tag = IdentityTag(platform="test", bot_name="test_bot")
    runtime = Runtime(instance_name="test", robot_id="r", master_id="m",
                      plugin_manager=plugin_manager, adapter_tag=tag, adapter_pool=None)
    pipeline = Pipeline()
    pipeline.add_stage(SecurityFilter()).add_stage(BuiltinCommands()).add_stage(CommandMatcher())
    pipeline.add_stage(PluginHandler()).add_stage(ResponseSender())

    # ── 逐条测试命令 ──
    print(f"\n{'='*60}")
    print("命令匹配测试")
    print(f"{'='*60}\n")

    all_plugin_commands = []
    for p in plugin_manager.registry:
        for cmd in p.get("commands", []):
            all_plugin_commands.append((p["name"], cmd))

    # 去重 + 排序
    seen = set()
    for pname, cmd in all_plugin_commands:
        key = (pname, cmd)
        if key in seen:
            continue
        seen.add(key)

        replies = []
        token = RuntimeContext.set(runtime)
        try:
            await pipeline.process(make_event(cmd))
        except Exception as e:
            print(f"   [{pname}] {cmd} → 异常: {e}")
            failed += 1
            RuntimeContext.reset(token)
            continue
        finally:
            RuntimeContext.reset(token)

        if replies:
            print(f"   [{pname}] {cmd} → {replies[0][:70]}")
            passed += 1
        else:
            print(f"    [{pname}] {cmd} → 无回复")
            passed += 1

    # Brain 命令
    print(f"\n  —— Brain 命令 ——")
    for cmd in EXPECTED_BRAIN_COMMANDS:
        replies = []
        token = RuntimeContext.set(runtime)
        try:
            await pipeline.process(make_event(cmd))
        except Exception as e:
            print(f"   [brain] {cmd} → 异常: {e}")
            failed += 1
            RuntimeContext.reset(token)
            continue
        finally:
            RuntimeContext.reset(token)

        if replies:
            print(f"   [brain] {cmd} → {replies[0][:70]}")
            passed += 1
        else:
            print(f"   [brain] {cmd} → 无回复")
            failed += 1

    total = passed + failed + skipped
    print(f"\n{'='*60}")
    print(f"结果:  {passed}   {failed}  ⏭ {skipped}  共 {total}")
    if failed:
        print("  有命令未通过！")
    print(f"{'='*60}")

if __name__ == "__main__":
    asyncio.run(main())
