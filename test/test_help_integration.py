"""帮助插件集成测试"""
import os
import pytest


class TestHelpIntegration:
    """帮助插件集成测试"""
    
    def test_generated_image_in_storage(self):
        """测试生成的图片在storage中"""
        alt_paths = [
            "/loyan/storage/data/plugins/builtin/temp_help.png",
            "/opt/LoyanBot/storage/data/plugins/builtin/temp_help.png",
        ]
        
        found = False
        for p in alt_paths:
            if os.path.exists(p):
                size = os.path.getsize(p)
                assert size > 0, f"图片为空: {p}"
                print(f"✅ 找到生成的图片: {p} ({size} bytes)")
                found = True
                break
        
        assert found, "未找到生成的图片"
    
    def test_drawer_can_generate_image(self):
        """测试绘图器能生成有效图片"""
        from loyan.builtin.modules.help import _get_drawer
        
        drawer = _get_drawer()
        test_data = {
            "builtin": ["/help#显示帮助", "/chat#与AI对话", "/关于#查看信息"]
        }
        image_data = drawer.draw_help_image(test_data)
        
        assert isinstance(image_data, bytes)
        assert len(image_data) > 1000
        assert image_data[:8] == b'\x89PNG\r\n\x1a\n'
        print(f"✅ 图片生成成功，大小: {len(image_data)} bytes")
    
    def test_help_module_imports(self):
        """测试模块能正常导入"""
        from loyan.builtin.modules.help import handle_help, _get_drawer, LoyanBotHelpDrawer
        assert callable(handle_help)
        assert callable(_get_drawer)
        assert callable(LoyanBotHelpDrawer.draw_help_image)
        print(f"✅ 模块导入成功")


class TestAboutAliases:
    """测试/about别名注册"""
    
    def test_about_module_exists(self):
        """测试about模块存在"""
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "about",
            "/root/LoyanBot/loyan/builtin/modules/about.py"
        )
        assert spec is not None
        print(f"✅ about模块存在")
    
    def test_about_register_calls(self):
        """测试about.py中有register_builtin_command调用"""
        with open('/root/LoyanBot/loyan/builtin/modules/about.py', 'r') as f:
            content = f.read()
        
        assert 'register_builtin_command("/关于"' in content, "缺少/关于注册"
        assert 'register_builtin_command("/about"' in content, "缺少/about注册"
        assert 'register_builtin_command("/About"' in content, "缺少/About注册"
        print(f"✅ /about别名注册代码存在")
    
    def test_help_aliases_in_metadata(self):
        """测试metadata.toml中有/help别名"""
        with open('/root/LoyanBot/loyan/builtin/metadata.toml', 'r') as f:
            content = f.read()
        
        assert '"/帮助"' in content, "缺少/帮助"
        assert '"/help"' in content, "缺少/help"
        assert '"/菜单"' in content, "缺少/菜单"
        assert '"/menu"' in content, "缺少/menu"
        assert '"/helps"' in content, "缺少/helps"
        print(f"✅ help别名在metadata.toml中注册")
