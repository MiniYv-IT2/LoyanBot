"""帮助插件单元测试"""
import os
import pytest
from unittest.mock import MagicMock, patch


class TestLoyanBotHelpDrawer:
    """帮助图绘制器测试"""
    
    def test_parse_single_command_list(self):
        """测试命令解析"""
        from loyan.builtin.modules.help import LoyanBotHelpDrawer
        
        text = """/help : 显示帮助
/chat : 与AI对话"""
        result = LoyanBotHelpDrawer._parse_single_command_list(text)
        assert len(result) == 2
        assert result[0] == ("/help", "显示帮助")
        assert result[1] == ("/chat", "与AI对话")
    
    def test_parse_command_with_hash(self):
        """测试#分隔符解析"""
        from loyan.builtin.modules.help import LoyanBotHelpDrawer
        
        text = "/command # 描述"
        result = LoyanBotHelpDrawer._parse_single_command_list(text)
        assert result[0][0] == "/command"
        assert result[0][1] == "描述"
    
    def test_font_path_exists(self):
        """测试字体路径"""
        from loyan.builtin.modules.help import _FONT_PATH
        assert os.path.exists(_FONT_PATH), f"字体文件不存在: {_FONT_PATH}"
    
    def test_logo_path_exists(self):
        """测试logo路径"""
        from loyan.builtin.modules.help import _LOGO_PATH
        assert os.path.exists(_LOGO_PATH), f"Logo文件不存在: {_LOGO_PATH}"
    
    def test_drawer_creation(self):
        """测试绘图器创建"""
        from loyan.builtin.modules.help import _get_drawer
        
        drawer = _get_drawer()
        assert drawer is not None
        assert hasattr(drawer, 'draw_help_image')
    
    def test_draw_help_image_output(self):
        """测试图片生成输出"""
        from loyan.builtin.modules.help import _get_drawer
        
        drawer = _get_drawer()
        test_data = {"TestPlugin": ["/cmd1#描述1", "/cmd2#描述2"]}
        image_data = drawer.draw_help_image(test_data)
        
        assert isinstance(image_data, bytes)
        assert len(image_data) > 0
        assert image_data[:8] == b'\x89PNG\r\n\x1a\n'


class TestHelpCommandLogic:
    """帮助命令逻辑测试"""
    
    def test_collect_plugin_commands(self):
        """测试收集插件命令逻辑"""
        import collections
        
        mock_plugin = {
            "name": "test_plugin",
            "description": "测试插件",
            "commands": ["/cmd1", "/cmd2"],
            "command_descriptions": {"/cmd1": "命令1描述", "/cmd2": "命令2描述"}
        }
        
        plugin_commands = collections.defaultdict(list)
        for plugin in [mock_plugin]:
            name = plugin.get("name", "未知插件")
            if name == "帮助插件":
                continue
            desc = plugin.get("description", "")
            cmd_descs = plugin.get("command_descriptions", {})
            for cmd in plugin.get("commands", []):
                cmd_desc = cmd_descs.get(cmd, "") or desc
                plugin_commands[name].append(f"{cmd}#{cmd_desc}" if cmd_desc else cmd)
        
        assert "test_plugin" in plugin_commands
        assert len(plugin_commands["test_plugin"]) == 2
