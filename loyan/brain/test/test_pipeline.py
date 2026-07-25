"""测试 brain 命令 —— 直接构造事件走 Pipeline，捕获回复"""
import asyncio, sys, os, logging
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

replies = []

from loyan.core.loyan_adapter import send as __send
from loyan.core.loyan_adapter.event import LoyanEvent
from loyan.core.loyan_adapter.identity import IdentityTag
from loyan.core.runtime.runtime import Runtime, RuntimeContext
from loyan.core.plugin_manager import plugin_manager
from loyan.brain import get_brain
from loyan.brain.chat.persona import persona_mgr
from loyan.core.pipeline.pipeline import Pipeline
from loyan.core.pipeline.security_filter import SecurityFilter
from loyan.core.pipeline.builtin_commands import BuiltinCommands
from loyan.core.pipeline.command_matcher import CommandMatcher
from loyan.core.pipeline.plugin_handler import PluginHandler
from loyan.core.pipeline.response_sender import ResponseSender
from loyan.core.pipeline.stats_collector import stats_collector


async def _fake_send(target, *segments, chat_type="private", tag=None):
    for seg in segments:
        if hasattr(seg, 'text'):
            replies.append(seg.text)
    return True


__send.loyan_send_msg = _fake_send


def make_event(text):
    return LoyanEvent(sender_id="test_user_001", target_id="test_user_001",
                      chat_type="private", raw_text=text, message_id="t1")


async def main():
    global replies
    await stats_collector.init()
    await persona_mgr.init()
    plugin_manager.init()

    # plugin_manager.init() 清空了 DECORATOR_COMMAND_REGISTRY
    # 但 test_registry.py 已确保 brain 命令不会因此丢失
    brain = get_brain()
    await brain.start()

    tag = IdentityTag(platform="test", bot_name="test_bot")
    runtime = Runtime(instance_name="test", robot_id="r", master_id="m",
                      plugin_manager=plugin_manager, adapter_tag=tag, adapter_pool=None)
    pipeline = Pipeline()
    pipeline.add_stage(SecurityFilter()).add_stage(BuiltinCommands()).add_stage(CommandMatcher())
    pipeline.add_stage(PluginHandler()).add_stage(ResponseSender())

    for cmd in ["/persona", "/chat 测试", "/about", "/chat reset"]:
        replies = []
        print(f"\n>>> {cmd}")
        token = RuntimeContext.set(runtime)
        try:
            await pipeline.process(make_event(cmd))
        except Exception as e:
            print(f"  !! {e}")
        finally:
            RuntimeContext.reset(token)
        if replies:
            for r in replies:
                print(f"  << {r[:120]}")
        else:
            print("  << (空)")
    print("\n✅ 测试完成")


if __name__ == "__main__":
    asyncio.run(main())
